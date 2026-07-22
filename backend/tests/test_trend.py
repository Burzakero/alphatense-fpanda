import pytest

from app.engine.trend import TrendError, build_client_trend
from app.models.domain import AccountCategory, FinancialStatement, LineItem, Scenario


def _stmt(period: str, revenue: float, cogs: float = 100, opex: float = 50) -> FinancialStatement:
    items = [
        LineItem(client_id="acme", period=period, scenario=Scenario.ACTUAL, account="rev",
                  category=AccountCategory.REVENUE, amount=revenue),
        LineItem(client_id="acme", period=period, scenario=Scenario.ACTUAL, account="cogs",
                  category=AccountCategory.COGS, amount=cogs),
        LineItem(client_id="acme", period=period, scenario=Scenario.ACTUAL, account="opex",
                  category=AccountCategory.OPEX, amount=opex),
    ]
    return FinancialStatement(client_id="acme", period=period, scenario=Scenario.ACTUAL, line_items=items)


def test_trend_raises_with_fewer_than_two_periods():
    with pytest.raises(TrendError):
        build_client_trend("acme", [_stmt("2026-06", 1000)])

    with pytest.raises(TrendError):
        build_client_trend("acme", [])


def test_trend_sorts_out_of_order_history():
    history = [_stmt("2026-03", 1200), _stmt("2026-01", 1000), _stmt("2026-02", 1100)]

    trend = build_client_trend("acme", history)

    assert trend.periods == ["2026-01", "2026-02", "2026-03"]
    assert [p.revenue for p in trend.points] == [1000, 1100, 1200]


def test_trend_keeps_only_most_recent_max_periods():
    history = [_stmt(f"2026-{m:02d}", 1000 + m * 10) for m in range(1, 15)]  # 14 periods

    trend = build_client_trend("acme", history, max_periods=12)

    assert len(trend.points) == 12
    assert trend.periods[0] == "2026-03"  # oldest 2 dropped
    assert trend.periods[-1] == "2026-14"


def test_trend_narrative_names_direction_and_endpoints():
    history = [_stmt("2026-01", 1000), _stmt("2026-02", 1500)]

    trend = build_client_trend("acme", history)

    assert "acme" in trend.narrative
    assert "2026-01" in trend.narrative
    assert "2026-02" in trend.narrative
    assert "grew" in trend.narrative
