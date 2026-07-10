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
from app.models.domain import ForecastResult, VarianceResult

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
        elements.append(Paragraph("Sin datos de comparación disponibles.", styles["BodyText"]))
        elements.append(Spacer(1, 12))
        return elements

    narrative_style = ParagraphStyle("narrative", parent=styles["BodyText"], fontSize=8, leading=10)
    rows = [["KPI", "Actual", "Comparación", "Delta", "Sev.", "Narrativa"]]
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
    rows = [["Periodo", "Escenario", "Net income", "Assumptions"]]
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


def generate_client_pdf(report: ClientReport, forecast: list[ForecastResult] | None = None) -> bytes:
    """Render one client/period's executive report to PDF bytes.

    `forecast` is optional: a client with fewer than 2 actual periods on
    file has no trend to project, and the forecast section is simply
    omitted rather than failing the whole report.
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

    elements.append(Paragraph(f"Informe Ejecutivo — {report.client_id}", styles["Title"]))
    elements.append(Paragraph(f"Periodo: {report.period}", styles["Normal"]))
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    elements.append(Paragraph(f"Generado: {generated_at}", styles["Normal"]))
    elements.append(Spacer(1, 16))

    kpis = report.actual_kpis
    elements.append(Paragraph("KPIs del periodo", styles["Heading2"]))
    kpi_rows = [
        ["Métrica", "Valor", "Margen"],
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

    doc.build(elements)
    return buffer.getvalue()
