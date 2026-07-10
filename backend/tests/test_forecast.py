from pathlib import Path

import pytest

from app.engine.forecast import ForecastError, generate_forecast, next_period_label
from app.engine.workspace import Workspace
from app.models.domain import AccountCategory, FinancialStatement, ForecastScenario, LineItem, Scenario

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_financials.csv"


def _stmt(client_id: str, period: str, revenue: float, opex: float = 100) -> FinancialStatement:
    items = [
        LineItem(client_id=client_id, period=period, scenario=Scenario.ACTUAL,
                  account="Sales", category=AccountCategory.REVENUE, amount=revenue),
        LineItem(client_id=client_id, period=period, scenario=Scenario.ACTUAL,
                  account="Overhead", category=AccountCategory.OPEX, amount=opex),
    ]
    return FinancialStatement(client_id=client_id, period=period, scenario=Scenario.ACTUAL, line_items=items)


def test_next_period_label_rolls_over_year():
    assert next_period_label("2026-11", 1) == "2026-12"
    assert next_period_label("2026-12", 1) == "2027-01"
    assert next_period_label("2026-06", 3) == "2026-09"


def test_next_period_label_falls_back_for_non_monthly_labels():
    assert next_period_label("2026-Q2", 1) == "2026-Q2+1"


def test_generate_forecast_requires_at_least_two_periods():
    with pytest.raises(ForecastError, match="at least 2 periods"):
        generate_forecast("acme", [_stmt("acme", "2026-01", 1000)])


def test_generate_forecast_rejects_mixed_clients():
    stmts = [_stmt("acme", "2026-01", 1000), _stmt("other", "2026-02", 1100)]
    with pytest.raises(ForecastError, match="same client_id"):
        generate_forecast("acme", stmts)


def test_generate_forecast_produces_three_scenarios_per_period():
    stmts = [_stmt("acme", f"2026-0{i}", 1000 * (1.05 ** i)) for i in range(1, 5)]
    results = generate_forecast("acme", stmts, periods_ahead=3)

    assert len(results) == 9  # 3 scenarios x 3 periods
    scenarios_seen = {r.scenario for r in results}
    assert scenarios_seen == {ForecastScenario.BEST, ForecastScenario.BASE, ForecastScenario.WORST}

    periods = sorted({r.period for r in results})
    assert periods == ["2026-05", "2026-06", "2026-07"]


def test_growing_history_orders_best_above_base_above_worst():
    """With a consistent upward revenue trend, best case should project
    higher revenue than base, and base higher than worst, for the same
    future period."""
    stmts = [_stmt("acme", f"2026-0{i}", 1000 * (1.08 ** i)) for i in range(1, 6)]
    results = generate_forecast("acme", stmts, periods_ahead=1)

    by_scenario = {r.scenario: r for r in results}
    assert by_scenario[ForecastScenario.BEST].revenue >= by_scenario[ForecastScenario.BASE].revenue
    assert by_scenario[ForecastScenario.BASE].revenue >= by_scenario[ForecastScenario.WORST].revenue


def test_forecast_assumptions_narrative_mentions_scenario_and_source_period():
    stmts = [_stmt("acme", "2026-01", 1000), _stmt("acme", "2026-02", 1100), _stmt("acme", "2026-03", 1210)]
    results = generate_forecast("acme", stmts, periods_ahead=1)

    for r in results:
        assert r.scenario.value.capitalize() in r.assumptions
        assert "2026-03" in r.assumptions


def test_workspace_build_forecast_uses_full_client_history():
    ws = Workspace.from_file(SAMPLE_CSV)
    forecasts = ws.build_forecast("acme-ltd", periods_ahead=2)

    assert len(forecasts) == 6  # 3 scenarios x 2 periods
    periods = sorted({f.period for f in forecasts})
    assert periods == ["2026-07", "2026-08"]

    # Acme's history trends up every month -- base-case revenue for the
    # first forecast period should exceed the last actual (227,000).
    base_next_month = next(f for f in forecasts if f.scenario == ForecastScenario.BASE and f.period == "2026-07")
    assert base_next_month.revenue > 227000


def test_workspace_build_portfolio_forecast_covers_both_clients():
    ws = Workspace.from_file(SAMPLE_CSV)
    portfolio = ws.build_portfolio_forecast(periods_ahead=2)
    assert set(portfolio.keys()) == {"acme-ltd", "beacon-partners"}


def test_unknown_client_raises_forecast_error():
    ws = Workspace.from_file(SAMPLE_CSV)
    with pytest.raises(ForecastError):
        ws.build_forecast("does-not-exist")
