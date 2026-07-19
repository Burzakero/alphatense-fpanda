"""
Xero client interface + a fake implementation for development without OAuth.

`XeroClient` is the seam: it returns raw JSON shaped exactly like the real
Xero Accounting API for the endpoints the mapper needs. `FakeXeroClient`
implements it with static fixtures for a demo tenant, so the sync path can
be built and tested end-to-end before real OAuth credentials exist.

When those credentials arrive, a `RealXeroClient` implementing the same
Protocol (OAuth2 bearer token + httpx calls to api.xro/2.0/...) swaps in
without changing `mapper.py`, `sync.py`, or the API route that calls this.

Endpoint shapes used here:
- GET /Invoices -> {"Invoices": [...]}, each with Type (ACCREC/ACCPAY),
  Contact.Name, DateString/DueDateString (ISO), Total/AmountDue/AmountPaid.
- GET /Reports/ProfitAndLoss -> {"Reports": [{"Rows": [...]}]}, a nested
  Header/Section/Row/SummaryRow tree (see mapper.py for the exact walk).
  Used instead of the flatter GET /Journals endpoint -- confirmed live
  (2026-07-18, against a real connected org) that /Journals returns a 401
  "AuthorizationUnsuccessful" under Xero's newer granular-scopes model, no
  matter the scope requested. "Manual journals" (accounting.manualjournals.
  read) is a narrower, different feature (manually-created entries), not
  the transaction-derived journal lines /Journals returns -- there is no
  granular scope for that endpoint at all. Reports/ProfitAndLoss, covered
  by accounting.reports.profitandloss.read, is the confirmed-working path.
- GET /Accounts -> {"Accounts": [...]}, each with AccountID, Code, Name,
  Type -- used as the canonical source for classifying a report line's
  account (joined by AccountID, which is what the report's Cells expose).
"""

from __future__ import annotations

from typing import Protocol

import httpx

from app.integrations.xero import oauth

DEMO_TENANT_ID = "demo-tenant-xero"


class XeroClient(Protocol):
    """What the mapper/sync layer needs from a Xero connection, real or fake."""

    def list_invoices(self, tenant_id: str) -> dict: ...

    def get_profit_and_loss_report(self, tenant_id: str) -> dict: ...

    def list_accounts(self, tenant_id: str) -> dict: ...


class FakeXeroClient:
    """Static fixtures for one demo tenant, shaped like real Xero API responses.

    Not connected to any real Xero org -- there's no OAuth flow behind this.
    It exists so the rest of the integration (mapping, sync, the API route)
    can be built and tested now, and only the client needs replacing once
    real credentials are available.
    """

    def list_invoices(self, tenant_id: str) -> dict:
        if tenant_id != DEMO_TENANT_ID:
            return {"Invoices": []}
        return {
            "Invoices": [
                {
                    "Type": "ACCREC",
                    "InvoiceID": "inv-demo-001",
                    "InvoiceNumber": "INV-1001",
                    "Contact": {"ContactID": "contact-001", "Name": "Northwind Traders"},
                    "DateString": "2026-06-05T00:00:00",
                    "DueDateString": "2026-07-05T00:00:00",
                    "Status": "AUTHORISED",
                    "Total": 8200.0,
                    "AmountDue": 8200.0,
                    "AmountPaid": 0.0,
                    "CurrencyCode": "GBP",
                },
                {
                    "Type": "ACCREC",
                    "InvoiceID": "inv-demo-002",
                    "InvoiceNumber": "INV-1002",
                    "Contact": {"ContactID": "contact-002", "Name": "Globex Corp"},
                    "DateString": "2026-05-01T00:00:00",
                    "DueDateString": "2026-05-15T00:00:00",
                    "Status": "AUTHORISED",
                    "Total": 3400.0,
                    "AmountDue": 1000.0,
                    "AmountPaid": 2400.0,
                    "CurrencyCode": "GBP",
                },
                {
                    "Type": "ACCPAY",
                    "InvoiceID": "bill-demo-001",
                    "InvoiceNumber": "BILL-2001",
                    "Contact": {"ContactID": "contact-003", "Name": "CloudHost Ltd"},
                    "DateString": "2026-06-10T00:00:00",
                    "DueDateString": "2026-06-25T00:00:00",
                    "Status": "AUTHORISED",
                    "Total": 950.0,
                    "AmountDue": 950.0,
                    "AmountPaid": 0.0,
                    "CurrencyCode": "GBP",
                },
            ]
        }

    def get_profit_and_loss_report(self, tenant_id: str) -> dict:
        if tenant_id != DEMO_TENANT_ID:
            return {"Reports": [{"Rows": []}]}

        def account_row(account_id: str, name: str, amount: float) -> dict:
            return {
                "RowType": "Row",
                "Cells": [
                    {"Value": name, "Attributes": [{"Value": account_id, "Id": "account"}]},
                    {"Value": str(amount)},
                ],
            }

        def computed_row(label: str, amount: float) -> dict:
            """No account attribute -- same shape Xero uses for Gross/Net Profit, which
            aren't real GL accounts. The mapper's skip logic relies on this."""
            return {"RowType": "Row", "Cells": [{"Value": label}, {"Value": str(amount)}]}

        return {
            "Reports": [
                {
                    "ReportID": "ProfitAndLoss",
                    "Rows": [
                        {"RowType": "Header", "Cells": [{"Value": ""}, {"Value": "30 Jun 26"}]},
                        {
                            "RowType": "Section",
                            "Title": "Trading Income",
                            "Rows": [
                                account_row("acct-200", "Sales", 62000.0),
                                {"RowType": "SummaryRow", "Cells": [{"Value": "Total Trading Income"}, {"Value": "62000.0"}]},
                            ],
                        },
                        {
                            "RowType": "Section",
                            "Title": "Cost of Sales",
                            "Rows": [
                                account_row("acct-310", "Cost of Goods Sold", 21000.0),
                                {"RowType": "SummaryRow", "Cells": [{"Value": "Total Cost of Sales"}, {"Value": "21000.0"}]},
                            ],
                        },
                        {"RowType": "Section", "Title": "", "Rows": [computed_row("Gross Profit", 41000.0)]},
                        {
                            "RowType": "Section",
                            "Title": "Operating Expenses",
                            "Rows": [
                                account_row("acct-400", "Advertising", 4200.0),
                                account_row("acct-477", "Salaries", 18500.0),
                                account_row("acct-445", "Income Tax Expense", 3100.0),
                                {"RowType": "SummaryRow", "Cells": [{"Value": "Total Operating Expenses"}, {"Value": "25800.0"}]},
                            ],
                        },
                        {
                            "RowType": "Section",
                            "Title": "Other Income",
                            "Rows": [
                                account_row("acct-270", "Interest Income", 180.0),
                                {"RowType": "SummaryRow", "Cells": [{"Value": "Total Other Income"}, {"Value": "180.0"}]},
                            ],
                        },
                        {"RowType": "Section", "Title": "", "Rows": [computed_row("Net Profit", 15380.0)]},
                    ],
                }
            ]
        }

    def list_accounts(self, tenant_id: str) -> dict:
        if tenant_id != DEMO_TENANT_ID:
            return {"Accounts": []}
        return {
            "Accounts": [
                {"AccountID": "acct-200", "Code": "200", "Name": "Sales", "Type": "SALES"},
                {"AccountID": "acct-310", "Code": "310", "Name": "Cost of Goods Sold", "Type": "DIRECTCOSTS"},
                {"AccountID": "acct-400", "Code": "400", "Name": "Advertising", "Type": "OVERHEADS"},
                {"AccountID": "acct-477", "Code": "477", "Name": "Salaries", "Type": "OVERHEADS"},
                {"AccountID": "acct-270", "Code": "270", "Name": "Interest Income", "Type": "OTHERINCOME"},
                {"AccountID": "acct-445", "Code": "445", "Name": "Income Tax Expense", "Type": "EXPENSE"},
            ]
        }


class RealXeroClient:
    """OAuth2-backed XeroClient, calling the real Xero Accounting API.

    Implements the same Protocol as FakeXeroClient -- swapping this in
    doesn't change mapper.py, sync.py, or the API route that calls this.
    Fetches a live access token per call via `oauth.get_valid_access_token`
    (which refreshes transparently), so this class itself holds no
    credentials.
    """

    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self._http = http_client or httpx.Client(timeout=15.0)

    def list_invoices(self, tenant_id: str) -> dict:
        return self._get(tenant_id, "Invoices")

    def get_profit_and_loss_report(self, tenant_id: str) -> dict:
        return self._get(tenant_id, "Reports/ProfitAndLoss")

    def list_accounts(self, tenant_id: str) -> dict:
        return self._get(tenant_id, "Accounts")

    def _get(self, tenant_id: str, resource: str) -> dict:
        token = oauth.get_valid_access_token(tenant_id)
        response = self._http.get(
            f"{oauth.XERO_API_BASE}/{resource}",
            headers={
                "Authorization": f"Bearer {token}",
                "Xero-tenant-id": tenant_id,
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()
