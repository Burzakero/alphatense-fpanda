import pytest

from app.engine.ebitda_bridge import calculate_ebitda_bridge
from app.models.domain import AccountCategory, FinancialStatement, LineItem, Scenario


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


def test_bridge_steps_sum_to_actual_ebitda():
    actual_stmt = _stmt(Scenario.ACTUAL, revenue=1000, cogs=300, opex=200)
    budget_stmt = _stmt(Scenario.BUDGET, revenue=900, cogs=250, opex=180)

    bridge = calculate_ebitda_bridge(actual_stmt, budget_stmt)

    assert bridge.budget_ebitda == 900 - 250 - 180  # 470
    assert bridge.actual_ebitda == 1000 - 300 - 200  # 500
    deltas = {s.label: s.value for s in bridge.steps if not s.is_total}
    assert bridge.budget_ebitda + sum(deltas.values()) == pytest.approx(bridge.actual_ebitda)
    assert deltas["Revenue"] == 100  # revenue up 100 helps EBITDA
    assert deltas["COGS"] == -50  # cogs up 50 hurts EBITDA
    assert deltas["Opex"] == -20  # opex up 20 hurts EBITDA


def test_bridge_narrative_names_the_biggest_driver():
    # Revenue swing (500) dwarfs COGS (10) and Opex (5) -- narrative should name Revenue.
    actual_stmt = _stmt(Scenario.ACTUAL, revenue=1500, cogs=310, opex=205)
    budget_stmt = _stmt(Scenario.BUDGET, revenue=1000, cogs=300, opex=200)

    bridge = calculate_ebitda_bridge(actual_stmt, budget_stmt)

    assert "Revenue" in bridge.narrative
    assert "acme" in bridge.narrative
    assert "2026-06" in bridge.narrative


def test_bridge_rejects_mismatched_client_or_period():
    actual_stmt = _stmt(Scenario.ACTUAL, revenue=1000)
    budget_stmt = FinancialStatement(
        client_id="other-client",
        period="2026-06",
        scenario=Scenario.BUDGET,
        line_items=[
            LineItem(
                client_id="other-client",
                period="2026-06",
                scenario=Scenario.BUDGET,
                account="x",
                category=AccountCategory.REVENUE,
                amount=900,
            )
        ],
    )

    with pytest.raises(ValueError):
        calculate_ebitda_bridge(actual_stmt, budget_stmt)


def test_bridge_handles_zero_delta():
    actual_stmt = _stmt(Scenario.ACTUAL, revenue=1000, cogs=300, opex=200)
    budget_stmt = _stmt(Scenario.BUDGET, revenue=1000, cogs=300, opex=200)

    bridge = calculate_ebitda_bridge(actual_stmt, budget_stmt)

    assert bridge.budget_ebitda == bridge.actual_ebitda == 500
    deltas = [s.value for s in bridge.steps if not s.is_total]
    assert all(d == 0 for d in deltas)
