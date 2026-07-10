from app.engine.kpis import calculate_kpis
from app.models.domain import AccountCategory, FinancialStatement, LineItem, Scenario


def _stmt(**category_amounts: float) -> FinancialStatement:
    """Build a minimal statement with one line item per category given."""
    items = [
        LineItem(
            client_id="test-client",
            period="2026-01",
            scenario=Scenario.ACTUAL,
            account=f"{category}-account",
            category=AccountCategory(category),
            amount=amount,
        )
        for category, amount in category_amounts.items()
    ]
    return FinancialStatement(client_id="test-client", period="2026-01", scenario=Scenario.ACTUAL, line_items=items)


def test_basic_kpi_rollup():
    stmt = _stmt(revenue=1000, cogs=400, opex=300, other_income=50, other_expense=20, tax=30)
    kpis = calculate_kpis(stmt)

    assert kpis.revenue == 1000
    assert kpis.cogs == 400
    assert kpis.gross_profit == 600
    assert kpis.gross_margin_pct == 60.0
    assert kpis.opex == 300
    assert kpis.ebitda == 300
    assert kpis.ebitda_margin_pct == 30.0
    assert kpis.net_income == 300 + 50 - 20 - 30  # 300
    assert kpis.net_margin_pct == 30.0


def test_zero_revenue_margins_are_none_not_error():
    stmt = _stmt(cogs=100, opex=50)
    kpis = calculate_kpis(stmt)

    assert kpis.revenue == 0
    assert kpis.gross_margin_pct is None
    assert kpis.ebitda_margin_pct is None
    assert kpis.net_margin_pct is None


def test_multiple_line_items_same_category_are_summed():
    items = [
        LineItem(
            client_id="c1", period="2026-01", scenario=Scenario.ACTUAL,
            account="Consulting", category=AccountCategory.REVENUE, amount=700,
        ),
        LineItem(
            client_id="c1", period="2026-01", scenario=Scenario.ACTUAL,
            account="Retainers", category=AccountCategory.REVENUE, amount=300,
        ),
    ]
    stmt = FinancialStatement(client_id="c1", period="2026-01", scenario=Scenario.ACTUAL, line_items=items)
    kpis = calculate_kpis(stmt)
    assert kpis.revenue == 1000
