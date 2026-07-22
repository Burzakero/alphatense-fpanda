from datetime import date

from app.engine.working_capital import calculate_working_capital
from app.models.domain import Invoice, InvoiceType

AS_OF = date(2026, 6, 30)


def _invoice(invoice_id, amount, amount_paid=0.0, inv_type=InvoiceType.AR, counterparty="Test Co"):
    return Invoice(
        client_id="test-client",
        invoice_id=invoice_id,
        type=inv_type,
        counterparty=counterparty,
        issue_date=date(2026, 6, 1),
        due_date=date(2026, 6, 15),
        amount=amount,
        amount_paid=amount_paid,
    )


def test_zero_revenue_gives_no_dso():
    metrics = calculate_working_capital("test-client", "2026-06", [], period_revenue=0, period_cogs=1000, as_of=AS_OF)

    assert metrics.dso is None
    assert metrics.dpo == 0.0
    assert metrics.ccc is None


def test_zero_cogs_gives_no_dpo():
    metrics = calculate_working_capital("test-client", "2026-06", [], period_revenue=1000, period_cogs=0, as_of=AS_OF)

    assert metrics.dpo is None
    assert metrics.dso == 0.0
    assert metrics.ccc is None


def test_ccc_is_dso_minus_dpo_when_both_present():
    invoices = [
        _invoice("AR-1", 3000, inv_type=InvoiceType.AR),
        _invoice("AP-1", 1500, inv_type=InvoiceType.AP),
    ]

    metrics = calculate_working_capital(
        "test-client", "2026-06", invoices, period_revenue=9000, period_cogs=4500, as_of=AS_OF, days_in_period=30
    )

    assert metrics.ar_outstanding == 3000
    assert metrics.ap_outstanding == 1500
    assert metrics.dso == 10.0  # (3000 / 9000) * 30
    assert metrics.dpo == 10.0  # (1500 / 4500) * 30
    assert metrics.ccc == 0.0


def test_no_invoices_gives_zero_dso_and_dpo_not_none():
    metrics = calculate_working_capital(
        "test-client", "2026-06", [], period_revenue=1000, period_cogs=500, as_of=AS_OF
    )

    assert metrics.dso == 0.0
    assert metrics.dpo == 0.0
    assert metrics.ccc == 0.0


def test_only_open_invoices_count_toward_outstanding():
    invoices = [
        _invoice("AR-1", 1000, amount_paid=1000, inv_type=InvoiceType.AR),  # fully paid, excluded
        _invoice("AR-2", 500, inv_type=InvoiceType.AR),
    ]

    metrics = calculate_working_capital(
        "test-client", "2026-06", invoices, period_revenue=1000, period_cogs=500, as_of=AS_OF
    )

    assert metrics.ar_outstanding == 500


def test_narrative_documents_scope_limitations():
    metrics = calculate_working_capital(
        "test-client", "2026-06", [], period_revenue=1000, period_cogs=500, as_of=AS_OF
    )

    assert "inventory" in metrics.narrative
    assert "30" in metrics.narrative
