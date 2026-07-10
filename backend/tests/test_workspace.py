from datetime import date
from pathlib import Path

from app.engine.workspace import Workspace
from app.ingestion.invoices import load_invoices
from app.models.domain import InvoiceType, Severity

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
