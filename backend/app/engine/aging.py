"""
AR/AP aging engine.

Buckets a client's open invoices (one side of the ledger at a time -- AR or
AP) by days past due, and produces a natural-language narrative naming the
counterparty with the largest open balance -- the same "don't just restate
the number, say what's driving it" approach as engine/variance.py's
`_driver_phrase`.

Kept pure (no I/O) and takes an already client-filtered invoice list, same
convention as engine/kpis.py taking a single FinancialStatement rather than
filtering internally -- callers (Workspace) own the filtering.
"""

from __future__ import annotations

from datetime import date

from app.models.domain import AgingBucket, AgingBucketAmount, AgingReport, Invoice, InvoiceType

_BUCKET_ORDER = [
    AgingBucket.CURRENT,
    AgingBucket.DAYS_1_30,
    AgingBucket.DAYS_31_60,
    AgingBucket.DAYS_61_90,
    AgingBucket.DAYS_90_PLUS,
]

_BUCKET_LABELS = {
    AgingBucket.CURRENT: "not yet due",
    AgingBucket.DAYS_1_30: "1-30 days overdue",
    AgingBucket.DAYS_31_60: "31-60 days overdue",
    AgingBucket.DAYS_61_90: "61-90 days overdue",
    AgingBucket.DAYS_90_PLUS: "more than 90 days overdue",
}


def _bucket_for(days_overdue: int) -> AgingBucket:
    if days_overdue <= 0:
        return AgingBucket.CURRENT
    if days_overdue <= 30:
        return AgingBucket.DAYS_1_30
    if days_overdue <= 60:
        return AgingBucket.DAYS_31_60
    if days_overdue <= 90:
        return AgingBucket.DAYS_61_90
    return AgingBucket.DAYS_90_PLUS


def _narrative_for(
    client_id: str,
    invoice_type: InvoiceType,
    as_of: date,
    total_outstanding: float,
    bucket_totals: dict[AgingBucket, float],
    open_invoices: list[Invoice],
) -> str:
    type_label = "AR" if invoice_type == InvoiceType.AR else "AP"

    if total_outstanding <= 0:
        return f"{client_id} has no outstanding {type_label} as of {as_of}."

    sentence = f"{client_id} has {total_outstanding:,.0f} in outstanding {type_label} as of {as_of}"

    worst_bucket = next(
        (b for b in reversed(_BUCKET_ORDER) if b != AgingBucket.CURRENT and bucket_totals.get(b, 0) > 0),
        None,
    )
    if worst_bucket is not None:
        worst_amount = bucket_totals[worst_bucket]
        worst_pct = (worst_amount / total_outstanding) * 100
        sentence += f", of which {worst_amount:,.0f} ({worst_pct:.1f}%) is {_BUCKET_LABELS[worst_bucket]}"

    top_invoice = max(open_invoices, key=lambda inv: inv.balance)
    sentence += f". The largest open balance is with {top_invoice.counterparty} ({top_invoice.balance:,.0f})."

    return sentence


def calculate_aging(
    client_id: str,
    invoices: list[Invoice],
    invoice_type: InvoiceType,
    as_of: date,
) -> AgingReport:
    """Bucket one client's open AR or AP invoices by days past due.

    `invoices` should already be filtered to the client/type in question --
    an empty list is a valid input (a client with no open invoices of that
    type) and produces a zeroed-out report, not an error.
    """
    open_invoices = [inv for inv in invoices if inv.balance > 0.01]

    bucket_totals: dict[AgingBucket, float] = {b: 0.0 for b in _BUCKET_ORDER}
    bucket_counts: dict[AgingBucket, int] = {b: 0 for b in _BUCKET_ORDER}
    for inv in open_invoices:
        days_overdue = (as_of - inv.due_date).days
        bucket = _bucket_for(days_overdue)
        bucket_totals[bucket] += inv.balance
        bucket_counts[bucket] += 1

    total_outstanding = round(sum(bucket_totals.values()), 2)

    narrative = _narrative_for(client_id, invoice_type, as_of, total_outstanding, bucket_totals, open_invoices)

    return AgingReport(
        client_id=client_id,
        type=invoice_type,
        as_of=as_of,
        total_outstanding=total_outstanding,
        buckets=[
            AgingBucketAmount(bucket=b, amount=round(bucket_totals[b], 2), invoice_count=bucket_counts[b])
            for b in _BUCKET_ORDER
        ],
        narrative=narrative,
    )
