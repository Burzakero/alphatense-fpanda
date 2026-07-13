from datetime import date

from app.integrations.quickbooks.mapper import map_invoices_and_bills, map_journal_entries
from app.models.domain import AccountCategory, InvoiceType, Scenario

RAW_INVOICES = {
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

RAW_BILLS = {
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


def test_map_invoices_and_bills_maps_type_and_fields():
    invoices = map_invoices_and_bills(RAW_INVOICES, RAW_BILLS, client_id="acme-ltd")

    assert len(invoices) == 3
    fully_open, partially_paid, bill = invoices

    assert fully_open.type == InvoiceType.AR
    assert fully_open.invoice_id == "1001"
    assert fully_open.counterparty == "Sonnenschein Family Store"
    assert fully_open.issue_date == date(2026, 6, 5)
    assert fully_open.due_date == date(2026, 7, 5)
    assert fully_open.amount == 8200.0
    assert fully_open.balance == 8200.0

    assert bill.type == InvoiceType.AP
    assert bill.counterparty == "CloudHost Ltd"


def test_map_invoices_and_bills_balance_is_outstanding_not_paid():
    """QuickBooks' `Balance` is the opposite convention from Xero's `AmountPaid` --
    this is the point the plan flagged as most likely to break."""
    invoices = map_invoices_and_bills(RAW_INVOICES, {"QueryResponse": {}}, client_id="acme-ltd")
    _, partially_paid = invoices

    assert partially_paid.amount == 3400.0
    assert partially_paid.amount_paid == 2400.0
    assert partially_paid.balance == 1000.0


def test_map_invoices_and_bills_empty():
    assert map_invoices_and_bills({"QueryResponse": {}}, {"QueryResponse": {}}, client_id="acme-ltd") == []


RAW_ACCOUNTS = {
    "QueryResponse": {
        "Account": [
            {"Id": "200", "Name": "Sales", "AccountType": "Income"},
            {"Id": "310", "Name": "Cost of Goods Sold", "AccountType": "Cost of Goods Sold"},
            {"Id": "400", "Name": "Advertising", "AccountType": "Expense"},
            {"Id": "270", "Name": "Interest Income", "AccountType": "Other Income"},
            {"Id": "445", "Name": "Income Tax Expense", "AccountType": "Expense"},
            {"Id": "999", "Name": "Miscellaneous", "AccountType": "SOMETHING_UNKNOWN"},
        ]
    }
}


def _journal_entry_line(account_id, account_name, amount):
    return {"Amount": amount, "JournalEntryLineDetail": {"AccountRef": {"value": account_id, "name": account_name}}}


def test_map_journal_entries_categorizes_by_account_type():
    raw_journal_entries = {
        "QueryResponse": {
            "JournalEntry": [
                {
                    "Line": [
                        _journal_entry_line("200", "Sales", 62000.0),
                        _journal_entry_line("310", "Cost of Goods Sold", 21000.0),
                        _journal_entry_line("400", "Advertising", 4200.0),
                        _journal_entry_line("270", "Interest Income", 180.0),
                    ]
                }
            ]
        }
    }

    statement = map_journal_entries(raw_journal_entries, RAW_ACCOUNTS, "acme-ltd", "2026-06", Scenario.ACTUAL)

    assert statement.client_id == "acme-ltd"
    assert statement.period == "2026-06"
    assert statement.scenario == Scenario.ACTUAL
    assert statement.total(AccountCategory.REVENUE) == 62000.0
    assert statement.total(AccountCategory.COGS) == 21000.0
    assert statement.total(AccountCategory.OPEX) == 4200.0
    assert statement.total(AccountCategory.OTHER_INCOME) == 180.0


def test_map_journal_entries_tax_heuristic_by_name():
    raw_journal_entries = {
        "QueryResponse": {"JournalEntry": [{"Line": [_journal_entry_line("445", "Income Tax Expense", 3100.0)]}]}
    }

    statement = map_journal_entries(raw_journal_entries, RAW_ACCOUNTS, "acme-ltd", "2026-06")

    assert statement.total(AccountCategory.TAX) == 3100.0
    assert statement.total(AccountCategory.OPEX) == 0.0


def test_map_journal_entries_unknown_account_type_falls_back_to_opex():
    raw_journal_entries = {
        "QueryResponse": {"JournalEntry": [{"Line": [_journal_entry_line("999", "Miscellaneous", 500.0)]}]}
    }

    statement = map_journal_entries(raw_journal_entries, RAW_ACCOUNTS, "acme-ltd", "2026-06")

    assert statement.total(AccountCategory.OPEX) == 500.0


def test_map_journal_entries_negative_amount_is_absolute():
    raw_journal_entries = {
        "QueryResponse": {"JournalEntry": [{"Line": [_journal_entry_line("200", "Sales", -62000.0)]}]}
    }

    statement = map_journal_entries(raw_journal_entries, RAW_ACCOUNTS, "acme-ltd", "2026-06")

    assert statement.total(AccountCategory.REVENUE) == 62000.0
