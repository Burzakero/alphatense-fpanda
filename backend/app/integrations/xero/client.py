"""
Xero client interface + a fake implementation for development without OAuth.

`XeroClient` is the seam: it returns raw JSON shaped exactly like the real
Xero Accounting API (confirmed against developer.xero.com before writing
this, not guessed) for the three endpoints the mapper needs. `FakeXeroClient`
implements it with static fixtures for a demo tenant, so the sync path can
be built and tested end-to-end before real OAuth credentials exist.

When those credentials arrive, a `RealXeroClient` implementing the same
Protocol (OAuth2 bearer token + httpx calls to api.xro/2.0/...) swaps in
without changing `mapper.py`, `sync.py`, or the API route that calls this.

Endpoint shapes used here:
- GET /Invoices -> {"Invoices": [...]}, each with Type (ACCREC/ACCPAY),
  Contact.Name, DateString/DueDateString (ISO), Total/AmountDue/AmountPaid.
- GET /Journals -> {"Journals": [...]}, each with JournalDate and
  JournalLines (AccountCode, AccountName, AccountType, NetAmount).
- GET /Accounts -> {"Accounts": [...]}, each with Code, Name, Type -- used
  as the canonical source for classifying a journal line's account.

Deliberately skips the nested Reports/ProfitAndLoss endpoint (Header/
Section/Row/Cell tree) in favor of the flatter Journals+Accounts pair,
which maps far more directly onto our (account, category, amount) schema.
"""

from __future__ import annotations

from typing import Protocol

DEMO_TENANT_ID = "demo-tenant-xero"


class XeroClient(Protocol):
    """What the mapper/sync layer needs from a Xero connection, real or fake."""

    def list_invoices(self, tenant_id: str) -> dict: ...

    def list_journals(self, tenant_id: str) -> dict: ...

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

    def list_journals(self, tenant_id: str) -> dict:
        if tenant_id != DEMO_TENANT_ID:
            return {"Journals": []}
        return {
            "Journals": [
                {
                    "JournalID": "journal-demo-2026-06",
                    "JournalDate": "2026-06-30T00:00:00",
                    "JournalLines": [
                        {"AccountCode": "200", "AccountName": "Sales", "AccountType": "SALES", "NetAmount": 62000.0},
                        {
                            "AccountCode": "310",
                            "AccountName": "Cost of Goods Sold",
                            "AccountType": "DIRECTCOSTS",
                            "NetAmount": 21000.0,
                        },
                        {
                            "AccountCode": "400",
                            "AccountName": "Advertising",
                            "AccountType": "OVERHEADS",
                            "NetAmount": 4200.0,
                        },
                        {
                            "AccountCode": "477",
                            "AccountName": "Salaries",
                            "AccountType": "OVERHEADS",
                            "NetAmount": 18500.0,
                        },
                        {
                            "AccountCode": "270",
                            "AccountName": "Interest Income",
                            "AccountType": "OTHERINCOME",
                            "NetAmount": 180.0,
                        },
                        {
                            "AccountCode": "445",
                            "AccountName": "Income Tax Expense",
                            "AccountType": "EXPENSE",
                            "NetAmount": 3100.0,
                        },
                    ],
                }
            ]
        }

    def list_accounts(self, tenant_id: str) -> dict:
        if tenant_id != DEMO_TENANT_ID:
            return {"Accounts": []}
        return {
            "Accounts": [
                {"Code": "200", "Name": "Sales", "Type": "SALES"},
                {"Code": "310", "Name": "Cost of Goods Sold", "Type": "DIRECTCOSTS"},
                {"Code": "400", "Name": "Advertising", "Type": "OVERHEADS"},
                {"Code": "477", "Name": "Salaries", "Type": "OVERHEADS"},
                {"Code": "270", "Name": "Interest Income", "Type": "OTHERINCOME"},
                {"Code": "445", "Name": "Income Tax Expense", "Type": "EXPENSE"},
            ]
        }
