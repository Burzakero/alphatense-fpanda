"""
Pure transforms: raw Xero JSON -> our domain objects.

No I/O here (same convention as ingestion/parser.py) -- these functions take
whatever a XeroClient returned and produce Invoice / FinancialStatement
objects the rest of the engine already knows how to work with. Kept
separate from client.py so a RealXeroClient can reuse this unchanged.
"""

from __future__ import annotations

from datetime import date

from app.models.domain import AccountCategory, FinancialStatement, Invoice, InvoiceType, LineItem, Scenario

_XERO_TYPE_TO_INVOICE_TYPE = {
    "ACCREC": InvoiceType.AR,
    "ACCPAY": InvoiceType.AP,
}

_ACCOUNT_TYPE_TO_CATEGORY = {
    "SALES": AccountCategory.REVENUE,
    "REVENUE": AccountCategory.REVENUE,
    "DIRECTCOSTS": AccountCategory.COGS,
    "OTHERINCOME": AccountCategory.OTHER_INCOME,
    "OVERHEADS": AccountCategory.OPEX,
    "EXPENSE": AccountCategory.OPEX,
    "WAGESEXPENSE": AccountCategory.OPEX,
    "DEPRECIATN": AccountCategory.OPEX,
}


def _parse_xero_date(date_string: str) -> date:
    """Xero's *String date fields are ISO with a trailing T00:00:00 -- drop the time."""
    return date.fromisoformat(date_string.split("T")[0])


def map_invoices(raw: dict, client_id: str) -> list[Invoice]:
    """Map a raw `GET /Invoices` response into our Invoice model.

    Uses `InvoiceNumber` (human-readable, e.g. "INV-1001") as our
    `invoice_id` rather than Xero's internal `InvoiceID` GUID.
    """
    invoices: list[Invoice] = []
    for raw_invoice in raw.get("Invoices", []):
        invoice_type = _XERO_TYPE_TO_INVOICE_TYPE[raw_invoice["Type"]]
        invoices.append(
            Invoice(
                client_id=client_id,
                invoice_id=raw_invoice["InvoiceNumber"],
                type=invoice_type,
                counterparty=raw_invoice["Contact"]["Name"],
                issue_date=_parse_xero_date(raw_invoice["DateString"]),
                due_date=_parse_xero_date(raw_invoice["DueDateString"]),
                amount=float(raw_invoice["Total"]),
                amount_paid=float(raw_invoice.get("AmountPaid", 0.0)),
            )
        )
    return invoices


def _category_for(account_type: str, account_name: str) -> AccountCategory:
    """Classify a Xero account into our AccountCategory.

    Xero has no clean "tax" AccountType for P&L purposes (corporation tax is
    usually just an EXPENSE-type account), so this falls back to a
    name-based heuristic before the type-based table -- an explicit,
    documented simplification rather than a silent one.
    """
    if "tax" in account_name.lower():
        return AccountCategory.TAX
    return _ACCOUNT_TYPE_TO_CATEGORY.get(account_type, AccountCategory.OPEX)


def _account_id_from_row(row: dict) -> str | None:
    """Return the account GUID a report Row references, or None if it's not a real account.

    Xero marks a genuine GL-account line with an `Id: "account"` attribute on
    its first Cell. SummaryRows (subtotals) and the computed Gross/Net Profit
    rows have no such attribute -- that absence is what lets us skip them
    without special-casing section titles, which vary by org/locale.
    """
    cells = row.get("Cells", [])
    if not cells:
        return None
    for attribute in cells[0].get("Attributes", []):
        if attribute.get("Id") == "account":
            return attribute.get("Value")
    return None


def _iter_report_account_rows(rows: list[dict]):
    """Recursively walk a Reports/ProfitAndLoss Rows tree, yielding only real account Rows."""
    for row in rows:
        row_type = row.get("RowType")
        if row_type == "Section":
            yield from _iter_report_account_rows(row.get("Rows", []))
        elif row_type == "Row" and _account_id_from_row(row) is not None:
            yield row


def map_profit_and_loss(
    raw_report: dict,
    raw_accounts: dict,
    client_id: str,
    period: str,
    scenario: Scenario = Scenario.ACTUAL,
) -> FinancialStatement:
    """Map `GET /Reports/ProfitAndLoss` + `GET /Accounts` into one FinancialStatement.

    `raw_accounts` is the canonical source for each account's category
    (looked up by AccountID, which is what the report's Cells expose) rather
    than trusting the report row's own label, since a real chart of accounts
    is the source of truth an advisor would actually maintain and correct
    over time.
    """
    accounts_by_id = {acc["AccountID"]: acc for acc in raw_accounts.get("Accounts", [])}

    reports = raw_report.get("Reports", [])
    rows = reports[0].get("Rows", []) if reports else []

    line_items: list[LineItem] = []
    for row in _iter_report_account_rows(rows):
        cells = row["Cells"]
        account_id = _account_id_from_row(row)
        account = accounts_by_id.get(account_id, {})
        account_name = account.get("Name", cells[0]["Value"])
        account_type = account.get("Type", "")
        line_items.append(
            LineItem(
                client_id=client_id,
                period=period,
                scenario=scenario,
                account=account_name,
                category=_category_for(account_type, account_name),
                amount=abs(float(cells[1]["Value"])),
            )
        )

    return FinancialStatement(client_id=client_id, period=period, scenario=scenario, line_items=line_items)
