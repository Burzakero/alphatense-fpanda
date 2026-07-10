from pathlib import Path

from app.engine.workspace import Workspace
from app.reporting.pdf_report import generate_client_pdf

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_financials.csv"


def _workspace() -> Workspace:
    return Workspace.from_file(SAMPLE_CSV)


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
