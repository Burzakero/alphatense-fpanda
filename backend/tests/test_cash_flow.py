from datetime import date

from app.engine.cash_flow import project_cash_flow
from app.models.domain import Invoice, InvoiceType

AS_OF = date(2026, 6, 30)


def _invoice(invoice_id, due_date, amount, amount_paid=0.0, inv_type=InvoiceType.AR, counterparty="Test Co"):
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


def test_no_invoices_produces_flat_balance():
    forecast = project_cash_flow("test-client", [], starting_balance=10000, as_of=AS_OF, weeks_ahead=4)

    assert len(forecast.weeks) == 4
    assert all(w.ending_balance == 10000 for w in forecast.weeks)
    assert all(w.ar_inflows == 0 and w.ap_outflows == 0 for w in forecast.weeks)


def test_overdue_invoice_lands_in_week_zero():
    invoices = [_invoice("INV-1", date(2026, 6, 1), 5000, inv_type=InvoiceType.AR)]
    forecast = project_cash_flow("test-client", invoices, starting_balance=1000, as_of=AS_OF, weeks_ahead=4)

    assert forecast.weeks[0].ar_inflows == 5000
    assert forecast.weeks[0].ending_balance == 6000


def test_due_date_equal_to_as_of_lands_in_week_zero():
    invoices = [_invoice("INV-1", AS_OF, 2000, inv_type=InvoiceType.AR)]
    forecast = project_cash_flow("test-client", invoices, starting_balance=0, as_of=AS_OF, weeks_ahead=4)

    assert forecast.weeks[0].ar_inflows == 2000


def test_invoice_due_in_future_week_lands_in_correct_bucket():
    # 14 days out -> week index 2
    invoices = [_invoice("INV-1", date(2026, 7, 14), 3000, inv_type=InvoiceType.AR)]
    forecast = project_cash_flow("test-client", invoices, starting_balance=0, as_of=AS_OF, weeks_ahead=4)

    assert forecast.weeks[2].ar_inflows == 3000
    assert forecast.weeks[0].ar_inflows == 0
    assert forecast.weeks[1].ar_inflows == 0


def test_invoice_beyond_horizon_is_excluded():
    invoices = [_invoice("INV-1", date(2026, 12, 1), 9000, inv_type=InvoiceType.AR)]
    forecast = project_cash_flow("test-client", invoices, starting_balance=1000, as_of=AS_OF, weeks_ahead=4)

    assert all(w.ar_inflows == 0 for w in forecast.weeks)
    assert forecast.weeks[-1].ending_balance == 1000


def test_ap_invoice_decreases_balance():
    invoices = [_invoice("BILL-1", date(2026, 6, 25), 4000, inv_type=InvoiceType.AP)]
    forecast = project_cash_flow("test-client", invoices, starting_balance=10000, as_of=AS_OF, weeks_ahead=2)

    assert forecast.weeks[0].ap_outflows == 4000
    assert forecast.weeks[0].ending_balance == 6000


def test_fully_paid_invoice_is_excluded():
    invoices = [_invoice("INV-1", date(2026, 6, 20), 5000, amount_paid=5000, inv_type=InvoiceType.AR)]
    forecast = project_cash_flow("test-client", invoices, starting_balance=1000, as_of=AS_OF, weeks_ahead=2)

    assert all(w.ar_inflows == 0 for w in forecast.weeks)


def test_running_balance_accumulates_across_weeks():
    invoices = [
        _invoice("INV-1", AS_OF, 5000, inv_type=InvoiceType.AR),  # week 0
        _invoice("BILL-1", date(2026, 7, 10), 2000, inv_type=InvoiceType.AP),  # week 1
    ]
    forecast = project_cash_flow("test-client", invoices, starting_balance=1000, as_of=AS_OF, weeks_ahead=3)

    assert forecast.weeks[0].ending_balance == 6000  # 1000 + 5000
    assert forecast.weeks[1].ending_balance == 4000  # 6000 - 2000
    assert forecast.weeks[2].ending_balance == 4000  # unchanged


def test_narrative_mentions_scope_caveat():
    forecast = project_cash_flow("test-client", [], starting_balance=1000, as_of=AS_OF, weeks_ahead=2)
    assert "recurring costs not billed as an AP invoice" in forecast.narrative
