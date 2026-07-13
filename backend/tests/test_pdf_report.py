from datetime import date
from pathlib import Path

from app.engine.workspace import Workspace
from app.ingestion.invoices import load_invoices
from app.models.domain import InvoiceType
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
