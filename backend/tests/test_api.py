from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_financials.csv"
SAMPLE_INVOICES_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_invoices.csv"


def _upload_sample() -> str:
    with open(SAMPLE_CSV, "rb") as f:
        response = client.post(
            "/workspaces",
            files={"file": ("sample_financials.csv", f, "text/csv")},
        )
    assert response.status_code == 201
    return response.json()["workspace_id"]


def _upload_sample_invoices(workspace_id: str) -> None:
    with open(SAMPLE_INVOICES_CSV, "rb") as f:
        response = client.post(
            f"/workspaces/{workspace_id}/invoices",
            files={"file": ("sample_invoices.csv", f, "text/csv")},
        )
    assert response.status_code == 201


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_creates_workspace_with_expected_clients():
    with open(SAMPLE_CSV, "rb") as f:
        response = client.post(
            "/workspaces",
            files={"file": ("sample_financials.csv", f, "text/csv")},
        )
    assert response.status_code == 201
    body = response.json()
    assert "workspace_id" in body and body["workspace_id"]
    assert body["client_ids"] == ["acme-ltd", "beacon-partners"]


def test_upload_rejects_unsupported_file_type():
    response = client.post(
        "/workspaces",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_malformed_csv():
    bad_csv = b"client_id,period,scenario,account,amount\nc1,2026-01,actual,Sales,100\n"
    response = client.post(
        "/workspaces",
        files={"file": ("bad.csv", bad_csv, "text/csv")},
    )
    assert response.status_code == 400
    assert "category" in response.json()["detail"]


def test_list_clients():
    workspace_id = _upload_sample()
    response = client.get(f"/workspaces/{workspace_id}/clients")
    assert response.status_code == 200
    assert response.json() == {"client_ids": ["acme-ltd", "beacon-partners"]}


def test_unknown_workspace_returns_404():
    response = client.get("/workspaces/does-not-exist/clients")
    assert response.status_code == 404


def test_portfolio_report_covers_every_client_period():
    workspace_id = _upload_sample()
    response = client.get(f"/workspaces/{workspace_id}/portfolio")
    assert response.status_code == 200
    reports = response.json()
    # 2 clients x 6 historical actual periods (2026-01..2026-06) = 12 reports.
    assert len(reports) == 12
    assert all("actual_kpis" in r for r in reports)


def test_client_report_for_beacon_june_has_variances():
    workspace_id = _upload_sample()
    response = client.get(
        f"/workspaces/{workspace_id}/clients/beacon-partners/report",
        params={"period": "2026-06"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["client_id"] == "beacon-partners"
    assert len(body["variances_vs_budget"]) > 0
    assert len(body["variances_vs_prior"]) > 0


def test_client_report_unknown_period_returns_404():
    workspace_id = _upload_sample()
    response = client.get(
        f"/workspaces/{workspace_id}/clients/acme-ltd/report",
        params={"period": "2099-12"},
    )
    assert response.status_code == 404


def test_client_report_pdf_returns_pdf_bytes():
    workspace_id = _upload_sample()
    response = client.get(
        f"/workspaces/{workspace_id}/clients/beacon-partners/report/pdf",
        params={"period": "2026-06"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_client_report_pdf_unknown_period_returns_404():
    workspace_id = _upload_sample()
    response = client.get(
        f"/workspaces/{workspace_id}/clients/acme-ltd/report/pdf",
        params={"period": "2099-12"},
    )
    assert response.status_code == 404


def test_client_report_pdf_with_aging_and_cash_flow_params():
    workspace_id = _upload_sample()
    _upload_sample_invoices(workspace_id)

    response = client.get(
        f"/workspaces/{workspace_id}/clients/beacon-partners/report/pdf",
        params={"period": "2026-06", "as_of": "2026-06-30", "starting_balance": 10000},
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_client_report_pdf_with_as_of_but_no_invoices_still_200s():
    workspace_id = _upload_sample()
    response = client.get(
        f"/workspaces/{workspace_id}/clients/beacon-partners/report/pdf",
        params={"period": "2026-06", "as_of": "2026-06-30"},
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_client_report_pdf_invalid_as_of_returns_400():
    workspace_id = _upload_sample()
    response = client.get(
        f"/workspaces/{workspace_id}/clients/beacon-partners/report/pdf",
        params={"period": "2026-06", "as_of": "not-a-date"},
    )
    assert response.status_code == 400


def test_client_cash_flow_returns_weekly_projection():
    workspace_id = _upload_sample()
    _upload_sample_invoices(workspace_id)

    response = client.get(
        f"/workspaces/{workspace_id}/clients/beacon-partners/cash-flow",
        params={"starting_balance": 10000, "as_of": "2026-06-30", "weeks_ahead": 8},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["client_id"] == "beacon-partners"
    assert body["starting_balance"] == 10000
    assert len(body["weeks"]) == 8


def test_client_cash_flow_invalid_as_of_returns_400():
    workspace_id = _upload_sample()
    response = client.get(
        f"/workspaces/{workspace_id}/clients/beacon-partners/cash-flow",
        params={"starting_balance": 10000, "as_of": "not-a-date"},
    )
    assert response.status_code == 400


def test_client_cash_flow_unknown_workspace_returns_404():
    response = client.get(
        "/workspaces/does-not-exist/clients/beacon-partners/cash-flow",
        params={"starting_balance": 10000, "as_of": "2026-06-30"},
    )
    assert response.status_code == 404


def test_chat_without_api_key_returns_503(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    workspace_id = _upload_sample()
    response = client.post(
        f"/workspaces/{workspace_id}/chat",
        json={"message": "How is beacon-partners doing?"},
    )
    assert response.status_code == 503


def test_chat_unknown_workspace_returns_404():
    response = client.post(
        "/workspaces/does-not-exist/chat",
        json={"message": "How is beacon-partners doing?"},
    )
    assert response.status_code == 404


def test_client_forecast_returns_best_base_worst_per_period():
    workspace_id = _upload_sample()
    response = client.get(
        f"/workspaces/{workspace_id}/clients/acme-ltd/forecast",
        params={"periods_ahead": 2},
    )
    assert response.status_code == 200
    results = response.json()
    # 3 scenarios (best/base/worst) x 2 periods ahead = 6 results.
    assert len(results) == 6
    scenarios = {r["scenario"] for r in results}
    assert scenarios == {"best", "base", "worst"}


def test_client_forecast_unknown_client_returns_404():
    workspace_id = _upload_sample()
    response = client.get(f"/workspaces/{workspace_id}/clients/nonexistent/forecast")
    assert response.status_code == 404


def test_portfolio_forecast_covers_both_clients():
    workspace_id = _upload_sample()
    response = client.get(f"/workspaces/{workspace_id}/portfolio/forecast", params={"periods_ahead": 1})
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"acme-ltd", "beacon-partners"}
    for results in body.values():
        assert len(results) == 3  # best/base/worst for 1 period ahead


def test_upload_invoices_returns_count():
    workspace_id = _upload_sample()
    with open(SAMPLE_INVOICES_CSV, "rb") as f:
        response = client.post(
            f"/workspaces/{workspace_id}/invoices",
            files={"file": ("sample_invoices.csv", f, "text/csv")},
        )
    assert response.status_code == 201
    assert response.json() == {"invoices_loaded": 14}


def test_upload_invoices_rejects_unsupported_file_type():
    workspace_id = _upload_sample()
    response = client.post(
        f"/workspaces/{workspace_id}/invoices",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_invoices_unknown_workspace_returns_404():
    with open(SAMPLE_INVOICES_CSV, "rb") as f:
        response = client.post(
            "/workspaces/does-not-exist/invoices",
            files={"file": ("sample_invoices.csv", f, "text/csv")},
        )
    assert response.status_code == 404


def test_client_aging_returns_buckets():
    workspace_id = _upload_sample()
    _upload_sample_invoices(workspace_id)

    response = client.get(
        f"/workspaces/{workspace_id}/clients/beacon-partners/aging",
        params={"type": "ar", "as_of": "2026-06-30"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["client_id"] == "beacon-partners"
    assert body["type"] == "ar"
    assert body["total_outstanding"] > 0
    assert {b["bucket"] for b in body["buckets"]} == {"current", "1-30", "31-60", "61-90", "90+"}


def test_client_aging_without_invoices_returns_404():
    workspace_id = _upload_sample()
    response = client.get(
        f"/workspaces/{workspace_id}/clients/beacon-partners/aging",
        params={"type": "ar", "as_of": "2026-06-30"},
    )
    assert response.status_code == 404


def test_client_aging_invalid_type_returns_400():
    workspace_id = _upload_sample()
    _upload_sample_invoices(workspace_id)

    response = client.get(
        f"/workspaces/{workspace_id}/clients/beacon-partners/aging",
        params={"type": "not-a-type", "as_of": "2026-06-30"},
    )
    assert response.status_code == 400


def test_client_aging_invalid_as_of_returns_400():
    workspace_id = _upload_sample()
    _upload_sample_invoices(workspace_id)

    response = client.get(
        f"/workspaces/{workspace_id}/clients/beacon-partners/aging",
        params={"type": "ar", "as_of": "not-a-date"},
    )
    assert response.status_code == 400
