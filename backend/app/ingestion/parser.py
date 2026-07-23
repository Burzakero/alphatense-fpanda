"""
Ingestion layer: turns a raw Excel/CSV upload into normalized FinancialStatement
objects, one per (client, period, scenario) combination.

Expected input schema (columns, case-insensitive, order doesn't matter):

    client_id | client_name | period | scenario | account | category | amount

- client_id:   short stable identifier for the end client, e.g. "acme-ltd"
- client_name: display name, e.g. "Acme Ltd" (optional if client_id given)
- period:      "2026-06" style label. Any consistent label works.
- scenario:    one of actual / budget / prior (case-insensitive)
- account:     the GL account / line description, e.g. "Marketing"
- category:    one of revenue / cogs / opex / other_income / other_expense / tax
- amount:      numeric. Expenses should be entered as positive numbers
               (the engine treats cogs/opex/other_expense/tax as costs).

This is intentionally file-format agnostic: the same normalization runs
whether the source was a multi-client CSV export or an Excel workbook, and
in later phases the same function signature can be backed by a Xero/
QuickBooks connector instead of a file path without touching the engine.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.models.domain import AccountCategory, FinancialStatement, LineItem, Scenario

_REQUIRED_COLUMNS = {"period", "scenario", "account", "category", "amount"}

# Common accounting synonyms for the fixed AccountCategory vocabulary. Real
# advisory P&Ls label categories inconsistently (e.g. "Cost of Sales" instead
# of "cogs") -- this lets those files load without the advisor hand-editing
# the source spreadsheet, while anything not on this list still gets a clear
# error naming the accepted values.
_CATEGORY_SYNONYMS: dict[str, AccountCategory] = {
    "sales": AccountCategory.REVENUE,
    "income": AccountCategory.REVENUE,
    "turnover": AccountCategory.REVENUE,
    "net sales": AccountCategory.REVENUE,
    "total revenue": AccountCategory.REVENUE,
    "cost of sales": AccountCategory.COGS,
    "cost of goods sold": AccountCategory.COGS,
    "cost of revenue": AccountCategory.COGS,
    "direct costs": AccountCategory.COGS,
    "direct cost": AccountCategory.COGS,
    "operating expenses": AccountCategory.OPEX,
    "operating expense": AccountCategory.OPEX,
    "expenses": AccountCategory.OPEX,
    "expense": AccountCategory.OPEX,
    "overheads": AccountCategory.OPEX,
    "overhead": AccountCategory.OPEX,
    "sg&a": AccountCategory.OPEX,
    "administrative expenses": AccountCategory.OPEX,
    "other income": AccountCategory.OTHER_INCOME,
    "non-operating income": AccountCategory.OTHER_INCOME,
    "miscellaneous income": AccountCategory.OTHER_INCOME,
    "other expenses": AccountCategory.OTHER_EXPENSE,
    "other expense": AccountCategory.OTHER_EXPENSE,
    "non-operating expense": AccountCategory.OTHER_EXPENSE,
    "non-operating expenses": AccountCategory.OTHER_EXPENSE,
    "interest expense": AccountCategory.OTHER_EXPENSE,
    "taxes": AccountCategory.TAX,
    "income tax": AccountCategory.TAX,
    "corporation tax": AccountCategory.TAX,
    "corporate tax": AccountCategory.TAX,
}


class IngestionError(ValueError):
    """Raised when an uploaded file doesn't match the expected schema."""


def _resolve_category(raw: str) -> AccountCategory:
    normalized = raw.strip().lower()
    try:
        return AccountCategory(normalized)
    except ValueError:
        pass
    mapped = _CATEGORY_SYNONYMS.get(normalized)
    if mapped is not None:
        return mapped
    valid = ", ".join(c.value for c in AccountCategory)
    raise ValueError(f"invalid category '{raw}' (expected one of: {valid})")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: str(c).strip().lower().replace(" ", "_") for c in df.columns})
    return df


def _validate_schema(df: pd.DataFrame, source: str) -> None:
    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise IngestionError(
            f"{source}: missing required column(s): {', '.join(sorted(missing))}. "
            f"Expected at least: {', '.join(sorted(_REQUIRED_COLUMNS))}"
        )
    if "client_id" not in df.columns and "client_name" not in df.columns:
        raise IngestionError(
            f"{source}: file must include a 'client_id' or 'client_name' column "
            "so rows can be attributed to the right client workspace."
        )


def load_dataframe(path: str | Path) -> pd.DataFrame:
    """Read a CSV or Excel file into a normalized DataFrame (no domain objects yet)."""
    path = Path(path)
    if not path.exists():
        raise IngestionError(f"File not found: {path}")

    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        raise IngestionError(f"Unsupported file type: {path.suffix} (expected .csv, .xlsx, .xls)")

    df = _normalize_columns(df)
    _validate_schema(df, source=path.name)

    if "client_id" not in df.columns:
        df["client_id"] = (
            df["client_name"].astype(str).str.strip().str.lower().str.replace(r"\s+", "-", regex=True)
        )

    return df


def parse_line_items(df: pd.DataFrame) -> list[LineItem]:
    """Convert a normalized DataFrame into validated LineItem objects.

    Rows that fail validation (bad scenario/category values, non-numeric
    amounts, etc.) raise an IngestionError that names the offending row so a
    human can fix the source file quickly, rather than failing silently.
    """
    items: list[LineItem] = []
    for idx, row in df.iterrows():
        row_num = idx + 2  # +1 for 0-index, +1 for header row -- matches spreadsheet row
        try:
            scenario = Scenario(str(row["scenario"]).strip().lower())
        except ValueError as exc:
            valid = ", ".join(s.value for s in Scenario)
            raise IngestionError(
                f"Row {row_num}: invalid scenario '{row['scenario']}' (expected one of: {valid})"
            ) from exc

        try:
            category = _resolve_category(str(row["category"]))
        except ValueError as exc:
            raise IngestionError(f"Row {row_num}: {exc}") from exc

        try:
            amount = float(row["amount"])
        except (TypeError, ValueError) as exc:
            raise IngestionError(f"Row {row_num}: amount '{row['amount']}' is not numeric") from exc

        items.append(
            LineItem(
                client_id=str(row["client_id"]).strip(),
                period=str(row["period"]).strip(),
                scenario=scenario,
                account=str(row["account"]).strip(),
                category=category,
                amount=amount,
            )
        )
    return items


def group_into_statements(items: list[LineItem]) -> list[FinancialStatement]:
    """Group flat line items into one FinancialStatement per (client, period, scenario)."""
    buckets: dict[tuple[str, str, Scenario], list[LineItem]] = {}
    for li in items:
        key = (li.client_id, li.period, li.scenario)
        buckets.setdefault(key, []).append(li)

    return [
        FinancialStatement(client_id=cid, period=period, scenario=scenario, line_items=lines)
        for (cid, period, scenario), lines in buckets.items()
    ]


def load_financial_statements(path: str | Path) -> list[FinancialStatement]:
    """End-to-end: file path -> list of FinancialStatement, one per client/period/scenario."""
    df = load_dataframe(path)
    items = parse_line_items(df)
    return group_into_statements(items)
