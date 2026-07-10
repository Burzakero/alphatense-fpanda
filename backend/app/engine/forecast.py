"""
Forecast AI engine (Phase 2): projects future periods under three scenarios
(best / base / worst) from a client's actual history.

Method (deliberately simple and explainable for the MVP -- no black box):
for each P&L category (revenue, cogs, opex, other income/expense, tax), look
at the period-over-period growth rate across the client's actual history.
The **base case** carries forward the average growth rate. The **best** and
**worst** cases apply that average plus/minus the historical volatility
(standard deviation of those growth rates), so a client with a stable
history gets a tight scenario band and a client with a choppy history
(like a recent revenue miss) gets a wider one -- the spread itself is a
signal, not just decoration.

This intentionally does not call an LLM: it's deterministic, fast, free to
run, and every number traces back to a growth rate the advisor can sanity
check. A narrative-generation upgrade (e.g. asking an LLM to phrase the
assumptions more richly) can wrap this module's output later without
changing how callers use it.
"""

from __future__ import annotations

import re
import statistics

from app.models.domain import (
    AccountCategory,
    FinancialStatement,
    ForecastResult,
    ForecastScenario,
    Scenario,
)

_PERIOD_RE = re.compile(r"^(\d{4})-(\d{2})$")

# How many standard deviations of historical growth volatility separate the
# base case from the best/worst cases.
_VOLATILITY_MULTIPLIER = 1.0

# Categories we project independently before rolling them up into KPIs.
_CATEGORIES = [
    AccountCategory.REVENUE,
    AccountCategory.COGS,
    AccountCategory.OPEX,
    AccountCategory.OTHER_INCOME,
    AccountCategory.OTHER_EXPENSE,
    AccountCategory.TAX,
]


class ForecastError(ValueError):
    """Raised when there isn't enough historical data to build a forecast."""


def next_period_label(period: str, months_ahead: int) -> str:
    """Increment a 'YYYY-MM' period label by N months.

    Falls back to a generic 'period+N' label if the input isn't in that
    format, so the engine still works with non-monthly period labels
    (e.g. '2026-Q2') rather than raising.
    """
    match = _PERIOD_RE.match(period)
    if not match:
        return f"{period}+{months_ahead}"

    year, month = int(match.group(1)), int(match.group(2))
    total_months = (year * 12 + (month - 1)) + months_ahead
    new_year, new_month = divmod(total_months, 12)
    return f"{new_year:04d}-{new_month + 1:02d}"


def _sort_key(period: str) -> tuple:
    match = _PERIOD_RE.match(period)
    if match:
        return (0, int(match.group(1)), int(match.group(2)))
    return (1, period)  # non-standard labels sort after, alphabetically


def _growth_stats(history: list[float]) -> tuple[float, float]:
    """Return (average growth rate, volatility) from a chronological series.

    Growth rate is a fraction (0.05 == 5%). Pairs where the prior value is
    zero are skipped (division by zero has no meaningful growth rate).
    Volatility is the sample standard deviation of the growth rates, or a
    conservative default if there's only one usable growth rate.
    """
    rates = [
        (history[i] - history[i - 1]) / abs(history[i - 1])
        for i in range(1, len(history))
        if history[i - 1] != 0
    ]
    if not rates:
        return 0.0, 0.0
    avg = statistics.mean(rates)
    if len(rates) < 2:
        # Not enough points for a meaningful stdev -- use 50% of the single
        # observed rate's magnitude as a conservative volatility estimate,
        # with a small floor so best/worst don't collapse onto base.
        return avg, max(abs(avg) * 0.5, 0.02)
    return avg, statistics.pstdev(rates)


def _project_series(last_value: float, growth_rate: float, periods_ahead: int) -> list[float]:
    """Compound `last_value` forward by `growth_rate` for `periods_ahead` steps."""
    values = []
    current = last_value
    for _ in range(periods_ahead):
        current = current * (1 + growth_rate)
        values.append(round(current, 2))
    return values


def _safe_pct(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round((numerator / denominator) * 100, 2)


def generate_forecast(
    client_id: str,
    historical_statements: list[FinancialStatement],
    periods_ahead: int = 3,
) -> list[ForecastResult]:
    """Build best/base/worst forecasts for the next `periods_ahead` periods.

    `historical_statements` must all be ACTUAL scenario for the same client,
    covering at least 2 periods (more history gives a more reliable trend).
    Order does not matter -- they're sorted chronologically internally.
    """
    if not historical_statements:
        raise ForecastError(f"No historical statements provided for client '{client_id}'")

    mismatched = [s for s in historical_statements if s.client_id != client_id]
    if mismatched:
        raise ForecastError("All historical statements must belong to the same client_id")

    non_actual = [s for s in historical_statements if s.scenario != Scenario.ACTUAL]
    if non_actual:
        raise ForecastError("Forecasts are built from ACTUAL history only")

    if len(historical_statements) < 2:
        raise ForecastError(
            f"Need at least 2 periods of actual history to project a trend for '{client_id}' "
            f"(got {len(historical_statements)})"
        )

    ordered = sorted(historical_statements, key=lambda s: _sort_key(s.period))
    last_period = ordered[-1].period

    # Compute growth stats per category from the historical totals series.
    stats: dict[AccountCategory, tuple[float, float]] = {}
    last_values: dict[AccountCategory, float] = {}
    for category in _CATEGORIES:
        series = [s.total(category) for s in ordered]
        stats[category] = _growth_stats(series)
        last_values[category] = series[-1]

    scenario_adjustment = {
        ForecastScenario.BEST: _VOLATILITY_MULTIPLIER,
        ForecastScenario.BASE: 0.0,
        ForecastScenario.WORST: -_VOLATILITY_MULTIPLIER,
    }

    results: list[ForecastResult] = []
    for scenario in (ForecastScenario.BEST, ForecastScenario.BASE, ForecastScenario.WORST):
        adj = scenario_adjustment[scenario]

        projected: dict[AccountCategory, list[float]] = {}
        applied_rate: dict[AccountCategory, float] = {}
        for category in _CATEGORIES:
            avg_growth, volatility = stats[category]
            rate = avg_growth + adj * volatility
            applied_rate[category] = rate
            projected[category] = _project_series(last_values[category], rate, periods_ahead)

        for step in range(periods_ahead):
            period_label = next_period_label(last_period, step + 1)

            revenue = projected[AccountCategory.REVENUE][step]
            cogs = projected[AccountCategory.COGS][step]
            opex = projected[AccountCategory.OPEX][step]
            other_income = projected[AccountCategory.OTHER_INCOME][step]
            other_expense = projected[AccountCategory.OTHER_EXPENSE][step]
            tax = projected[AccountCategory.TAX][step]

            gross_profit = round(revenue - cogs, 2)
            ebitda = round(gross_profit - opex, 2)
            net_income = round(ebitda + other_income - other_expense - tax, 2)

            revenue_rate_pct = round(applied_rate[AccountCategory.REVENUE] * 100, 1)
            opex_rate_pct = round(applied_rate[AccountCategory.OPEX] * 100, 1)
            assumptions = (
                f"{scenario.value.capitalize()} case: revenue projected at {revenue_rate_pct:+.1f}%/period "
                f"(trailing {len(ordered)}-period average{' plus' if adj > 0 else ' minus' if adj < 0 else ''}"
                f"{' 1 std-dev of historical volatility' if adj != 0 else ''}), "
                f"opex at {opex_rate_pct:+.1f}%/period, compounded {step + 1} period(s) from {last_period}."
            )

            results.append(
                ForecastResult(
                    client_id=client_id,
                    period=period_label,
                    scenario=scenario,
                    revenue=round(revenue, 2),
                    cogs=round(cogs, 2),
                    gross_profit=gross_profit,
                    gross_margin_pct=_safe_pct(gross_profit, revenue),
                    opex=round(opex, 2),
                    ebitda=ebitda,
                    ebitda_margin_pct=_safe_pct(ebitda, revenue),
                    other_income=round(other_income, 2),
                    other_expense=round(other_expense, 2),
                    tax=round(tax, 2),
                    net_income=net_income,
                    net_margin_pct=_safe_pct(net_income, revenue),
                    assumptions=assumptions,
                )
            )

    return results
