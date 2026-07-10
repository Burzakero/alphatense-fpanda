"""
KPI calculation engine.

Takes a single FinancialStatement (one client, one period, one scenario) and
rolls its line items up into the standard KPI set an advisor reviews at
close: revenue, gross margin, EBITDA, net income, and the margin percentages
that go with each.

Kept deliberately pure (no I/O, no client-fan-out) so it's trivially unit
testable and reusable regardless of whether the statement came from a CSV
upload or a future Xero/QuickBooks connector.
"""

from __future__ import annotations

from app.models.domain import AccountCategory, FinancialStatement, KPISet


def _safe_pct(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round((numerator / denominator) * 100, 2)


def calculate_kpis(statement: FinancialStatement) -> KPISet:
    """Compute the standard KPI set for a single financial statement."""
    revenue = statement.total(AccountCategory.REVENUE)
    cogs = statement.total(AccountCategory.COGS)
    opex = statement.total(AccountCategory.OPEX)
    other_income = statement.total(AccountCategory.OTHER_INCOME)
    other_expense = statement.total(AccountCategory.OTHER_EXPENSE)
    tax = statement.total(AccountCategory.TAX)

    gross_profit = revenue - cogs
    ebitda = gross_profit - opex
    net_income = ebitda + other_income - other_expense - tax

    return KPISet(
        client_id=statement.client_id,
        period=statement.period,
        scenario=statement.scenario,
        revenue=round(revenue, 2),
        cogs=round(cogs, 2),
        gross_profit=round(gross_profit, 2),
        gross_margin_pct=_safe_pct(gross_profit, revenue),
        opex=round(opex, 2),
        ebitda=round(ebitda, 2),
        ebitda_margin_pct=_safe_pct(ebitda, revenue),
        other_income=round(other_income, 2),
        other_expense=round(other_expense, 2),
        tax=round(tax, 2),
        net_income=round(net_income, 2),
        net_margin_pct=_safe_pct(net_income, revenue),
    )


def calculate_kpis_for_all(statements: list[FinancialStatement]) -> list[KPISet]:
    """Convenience wrapper: calculate KPIs for a batch of statements."""
    return [calculate_kpis(s) for s in statements]
