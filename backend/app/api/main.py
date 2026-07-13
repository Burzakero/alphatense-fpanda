"""
FastAPI HTTP layer over the FP&A + Forecast AI engine.

Exposes the Workspace orchestrator (see app/engine/workspace.py) as a small
set of REST endpoints an advisor's frontend (or Postman, or a script) can
call directly:

    POST /workspaces                                    -- upload a file, get a workspace_id back
    GET  /workspaces/{workspace_id}/clients              -- list client ids found in the file
    GET  /workspaces/{workspace_id}/portfolio            -- KPIs + variance for every client/period
    GET  /workspaces/{workspace_id}/clients/{client_id}/report?period=...
    GET  /workspaces/{workspace_id}/clients/{client_id}/forecast?periods_ahead=3
    GET  /workspaces/{workspace_id}/portfolio/forecast?periods_ahead=3
    POST /workspaces/{workspace_id}/invoices                     -- attach an AR/AP invoices file
    GET  /workspaces/{workspace_id}/clients/{client_id}/aging?type=ar&as_of=2026-06-30
    POST /workspaces/{workspace_id}/chat                          -- ask the conversational FP&A agent
    GET  /workspaces/{workspace_id}/clients/{client_id}/cash-flow?starting_balance=50000&as_of=2026-06-30&weeks_ahead=13

Workspaces are held in memory for the lifetime of the process, keyed by a
generated UUID -- there's no database yet (this is the first infrastructure
piece of Phase 2), so restarting the server clears all uploaded data. That's
fine for the current stage: the point of this layer is to unblock a
frontend and a PDF-export feature, not to add persistence. A real datastore
can replace `_WORKSPACES` later without changing any route signature.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from datetime import date

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app.agents.fpa_agent import AgentNotConfiguredError, ask
from app.api.auth import verify_access_key
from app.engine.forecast import ForecastError
from app.engine.workspace import Workspace
from app.ingestion.invoices import load_invoices
from app.ingestion.parser import IngestionError
from app.models.domain import InvoiceType
from app.reporting.pdf_report import generate_client_pdf

app = FastAPI(
    title="Alphatense AI -- FP&A Engine API",
    description="HTTP API over the ingestion, KPI, variance, and forecast engine.",
    version="0.1.0",
    dependencies=[Depends(verify_access_key)],
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

# In-memory workspace store: workspace_id -> Workspace.
# No persistence layer yet -- see module docstring.
_WORKSPACES: dict[str, Workspace] = {}


def _get_workspace(workspace_id: str) -> Workspace:
    workspace = _WORKSPACES.get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail=f"Unknown workspace_id: {workspace_id}")
    return workspace


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/workspaces", status_code=201)
async def create_workspace(file: UploadFile = File(...)) -> dict:
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

    return {"workspace_id": workspace_id, "client_ids": workspace.client_ids}


@app.post("/workspaces/{workspace_id}/invoices", status_code=201)
async def upload_invoices(workspace_id: str, file: UploadFile = File(...)) -> dict:
    """Attach an AR/AP invoices file to an existing workspace, on top of its P&L data."""
    workspace = _get_workspace(workspace_id)

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
    return {"invoices_loaded": len(invoices)}


@app.get("/workspaces/{workspace_id}/clients")
def list_clients(workspace_id: str) -> dict:
    workspace = _get_workspace(workspace_id)
    return {"client_ids": workspace.client_ids}


@app.get("/workspaces/{workspace_id}/portfolio")
def portfolio_report(workspace_id: str) -> list[dict]:
    """KPIs + variance analysis for every (client, period) pair on file.

    This is the single call an advisor's dashboard makes to refresh every
    client in their portfolio at once.
    """
    workspace = _get_workspace(workspace_id)
    return [report.to_dict() for report in workspace.build_portfolio_report()]


@app.get("/workspaces/{workspace_id}/clients/{client_id}/report")
def client_report(workspace_id: str, client_id: str, period: str) -> dict:
    workspace = _get_workspace(workspace_id)
    report = workspace.build_client_report(client_id, period)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"No actual data on file for client '{client_id}' in period '{period}'",
        )
    return report.to_dict()


@app.get("/workspaces/{workspace_id}/clients/{client_id}/report/pdf")
def client_report_pdf(workspace_id: str, client_id: str, period: str, periods_ahead: int = 3) -> Response:
    """One-click executive PDF: KPIs + variance + forecast (if there's enough history)."""
    workspace = _get_workspace(workspace_id)
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

    pdf_bytes = generate_client_pdf(report, forecast)
    filename = f"{client_id}_{period}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/workspaces/{workspace_id}/clients/{client_id}/forecast")
def client_forecast(workspace_id: str, client_id: str, periods_ahead: int = 3) -> list[dict]:
    workspace = _get_workspace(workspace_id)
    if client_id not in workspace.client_ids:
        raise HTTPException(status_code=404, detail=f"Unknown client_id: {client_id}")
    try:
        results = workspace.build_forecast(client_id, periods_ahead=periods_ahead)
    except ForecastError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [r.model_dump() for r in results]


@app.get("/workspaces/{workspace_id}/clients/{client_id}/aging")
def client_aging(workspace_id: str, client_id: str, type: str, as_of: str) -> dict:
    """AR or AP aging for one client, bucketed by days past due."""
    workspace = _get_workspace(workspace_id)

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
    workspace_id: str, client_id: str, starting_balance: float, as_of: str, weeks_ahead: int = 13
) -> dict:
    """Project a client's cash balance week by week from their AR/AP invoices on file."""
    workspace = _get_workspace(workspace_id)

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
def chat(workspace_id: str, request: ChatRequest) -> dict:
    """Ask the conversational FP&A agent a question about this workspace's portfolio.

    Stateless like the rest of the API: pass back the `history` this
    endpoint returns on the next call to continue the conversation.
    """
    workspace = _get_workspace(workspace_id)
    try:
        reply, history = ask(workspace, request.message, request.history)
    except AgentNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"reply": reply, "history": history}


@app.get("/workspaces/{workspace_id}/portfolio/forecast")
def portfolio_forecast(workspace_id: str, periods_ahead: int = 3) -> dict:
    """Best/base/worst forecast for every client with enough history to project.

    Clients with fewer than 2 actual periods on file are silently skipped by
    the underlying engine (see Workspace.build_portfolio_forecast) rather
    than failing the whole portfolio refresh.
    """
    workspace = _get_workspace(workspace_id)
    forecasts = workspace.build_portfolio_forecast(periods_ahead=periods_ahead)
    return {client_id: [r.model_dump() for r in results] for client_id, results in forecasts.items()}
