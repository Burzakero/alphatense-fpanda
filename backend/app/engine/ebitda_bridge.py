"""
EBITDA bridge (waterfall) engine.

Walks Budget EBITDA to Actual EBITDA for one client/period, decomposed into
the three category-level deltas that make up the difference: Revenue, COGS,
Opex (the same three totals engine/kpis.py sums to compute EBITDA). This is
the "why did EBITDA move" complement to engine/variance.py's per-KPI
narrative -- variance.py explains each KPI's swing independently, this
module shows how the category swings compose into the EBITDA swing.

Kept pure (no I/O) and takes the two already-loaded FinancialStatements,
same convention as engine/variance.py's analyze_variance -- callers
(Workspace) own fetching actual/budget by client/period.
"""

from __future__ import annotations

from app.models.domain import AccountCategory, EbitdaBridge, EbitdaBridgeStep, FinancialStatement


def _category_totals(statement: FinancialStatement) -> tuple[float, float, float]:
    revenue = statement.total(AccountCategory.REVENUE)
    cogs = statement.total(AccountCategory.COGS)
    opex = statement.total(AccountCategory.OPEX)
    return revenue, cogs, opex


def _narrative_for(
    client_id: str,
    period: str,
    budget_ebitda: float,
    actual_ebitda: float,
    revenue_delta: float,
    cogs_delta: float,
    opex_delta: float,
) -> str:
    total_delta = actual_ebitda - budget_ebitda
    direction = "above" if total_delta > 0 else "below" if total_delta < 0 else "in line with"

    drivers = [("Revenue", revenue_delta), ("COGS", cogs_delta), ("Opex", opex_delta)]
    drivers.sort(key=lambda d: abs(d[1]), reverse=True)
    top_label, top_value = drivers[0]
    driver_direction = "helped" if top_value > 0 else "hurt" if top_value < 0 else "had no effect on"

    return (
        f"{client_id}'s EBITDA of {actual_ebitda:,.0f} in {period} came in "
        f"{abs(total_delta):,.0f} {direction} budget ({budget_ebitda:,.0f}), "
        f"primarily because {top_label} {driver_direction} EBITDA by {abs(top_value):,.0f}."
    )


def calculate_ebitda_bridge(actual: FinancialStatement, budget: FinancialStatement) -> EbitdaBridge:
    """Decompose the Budget -> Actual EBITDA walk for one client/period.

    `actual` and `budget` must be for the same client and period -- pass the
    ACTUAL and BUDGET FinancialStatements for that pair (same validation as
    engine/variance.py's analyze_variance).
    """
    if actual.client_id != budget.client_id or actual.period != budget.period:
        raise ValueError(
            "actual and budget statements must be for the same client and period "
            f"(got {actual.client_id}/{actual.period} vs {budget.client_id}/{budget.period})"
        )

    actual_revenue, actual_cogs, actual_opex = _category_totals(actual)
    budget_revenue, budget_cogs, budget_opex = _category_totals(budget)

    budget_ebitda = round((budget_revenue - budget_cogs) - budget_opex, 2)
    actual_ebitda = round((actual_revenue - actual_cogs) - actual_opex, 2)

    # Revenue up helps EBITDA; COGS/Opex up hurt it -- sign flipped so every
    # step's value is "this category's contribution to the EBITDA delta".
    revenue_delta = round(actual_revenue - budget_revenue, 2)
    cogs_delta = round(-(actual_cogs - budget_cogs), 2)
    opex_delta = round(-(actual_opex - budget_opex), 2)

    steps = [
        EbitdaBridgeStep(label="Budget EBITDA", value=budget_ebitda, is_total=True),
        EbitdaBridgeStep(label="Revenue", value=revenue_delta, is_total=False),
        EbitdaBridgeStep(label="COGS", value=cogs_delta, is_total=False),
        EbitdaBridgeStep(label="Opex", value=opex_delta, is_total=False),
        EbitdaBridgeStep(label="Actual EBITDA", value=actual_ebitda, is_total=True),
    ]

    narrative = _narrative_for(
        actual.client_id, actual.period, budget_ebitda, actual_ebitda, revenue_delta, cogs_delta, opex_delta
    )

    return EbitdaBridge(
        client_id=actual.client_id,
        period=actual.period,
        budget_ebitda=budget_ebitda,
        actual_ebitda=actual_ebitda,
        steps=steps,
        narrative=narrative,
    )
