import pytest

from app.engine.kpis import calculate_kpis
from app.engine.variance import analyze_variance, material_variances
from app.models.domain import AccountCategory, FinancialStatement, LineItem, Scenario, Severity


def _stmt(scenario: Scenario, **category_amounts: float) -> FinancialStatement:
    items = [
        LineItem(
            client_id="acme",
            period="2026-06",
            scenario=scenario,
            account=f"{category}-account",
            category=AccountCategory(category),
            amount=amount,
        )
        for category, amount in category_amounts.items()
    ]
    return FinancialStatement(client_id="acme", period="2026-06", scenario=scenario, line_items=items)


def test_variance_flags_high_severity_on_large_miss():
    actual_stmt = _stmt(Scenario.ACTUAL, revenue=800, cogs=300, opex=200)
    budget_stmt = _stmt(Scenario.BUDGET, revenue=1000, cogs=300, opex=200)

    actual_kpis = calculate_kpis(actual_stmt)
    budget_kpis = calculate_kpis(budget_stmt)

    results = analyze_variance(actual_kpis, budget_kpis, actual_stmt, budget_stmt)
    revenue_variance = next(r for r in results if r.kpi_name == "Revenue")

    assert revenue_variance.delta == -200
    assert revenue_variance.delta_pct == -20.0
    assert revenue_variance.severity == Severity.HIGH
    assert "Revenue" in revenue_variance.narrative


def test_variance_rejects_mismatched_client_or_period():
    stmt_a = _stmt(Scenario.ACTUAL, revenue=100)
    stmt_b = FinancialStatement(
        client_id="other-client", period="2026-06", scenario=Scenario.BUDGET,
        line_items=[LineItem(client_id="other-client", period="2026-06", scenario=Scenario.BUDGET,
                              account="x", category=AccountCategory.REVENUE, amount=100)],
    )
    kpis_a = calculate_kpis(stmt_a)
    kpis_b = calculate_kpis(stmt_b)

    with pytest.raises(ValueError):
        analyze_variance(kpis_a, kpis_b)


def test_material_variances_filters_low_severity():
    actual_stmt = _stmt(Scenario.ACTUAL, revenue=1000, cogs=300, opex=200)
    budget_stmt = _stmt(Scenario.BUDGET, revenue=1005, cogs=300, opex=200)  # ~0.5% miss -> LOW

    actual_kpis = calculate_kpis(actual_stmt)
    budget_kpis = calculate_kpis(budget_stmt)
    results = analyze_variance(actual_kpis, budget_kpis, actual_stmt, budget_stmt)

    assert all(r.severity == Severity.LOW for r in results if r.kpi_name == "Revenue")
    assert material_variances(results) == [r for r in results if r.severity != Severity.LOW]


def test_driver_phrase_names_top_moving_account():
    actual_stmt = _stmt(Scenario.ACTUAL, revenue=1000)
    actual_stmt.line_items.append(
        LineItem(client_id="acme", period="2026-06", scenario=Scenario.ACTUAL,
                  account="Marketing", category=AccountCategory.OPEX, amount=20000)
    )
    budget_stmt = _stmt(Scenario.BUDGET, revenue=1000)
    budget_stmt.line_items.append(
        LineItem(client_id="acme", period="2026-06", scenario=Scenario.BUDGET,
                  account="Marketing", category=AccountCategory.OPEX, amount=5000)
    )

    actual_kpis = calculate_kpis(actual_stmt)
    budget_kpis = calculate_kpis(budget_stmt)
    results = analyze_variance(actual_kpis, budget_kpis, actual_stmt, budget_stmt)
    opex_variance = next(r for r in results if r.kpi_name == "Opex")

    assert "Marketing" in opex_variance.narrative
