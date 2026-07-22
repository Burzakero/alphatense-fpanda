"""
Per-advisor session auth.

Each advisory firm has its own account (email + password); requests carry
an opaque bearer token issued at signup/login (see app/db/repository.py for
hashing/session mechanics -- tokens are stored as a SHA-256 hash, 30-day
fixed expiry, no JWT). `get_current_advisor` is applied per-route (not as a
blanket app-level dependency) so /health, /auth/signup, /auth/login, and
Xero's OAuth callback (a third-party redirect that can't attach our
Authorization header) stay open without needing an exemption list.

The token is also accepted via a `token` query param, alongside the usual
`Authorization: Bearer` header -- needed for the PDF report download link
(see app/api/main.py's client_report_pdf), which the frontend renders as a
plain `<a href>` with no way to attach a custom header.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.database import get_session
from app.db.models import AdvisorAccount
from app.db.repository import get_advisor_by_token, is_trial_expired

TRIAL_EXPIRED_DETAIL = "Your 15-day trial has ended. Contact us to keep using Alphatense."


def _extract_token(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return request.query_params.get("token", "")


def get_current_advisor(request: Request, db: Session = Depends(get_session)) -> AdvisorAccount:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    advisor = get_advisor_by_token(db, token)
    if advisor is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if is_trial_expired(advisor):
        # 403, not 401 -- the token itself is valid, the account just can't act on
        # it anymore. Unused elsewhere in this API, so the frontend can key off
        # the status code alone with no ambiguity (see RequireAuth.tsx).
        raise HTTPException(status_code=403, detail=TRIAL_EXPIRED_DETAIL)
    return advisor
