from datetime import date

from app.integrations.xero.mapper import map_invoices, map_journal_lines
from app.models.domain import AccountCategory, InvoiceType, Scenario

RAW_INVOICES = {
    "Invoices": [
        {
            "Type": "ACCREC",
            "InvoiceNumber": "INV-1001",
            "Contact": {"Name": "Northwind Traders"},
            "DateString": "2026-06-05T00:00:00",
            "DueDateString": "2026-07-05T00:00:00",
            "Total": 8200.0,
            "AmountPaid": 0.0,
        },
        {
            "Type": "ACCPAY",
            "InvoiceNumber": "BILL-2001",
            "Contact": {"Name": "CloudHost Ltd"},
            "DateString": "2026-06-10T00:00:00",
            "DueDateString": "2026-06-25T00:00:00",
            "Total": 950.0,
            "AmountPaid": 200.0,
        },
    ]
}


def test_map_invoices_maps_type_and_fields():
    invoices = map_invoices(RAW_INVOICES, client_id="acme-ltd")

    assert len(invoices) == 2
    ar, ap = invoices

    assert ar.type == InvoiceType.AR
    assert ar.invoice_id == "INV-1001"
    assert ar.counterparty == "Northwind Traders"
    assert ar.issue_date == date(2026, 6, 5)
    assert ar.due_date == date(2026, 7, 5)
    assert ar.amount == 8200.0
    assert ar.balance == 8200.0

    assert ap.type == InvoiceType.AP
    assert ap.amount_paid == 200.0
    assert ap.balance == 750.0


def test_map_invoices_empty():
    assert map_invoices({"Invoices": []}, client_id="acme-ltd") == []


RAW_ACCOUNTS = {
    "Accounts": [
        {"Code": "200", "Name": "Sales", "Type": "SALES"},
        {"Code": "310", "Name": "Cost of Goods Sold", "Type": "DIRECTCOSTS"},
        {"Code": "400", "Name": "Advertising", "Type": "OVERHEADS"},
        {"Code": "270", "Name": "Interest Income", "Type": "OTHERINCOME"},
        {"Code": "445", "Name": "Income Tax Expense", "Type": "EXPENSE"},
        {"Code": "999", "Name": "Miscellaneous", "Type": "SOMETHING_UNKNOWN"},
    ]
}


def _journal_line(code, amount):
    return {"AccountCode": code, "NetAmount": amount}


def test_map_journal_lines_categorizes_by_account_type():
    raw_journals = {
        "Journals": [
            {
                "JournalLines": [
                    _journal_line("200", 62000.0),
                    _journal_line("310", 21000.0),
                    _journal_line("400", 4200.0),
                    _journal_line("270", 180.0),
                ]
            }
        ]
    }

    statement = map_journal_lines(raw_journals, RAW_ACCOUNTS, "acme-ltd", "2026-06", Scenario.ACTUAL)

    assert statement.client_id == "acme-ltd"
    assert statement.period == "2026-06"
    assert statement.scenario == Scenario.ACTUAL
    assert statement.total(AccountCategory.REVENUE) == 62000.0
    assert statement.total(AccountCategory.COGS) == 21000.0
    assert statement.total(AccountCategory.OPEX) == 4200.0
    assert statement.total(AccountCategory.OTHER_INCOME) == 180.0


def test_map_journal_lines_tax_heuristic_by_name():
    raw_journals = {"Journals": [{"JournalLines": [_journal_line("445", 3100.0)]}]}

    statement = map_journal_lines(raw_journals, RAW_ACCOUNTS, "acme-ltd", "2026-06")

    assert statement.total(AccountCategory.TAX) == 3100.0
    assert statement.total(AccountCategory.OPEX) == 0.0


def test_map_journal_lines_unknown_account_type_falls_back_to_opex():
    raw_journals = {"Journals": [{"JournalLines": [_journal_line("999", 500.0)]}]}

    statement = map_journal_lines(raw_journals, RAW_ACCOUNTS, "acme-ltd", "2026-06")

    assert statement.total(AccountCategory.OPEX) == 500.0


def test_map_journal_lines_negative_net_amount_is_absolute():
    raw_journals = {"Journals": [{"JournalLines": [_journal_line("200", -62000.0)]}]}

    statement = map_journal_lines(raw_journals, RAW_ACCOUNTS, "acme-ltd", "2026-06")

    assert statement.total(AccountCategory.REVENUE) == 62000.0
