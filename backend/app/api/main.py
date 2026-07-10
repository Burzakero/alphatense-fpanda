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

Workspaces are held in memory for the lifetime of the process, keyed by a
generated UUID -- there's no database yet (this is the first infrastructure
piece of Phase 2), so restarting the server clears all uploaded data. That's
fine for the current stage: the point of this layer is to unblock a
frontend and a PDF-export feature, not to add persistence. A real datastore
can replace `_WORKSPACES` later without changing any route signature.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.engine.forecast import ForecastError
from app.engine.workspace import Workspace
from app.ingestion.parser import IngestionError
from app.reporting.pdf_report import generate_client_pdf

app = FastAPI(
    title="Alphatense AI -- FP&A Engine API",
    description="HTTP API over the ingestion, KPI, variance, and forecast engine.",
    version="0.1.0",
)

# Allows the Vite dev server (frontend/) to call this API directly during
# local development. Tighten to the deployed frontend origin in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
