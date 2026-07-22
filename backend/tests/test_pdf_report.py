from datetime import date
from pathlib import Path

from app.engine.workspace import Workspace
from app.ingestion.invoices import load_invoices
from app.models.domain import AIExecutiveNarrative, InvoiceType
from app.reporting import pdf_report
from app.reporting.pdf_report import generate_client_pdf

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_financials.csv"
SAMPLE_INVOICES_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_invoices.csv"


def _workspace() -> Workspace:
    return Workspace.from_file(SAMPLE_CSV)


def _workspace_with_invoices() -> Workspace:
    workspace = _workspace()
    workspace.add_invoices(load_invoices(SAMPLE_INVOICES_CSV))
    return workspace


def test_generate_client_pdf_returns_pdf_bytes_with_forecast():
    workspace = _workspace()
    report = workspace.build_client_report("beacon-partners", "2026-06")
    forecast = workspace.build_forecast("beacon-partners", periods_ahead=2)

    pdf_bytes = generate_client_pdf(report, forecast)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_generate_client_pdf_without_forecast_still_produces_valid_pdf():
    workspace = _workspace()
    report = workspace.build_client_report("beacon-partners", "2026-06")

    pdf_bytes = generate_client_pdf(report, forecast=None)

    assert pdf_bytes.startswith(b"%PDF")


def test_generate_client_pdf_handles_period_with_no_comparison_data():
    # 2026-01 only has an "actual" scenario on file (no budget/prior), so both
    # variance lists are empty -- the report must still render, not crash.
    workspace = _workspace()
    report = workspace.build_client_report("acme-ltd", "2026-01")
    assert report.variances_vs_budget == []
    assert report.variances_vs_prior == []

    pdf_bytes = generate_client_pdf(report, forecast=None)

    assert pdf_bytes.startswith(b"%PDF")


def test_generate_client_pdf_with_aging_and_cash_flow():
    workspace = _workspace_with_invoices()
    report = workspace.build_client_report("beacon-partners", "2026-06")
    as_of = date(2026, 6, 30)
    aging_reports = [
        r
        for r in (workspace.build_aging_report("beacon-partners", t, as_of) for t in InvoiceType)
        if r is not None
    ]
    cash_flow = workspace.build_cash_flow_forecast("beacon-partners", 10000, as_of, weeks_ahead=4)

    pdf_bytes = generate_client_pdf(report, aging_reports=aging_reports, cash_flow=cash_flow)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(aging_reports) == 2  # beacon-partners has both AR and AP invoices


def test_generate_client_pdf_without_aging_or_cash_flow_still_works():
    workspace = _workspace()
    report = workspace.build_client_report("beacon-partners", "2026-06")

    pdf_bytes = generate_client_pdf(report)

    assert pdf_bytes.startswith(b"%PDF")


def test_logo_asset_exists_in_repo():
    # The PDF can't reach frontend/public at runtime (Railway's deploy root is
    # backend/), so the brand logo must be its own committed copy.
    assert pdf_report._LOGO_PATH.exists()


def test_generate_client_pdf_without_logo_file_still_works(monkeypatch):
    monkeypatch.setattr(pdf_report, "_LOGO_PATH", Path("/nonexistent/logo.png"))
    workspace = _workspace()
    report = workspace.build_client_report("beacon-partners", "2026-06")

    pdf_bytes = generate_client_pdf(report)

    assert pdf_bytes.startswith(b"%PDF")


def test_generate_client_pdf_with_full_cash_flow_horizon():
    # Default weeks_ahead=13 stresses the chart's angled weekly category labels.
    workspace = _workspace_with_invoices()
    report = workspace.build_client_report("beacon-partners", "2026-06")
    as_of = date(2026, 6, 30)
    cash_flow = workspace.build_cash_flow_forecast("beacon-partners", 10000, as_of)

    pdf_bytes = generate_client_pdf(report, cash_flow=cash_flow)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(cash_flow.weeks) == 13


def test_executive_summary_mentions_biggest_variance():
    workspace = _workspace()
    report = workspace.build_client_report("beacon-partners", "2026-06")

    summary = pdf_report._executive_summary(report)

    top_movers = pdf_report.material_variances(report.variances_vs_budget) or pdf_report.material_variances(
        report.variances_vs_prior
    )
    assert top_movers, "fixture period should have at least one material variance"
    biggest = max(top_movers, key=lambda v: abs(v.delta_pct or 0))
    assert biggest.narrative in summary
    assert report.client_id in summary


def test_executive_summary_handles_no_material_variances():
    workspace = _workspace()
    report = workspace.build_client_report("acme-ltd", "2026-01")
    assert report.variances_vs_budget == []
    assert report.variances_vs_prior == []

    summary = pdf_report._executive_summary(report)

    assert report.client_id in summary


def test_generate_client_pdf_with_ebitda_bridge():
    workspace = _workspace()
    report = workspace.build_client_report("beacon-partners", "2026-06")
    bridge = workspace.build_ebitda_bridge("beacon-partners", "2026-06")
    assert bridge is not None

    pdf_bytes = generate_client_pdf(report, bridge=bridge)

    assert pdf_bytes.startswith(b"%PDF")


def test_generate_client_pdf_without_ebitda_bridge_still_works():
    workspace = _workspace()
    report = workspace.build_client_report("acme-ltd", "2026-01")
    bridge = workspace.build_ebitda_bridge("acme-ltd", "2026-01")
    assert bridge is None  # no budget data for this period

    pdf_bytes = generate_client_pdf(report, bridge=None)

    assert pdf_bytes.startswith(b"%PDF")


def test_generate_client_pdf_with_trend():
    workspace = _workspace()
    report = workspace.build_client_report("beacon-partners", "2026-06")
    trend = workspace.build_trend("beacon-partners")

    pdf_bytes = generate_client_pdf(report, trend=trend)

    assert pdf_bytes.startswith(b"%PDF")


def test_generate_client_pdf_without_trend_still_works():
    workspace = _workspace()
    report = workspace.build_client_report("beacon-partners", "2026-06")

    pdf_bytes = generate_client_pdf(report, trend=None)

    assert pdf_bytes.startswith(b"%PDF")


def test_generate_client_pdf_with_working_capital():
    workspace = _workspace_with_invoices()
    report = workspace.build_client_report("beacon-partners", "2026-06")
    working_capital = workspace.build_working_capital("beacon-partners", "2026-06", date(2026, 6, 30))
    assert working_capital is not None

    pdf_bytes = generate_client_pdf(report, working_capital=working_capital)

    assert pdf_bytes.startswith(b"%PDF")


def test_generate_client_pdf_without_working_capital_still_works():
    workspace = _workspace()
    report = workspace.build_client_report("beacon-partners", "2026-06")

    pdf_bytes = generate_client_pdf(report, working_capital=None)

    assert pdf_bytes.startswith(b"%PDF")


def test_generate_client_pdf_with_ai_narrative_and_risks_renders_extra_section():
    workspace = _workspace()
    report = workspace.build_client_report("beacon-partners", "2026-06")
    narrative = AIExecutiveNarrative(
        summary="AI-written summary of the period.",
        risks=["Client concentration risk."],
        opportunities=["Upsell opportunity."],
    )

    with_narrative = generate_client_pdf(report, ai_narrative=narrative)
    without_narrative = generate_client_pdf(report, ai_narrative=None)

    assert with_narrative.startswith(b"%PDF")
    # The risks/opportunities section adds real content, so the PDF with it
    # should not be smaller than the one without.
    assert len(with_narrative) >= len(without_narrative)


def test_generate_client_pdf_with_empty_ai_narrative_omits_risks_section():
    workspace = _workspace()
    report = workspace.build_client_report("beacon-partners", "2026-06")
    narrative = AIExecutiveNarrative(summary="Just a summary, no risks or opportunities.")

    pdf_bytes = generate_client_pdf(report, ai_narrative=narrative)

    assert pdf_bytes.startswith(b"%PDF")
