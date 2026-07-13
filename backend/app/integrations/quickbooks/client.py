"""
QuickBooks Online client interface + a fake implementation for dev without OAuth.

Same role as `app/integrations/xero/client.py`, for QuickBooks. Shapes here
were confirmed against real QuickBooks Online API responses (Intuit's docs
site, SDK references, and captured sandbox JSON) before writing this, not
guessed:

- GET .../query?query=select * from Invoice -> {"QueryResponse": {"Invoice": [...]}},
  CustomerRef {value, name}, TxnDate/DueDate as plain "YYYY-MM-DD", TotalAmt
  (invoice total) + Balance (outstanding, NOT amount paid -- see mapper.py).
- GET .../query?query=select * from Bill -> same shape, VendorRef instead
  of CustomerRef. QuickBooks models AR and AP as two separate entities,
  unlike Xero's single Invoice + Type flag.
- GET .../query?query=select * from JournalEntry -> {"QueryResponse":
  {"JournalEntry": [...]}}, each with a flat Line[] where each line has
  Amount and JournalEntryLineDetail.AccountRef {value, name}.
- GET .../query?query=select * from Account -> {"QueryResponse": {"Account": [...]}},
  each with Id, Name, AccountType (Income / Cost of Goods Sold / Expense /
  Other Income / Other Expense) -- the confirmed subset of the enum that
  actually shows up in P&L reports. Deliberately skips the nested
  reports/ProfitAndLoss endpoint (Row/ColData/group tree) in favor of this
  flatter Account+JournalEntry pair, same call as for Xero.
"""

from __future__ import annotations

from typing import Protocol

DEMO_REALM_ID = "demo-realm-quickbooks"


class QuickBooksClient(Protocol):
    """What the mapper/sync layer needs from a QuickBooks connection, real or fake."""

    def list_invoices(self, realm_id: str) -> dict: ...

    def list_bills(self, realm_id: str) -> dict: ...

    def list_journal_entries(self, realm_id: str) -> dict: ...

    def list_accounts(self, realm_id: str) -> dict: ...


class FakeQuickBooksClient:
    """Static fixtures for one demo realm, shaped like real QuickBooks API responses.

    Not connected to any real QuickBooks company -- there's no OAuth flow
    behind this. Exists so the integration can be built and tested now; a
    RealQuickBooksClient implementing the same Protocol swaps in once real
    credentials exist.
    """

    def list_invoices(self, realm_id: str) -> dict:
        if realm_id != DEMO_REALM_ID:
            return {"QueryResponse": {}}
        return {
            "QueryResponse": {
                "Invoice": [
                    {
                        "Id": "1",
                        "DocNumber": "1001",
                        "CustomerRef": {"value": "24", "name": "Sonnenschein Family Store"},
                        "TxnDate": "2026-06-05",
                        "DueDate": "2026-07-05",
                        "TotalAmt": 8200.0,
                        "Balance": 8200.0,
                    },
                    {
                        "Id": "2",
                        "DocNumber": "1002",
                        "CustomerRef": {"value": "31", "name": "Cool Cars Ltd"},
                        "TxnDate": "2026-05-01",
                        "DueDate": "2026-05-15",
                        "TotalAmt": 3400.0,
                        "Balance": 1000.0,
                    },
                ]
            }
        }

    def list_bills(self, realm_id: str) -> dict:
        if realm_id != DEMO_REALM_ID:
            return {"QueryResponse": {}}
        return {
            "QueryResponse": {
                "Bill": [
                    {
                        "Id": "1",
                        "DocNumber": "BILL-1",
                        "VendorRef": {"value": "56", "name": "CloudHost Ltd"},
                        "TxnDate": "2026-06-10",
                        "DueDate": "2026-06-25",
                        "TotalAmt": 950.0,
                        "Balance": 950.0,
                    }
                ]
            }
        }

    def list_journal_entries(self, realm_id: str) -> dict:
        if realm_id != DEMO_REALM_ID:
            return {"QueryResponse": {}}
        return {
            "QueryResponse": {
                "JournalEntry": [
                    {
                        "Id": "je-1",
                        "TxnDate": "2026-06-30",
                        "Line": [
                            {
                                "Amount": 62000.0,
                                "JournalEntryLineDetail": {"AccountRef": {"value": "200", "name": "Sales"}},
                            },
                            {
                                "Amount": 21000.0,
                                "JournalEntryLineDetail": {
                                    "AccountRef": {"value": "310", "name": "Cost of Goods Sold"}
                                },
                            },
                            {
                                "Amount": 4200.0,
                                "JournalEntryLineDetail": {"AccountRef": {"value": "400", "name": "Advertising"}},
                            },
                            {
                                "Amount": 18500.0,
                                "JournalEntryLineDetail": {"AccountRef": {"value": "477", "name": "Salaries"}},
                            },
                            {
                                "Amount": 180.0,
                                "JournalEntryLineDetail": {
                                    "AccountRef": {"value": "270", "name": "Interest Income"}
                                },
                            },
                            {
                                "Amount": 3100.0,
                                "JournalEntryLineDetail": {
                                    "AccountRef": {"value": "445", "name": "Income Tax Expense"}
                                },
                            },
                        ],
                    }
                ]
            }
        }

    def list_accounts(self, realm_id: str) -> dict:
        if realm_id != DEMO_REALM_ID:
            return {"QueryResponse": {}}
        return {
            "QueryResponse": {
                "Account": [
                    {"Id": "200", "Name": "Sales", "AccountType": "Income"},
                    {"Id": "310", "Name": "Cost of Goods Sold", "AccountType": "Cost of Goods Sold"},
                    {"Id": "400", "Name": "Advertising", "AccountType": "Expense"},
                    {"Id": "477", "Name": "Salaries", "AccountType": "Expense"},
                    {"Id": "270", "Name": "Interest Income", "AccountType": "Other Income"},
                    {"Id": "445", "Name": "Income Tax Expense", "AccountType": "Expense"},
                ]
            }
        }
