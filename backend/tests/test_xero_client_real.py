from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.integrations.xero import oauth
from app.integrations.xero.client import RealXeroClient


@pytest.fixture(autouse=True)
def _connected_tenant(monkeypatch):
    monkeypatch.setattr(oauth, "_TOKENS", {})
    monkeypatch.setenv("XERO_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("XERO_CLIENT_SECRET", "test-client-secret")
    oauth._TOKENS["tenant-a"] = oauth.TokenSet(
        access_token="live-token",
        refresh_token="live-refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        tenant_id="tenant-a",
        tenant_name="Acme Ltd",
    )
    yield


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_list_invoices_sends_bearer_and_tenant_header():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        return httpx.Response(200, json={"Invoices": []})

    client = RealXeroClient(http_client=_mock_client(handler))
    result = client.list_invoices("tenant-a")

    assert result == {"Invoices": []}
    assert captured["url"] == f"{oauth.XERO_API_BASE}/Invoices"
    assert captured["headers"]["authorization"] == "Bearer live-token"
    assert captured["headers"]["xero-tenant-id"] == "tenant-a"


def test_get_profit_and_loss_report_and_accounts_hit_correct_paths():
    seen_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        return httpx.Response(200, json={})

    client = RealXeroClient(http_client=_mock_client(handler))
    client.get_profit_and_loss_report("tenant-a")
    client.list_accounts("tenant-a")

    assert seen_paths == ["/api.xro/2.0/Reports/ProfitAndLoss", "/api.xro/2.0/Accounts"]


def test_unconnected_tenant_raises_before_any_http_call():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not make an HTTP call for an unconnected tenant")

    client = RealXeroClient(http_client=_mock_client(handler))

    with pytest.raises(oauth.XeroNotConnectedError):
        client.list_invoices("never-connected-tenant")


def test_http_error_propagates():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    client = RealXeroClient(http_client=_mock_client(handler))

    with pytest.raises(httpx.HTTPStatusError):
        client.list_invoices("tenant-a")
