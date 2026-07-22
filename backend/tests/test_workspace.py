from datetime import date
from pathlib import Path

import pytest

from app.engine.trend import TrendError
from app.engine.workspace import Workspace
from app.ingestion.invoices import load_invoices
from app.models.domain import FinancialStatement, InvoiceType, LineItem, Scenario, Severity, AccountCategory

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_financials.csv"
SAMPLE_INVOICES_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_invoices.csv"


def test_workspace_discovers_all_clients():
    ws = Workspace.from_file(SAMPLE_CSV)
    assert ws.client_ids == ["acme-ltd", "beacon-partners"]


def test_portfolio_report_covers_every_client():
    ws = Workspace.from_file(SAMPLE_CSV)
    reports = ws.build_portfolio_report()

    covered = {r.client_id for r in reports}
    assert covered == {"acme-ltd", "beacon-partners"}
    # 6 historical actual periods (2026-01..2026-06) per client
    assert len([r for r in reports if r.client_id == "acme-ltd"]) == 6
    assert len([r for r in reports if r.client_id == "beacon-partners"]) == 6
    for report in reports:
        assert report.actual_kpis.revenue > 0

    # Only 2026-06 has budget/prior data on file -- variances should be
    # populated there and empty for the other historical months.
    june_reports = [r for r in reports if r.period == "2026-06"]
    assert len(june_reports) == 2
    for report in june_reports:
        assert len(report.variances_vs_budget) > 0
        assert len(report.variances_vs_prior) > 0

    january_reports = [r for r in reports if r.period == "2026-01"]
    for report in january_reports:
        assert report.variances_vs_budget == []
        assert report.variances_vs_prior == []


def test_beacon_revenue_miss_is_material():
    """Beacon Partners actual revenue (113,000) is well below budget (130,000) --
    the plan's whole pitch is surfacing exactly this kind of miss automatically."""
    ws = Workspace.from_file(SAMPLE_CSV)
    report = ws.build_client_report("beacon-partners", "2026-06")
    assert report is not None

    revenue_variance = next(v for v in report.variances_vs_budget if v.kpi_name == "Revenue")
    assert revenue_variance.delta < 0
    assert revenue_variance.severity in (Severity.MEDIUM, Severity.HIGH)


def test_unknown_client_period_returns_none():
    ws = Workspace.from_file(SAMPLE_CSV)
    assert ws.build_client_report("nonexistent", "2026-06") is None


def test_build_aging_report_after_adding_invoices():
    ws = Workspace.from_file(SAMPLE_CSV)
    ws.add_invoices(load_invoices(SAMPLE_INVOICES_CSV))

    report = ws.build_aging_report("beacon-partners", InvoiceType.AR, date(2026, 6, 30))

    assert report is not None
    assert report.client_id == "beacon-partners"
    assert report.total_outstanding > 0


def test_build_aging_report_returns_none_without_invoices():
    ws = Workspace.from_file(SAMPLE_CSV)
    assert ws.build_aging_report("beacon-partners", InvoiceType.AR, date(2026, 6, 30)) is None


def test_build_cash_flow_forecast_after_adding_invoices():
    ws = Workspace.from_file(SAMPLE_CSV)
    ws.add_invoices(load_invoices(SAMPLE_INVOICES_CSV))

    forecast = ws.build_cash_flow_forecast("beacon-partners", starting_balance=10000, as_of=date(2026, 6, 30))

    assert forecast.client_id == "beacon-partners"
    assert forecast.starting_balance == 10000
    assert len(forecast.weeks) == 13


def test_build_cash_flow_forecast_without_invoices_is_flat():
    ws = Workspace.from_file(SAMPLE_CSV)
    forecast = ws.build_cash_flow_forecast("beacon-partners", starting_balance=5000, as_of=date(2026, 6, 30))
    assert all(w.ending_balance == 5000 for w in forecast.weeks)


def test_add_statements_makes_new_client_available():
    ws = Workspace.from_file(SAMPLE_CSV)
    assert "xero-demo-co" not in ws.client_ids

    new_statement = FinancialStatement(
        client_id="xero-demo-co",
        period="2026-06",
        scenario=Scenario.ACTUAL,
        line_items=[
            LineItem(
                client_id="xero-demo-co", period="2026-06", scenario=Scenario.ACTUAL,
                account="Sales", category=AccountCategory.REVENUE, amount=1000,
            )
        ],
    )
    ws.add_statements([new_statement])

    assert "xero-demo-co" in ws.client_ids
    report = ws.build_client_report("xero-demo-co", "2026-06")
    assert report is not None
    assert report.actual_kpis.revenue == 1000


def test_build_ebitda_bridge_returns_none_without_budget_data():
    ws = Workspace.from_file(SAMPLE_CSV)
    # 2026-01 only has an ACTUAL scenario on file for either client (see
    # test_portfolio_report_covers_every_client) -- no budget to bridge from.
    assert ws.build_ebitda_bridge("acme-ltd", "2026-01") is None


def test_build_ebitda_bridge_for_period_with_budget_data():
    ws = Workspace.from_file(SAMPLE_CSV)
    bridge = ws.build_ebitda_bridge("beacon-partners", "2026-06")

    assert bridge is not None
    assert bridge.client_id == "beacon-partners"
    assert bridge.period == "2026-06"
    deltas = sum(s.value for s in bridge.steps if not s.is_total)
    assert bridge.budget_ebitda + deltas == bridge.actual_ebitda


def test_build_trend_raises_for_a_fresh_single_period_client():
    ws = Workspace.from_file(SAMPLE_CSV)
    ws.add_statements(
        [
            FinancialStatement(
                client_id="brand-new-co", period="2026-06", scenario=Scenario.ACTUAL,
                line_items=[
                    LineItem(
                        client_id="brand-new-co", period="2026-06", scenario=Scenario.ACTUAL,
                        account="Sales", category=AccountCategory.REVENUE, amount=1000,
                    )
                ],
            )
        ]
    )

    with pytest.raises(TrendError):
        ws.build_trend("brand-new-co")


def test_build_trend_for_client_with_history():
    ws = Workspace.from_file(SAMPLE_CSV)
    trend = ws.build_trend("acme-ltd")

    assert trend.client_id == "acme-ltd"
    assert trend.periods == ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]


def test_build_working_capital_returns_none_without_invoices():
    ws = Workspace.from_file(SAMPLE_CSV)
    assert ws.build_working_capital("beacon-partners", "2026-06", date(2026, 6, 30)) is None


def test_build_working_capital_after_adding_invoices():
    ws = Workspace.from_file(SAMPLE_CSV)
    ws.add_invoices(load_invoices(SAMPLE_INVOICES_CSV))

    metrics = ws.build_working_capital("beacon-partners", "2026-06", date(2026, 6, 30))

    assert metrics is not None
    assert metrics.client_id == "beacon-partners"
    assert metrics.dso is not None
