from io import BytesIO
from pathlib import Path

import pandas as pd

from app.engine.workspace import Workspace
from app.ingestion.invoices import load_invoices
from app.reporting.data_export import generate_portfolio_workbook

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_financials.csv"
SAMPLE_INVOICES_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_invoices.csv"


def _workspace() -> Workspace:
    return Workspace.from_file(SAMPLE_CSV)


def _workspace_with_invoices() -> Workspace:
    workspace = _workspace()
    workspace.add_invoices(load_invoices(SAMPLE_INVOICES_CSV))
    return workspace


def test_generate_portfolio_workbook_returns_valid_xlsx_bytes():
    workbook_bytes = generate_portfolio_workbook(_workspace())

    assert workbook_bytes.startswith(b"PK")  # .xlsx is a zip archive
    assert len(workbook_bytes) > 1000


def test_sheet_names_and_row_counts_match_workspace_data():
    workspace = _workspace_with_invoices()
    workbook_bytes = generate_portfolio_workbook(workspace)

    sheets = pd.read_excel(BytesIO(workbook_bytes), sheet_name=None)

    assert set(sheets.keys()) == {"Line Items", "KPIs", "Variance", "Forecast", "Invoices", "Notes"}

    expected_line_items = sum(len(s.line_items) for s in workspace.statements)
    assert len(sheets["Line Items"]) == expected_line_items

    reports = workspace.build_portfolio_report()
    assert len(sheets["KPIs"]) == len(reports)

    expected_variance = sum(len(r.variances_vs_budget) + len(r.variances_vs_prior) for r in reports)
    assert len(sheets["Variance"]) == expected_variance

    expected_forecast = sum(len(v) for v in workspace.build_portfolio_forecast().values())
    assert len(sheets["Forecast"]) == expected_forecast

    assert len(sheets["Invoices"]) == len(workspace.invoices)
    assert len(sheets["Notes"]) > 0


def test_export_without_invoices_has_empty_invoices_sheet_with_headers():
    workbook_bytes = generate_portfolio_workbook(_workspace())

    sheets = pd.read_excel(BytesIO(workbook_bytes), sheet_name=None)

    assert len(sheets["Invoices"]) == 0
    assert "balance" in sheets["Invoices"].columns
    assert "amount_paid" in sheets["Invoices"].columns


def test_invoice_balance_column_is_amount_minus_amount_paid():
    workspace = _workspace_with_invoices()
    workbook_bytes = generate_portfolio_workbook(workspace)

    invoices = pd.read_excel(BytesIO(workbook_bytes), sheet_name="Invoices")
    row = invoices[invoices["invoice_id"] == "INV-3002"].iloc[0]

    assert row["amount"] == 9000
    assert row["amount_paid"] == 3000
    assert row["balance"] == 6000
