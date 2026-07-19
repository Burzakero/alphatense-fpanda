"""
OAuth2 authorization-code flow + token storage for the real Xero connector.

Mirrors two existing conventions in this codebase rather than inventing new
ones: `_WORKSPACES` in app/api/main.py (in-memory dict store, no DB yet) and
the `load_dotenv()` + `os.getenv()` + custom `*NotConfiguredError` pattern in
app/agents/fpa_agent.py.

Flow: GET /xero/connect (app/api/main.py) calls `build_authorize_url()` and
redirects the advisor to Xero's consent screen. Xero redirects back to
GET /xero/callback with `code` + `state`; that route calls
`exchange_code_for_tokens()`, which trades the code for an access+refresh
token pair, then calls Xero's /connections endpoint to find out which
tenant(s) the advisor just granted access to. `RealXeroClient` (client.py)
calls `get_valid_access_token()` before every API request, which
transparently refreshes an expiring token.

Scope note: this app was registered under Xero's newer granular-scopes
model (apps created after 2026-03-02 only get granular scopes, not the old
broad ones). Confirmed live (2026-07-18, against a real connected org) that
there is no granular scope covering the `GET /Journals` endpoint at all --
`accounting.manualjournals.read` is a narrower, different feature
(manually-created journal entries) and still 401s on it. `client.py`'s
RealXeroClient builds the P&L from `Reports/ProfitAndLoss` instead, which
`accounting.reports.profitandloss.read` (below) does cover.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv()

AUTHORIZE_URL = "https://login.xero.com/identity/connect/authorize"
TOKEN_URL = "https://identity.xero.com/connect/token"
CONNECTIONS_URL = "https://api.xero.com/connections"
XERO_API_BASE = "https://api.xero.com/api.xro/2.0"

_DEFAULT_REDIRECT_URI = "http://localhost:8000/xero/callback"
# Scope names must match exactly what Xero's granular-scopes model exposes
# for this app (visible on the app's Configuration page) -- there is no
# generic "accounting.transactions" or "accounting.reports" scope in that
# model, unlike the old broad-scopes API. accounting.manualjournals.read is
# deliberately omitted -- confirmed it doesn't grant /Journals access (see
# module docstring), and we have no manual-journal feature to use it for.
_SCOPES = (
    "openid profile email offline_access "
    "accounting.contacts.read accounting.invoices.read "
    "accounting.settings.read "
    "accounting.reports.profitandloss.read accounting.reports.balancesheet.read"
)
_REFRESH_BUFFER = timedelta(seconds=60)


class XeroNotConfiguredError(RuntimeError):
    """Raised when XERO_CLIENT_ID / XERO_CLIENT_SECRET aren't set."""


class XeroNotConnectedError(RuntimeError):
    """Raised when a tenant_id has no stored token -- advisor hasn't connected yet."""


class XeroStateMismatchError(RuntimeError):
    """Raised when the OAuth callback's `state` doesn't match one we issued."""


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str
    expires_at: datetime
    tenant_id: str
    tenant_name: str


# In-memory stores -- no DB yet, same stage as `_WORKSPACES` in api/main.py.
_TOKENS: dict[str, TokenSet] = {}
_PENDING_STATES: set[str] = set()


def _client_credentials() -> tuple[str, str]:
    client_id = os.getenv("XERO_CLIENT_ID")
    client_secret = os.getenv("XERO_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise XeroNotConfiguredError("XERO_CLIENT_ID / XERO_CLIENT_SECRET are not configured.")
    return client_id, client_secret


def _redirect_uri() -> str:
    return os.getenv("XERO_REDIRECT_URI", _DEFAULT_REDIRECT_URI)


def is_connected(tenant_id: str) -> bool:
    return tenant_id in _TOKENS


def build_authorize_url(state: str) -> str:
    """Build the URL that starts the Xero consent flow, tracking `state` for the callback."""
    client_id, _ = _client_credentials()
    _PENDING_STATES.add(state)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": _redirect_uri(),
        "scope": _SCOPES,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code: str, state: str) -> list[TokenSet]:
    """Trade an authorization code for tokens, then enumerate connected tenants.

    Raises XeroStateMismatchError if `state` wasn't one we issued (minimal
    CSRF protection -- there's no session/cookie layer in this stateless API
    to compare against otherwise).
    """
    if state not in _PENDING_STATES:
        raise XeroStateMismatchError(f"Unrecognized OAuth state: {state!r}")
    _PENDING_STATES.discard(state)

    client_id, client_secret = _client_credentials()
    token_response = httpx.post(
        TOKEN_URL,
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": _redirect_uri()},
        auth=(client_id, client_secret),
        timeout=15.0,
    )
    token_response.raise_for_status()
    token_data = token_response.json()

    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

    connections_response = httpx.get(
        CONNECTIONS_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15.0,
    )
    connections_response.raise_for_status()

    connected: list[TokenSet] = []
    for connection in connections_response.json():
        tenant_id = connection["tenantId"]
        token_set = TokenSet(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            tenant_id=tenant_id,
            tenant_name=connection.get("tenantName", tenant_id),
        )
        _TOKENS[tenant_id] = token_set
        connected.append(token_set)
    return connected


def refresh_access_token(tenant_id: str) -> None:
    """Refresh an expiring token in place. Xero rotates the refresh token on every use."""
    token_set = _TOKENS.get(tenant_id)
    if token_set is None:
        raise XeroNotConnectedError(f"No Xero connection for tenant_id={tenant_id!r}.")

    client_id, client_secret = _client_credentials()
    response = httpx.post(
        TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": token_set.refresh_token},
        auth=(client_id, client_secret),
        timeout=15.0,
    )
    response.raise_for_status()
    token_data = response.json()

    token_set.access_token = token_data["access_token"]
    token_set.refresh_token = token_data["refresh_token"]
    token_set.expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])


def get_valid_access_token(tenant_id: str) -> str:
    """Return a live access token for `tenant_id`, refreshing first if it's about to expire."""
    token_set = _TOKENS.get(tenant_id)
    if token_set is None:
        raise XeroNotConnectedError(f"No Xero connection for tenant_id={tenant_id!r}. Connect via /xero/connect first.")

    if datetime.now(timezone.utc) + _REFRESH_BUFFER >= token_set.expires_at:
        refresh_access_token(tenant_id)
        token_set = _TOKENS[tenant_id]

    return token_set.access_token
