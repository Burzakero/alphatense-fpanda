"""
Cash flow forecast engine.

Projects a client's cash balance week by week from their open AR/AP
invoices -- the standard "13-week cash flow" a finance team builds before a
board meeting to answer "are we going to run out of cash?".

Deliberately scoped to invoices with a due_date already on file. There's no
balance sheet in this engine and no recurring-cost-with-a-date concept
outside of invoices, so blending in an opex run-rate derived from
FinancialStatement actuals risks double-counting against AP invoices that
already represent some of those same costs. Narrower and auditable beats
broader and quietly wrong -- same call as engine/forecast.py's "no LLM,
every number traces to something concrete" stance.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.models.domain import CashFlowForecast, CashFlowWeek, Invoice, InvoiceType


def _narrative_for(
    client_id: str,
    starting_balance: float,
    ending_balance: float,
    lowest_week: CashFlowWeek | None,
    weeks_ahead: int,
) -> str:
    sentence = (
        f"{client_id} starts at {starting_balance:,.0f} and is projected to end the "
        f"{weeks_ahead}-week window at {ending_balance:,.0f}"
    )
    if lowest_week is not None and lowest_week.ending_balance < starting_balance:
        sentence += (
            f", with the lowest point at {lowest_week.ending_balance:,.0f} "
            f"in the week of {lowest_week.week_start}"
        )
    sentence += (
        ". Based only on AR/AP invoices with a due date on file -- recurring costs not "
        "billed as an AP invoice (payroll, rent, etc.) aren't included."
    )
    return sentence


def project_cash_flow(
    client_id: str,
    invoices: list[Invoice],
    starting_balance: float,
    as_of: date,
    weeks_ahead: int = 13,
) -> CashFlowForecast:
    """Project a client's cash balance over `weeks_ahead` weeks from `as_of`.

    `invoices` should already be filtered to the client in question (both AR
    and AP) -- same convention as engine/aging.py's calculate_aging. Invoices
    already past due (due_date <= as_of) are assumed collected/paid in week
    0; invoices due beyond the window are excluded rather than distorting
    the near-term projection.
    """
    open_invoices = [inv for inv in invoices if inv.balance > 0.01]

    ar_by_week = [0.0] * weeks_ahead
    ap_by_week = [0.0] * weeks_ahead
    for inv in open_invoices:
        if inv.due_date <= as_of:
            week_index = 0
        else:
            week_index = (inv.due_date - as_of).days // 7
        if week_index >= weeks_ahead:
            continue

        if inv.type == InvoiceType.AR:
            ar_by_week[week_index] += inv.balance
        else:
            ap_by_week[week_index] += inv.balance

    weeks: list[CashFlowWeek] = []
    balance = starting_balance
    for i in range(weeks_ahead):
        week_start = as_of + timedelta(days=7 * i)
        net = round(ar_by_week[i] - ap_by_week[i], 2)
        balance = round(balance + net, 2)
        weeks.append(
            CashFlowWeek(
                week_start=week_start,
                week_end=week_start + timedelta(days=6),
                ar_inflows=round(ar_by_week[i], 2),
                ap_outflows=round(ap_by_week[i], 2),
                net_change=net,
                ending_balance=balance,
            )
        )

    ending_balance = weeks[-1].ending_balance if weeks else starting_balance
    lowest_week = min(weeks, key=lambda w: w.ending_balance) if weeks else None
    narrative = _narrative_for(client_id, starting_balance, ending_balance, lowest_week, weeks_ahead)

    return CashFlowForecast(
        client_id=client_id,
        as_of=as_of,
        starting_balance=starting_balance,
        weeks=weeks,
        narrative=narrative,
    )
