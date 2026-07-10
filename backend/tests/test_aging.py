from datetime import date

from app.engine.aging import calculate_aging
from app.models.domain import AgingBucket, Invoice, InvoiceType

AS_OF = date(2026, 6, 30)


def _invoice(invoice_id, due_date, amount, amount_paid=0.0, counterparty="Test Co", inv_type=InvoiceType.AR):
    return Invoice(
        client_id="test-client",
        invoice_id=invoice_id,
        type=inv_type,
        counterparty=counterparty,
        issue_date=date(2026, 1, 1),
        due_date=due_date,
        amount=amount,
        amount_paid=amount_paid,
    )


def _bucket_amount(report, bucket: AgingBucket) -> float:
    return next(b.amount for b in report.buckets if b.bucket == bucket)


def test_empty_invoice_list_produces_zeroed_report():
    report = calculate_aging("test-client", [], InvoiceType.AR, AS_OF)

    assert report.total_outstanding == 0
    assert all(b.amount == 0 for b in report.buckets)
    assert "no outstanding" in report.narrative.lower()


def test_invoices_bucketed_by_days_overdue():
    invoices = [
        _invoice("INV-1", date(2026, 7, 15), 100),  # not yet due -> current
        _invoice("INV-2", date(2026, 6, 15), 200),  # 15 days overdue -> 1-30
        _invoice("INV-3", date(2026, 5, 15), 300),  # 46 days overdue -> 31-60
        _invoice("INV-4", date(2026, 4, 15), 400),  # 76 days overdue -> 61-90
        _invoice("INV-5", date(2026, 1, 15), 500),  # 166 days overdue -> 90+
    ]
    report = calculate_aging("test-client", invoices, InvoiceType.AR, AS_OF)

    assert _bucket_amount(report, AgingBucket.CURRENT) == 100
    assert _bucket_amount(report, AgingBucket.DAYS_1_30) == 200
    assert _bucket_amount(report, AgingBucket.DAYS_31_60) == 300
    assert _bucket_amount(report, AgingBucket.DAYS_61_90) == 400
    assert _bucket_amount(report, AgingBucket.DAYS_90_PLUS) == 500
    assert report.total_outstanding == 1500


def test_fully_paid_invoice_is_excluded():
    invoices = [_invoice("INV-1", date(2026, 1, 1), 1000, amount_paid=1000)]
    report = calculate_aging("test-client", invoices, InvoiceType.AR, AS_OF)

    assert report.total_outstanding == 0


def test_partially_paid_invoice_uses_remaining_balance():
    invoices = [_invoice("INV-1", date(2026, 6, 15), 1000, amount_paid=400)]
    report = calculate_aging("test-client", invoices, InvoiceType.AR, AS_OF)

    assert report.total_outstanding == 600
    assert _bucket_amount(report, AgingBucket.DAYS_1_30) == 600


def test_narrative_names_largest_open_counterparty():
    invoices = [
        _invoice("INV-1", date(2026, 1, 15), 500, counterparty="Small Balance Co"),
        _invoice("INV-2", date(2026, 1, 15), 9000, counterparty="Big Balance Inc"),
    ]
    report = calculate_aging("test-client", invoices, InvoiceType.AR, AS_OF)

    assert "Big Balance Inc" in report.narrative
    assert "Small Balance Co" not in report.narrative


def test_due_date_equal_to_as_of_is_current():
    invoices = [_invoice("INV-1", AS_OF, 100)]
    report = calculate_aging("test-client", invoices, InvoiceType.AR, AS_OF)

    assert _bucket_amount(report, AgingBucket.CURRENT) == 100
