"""
Working capital engine: DSO, DPO, Cash Conversion Cycle.

Complements engine/aging.py (which buckets open invoices by days overdue)
with the standard summary ratios a CFO reads at a glance: Days Sales
Outstanding, Days Payable Outstanding, and the Cash Conversion Cycle they
combine into.

Deliberately excludes a DIO (Days Inventory Outstanding) term -- this is a
services-business product and the domain model (see app/models/domain.py)
has no inventory concept anywhere, so CCC here is DSO - DPO, not the full
three-term formula. `days_in_period` is a fixed assumption (default 30),
not derived from the calendar length of the reporting period. Both
limitations are spelled out in the narrative, same "narrower and auditable
beats broader and quietly wrong" stance as engine/cash_flow.py.

Kept pure (no I/O) and takes an already client-filtered invoice list, same
convention as engine/aging.py and engine/cash_flow.py.
"""

from __future__ import annotations

from datetime import date

from app.models.domain import Invoice, InvoiceType, WorkingCapitalMetrics

_DEFAULT_DAYS_IN_PERIOD = 30


def _outstanding(invoices: list[Invoice], invoice_type: InvoiceType) -> float:
    return round(sum(inv.balance for inv in invoices if inv.type == invoice_type and inv.balance > 0.01), 2)


def _narrative_for(
    client_id: str,
    dso: float | None,
    dpo: float | None,
    ccc: float | None,
    days_in_period: int,
) -> str:
    parts = [f"DSO {dso:.1f} days" if dso is not None else "DSO n/a (no revenue on file)"]
    parts.append(f"DPO {dpo:.1f} days" if dpo is not None else "DPO n/a (no COGS on file)")
    if ccc is not None:
        parts.append(f"Cash Conversion Cycle {ccc:.1f} days")
    sentence = f"{client_id}'s working capital: " + ", ".join(parts) + "."
    sentence += (
        f" Assumes a {days_in_period}-day period and excludes inventory (DIO) -- this is a "
        "services business with no inventory data in the model, so CCC here is DSO - DPO only."
    )
    return sentence


def calculate_working_capital(
    client_id: str,
    period: str,
    invoices: list[Invoice],
    period_revenue: float,
    period_cogs: float,
    as_of: date,
    days_in_period: int = _DEFAULT_DAYS_IN_PERIOD,
) -> WorkingCapitalMetrics:
    """Compute DSO/DPO/CCC for one client/period as of a given date.

    `invoices` should already be filtered to the client in question (both
    AR and AP) -- same convention as calculate_aging/project_cash_flow.
    `period_revenue`/`period_cogs` are the ACTUAL statement's totals for
    the same period (the caller already has these from calculate_kpis).
    """
    ar_outstanding = _outstanding(invoices, InvoiceType.AR)
    ap_outstanding = _outstanding(invoices, InvoiceType.AP)

    dso = None if period_revenue <= 0 else round((ar_outstanding / period_revenue) * days_in_period, 1)
    dpo = None if period_cogs <= 0 else round((ap_outstanding / period_cogs) * days_in_period, 1)
    ccc = None if dso is None or dpo is None else round(dso - dpo, 1)

    return WorkingCapitalMetrics(
        client_id=client_id,
        period=period,
        as_of=as_of,
        ar_outstanding=ar_outstanding,
        ap_outstanding=ap_outstanding,
        days_in_period=days_in_period,
        dso=dso,
        dpo=dpo,
        ccc=ccc,
        narrative=_narrative_for(client_id, dso, dpo, ccc, days_in_period),
    )
