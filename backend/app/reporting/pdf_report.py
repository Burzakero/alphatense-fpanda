"""
One-click executive PDF report.

Renders a single client/period's KPIs, variance analysis, and forecast (if
available) into a presentable PDF -- the document an advisor hands to their
client or uses in the monthly review meeting, instead of screen-sharing the
dashboard.

Kept deliberately pure (bytes in, bytes out, no I/O) so it's unit-testable
and agnostic to how the caller obtained the report -- same pattern as
engine/kpis.py and engine/variance.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.engine.workspace import ClientReport
from app.models.domain import AgingReport, CashFlowForecast, ForecastResult, VarianceResult

_HEADER_BG = colors.HexColor("#eef2ff")
_GRID_COLOR = colors.HexColor("#e2e8f0")


def _currency(value: float) -> str:
    return f"£{value:,.0f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def _table_style(header_rows: int = 1) -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, header_rows - 1), _HEADER_BG),
            ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, _GRID_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _variance_section(title: str, variances: list[VarianceResult], styles) -> list:
    elements: list = [Paragraph(title, styles["Heading3"])]
    if not variances:
        elements.append(Paragraph("No comparison data available.", styles["BodyText"]))
        elements.append(Spacer(1, 12))
        return elements

    narrative_style = ParagraphStyle("narrative", parent=styles["BodyText"], fontSize=8, leading=10)
    rows = [["KPI", "Actual", "Comparison", "Delta", "Sev.", "Narrative"]]
    for v in variances:
        rows.append(
            [
                v.kpi_name,
                _currency(v.actual_value),
                _currency(v.comparison_value),
                f"{_currency(v.delta)} ({_pct(v.delta_pct)})",
                v.severity.value.upper(),
                Paragraph(v.narrative, narrative_style),
            ]
        )
    table = Table(rows, colWidths=[65, 55, 60, 80, 30, 187], repeatRows=1)
    table.setStyle(_table_style())
    elements.append(table)
    elements.append(Spacer(1, 12))
    return elements


def _forecast_section(forecast: list[ForecastResult], styles) -> list:
    elements: list = [Paragraph("Forecast (best / base / worst)", styles["Heading2"])]
    narrative_style = ParagraphStyle("forecast_narrative", parent=styles["BodyText"], fontSize=8, leading=10)
    rows = [["Period", "Scenario", "Net income", "Assumptions"]]
    for f in forecast:
        rows.append(
            [
                f.period,
                f.scenario.value.title(),
                _currency(f.net_income),
                Paragraph(f.assumptions, narrative_style),
            ]
        )
    table = Table(rows, colWidths=[55, 60, 80, 282], repeatRows=1)
    table.setStyle(_table_style())
    elements.append(table)
    return elements


def _aging_section(aging_reports: list[AgingReport], styles) -> list:
    elements: list = [Paragraph("Aging AR/AP", styles["Heading2"])]
    narrative_style = ParagraphStyle("aging_narrative", parent=styles["BodyText"], fontSize=8, leading=10)
    for report in aging_reports:
        elements.append(
            Paragraph(f"{report.type.value.upper()} — Total: {_currency(report.total_outstanding)}", styles["Heading3"])
        )
        rows = [["Bucket", "Amount", "Invoices"]]
        for b in report.buckets:
            rows.append([b.bucket.value, _currency(b.amount), str(b.invoice_count)])
        table = Table(rows, colWidths=[100, 150, 100])
        table.setStyle(_table_style())
        elements.append(table)
        elements.append(Paragraph(report.narrative, narrative_style))
        elements.append(Spacer(1, 12))
    return elements


def _cash_flow_section(cash_flow: CashFlowForecast, styles) -> list:
    elements: list = [
        Paragraph(f"Projected Cash Flow ({len(cash_flow.weeks)} weeks)", styles["Heading2"]),
    ]
    rows = [["Week", "AR", "AP", "Net", "Balance"]]
    for w in cash_flow.weeks:
        rows.append(
            [
                str(w.week_start),
                _currency(w.ar_inflows),
                _currency(w.ap_outflows),
                _currency(w.net_change),
                _currency(w.ending_balance),
            ]
        )
    table = Table(rows, colWidths=[80, 90, 90, 90, 90], repeatRows=1)
    table.setStyle(_table_style())
    elements.append(table)
    elements.append(Spacer(1, 6))
    narrative_style = ParagraphStyle("cash_flow_narrative", parent=styles["BodyText"], fontSize=8, leading=10)
    elements.append(Paragraph(cash_flow.narrative, narrative_style))
    return elements


def generate_client_pdf(
    report: ClientReport,
    forecast: list[ForecastResult] | None = None,
    aging_reports: list[AgingReport] | None = None,
    cash_flow: CashFlowForecast | None = None,
) -> bytes:
    """Render one client/period's executive report to PDF bytes.

    `forecast`, `aging_reports`, and `cash_flow` are all optional and each
    section is simply omitted when its data isn't available or wasn't
    requested -- a client with fewer than 2 actual periods on file has no
    trend to project, aging needs invoices on file, and cash flow needs an
    advisor-supplied starting balance.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"{report.client_id} {report.period}",
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    elements: list = []

    elements.append(Paragraph(f"Executive Report — {report.client_id}", styles["Title"]))
    elements.append(Paragraph(f"Period: {report.period}", styles["Normal"]))
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    elements.append(Paragraph(f"Generated: {generated_at}", styles["Normal"]))
    elements.append(Spacer(1, 16))

    kpis = report.actual_kpis
    elements.append(Paragraph("Period KPIs", styles["Heading2"]))
    kpi_rows = [
        ["Metric", "Value", "Margin"],
        ["Revenue", _currency(kpis.revenue), "—"],
        ["Gross profit", _currency(kpis.gross_profit), _pct(kpis.gross_margin_pct)],
        ["EBITDA", _currency(kpis.ebitda), _pct(kpis.ebitda_margin_pct)],
        ["Net income", _currency(kpis.net_income), _pct(kpis.net_margin_pct)],
    ]
    kpi_table = Table(kpi_rows, colWidths=[150, 100, 100])
    kpi_table.setStyle(_table_style())
    elements.append(kpi_table)
    elements.append(Spacer(1, 16))

    elements += _variance_section("Actual vs Budget", report.variances_vs_budget, styles)
    elements += _variance_section("Actual vs Prior", report.variances_vs_prior, styles)

    if forecast:
        elements += _forecast_section(forecast, styles)
        elements.append(Spacer(1, 16))

    if aging_reports:
        elements += _aging_section(aging_reports, styles)

    if cash_flow is not None:
        elements += _cash_flow_section(cash_flow, styles)

    doc.build(elements)
    return buffer.getvalue()
