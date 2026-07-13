"""
Orchestrates a XeroClient + the mapper into domain objects.

Plays the same role for Xero that Workspace.from_file() plays for a CSV/
Excel upload: given a data source, produce the FinancialStatement and
Invoice objects the rest of the engine already knows how to consume.
"""

from __future__ import annotations

from app.integrations.xero.client import XeroClient
from app.integrations.xero.mapper import map_invoices, map_journal_lines
from app.models.domain import FinancialStatement, Invoice, Scenario


def sync_client_from_xero(
    client: XeroClient,
    tenant_id: str,
    client_id: str,
    period: str,
    scenario: Scenario = Scenario.ACTUAL,
) -> tuple[FinancialStatement, list[Invoice]]:
    """Pull one client's P&L and AR/AP invoices from a Xero tenant.

    `client` is a `XeroClient` -- real or fake. Callers own the workspace
    wiring (`Workspace.add_statements()` / `add_invoices()`); this function
    only fetches and maps.
    """
    raw_journals = client.list_journals(tenant_id)
    raw_accounts = client.list_accounts(tenant_id)
    statement = map_journal_lines(raw_journals, raw_accounts, client_id, period, scenario)

    raw_invoices = client.list_invoices(tenant_id)
    invoices = map_invoices(raw_invoices, client_id)

    return statement, invoices
