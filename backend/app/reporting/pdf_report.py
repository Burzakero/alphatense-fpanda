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
from pathlib import Path

from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.engine.variance import material_variances
from app.engine.workspace import ClientReport
from app.models.domain import (
    AgingReport,
    AIExecutiveNarrative,
    CashFlowForecast,
    ClientTrend,
    EbitdaBridge,
    ForecastResult,
    Severity,
    VarianceResult,
    WorkingCapitalMetrics,
)

_HEADER_BG = colors.HexColor("#eef2ff")
_GRID_COLOR = colors.HexColor("#e2e8f0")
_HIGH_BG = colors.HexColor("#fee2e2")
_MEDIUM_BG = colors.HexColor("#fef3c7")
_FOOTER_COLOR = colors.HexColor("#94a3b8")
_LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"

_SCENARIO_HEX = {"best": "#059669", "base": "#1b69b0", "worst": "#dc2626"}


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


def _severity_row_style(variances: list[VarianceResult], header_rows: int = 1) -> TableStyle:
    """Highlight HIGH/MEDIUM severity rows -- plain-text "HIGH" alone has no visual weight."""
    commands = []
    for i, v in enumerate(variances):
        row = header_rows + i
        if v.severity == Severity.HIGH:
            commands.append(("BACKGROUND", (0, row), (-1, row), _HIGH_BG))
        elif v.severity == Severity.MEDIUM:
            commands.append(("BACKGROUND", (0, row), (-1, row), _MEDIUM_BG))
    return TableStyle(commands)


def _executive_summary(report: ClientReport) -> str:
    """Compose a 2-3 sentence summary from data already on the report -- no AI call, so
    generation stays deterministic, fast, and testable (same engine/agent split as the
    rest of the codebase, see CLAUDE.md)."""
    kpis = report.actual_kpis
    sentences = [
        f"{report.client_id} generated {_currency(kpis.revenue)} in revenue for {report.period}, "
        f"with net income of {_currency(kpis.net_income)} ({_pct(kpis.net_margin_pct)} margin)."
    ]
    top_movers = material_variances(report.variances_vs_budget) or material_variances(
        report.variances_vs_prior
    )
    if top_movers:
        biggest = max(top_movers, key=lambda v: abs(v.delta_pct or 0))
        sentences.append(biggest.narrative)
    return " ".join(sentences)


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
    table = Table(rows, colWidths=[65, 55, 60, 75, 45, 177], repeatRows=1)
    table.setStyle(_table_style())
    table.setStyle(_severity_row_style(variances))
    elements.append(table)
    elements.append(Spacer(1, 12))
    return elements


def _risks_opportunities_section(narrative: AIExecutiveNarrative, styles) -> list:
    elements: list = []
    bullet_style = ParagraphStyle("bullet", parent=styles["BodyText"], fontSize=9, leading=12, leftIndent=10)
    if narrative.risks:
        elements.append(Paragraph("Key Risks", styles["Heading3"]))
        for risk in narrative.risks:
            elements.append(Paragraph(f"• {risk}", bullet_style))
        elements.append(Spacer(1, 8))
    if narrative.opportunities:
        elements.append(Paragraph("Opportunities", styles["Heading3"]))
        for opportunity in narrative.opportunities:
            elements.append(Paragraph(f"• {opportunity}", bullet_style))
        elements.append(Spacer(1, 8))
    return elements


def _ebitda_bridge_chart(bridge: EbitdaBridge) -> Drawing:
    """Hand-drawn waterfall: reportlab's barcharts don't support floating bars, so each
    step's cumulative (y0, y1) is computed manually and drawn as a Rect -- total steps
    (Budget/Actual EBITDA) anchor at 0, delta steps float on the running total."""
    bars: list[tuple[str, float, bool, float, float]] = []
    running = 0.0
    for step in bridge.steps:
        if step.is_total:
            y0, y1 = 0.0, step.value
            running = step.value
        else:
            y0 = running
            y1 = running + step.value
            running = y1
        bars.append((step.label, step.value, step.is_total, y0, y1))

    all_vals = [v for bar in bars for v in (bar[3], bar[4])] + [0.0]
    vmin, vmax = min(all_vals), max(all_vals)
    vrange = (vmax - vmin) or 1.0

    plot_x, plot_y, plot_w, plot_h = 40.0, 30.0, 400.0, 100.0
    gap = plot_w / len(bars)
    bar_w = gap * 0.6

    def _y(v: float) -> float:
        return plot_y + (v - vmin) / vrange * plot_h

    drawing = Drawing(460, 160)
    zero_px = _y(0.0)
    drawing.add(Line(plot_x, zero_px, plot_x + plot_w, zero_px, strokeColor=colors.HexColor("#cbd5e1"), strokeWidth=0.5))

    for i, (label, value, is_total, y0, y1) in enumerate(bars):
        x = plot_x + i * gap + (gap - bar_w) / 2
        y_bottom, y_top = _y(min(y0, y1)), _y(max(y0, y1))
        if is_total:
            fill = colors.HexColor(_SCENARIO_HEX["base"])
        elif value >= 0:
            fill = colors.HexColor(_SCENARIO_HEX["best"])
        else:
            fill = colors.HexColor(_SCENARIO_HEX["worst"])
        drawing.add(Rect(x, y_bottom, bar_w, max(y_top - y_bottom, 1.2), fillColor=fill, strokeColor=None))
        drawing.add(String(x + bar_w / 2, y_top + 4, _currency(value), fontSize=7, textAnchor="middle"))
        drawing.add(String(x + bar_w / 2, plot_y - 14, label, fontSize=7, textAnchor="middle"))

    return drawing


def _ebitda_bridge_section(bridge: EbitdaBridge, styles) -> list:
    elements: list = [Paragraph("EBITDA Bridge (Budget → Actual)", styles["Heading2"])]
    elements.append(_ebitda_bridge_chart(bridge))
    elements.append(Spacer(1, 6))
    narrative_style = ParagraphStyle("bridge_narrative", parent=styles["BodyText"], fontSize=8, leading=10)
    elements.append(Paragraph(bridge.narrative, narrative_style))
    elements.append(Spacer(1, 16))
    return elements


def _trend_chart(periods: list[str], values: list[float], value_format: str) -> Drawing:
    drawing = Drawing(180, 100)
    chart = HorizontalLineChart()
    chart.x, chart.y = 30, 22
    chart.width, chart.height = 140, 62
    chart.categoryAxis.categoryNames = periods
    chart.categoryAxis.labels.fontSize = 5
    chart.valueAxis.labelTextFormat = value_format
    chart.valueAxis.labels.fontSize = 5
    chart.data = [values]
    chart.lines[0].strokeColor = colors.HexColor(_SCENARIO_HEX["base"])
    chart.lines[0].strokeWidth = 1.3
    drawing.add(chart)
    return drawing


def _trend_section(trend: ClientTrend, styles) -> list:
    elements: list = [Paragraph("12-Month Trend", styles["Heading2"])]
    revenue = [p.revenue for p in trend.points]
    ebitda = [p.ebitda for p in trend.points]
    margin = [p.net_margin_pct or 0.0 for p in trend.points]

    heading_style = ParagraphStyle("trend_heading", parent=styles["BodyText"], fontSize=8, alignment=1)
    grid = [
        [Paragraph("Revenue", heading_style), Paragraph("EBITDA", heading_style), Paragraph("Net Margin %", heading_style)],
        [
            _trend_chart(trend.periods, revenue, "£%0.0f"),
            _trend_chart(trend.periods, ebitda, "£%0.0f"),
            _trend_chart(trend.periods, margin, "%0.0f%%"),
        ],
    ]
    table = Table(grid, colWidths=[160, 160, 160])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elements.append(table)
    elements.append(Spacer(1, 6))
    narrative_style = ParagraphStyle("trend_narrative", parent=styles["BodyText"], fontSize=8, leading=10)
    elements.append(Paragraph(trend.narrative, narrative_style))
    elements.append(Spacer(1, 16))
    return elements


def _working_capital_section(working_capital: WorkingCapitalMetrics, styles) -> list:
    elements: list = [Paragraph("Working Capital", styles["Heading2"])]
    rows = [
        ["Metric", "Value"],
        ["DSO (Days Sales Outstanding)", f"{working_capital.dso:.1f} days" if working_capital.dso is not None else "—"],
        ["DPO (Days Payable Outstanding)", f"{working_capital.dpo:.1f} days" if working_capital.dpo is not None else "—"],
        ["Cash Conversion Cycle", f"{working_capital.ccc:.1f} days" if working_capital.ccc is not None else "—"],
    ]
    table = Table(rows, colWidths=[250, 100])
    table.setStyle(_table_style())
    elements.append(table)
    elements.append(Spacer(1, 6))
    narrative_style = ParagraphStyle("wc_narrative", parent=styles["BodyText"], fontSize=8, leading=10)
    elements.append(Paragraph(working_capital.narrative, narrative_style))
    elements.append(Spacer(1, 12))
    return elements


def _forecast_chart(forecast: list[ForecastResult]) -> Drawing:
    periods = sorted({f.period for f in forecast})
    by_scenario: dict[str, dict[str, float]] = {}
    for f in forecast:
        by_scenario.setdefault(f.scenario.value, {})[f.period] = f.net_income
    scenarios = [s for s in ("best", "base", "worst") if s in by_scenario]

    drawing = Drawing(450, 160)
    chart = HorizontalLineChart()
    chart.x, chart.y = 45, 30
    chart.width, chart.height = 390, 115
    chart.categoryAxis.categoryNames = periods
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labelTextFormat = "£%0.0f"
    chart.valueAxis.labels.fontSize = 7
    chart.data = [[by_scenario[s].get(p, 0) for p in periods] for s in scenarios]
    for i, s in enumerate(scenarios):
        chart.lines[i].strokeColor = colors.HexColor(_SCENARIO_HEX[s])
        chart.lines[i].strokeWidth = 1.5
    drawing.add(chart)
    return drawing


def _forecast_section(forecast: list[ForecastResult], styles) -> list:
    elements: list = [Paragraph("Forecast (best / base / worst)", styles["Heading2"])]
    legend_style = ParagraphStyle("forecast_legend", parent=styles["BodyText"], fontSize=8)
    legend = "&nbsp;&nbsp;&nbsp;".join(
        f'<font color="{_SCENARIO_HEX[s]}">●</font> {s.title()}'
        for s in ("best", "base", "worst")
        if any(f.scenario.value == s for f in forecast)
    )
    elements.append(Paragraph(legend, legend_style))
    elements.append(Spacer(1, 4))
    elements.append(_forecast_chart(forecast))
    elements.append(Spacer(1, 8))

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


def _cash_flow_chart(cash_flow: CashFlowForecast) -> Drawing:
    weeks = [str(w.week_start) for w in cash_flow.weeks]
    balances = [w.ending_balance for w in cash_flow.weeks]

    drawing = Drawing(450, 170)
    chart = HorizontalLineChart()
    chart.x, chart.y = 45, 40
    chart.width, chart.height = 390, 115
    chart.categoryAxis.categoryNames = weeks
    chart.categoryAxis.labels.fontSize = 6
    chart.categoryAxis.labels.angle = 45
    chart.categoryAxis.labels.dy = -8
    chart.valueAxis.labelTextFormat = "£%0.0f"
    chart.valueAxis.labels.fontSize = 7
    chart.data = [balances]
    chart.lines[0].strokeColor = colors.HexColor(_SCENARIO_HEX["base"])
    chart.lines[0].strokeWidth = 1.5
    drawing.add(chart)
    return drawing


def _cash_flow_section(cash_flow: CashFlowForecast, styles) -> list:
    elements: list = [
        Paragraph(f"Projected Cash Flow ({len(cash_flow.weeks)} weeks)", styles["Heading2"]),
    ]
    elements.append(_cash_flow_chart(cash_flow))
    elements.append(Spacer(1, 8))
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


def _draw_footer(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_FOOTER_COLOR)
    canvas.drawString(1.5 * cm, 1 * cm, "Alphatense — Confidential")
    canvas.drawRightString(A4[0] - 1.5 * cm, 1 * cm, f"Page {doc.page}")
    canvas.restoreState()


def generate_client_pdf(
    report: ClientReport,
    forecast: list[ForecastResult] | None = None,
    aging_reports: list[AgingReport] | None = None,
    cash_flow: CashFlowForecast | None = None,
    bridge: EbitdaBridge | None = None,
    trend: ClientTrend | None = None,
    working_capital: WorkingCapitalMetrics | None = None,
    ai_narrative: AIExecutiveNarrative | None = None,
) -> bytes:
    """Render one client/period's executive report to PDF bytes.

    `forecast`, `aging_reports`, `cash_flow`, `bridge`, `trend`, and
    `working_capital` are all optional and each section is simply omitted
    when its data isn't available or wasn't requested -- a client with
    fewer than 2 actual periods on file has no trend to project, aging
    needs invoices on file, cash flow needs an advisor-supplied starting
    balance, and the EBITDA bridge needs both actual and budget data for
    the period. `ai_narrative`, if provided, replaces the deterministic
    executive summary and adds a Risks/Opportunities section -- the caller
    (the API route) is responsible for generating it and falling back to
    None on any failure; this function never calls out to an LLM itself.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"{report.client_id} {report.period}",
        topMargin=1.5 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    elements: list = []

    if _LOGO_PATH.exists():
        logo = Image(str(_LOGO_PATH), width=1.3 * cm, height=1.3 * cm)
        logo.hAlign = "LEFT"
        elements.append(logo)
        elements.append(Spacer(1, 6))

    elements.append(Paragraph(f"Executive Report — {report.client_id}", styles["Title"]))
    elements.append(Paragraph(f"Period: {report.period}", styles["Normal"]))
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    elements.append(Paragraph(f"Generated: {generated_at}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    summary_style = ParagraphStyle(
        "executive_summary", parent=styles["BodyText"], fontSize=9.5, leading=13
    )
    summary_text = ai_narrative.summary if ai_narrative is not None else _executive_summary(report)
    elements.append(Paragraph(summary_text, summary_style))
    elements.append(Spacer(1, 8))

    if ai_narrative is not None and (ai_narrative.risks or ai_narrative.opportunities):
        elements += _risks_opportunities_section(ai_narrative, styles)
    elements.append(Spacer(1, 8))

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

    if bridge is not None:
        elements += _ebitda_bridge_section(bridge, styles)

    elements += _variance_section("Actual vs Budget", report.variances_vs_budget, styles)
    elements += _variance_section("Actual vs Prior", report.variances_vs_prior, styles)

    if trend is not None:
        elements += _trend_section(trend, styles)

    if forecast:
        elements += _forecast_section(forecast, styles)
        elements.append(Spacer(1, 16))

    if aging_reports:
        elements += _aging_section(aging_reports, styles)

    if working_capital is not None:
        elements += _working_capital_section(working_capital, styles)

    if cash_flow is not None:
        elements += _cash_flow_section(cash_flow, styles)

    doc.build(elements, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()
