"""
Orchestrates a QuickBooksClient + the mapper into domain objects.

Same role as app/integrations/xero/sync.py, for QuickBooks.
"""

from __future__ import annotations

from app.integrations.quickbooks.client import QuickBooksClient
from app.integrations.quickbooks.mapper import map_invoices_and_bills, map_journal_entries
from app.models.domain import FinancialStatement, Invoice, Scenario


def sync_client_from_quickbooks(
    client: QuickBooksClient,
    realm_id: str,
    client_id: str,
    period: str,
    scenario: Scenario = Scenario.ACTUAL,
) -> tuple[FinancialStatement, list[Invoice]]:
    """Pull one client's P&L and AR/AP invoices from a QuickBooks company (realm).

    `client` is a QuickBooksClient -- real or fake. Callers own the
    workspace wiring (Workspace.add_statements() / add_invoices()).
    """
    raw_journal_entries = client.list_journal_entries(realm_id)
    raw_accounts = client.list_accounts(realm_id)
    statement = map_journal_entries(raw_journal_entries, raw_accounts, client_id, period, scenario)

    raw_invoices = client.list_invoices(realm_id)
    raw_bills = client.list_bills(realm_id)
    invoices = map_invoices_and_bills(raw_invoices, raw_bills, client_id)

    return statement, invoices
