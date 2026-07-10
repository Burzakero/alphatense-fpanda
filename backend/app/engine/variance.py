"""
Variance analysis engine.

Compares an ACTUAL KPISet against a comparison basis (BUDGET or PRIOR period)
and, for each KPI, produces a VarianceResult: the raw delta, the percentage
delta, a severity flag, and a natural-language narrative explaining what
drove the movement -- pulling the top contributing accounts from the
underlying financial statements rather than just restating the number.

This is the "explica desviaciones en lenguaje natural" piece from the
product plan. It's rule-based/templated for the MVP (deterministic, no LLM
call, no latency, no cost) -- a narrative-quality upgrade via an LLM call
can be layered on top later without changing this module's interface, since
callers just consume `.narrative: str`.
"""

from __future__ import annotations

from app.models.domain import (
    AccountCategory,
    FinancialStatement,
    KPISet,
    Scenario,
    Severity,
    VarianceResult,
)

# KPIs we report on, in display order, with a friendly label and which raw
# financial-statement category (if any) best explains a swing in that KPI.
_KPI_FIELDS: list[tuple[str, str, AccountCategory | None]] = [
    ("revenue", "Revenue", AccountCategory.REVENUE),
    ("gross_profit", "Gross Profit", AccountCategory.COGS),
    ("opex", "Opex", AccountCategory.OPEX),
    ("ebitda", "EBITDA", None),
    ("net_income", "Net Income", None),
]

# Materiality thresholds on the absolute percentage delta.
_HIGH_THRESHOLD_PCT = 15.0
_MEDIUM_THRESHOLD_PCT = 7.0


def _severity_for(delta_pct: float | None) -> Severity:
    if delta_pct is None:
        return Severity.MEDIUM
    magnitude = abs(delta_pct)
    if magnitude >= _HIGH_THRESHOLD_PCT:
        return Severity.HIGH
    if magnitude >= _MEDIUM_THRESHOLD_PCT:
        return Severity.MEDIUM
    return Severity.LOW


def _driver_phrase(
    actual_stmt: FinancialStatement | None,
    comparison_stmt: FinancialStatement | None,
    category: AccountCategory | None,
) -> str:
    """Name the account(s) that moved the most within `category`, if we can."""
    if category is None or actual_stmt is None or comparison_stmt is None:
        return ""

    comparison_by_account = {li.account: li.amount for li in comparison_stmt.line_items if li.category == category}
    moves: list[tuple[str, float]] = []
    for li in actual_stmt.line_items:
        if li.category != category:
            continue
        prior_amount = comparison_by_account.get(li.account, 0.0)
        moves.append((li.account, li.amount - prior_amount))

    moves = [m for m in moves if abs(m[1]) > 0.01]
    if not moves:
        return ""

    moves.sort(key=lambda m: abs(m[1]), reverse=True)
    top_account, top_move = moves[0]
    direction = "up" if top_move > 0 else "down"
    return f", driven mainly by {top_account} ({direction} {abs(top_move):,.0f})"


def _narrative_for(
    kpi_label: str,
    actual_value: float,
    comparison_value: float,
    delta: float,
    delta_pct: float | None,
    comparison_scenario: Scenario,
    driver_phrase: str,
) -> str:
    basis = "budget" if comparison_scenario == Scenario.BUDGET else "the prior period"
    direction = "above" if delta > 0 else "below" if delta < 0 else "in line with"

    if delta_pct is None:
        magnitude = f"a change of {delta:,.0f}"
    else:
        magnitude = f"{abs(delta_pct):.1f}% {direction} {basis}"

    return (
        f"{kpi_label} came in at {actual_value:,.0f}, {magnitude} "
        f"({comparison_value:,.0f}){driver_phrase}."
    )


def analyze_variance(
    actual: KPISet,
    comparison: KPISet,
    actual_statement: FinancialStatement | None = None,
    comparison_statement: FinancialStatement | None = None,
) -> list[VarianceResult]:
    """Compare one client-period's ACTUAL KPIs against a BUDGET or PRIOR KPISet.

    Passing the underlying FinancialStatements is optional but recommended:
    without them the narrative still reports the size of the miss, but can't
    name which accounts drove it.
    """
    if actual.client_id != comparison.client_id or actual.period != comparison.period:
        raise ValueError(
            "actual and comparison KPISets must be for the same client and period "
            f"(got {actual.client_id}/{actual.period} vs {comparison.client_id}/{comparison.period})"
        )
    if comparison.scenario not in (Scenario.BUDGET, Scenario.PRIOR):
        raise ValueError("comparison KPISet must have scenario BUDGET or PRIOR")

    results: list[VarianceResult] = []
    for field_name, label, category in _KPI_FIELDS:
        actual_value = getattr(actual, field_name)
        comparison_value = getattr(comparison, field_name)
        delta = round(actual_value - comparison_value, 2)
        delta_pct = None if comparison_value == 0 else round((delta / abs(comparison_value)) * 100, 2)

        driver_phrase = _driver_phrase(actual_statement, comparison_statement, category)
        narrative = _narrative_for(
            label, actual_value, comparison_value, delta, delta_pct, comparison.scenario, driver_phrase
        )

        results.append(
            VarianceResult(
                client_id=actual.client_id,
                period=actual.period,
                kpi_name=label,
                comparison_scenario=comparison.scenario,
                actual_value=actual_value,
                comparison_value=comparison_value,
                delta=delta,
                delta_pct=delta_pct,
                severity=_severity_for(delta_pct),
                narrative=narrative,
            )
        )
    return results


def material_variances(results: list[VarianceResult]) -> list[VarianceResult]:
    """Filter to only medium/high severity variances -- what an exec summary should surface."""
    return [r for r in results if r.severity in (Severity.MEDIUM, Severity.HIGH)]
