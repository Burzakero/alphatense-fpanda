import json
from datetime import date
from pathlib import Path

from app.agents.fpa_agent import (
    _client_aging,
    _client_cash_flow,
    _client_forecast,
    _client_report,
    _portfolio_summary,
)
from app.engine.workspace import Workspace
from app.ingestion.invoices import load_invoices

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_financials.csv"
SAMPLE_INVOICES_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_invoices.csv"


def _workspace_with_invoices() -> Workspace:
    ws = Workspace.from_file(SAMPLE_CSV)
    ws.add_invoices(load_invoices(SAMPLE_INVOICES_CSV))
    return ws


def test_portfolio_summary_returns_json_with_both_clients():
    ws = Workspace.from_file(SAMPLE_CSV)
    reports = json.loads(_portfolio_summary(ws))
    covered = {r["client_id"] for r in reports}
    assert covered == {"acme-ltd", "beacon-partners"}


def test_client_report_returns_beacon_variance():
    ws = Workspace.from_file(SAMPLE_CSV)
    report = json.loads(_client_report(ws, "beacon-partners", "2026-06"))
    assert report["client_id"] == "beacon-partners"
    assert len(report["variances_vs_budget"]) > 0


def test_client_report_unknown_period_returns_message_not_json():
    ws = Workspace.from_file(SAMPLE_CSV)
    result = _client_report(ws, "acme-ltd", "2099-12")
    assert "No actual data on file" in result


def test_client_forecast_returns_three_scenarios():
    ws = Workspace.from_file(SAMPLE_CSV)
    results = json.loads(_client_forecast(ws, "acme-ltd", periods_ahead=2))
    assert len(results) == 6  # 3 scenarios x 2 periods
    assert {r["scenario"] for r in results} == {"best", "base", "worst"}


def test_client_forecast_unknown_client_returns_message_not_json():
    ws = Workspace.from_file(SAMPLE_CSV)
    result = _client_forecast(ws, "nonexistent")
    assert "No actual history on file" in result


def test_client_aging_returns_buckets():
    ws = _workspace_with_invoices()
    report = json.loads(_client_aging(ws, "beacon-partners", "ar", "2026-06-30"))
    assert report["total_outstanding"] > 0
    assert {b["bucket"] for b in report["buckets"]} == {"current", "1-30", "31-60", "61-90", "90+"}


def test_client_aging_invalid_type_returns_message_not_json():
    ws = _workspace_with_invoices()
    result = _client_aging(ws, "beacon-partners", "not-a-type", "2026-06-30")
    assert "Invalid invoice_type" in result


def test_client_aging_invalid_date_returns_message_not_json():
    ws = _workspace_with_invoices()
    result = _client_aging(ws, "beacon-partners", "ar", "not-a-date")
    assert "Invalid as_of date" in result


def test_client_aging_no_invoices_returns_message_not_json():
    ws = Workspace.from_file(SAMPLE_CSV)  # no invoices loaded
    result = _client_aging(ws, "beacon-partners", "ar", "2026-06-30")
    assert "No AR invoices on file" in result


def test_client_cash_flow_returns_json_with_weeks():
    ws = _workspace_with_invoices()
    result = json.loads(_client_cash_flow(ws, "beacon-partners", 10000, "2026-06-30", weeks_ahead=4))
    assert result["client_id"] == "beacon-partners"
    assert len(result["weeks"]) == 4


def test_client_cash_flow_invalid_date_returns_message_not_json():
    ws = _workspace_with_invoices()
    result = _client_cash_flow(ws, "beacon-partners", 10000, "not-a-date")
    assert "Invalid as_of date" in result
