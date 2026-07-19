"""
Shared-secret access gate for the demo deployment.

Not a real auth system (no per-user identity) -- just enough to stop a
public URL from being wide open to anyone who finds it, since the chat
endpoint (app/agents/fpa_agent.py) calls a paid API. Controlled entirely by
whether DEMO_ACCESS_KEY is set: unset locally (no friction for
development), set in production (Railway) to actually gate the deployment.

Accepts the key via the X-Demo-Key header (used by the frontend's fetch
calls) or a `key` query param (needed for the PDF download link, which is
a plain <a href> with no custom headers).

`_PUBLIC_PATHS` exempts routes that a third party redirects to directly and
can't attach our header/query param to -- currently just Xero's OAuth
callback (app/integrations/xero/oauth.py).
"""

from __future__ import annotations

import os

from fastapi import HTTPException, Request

_PUBLIC_PATHS = {"/xero/callback"}


def verify_access_key(request: Request) -> None:
    if request.url.path in _PUBLIC_PATHS:
        return

    expected = os.getenv("DEMO_ACCESS_KEY")
    if not expected:
        return

    provided = request.headers.get("x-demo-key") or request.query_params.get("key")
    if provided != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid access key")
