"""
FastAPI HTTP layer over the FP&A + Forecast AI engine.

Exposes the Workspace orchestrator (see app/engine/workspace.py) as a small
set of REST endpoints an advisor's frontend (or Postman, or a script) can
call directly:

    POST /auth/signup                                    -- create an advisor account, get a session token
    POST /auth/login                                      -- log in, get a session token
    POST /auth/logout                                      -- invalidate the current session token
    GET  /auth/me                                           -- current advisor + their workspace_ids
    POST /workspaces                                    -- upload a file, get a workspace_id back
    GET  /workspaces/{workspace_id}/clients              -- list client ids found in the file
    GET  /workspaces/{workspace_id}/portfolio            -- KPIs + variance for every client/period
    GET  /workspaces/{workspace_id}/export/excel         -- multi-sheet .xlsx export of the whole portfolio
    GET  /workspaces/{workspace_id}/clients/{client_id}/report?period=...
    GET  /workspaces/{workspace_id}/clients/{client_id}/report/pdf?period=...&as_of=2026-06-30&starting_balance=50000
    GET  /workspaces/{workspace_id}/clients/{client_id}/forecast?periods_ahead=3
    GET  /workspaces/{workspace_id}/portfolio/forecast?periods_ahead=3
    POST /workspaces/{workspace_id}/invoices                     -- attach an AR/AP invoices file
    GET  /workspaces/{workspace_id}/clients/{client_id}/aging?type=ar&as_of=2026-06-30
    POST /workspaces/{workspace_id}/chat                          -- ask the conversational FP&A agent
    GET  /workspaces/{workspace_id}/clients/{client_id}/cash-flow?starting_balance=50000&as_of=2026-06-30&weeks_ahead=13
    GET  /xero/connect                                             -- start the Xero OAuth consent flow
    GET  /xero/callback                                            -- Xero OAuth redirect target (public, no advisor auth)
    POST /workspaces/{workspace_id}/xero/sync                     -- sync a client's P&L + invoices from Xero (real once connected, else simulated)
    POST /workspaces/{workspace_id}/quickbooks/sync                -- sync a client's P&L + invoices from QuickBooks (simulated)

Each advisor account (see POST /auth/signup) owns its own workspaces --
`_get_workspace` enforces that on every workspace-scoped route below.
Workspace data (P&L statements + invoices) is cached in memory for the
lifetime of the process, keyed by a generated UUID, but persisted to SQLite
(see app/db/) on every write, so a restart just means the next request
rehydrates from disk instead of losing the data.
"""

from __future__ import annotations

import os
import secrets
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from datetime import date

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.fpa_agent import AgentNotConfiguredError, ask
from app.api.auth import _extract_token, get_current_advisor
from app.db import repository
from app.db.database import get_session, init_db
from app.db.models import AdvisorAccount
from app.engine.forecast import ForecastError
from app.engine.workspace import Workspace
from app.ingestion.invoices import load_invoices
from app.ingestion.parser import IngestionError
from app.integrations.quickbooks.client import FakeQuickBooksClient
from app.integrations.quickbooks.sync import sync_client_from_quickbooks
from app.integrations.xero import oauth
from app.integrations.xero.client import FakeXeroClient, RealXeroClient
from app.integrations.xero.sync import sync_client_from_xero
from app.models.domain import InvoiceType
from app.reporting.data_export import generate_portfolio_workbook
from app.reporting.pdf_report import generate_client_pdf


@asynccontextmanager
async def _lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Alphatense AI -- FP&A Engine API",
    description="HTTP API over the ingestion, KPI, variance, and forecast engine.",
    version="0.1.0",
    lifespan=_lifespan,
)

# Local dev origins are always allowed; production origins (the deployed
# frontend) come from ALLOWED_ORIGINS (comma-separated) so this doesn't need
# a code change per deploy.
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_extra_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ALLOWED_SUFFIXES = {".csv", ".xlsx", ".xls"}

# In-memory cache: workspace_id -> Workspace. Every write goes through to
# SQLite (app/db/repository.py) too, so a cache miss (fresh process) just
# means the next request rehydrates from disk. Ownership is re-checked
# against the DB on every request regardless of cache state -- see
# _get_workspace -- since the cache itself has no notion of who owns what.
_WORKSPACES: dict[str, Workspace] = {}


def _get_workspace(
    workspace_id: str,
    advisor: AdvisorAccount = Depends(get_current_advisor),
    db: Session = Depends(get_session),
) -> Workspace:
    owner_id = repository.get_workspace_owner_id(db, workspace_id)
    if owner_id is None or owner_id != advisor.advisor_id:
        # 404 either way (not 403) so a wrong workspace_id can't be used to
        # probe whether it belongs to someone else.
        raise HTTPException(status_code=404, detail=f"Unknown workspace_id: {workspace_id}")

    cached = _WORKSPACES.get(workspace_id)
    if cached is not None:
        return cached

    loaded = repository.load_workspace(db, workspace_id)
    assert loaded is not None  # owner_id lookup above already confirmed the row exists
    workspace, _ = loaded
    _WORKSPACES[workspace_id] = workspace
    return workspace


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def _advisor_payload(advisor: AdvisorAccount) -> dict:
    return {"advisor_id": advisor.advisor_id, "name": advisor.name, "email": advisor.email}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/signup", status_code=201)
def signup(request: SignupRequest, db: Session = Depends(get_session)) -> dict:
    if repository.get_advisor_by_email(db, request.email) is not None:
        raise HTTPException(status_code=409, detail="An account with that email already exists")
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    advisor = repository.create_advisor(db, name=request.name, email=request.email, password=request.password)
    token = repository.create_session(db, advisor.advisor_id)
    return {"token": token, "advisor": _advisor_payload(advisor)}


@app.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_session)) -> dict:
    advisor = repository.get_advisor_by_email(db, request.email)
    if advisor is None or not repository.verify_password(request.password, advisor.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = repository.create_session(db, advisor.advisor_id)
    return {"token": token, "advisor": _advisor_payload(advisor)}


@app.post("/auth/logout")
def logout(request: Request, db: Session = Depends(get_session)) -> dict:
    token = _extract_token(request)
    if token:
        repository.delete_session(db, token)
    return {"status": "ok"}


@app.get("/auth/me")
def me(
    advisor: AdvisorAccount = Depends(get_current_advisor),
    db: Session = Depends(get_session),
) -> dict:
    workspace_ids = repository.list_advisor_workspace_ids(db, advisor.advisor_id)
    return {"advisor": _advisor_payload(advisor), "workspace_ids": workspace_ids}


@app.post("/workspaces", status_code=201)
async def create_workspace(
    file: UploadFile = File(...),
    advisor: AdvisorAccount = Depends(get_current_advisor),
    db: Session = Depends(get_session),
) -> dict:
    """Upload a CSV/Excel file and build a Workspace from it.

    Returns the generated workspace_id plus the list of client_ids found in
    the file, so a caller can immediately start requesting reports without a
    second round trip.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Expected one of: {', '.join(sorted(_ALLOWED_SUFFIXES))}",
        )

    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        workspace = Workspace.from_file(tmp_path)
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    workspace_id = str(uuid.uuid4())
    _WORKSPACES[workspace_id] = workspace
    repository.save_workspace(db, workspace_id, advisor.advisor_id, workspace)

    return {"workspace_id": workspace_id, "client_ids": workspace.client_ids}


@app.post("/workspaces/{workspace_id}/invoices", status_code=201)
async def upload_invoices(
    workspace_id: str,
    file: UploadFile = File(...),
    workspace: Workspace = Depends(_get_workspace),
    advisor: AdvisorAccount = Depends(get_current_advisor),
    db: Session = Depends(get_session),
) -> dict:
    """Attach an AR/AP invoices file to an existing workspace, on top of its P&L data."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Expected one of: {', '.join(sorted(_ALLOWED_SUFFIXES))}",
        )

    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        invoices = load_invoices(tmp_path)
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    workspace.add_invoices(invoices)
    repository.save_workspace(db, workspace_id, advisor.advisor_id, workspace)
    return {"invoices_loaded": len(invoices)}


class XeroSyncRequest(BaseModel):
    tenant_id: str
    client_id: str
    period: str


@app.get("/xero/connect")
def xero_connect() -> RedirectResponse:
    """Start the Xero OAuth consent flow -- redirects the advisor to Xero's login/consent screen."""
    state = secrets.token_urlsafe(16)
    try:
        url = oauth.build_authorize_url(state)
    except oauth.XeroNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return RedirectResponse(url)


@app.get("/xero/callback")
def xero_callback(code: str, state: str) -> dict:
    """Xero redirects here after consent. No advisor auth here by construction -- Xero can't attach
    our Authorization header, and this route never declares Depends(get_current_advisor)."""
    try:
        connected = oauth.exchange_code_for_tokens(code, state)
    except oauth.XeroStateMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "connected_tenants": [
            {"tenant_id": t.tenant_id, "tenant_name": t.tenant_name} for t in connected
        ]
    }


@app.post("/workspaces/{workspace_id}/xero/sync", status_code=201)
def xero_sync(
    workspace_id: str,
    request: XeroSyncRequest,
    workspace: Workspace = Depends(_get_workspace),
    advisor: AdvisorAccount = Depends(get_current_advisor),
    db: Session = Depends(get_session),
) -> dict:
    """Sync one client's P&L + AR/AP invoices from Xero into this workspace.

    Uses RealXeroClient once the tenant has connected via /xero/connect;
    otherwise falls back to FakeXeroClient (static fixtures for
    tenant_id="demo-tenant-xero") -- see app/integrations/xero/client.py.
    """
    xero_client = RealXeroClient() if oauth.is_connected(request.tenant_id) else FakeXeroClient()
    statement, invoices = sync_client_from_xero(
        xero_client, request.tenant_id, request.client_id, request.period
    )
    workspace.add_statements([statement])
    workspace.add_invoices(invoices)
    repository.save_workspace(db, workspace_id, advisor.advisor_id, workspace)
    return {
        "client_id": request.client_id,
        "period": request.period,
        "line_items_loaded": len(statement.line_items),
        "invoices_loaded": len(invoices),
    }


class QuickBooksSyncRequest(BaseModel):
    realm_id: str
    client_id: str
    period: str


@app.post("/workspaces/{workspace_id}/quickbooks/sync", status_code=201)
def quickbooks_sync(
    workspace_id: str,
    request: QuickBooksSyncRequest,
    workspace: Workspace = Depends(_get_workspace),
    advisor: AdvisorAccount = Depends(get_current_advisor),
    db: Session = Depends(get_session),
) -> dict:
    """Sync one client's P&L + AR/AP invoices from QuickBooks into this workspace.

    Simulated for now: uses FakeQuickBooksClient (static fixtures for
    realm_id="demo-realm-quickbooks"), not a real OAuth-connected QuickBooks
    company -- see app/integrations/quickbooks/client.py. Swapping in a
    RealQuickBooksClient later doesn't change this route.
    """
    statement, invoices = sync_client_from_quickbooks(
        FakeQuickBooksClient(), request.realm_id, request.client_id, request.period
    )
    workspace.add_statements([statement])
    workspace.add_invoices(invoices)
    repository.save_workspace(db, workspace_id, advisor.advisor_id, workspace)
    return {
        "client_id": request.client_id,
        "period": request.period,
        "line_items_loaded": len(statement.line_items),
        "invoices_loaded": len(invoices),
    }


@app.get("/workspaces/{workspace_id}/clients")
def list_clients(workspace: Workspace = Depends(_get_workspace)) -> dict:
    return {"client_ids": workspace.client_ids}


@app.get("/workspaces/{workspace_id}/portfolio")
def portfolio_report(workspace: Workspace = Depends(_get_workspace)) -> list[dict]:
    """KPIs + variance analysis for every (client, period) pair on file.

    This is the single call an advisor's dashboard makes to refresh every
    client in their portfolio at once.
    """
    return [report.to_dict() for report in workspace.build_portfolio_report()]


@app.get("/workspaces/{workspace_id}/export/excel")
def export_portfolio_excel(workspace: Workspace = Depends(_get_workspace)) -> Response:
    """Multi-sheet .xlsx export of the whole portfolio (Line Items, KPIs, Variance,
    Forecast, Invoices), for advisors who want to build their own charts/pivots in
    Power BI or Excel. Auth accepts a `token` query param (see app/api/auth.py) since
    the frontend renders this as a plain <a href> download link, same as the PDF route.
    """
    workbook_bytes = generate_portfolio_workbook(workspace)
    return Response(
        content=workbook_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="alphatense_portfolio_export.xlsx"'},
    )


@app.get("/workspaces/{workspace_id}/clients/{client_id}/report")
def client_report(client_id: str, period: str, workspace: Workspace = Depends(_get_workspace)) -> dict:
    report = workspace.build_client_report(client_id, period)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"No actual data on file for client '{client_id}' in period '{period}'",
        )
    return report.to_dict()


@app.get("/workspaces/{workspace_id}/clients/{client_id}/report/pdf")
def client_report_pdf(
    client_id: str,
    period: str,
    periods_ahead: int = 3,
    as_of: str | None = None,
    starting_balance: float | None = None,
    weeks_ahead: int = 13,
    workspace: Workspace = Depends(_get_workspace),
) -> Response:
    """One-click executive PDF: KPIs + variance + forecast, plus aging and cash flow if requested.

    `as_of` (a real calendar date, unlike `period`) opts into the aging
    section (if invoices are on file) and, combined with
    `starting_balance`, the cash flow section. Omit both to get the same
    PDF as before -- these sections are additive, not required. Auth for
    this route accepts a `token` query param (see app/api/auth.py) since
    the frontend renders this as a plain <a href> download link.
    """
    report = workspace.build_client_report(client_id, period)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"No actual data on file for client '{client_id}' in period '{period}'",
        )

    try:
        forecast = workspace.build_forecast(client_id, periods_ahead=periods_ahead)
    except ForecastError:
        forecast = None

    aging_reports: list = []
    cash_flow = None
    if as_of is not None:
        try:
            as_of_date = date.fromisoformat(as_of)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid as_of date '{as_of}' (expected YYYY-MM-DD)"
            ) from exc

        for invoice_type in InvoiceType:
            aging_report = workspace.build_aging_report(client_id, invoice_type, as_of_date)
            if aging_report is not None:
                aging_reports.append(aging_report)

        if starting_balance is not None:
            cash_flow = workspace.build_cash_flow_forecast(
                client_id, starting_balance, as_of_date, weeks_ahead=weeks_ahead
            )

    pdf_bytes = generate_client_pdf(report, forecast, aging_reports=aging_reports, cash_flow=cash_flow)
    filename = f"{client_id}_{period}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/workspaces/{workspace_id}/clients/{client_id}/forecast")
def client_forecast(
    client_id: str, periods_ahead: int = 3, workspace: Workspace = Depends(_get_workspace)
) -> list[dict]:
    if client_id not in workspace.client_ids:
        raise HTTPException(status_code=404, detail=f"Unknown client_id: {client_id}")
    try:
        results = workspace.build_forecast(client_id, periods_ahead=periods_ahead)
    except ForecastError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [r.model_dump() for r in results]


@app.get("/workspaces/{workspace_id}/clients/{client_id}/aging")
def client_aging(
    client_id: str, type: str, as_of: str, workspace: Workspace = Depends(_get_workspace)
) -> dict:
    """AR or AP aging for one client, bucketed by days past due."""
    try:
        invoice_type = InvoiceType(type.strip().lower())
    except ValueError as exc:
        valid = ", ".join(t.value for t in InvoiceType)
        raise HTTPException(status_code=400, detail=f"Invalid type '{type}' (expected one of: {valid})") from exc

    try:
        as_of_date = date.fromisoformat(as_of)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid as_of date '{as_of}' (expected YYYY-MM-DD)") from exc

    report = workspace.build_aging_report(client_id, invoice_type, as_of_date)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"No {invoice_type.value.upper()} invoices on file for client '{client_id}'",
        )
    return report.model_dump()


@app.get("/workspaces/{workspace_id}/clients/{client_id}/cash-flow")
def client_cash_flow(
    client_id: str,
    starting_balance: float,
    as_of: str,
    weeks_ahead: int = 13,
    workspace: Workspace = Depends(_get_workspace),
) -> dict:
    """Project a client's cash balance week by week from their AR/AP invoices on file."""
    try:
        as_of_date = date.fromisoformat(as_of)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid as_of date '{as_of}' (expected YYYY-MM-DD)") from exc

    forecast = workspace.build_cash_flow_forecast(
        client_id, starting_balance, as_of_date, weeks_ahead=weeks_ahead
    )
    return forecast.model_dump(mode="json")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.post("/workspaces/{workspace_id}/chat")
def chat(request: ChatRequest, workspace: Workspace = Depends(_get_workspace)) -> dict:
    """Ask the conversational FP&A agent a question about this workspace's portfolio.

    Stateless like the rest of the API: pass back the `history` this
    endpoint returns on the next call to continue the conversation.
    """
    try:
        reply, history = ask(workspace, request.message, request.history)
    except AgentNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"reply": reply, "history": history}


@app.get("/workspaces/{workspace_id}/portfolio/forecast")
def portfolio_forecast(periods_ahead: int = 3, workspace: Workspace = Depends(_get_workspace)) -> dict:
    """Best/base/worst forecast for every client with enough history to project.

    Clients with fewer than 2 actual periods on file are silently skipped by
    the underlying engine (see Workspace.build_portfolio_forecast) rather
    than failing the whole portfolio refresh.
    """
    forecasts = workspace.build_portfolio_forecast(periods_ahead=periods_ahead)
    return {client_id: [r.model_dump() for r in results] for client_id, results in forecasts.items()}
