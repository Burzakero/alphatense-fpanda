from datetime import date

from app.integrations.xero.mapper import map_invoices, map_profit_and_loss
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
        {"AccountID": "acct-200", "Code": "200", "Name": "Sales", "Type": "SALES"},
        {"AccountID": "acct-310", "Code": "310", "Name": "Cost of Goods Sold", "Type": "DIRECTCOSTS"},
        {"AccountID": "acct-400", "Code": "400", "Name": "Advertising", "Type": "OVERHEADS"},
        {"AccountID": "acct-270", "Code": "270", "Name": "Interest Income", "Type": "OTHERINCOME"},
        {"AccountID": "acct-445", "Code": "445", "Name": "Income Tax Expense", "Type": "EXPENSE"},
        {"AccountID": "acct-999", "Code": "999", "Name": "Miscellaneous", "Type": "SOMETHING_UNKNOWN"},
    ]
}


def _account_row(account_id, amount):
    return {
        "RowType": "Row",
        "Cells": [{"Value": "placeholder", "Attributes": [{"Value": account_id, "Id": "account"}]}, {"Value": str(amount)}],
    }


def _summary_row(label, amount):
    return {"RowType": "SummaryRow", "Cells": [{"Value": label}, {"Value": str(amount)}]}


def _computed_row(label, amount):
    """A row with no account attribute -- e.g. Gross/Net Profit. Must be skipped."""
    return {"RowType": "Row", "Cells": [{"Value": label}, {"Value": str(amount)}]}


def _report(rows):
    return {"Reports": [{"Rows": rows}]}


def test_map_profit_and_loss_categorizes_by_account_type():
    raw_report = _report(
        [
            {"RowType": "Header", "Cells": [{"Value": ""}, {"Value": "30 Jun 26"}]},
            {
                "RowType": "Section",
                "Title": "Trading Income",
                "Rows": [_account_row("acct-200", 62000.0), _summary_row("Total Trading Income", 62000.0)],
            },
            {
                "RowType": "Section",
                "Title": "Cost of Sales",
                "Rows": [_account_row("acct-310", 21000.0)],
            },
            {"RowType": "Section", "Title": "", "Rows": [_computed_row("Gross Profit", 41000.0)]},
            {
                "RowType": "Section",
                "Title": "Operating Expenses",
                "Rows": [_account_row("acct-400", 4200.0)],
            },
            {
                "RowType": "Section",
                "Title": "Other Income",
                "Rows": [_account_row("acct-270", 180.0)],
            },
            {"RowType": "Section", "Title": "", "Rows": [_computed_row("Net Profit", 15380.0)]},
        ]
    )

    statement = map_profit_and_loss(raw_report, RAW_ACCOUNTS, "acme-ltd", "2026-06", Scenario.ACTUAL)

    assert statement.client_id == "acme-ltd"
    assert statement.period == "2026-06"
    assert statement.scenario == Scenario.ACTUAL
    assert statement.total(AccountCategory.REVENUE) == 62000.0
    assert statement.total(AccountCategory.COGS) == 21000.0
    assert statement.total(AccountCategory.OPEX) == 4200.0
    assert statement.total(AccountCategory.OTHER_INCOME) == 180.0


def test_map_profit_and_loss_skips_summary_and_computed_rows():
    raw_report = _report(
        [
            {
                "RowType": "Section",
                "Title": "Trading Income",
                "Rows": [_account_row("acct-200", 62000.0), _summary_row("Total Trading Income", 62000.0)],
            },
            {"RowType": "Section", "Title": "", "Rows": [_computed_row("Gross Profit", 62000.0)]},
        ]
    )

    statement = map_profit_and_loss(raw_report, RAW_ACCOUNTS, "acme-ltd", "2026-06")

    assert len(statement.line_items) == 1
    assert statement.line_items[0].account == "Sales"


def test_map_profit_and_loss_tax_heuristic_by_name():
    raw_report = _report(
        [{"RowType": "Section", "Title": "Operating Expenses", "Rows": [_account_row("acct-445", 3100.0)]}]
    )

    statement = map_profit_and_loss(raw_report, RAW_ACCOUNTS, "acme-ltd", "2026-06")

    assert statement.total(AccountCategory.TAX) == 3100.0
    assert statement.total(AccountCategory.OPEX) == 0.0


def test_map_profit_and_loss_unknown_account_type_falls_back_to_opex():
    raw_report = _report(
        [{"RowType": "Section", "Title": "Operating Expenses", "Rows": [_account_row("acct-999", 500.0)]}]
    )

    statement = map_profit_and_loss(raw_report, RAW_ACCOUNTS, "acme-ltd", "2026-06")

    assert statement.total(AccountCategory.OPEX) == 500.0


def test_map_profit_and_loss_negative_amount_is_absolute():
    raw_report = _report(
        [{"RowType": "Section", "Title": "Trading Income", "Rows": [_account_row("acct-200", -62000.0)]}]
    )

    statement = map_profit_and_loss(raw_report, RAW_ACCOUNTS, "acme-ltd", "2026-06")

    assert statement.total(AccountCategory.REVENUE) == 62000.0
