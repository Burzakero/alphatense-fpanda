from app.integrations.xero.client import DEMO_TENANT_ID, FakeXeroClient
from app.integrations.xero.sync import sync_client_from_xero
from app.models.domain import AccountCategory, InvoiceType


def test_sync_client_from_xero_maps_statement_and_invoices():
    statement, invoices = sync_client_from_xero(
        FakeXeroClient(), DEMO_TENANT_ID, "xero-demo-co", "2026-06"
    )

    assert statement.client_id == "xero-demo-co"
    assert statement.period == "2026-06"
    assert statement.total(AccountCategory.REVENUE) > 0
    assert statement.total(AccountCategory.COGS) > 0
    assert statement.total(AccountCategory.TAX) > 0  # "Income Tax Expense" fixture line

    assert len(invoices) == 3
    assert all(inv.client_id == "xero-demo-co" for inv in invoices)
    assert sum(1 for inv in invoices if inv.type == InvoiceType.AR) == 2
    assert sum(1 for inv in invoices if inv.type == InvoiceType.AP) == 1


def test_sync_client_from_xero_unknown_tenant_returns_empty():
    statement, invoices = sync_client_from_xero(
        FakeXeroClient(), "some-other-tenant", "client-x", "2026-06"
    )

    assert statement.line_items == []
    assert invoices == []
