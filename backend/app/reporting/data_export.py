"""
Multi-sheet Excel export of a whole portfolio, for advisors who want to build
their own charts/pivots in Power BI or Excel instead of (or alongside) the
in-app views.

Kept deliberately pure (bytes in, bytes out, no I/O) -- same pattern as
reporting/pdf_report.py. Every domain model is already a pydantic v2
BaseModel, so each sheet is just `model.model_dump()` rows through pandas.
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from app.engine.workspace import ClientReport, Workspace
from app.models.domain import ForecastResult, Invoice, KPISet, LineItem, VarianceResult

_LINE_ITEM_COLUMNS = list(LineItem.model_fields.keys())
_KPI_COLUMNS = list(KPISet.model_fields.keys())
_VARIANCE_COLUMNS = list(VarianceResult.model_fields.keys())
_FORECAST_COLUMNS = list(ForecastResult.model_fields.keys())
_INVOICE_COLUMNS = [*Invoice.model_fields.keys(), "balance"]

_NOTES = [
    "This workbook is a raw data export of your Alphatense portfolio, for building "
    "your own reports/charts in Power BI or Excel.",
    "Line Items: every P&L account amount on file, across all clients, periods and "
    "scenarios (actual/budget/prior).",
    "KPIs: computed revenue/margin/EBITDA/net income per client and period (actual "
    "scenario only).",
    "Variance: actual vs budget and actual vs prior comparisons, with severity and "
    "narrative.",
    "Forecast: best/base/worst net income projections, for clients with enough "
    "history to project (2+ actual periods on file).",
    "Invoices: raw AR/AP invoices on file, including a computed 'balance' column "
    "(amount - amount_paid).",
    "Not included: Aging and Cash Flow. Both require an advisor-supplied as-of date "
    "(cash flow also needs a starting balance) that isn't stored anywhere in bulk -- "
    "use the in-app Aging & Cash Flow tab per client for those.",
]


def _to_df(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns)


def _line_item_rows(workspace: Workspace) -> list[dict]:
    return [li.model_dump() for statement in workspace.statements for li in statement.line_items]


def _kpi_rows(reports: list[ClientReport]) -> list[dict]:
    return [r.actual_kpis.model_dump() for r in reports]


def _variance_rows(reports: list[ClientReport]) -> list[dict]:
    return [
        v.model_dump() for r in reports for v in (*r.variances_vs_budget, *r.variances_vs_prior)
    ]


def _forecast_rows(portfolio_forecast: dict[str, list[ForecastResult]]) -> list[dict]:
    return [f.model_dump() for forecasts in portfolio_forecast.values() for f in forecasts]


def _invoice_rows(workspace: Workspace) -> list[dict]:
    return [{**inv.model_dump(), "balance": inv.balance} for inv in workspace.invoices]


def generate_portfolio_workbook(workspace: Workspace) -> bytes:
    """Export every client/period on file as a multi-sheet .xlsx workbook.

    Aging and Cash Flow are intentionally excluded -- both need an
    advisor-supplied as-of date (cash flow also a starting balance) that
    isn't stored anywhere in bulk, so a portfolio-wide export would have to
    guess those inputs. See the Notes sheet for the same explanation, kept
    in the file itself since advisors won't necessarily read this docstring.
    """
    reports = workspace.build_portfolio_report()
    portfolio_forecast = workspace.build_portfolio_forecast()

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _to_df(_line_item_rows(workspace), _LINE_ITEM_COLUMNS).to_excel(
            writer, sheet_name="Line Items", index=False
        )
        _to_df(_kpi_rows(reports), _KPI_COLUMNS).to_excel(writer, sheet_name="KPIs", index=False)
        _to_df(_variance_rows(reports), _VARIANCE_COLUMNS).to_excel(
            writer, sheet_name="Variance", index=False
        )
        _to_df(_forecast_rows(portfolio_forecast), _FORECAST_COLUMNS).to_excel(
            writer, sheet_name="Forecast", index=False
        )
        _to_df(_invoice_rows(workspace), _INVOICE_COLUMNS).to_excel(
            writer, sheet_name="Invoices", index=False
        )
        pd.DataFrame({"Note": _NOTES}).to_excel(writer, sheet_name="Notes", index=False)

    return buffer.getvalue()
