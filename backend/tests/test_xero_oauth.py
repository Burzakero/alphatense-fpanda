from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.integrations.xero import oauth


@pytest.fixture(autouse=True)
def _clean_oauth_state(monkeypatch):
    """Each test gets a fresh token store, pending-states set, and real credentials."""
    monkeypatch.setattr(oauth, "_TOKENS", {})
    monkeypatch.setattr(oauth, "_PENDING_STATES", set())
    monkeypatch.setenv("XERO_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("XERO_CLIENT_SECRET", "test-client-secret")
    yield


def test_build_authorize_url_contains_required_params():
    url = oauth.build_authorize_url("state-123")

    assert url.startswith(oauth.AUTHORIZE_URL)
    assert "client_id=test-client-id" in url
    assert "state=state-123" in url
    assert "response_type=code" in url
    assert "state-123" in oauth._PENDING_STATES


def test_build_authorize_url_without_credentials_raises():
    import os

    os.environ.pop("XERO_CLIENT_ID", None)
    os.environ.pop("XERO_CLIENT_SECRET", None)

    with pytest.raises(oauth.XeroNotConfiguredError):
        oauth.build_authorize_url("state-123")


def test_exchange_code_for_tokens_rejects_unknown_state():
    with pytest.raises(oauth.XeroStateMismatchError):
        oauth.exchange_code_for_tokens("some-code", "never-issued-state")


def test_exchange_code_for_tokens_stores_one_tokenset_per_tenant(monkeypatch):
    oauth._PENDING_STATES.add("state-abc")

    def fake_post(url, **kwargs):
        assert url == oauth.TOKEN_URL
        return httpx.Response(
            200,
            json={"access_token": "acc-1", "refresh_token": "ref-1", "expires_in": 1800},
            request=httpx.Request("POST", url),
        )

    def fake_get(url, **kwargs):
        assert url == oauth.CONNECTIONS_URL
        return httpx.Response(
            200,
            json=[
                {"tenantId": "tenant-a", "tenantName": "Acme Ltd"},
                {"tenantId": "tenant-b", "tenantName": "Beacon Partners"},
            ],
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(oauth.httpx, "post", fake_post)
    monkeypatch.setattr(oauth.httpx, "get", fake_get)

    connected = oauth.exchange_code_for_tokens("some-code", "state-abc")

    assert {t.tenant_id for t in connected} == {"tenant-a", "tenant-b"}
    assert oauth.is_connected("tenant-a")
    assert oauth.is_connected("tenant-b")
    assert oauth._TOKENS["tenant-a"].access_token == "acc-1"
    assert "state-abc" not in oauth._PENDING_STATES


def test_get_valid_access_token_unconnected_tenant_raises():
    with pytest.raises(oauth.XeroNotConnectedError):
        oauth.get_valid_access_token("never-connected")


def test_get_valid_access_token_returns_token_when_fresh():
    oauth._TOKENS["tenant-a"] = oauth.TokenSet(
        access_token="fresh-token",
        refresh_token="refresh-token",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        tenant_id="tenant-a",
        tenant_name="Acme Ltd",
    )

    assert oauth.get_valid_access_token("tenant-a") == "fresh-token"


def test_get_valid_access_token_refreshes_when_near_expiry(monkeypatch):
    oauth._TOKENS["tenant-a"] = oauth.TokenSet(
        access_token="stale-token",
        refresh_token="old-refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=5),
        tenant_id="tenant-a",
        tenant_name="Acme Ltd",
    )

    def fake_post(url, **kwargs):
        assert kwargs["data"]["grant_type"] == "refresh_token"
        assert kwargs["data"]["refresh_token"] == "old-refresh"
        return httpx.Response(
            200,
            json={"access_token": "new-token", "refresh_token": "new-refresh", "expires_in": 1800},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(oauth.httpx, "post", fake_post)

    token = oauth.get_valid_access_token("tenant-a")

    assert token == "new-token"
    assert oauth._TOKENS["tenant-a"].refresh_token == "new-refresh"
