"""
Pure transforms: raw QuickBooks JSON -> our domain objects.

No I/O (same convention as app/integrations/xero/mapper.py and
ingestion/parser.py).
"""

from __future__ import annotations

from datetime import date

from app.models.domain import AccountCategory, FinancialStatement, Invoice, InvoiceType, LineItem, Scenario

_ACCOUNT_TYPE_TO_CATEGORY = {
    "Income": AccountCategory.REVENUE,
    "Cost of Goods Sold": AccountCategory.COGS,
    "Expense": AccountCategory.OPEX,
    "Other Income": AccountCategory.OTHER_INCOME,
    "Other Expense": AccountCategory.OTHER_EXPENSE,
}


def _map_invoice_like(raw_entity: dict, client_id: str, invoice_type: InvoiceType, counterparty_ref: str) -> Invoice:
    """Shared mapping for Invoice (AR) and Bill (AP) -- same fields, different ref key.

    QuickBooks' `Balance` is the OUTSTANDING amount, the opposite of Xero's
    `AmountPaid` (a paid-so-far total). Get this backwards and aging comes
    out wrong: a fully-paid invoice has `Balance == 0`, not `TotalAmt`.
    """
    total = float(raw_entity["TotalAmt"])
    balance = float(raw_entity["Balance"])
    return Invoice(
        client_id=client_id,
        invoice_id=raw_entity.get("DocNumber", raw_entity["Id"]),
        type=invoice_type,
        counterparty=raw_entity[counterparty_ref]["name"],
        issue_date=date.fromisoformat(raw_entity["TxnDate"]),
        due_date=date.fromisoformat(raw_entity["DueDate"]),
        amount=total,
        amount_paid=total - balance,
    )


def map_invoices_and_bills(raw_invoices: dict, raw_bills: dict, client_id: str) -> list[Invoice]:
    """Map QuickBooks Invoice (AR) + Bill (AP) query responses into our Invoice model."""
    invoices = [
        _map_invoice_like(raw, client_id, InvoiceType.AR, "CustomerRef")
        for raw in raw_invoices.get("QueryResponse", {}).get("Invoice", [])
    ]
    bills = [
        _map_invoice_like(raw, client_id, InvoiceType.AP, "VendorRef")
        for raw in raw_bills.get("QueryResponse", {}).get("Bill", [])
    ]
    return invoices + bills


def _category_for(account_type: str, account_name: str) -> AccountCategory:
    """Classify a QuickBooks account into our AccountCategory.

    Same name-based fallback for "tax" as the Xero mapper -- QuickBooks has
    no clean AccountType for corporation tax either, it's usually just an
    "Expense" account named something like "Income Tax Expense".
    """
    if "tax" in account_name.lower():
        return AccountCategory.TAX
    return _ACCOUNT_TYPE_TO_CATEGORY.get(account_type, AccountCategory.OPEX)


def map_journal_entries(
    raw_journal_entries: dict,
    raw_accounts: dict,
    client_id: str,
    period: str,
    scenario: Scenario = Scenario.ACTUAL,
) -> FinancialStatement:
    """Map QuickBooks JournalEntry + Account query responses into one FinancialStatement.

    `raw_accounts` (looked up by account Id) is the canonical source for
    each line's category, same rationale as xero/mapper.py's
    map_journal_lines: the chart of accounts is what an advisor actually
    maintains and corrects over time.
    """
    account_types = {acc["Id"]: acc["AccountType"] for acc in raw_accounts.get("QueryResponse", {}).get("Account", [])}
    account_names = {acc["Id"]: acc["Name"] for acc in raw_accounts.get("QueryResponse", {}).get("Account", [])}

    line_items: list[LineItem] = []
    for entry in raw_journal_entries.get("QueryResponse", {}).get("JournalEntry", []):
        for line in entry.get("Line", []):
            account_ref = line["JournalEntryLineDetail"]["AccountRef"]
            account_id = account_ref["value"]
            account_name = account_names.get(account_id, account_ref.get("name", account_id))
            account_type = account_types.get(account_id, "")
            line_items.append(
                LineItem(
                    client_id=client_id,
                    period=period,
                    scenario=scenario,
                    account=account_name,
                    category=_category_for(account_type, account_name),
                    amount=abs(float(line["Amount"])),
                )
            )

    return FinancialStatement(client_id=client_id, period=period, scenario=scenario, line_items=line_items)
