from app.integrations.quickbooks.client import DEMO_REALM_ID, FakeQuickBooksClient
from app.integrations.quickbooks.sync import sync_client_from_quickbooks
from app.models.domain import AccountCategory, InvoiceType


def test_sync_client_from_quickbooks_maps_statement_and_invoices():
    statement, invoices = sync_client_from_quickbooks(
        FakeQuickBooksClient(), DEMO_REALM_ID, "quickbooks-demo-co", "2026-06"
    )

    assert statement.client_id == "quickbooks-demo-co"
    assert statement.period == "2026-06"
    assert statement.total(AccountCategory.REVENUE) > 0
    assert statement.total(AccountCategory.COGS) > 0
    assert statement.total(AccountCategory.TAX) > 0  # "Income Tax Expense" fixture line

    assert len(invoices) == 3
    assert all(inv.client_id == "quickbooks-demo-co" for inv in invoices)
    assert sum(1 for inv in invoices if inv.type == InvoiceType.AR) == 2
    assert sum(1 for inv in invoices if inv.type == InvoiceType.AP) == 1

    partially_paid = next(inv for inv in invoices if inv.counterparty == "Cool Cars Ltd")
    assert partially_paid.amount_paid == 2400.0
    assert partially_paid.balance == 1000.0


def test_sync_client_from_quickbooks_unknown_realm_returns_empty():
    statement, invoices = sync_client_from_quickbooks(
        FakeQuickBooksClient(), "some-other-realm", "client-x", "2026-06"
    )

    assert statement.line_items == []
    assert invoices == []
