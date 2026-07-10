"""
Ingestion layer for AR/AP invoices, used by the aging engine.

Expected input schema (columns, case-insensitive, order doesn't matter):

    client_id | client_name | invoice_id | type | counterparty | issue_date | due_date | amount | amount_paid

- client_id/client_name: same fallback rule as the P&L ingestion (parser.py)
- invoice_id:  identifier for the invoice, e.g. "INV-1042"
- type:        "ar" or "ap" (case-insensitive)
- counterparty: customer name (AR) or vendor name (AP)
- issue_date/due_date: ISO dates, e.g. "2026-06-15"
- amount:      invoice total, positive
- amount_paid: optional, defaults to 0 if the column is missing

Kept as its own module (not merged into parser.py) because the column
schema is entirely different from the P&L line-item schema -- invoices are
a separate dataset that gets attached to an existing Workspace, not part of
the financial-statement upload.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from app.ingestion.parser import IngestionError
from app.models.domain import Invoice, InvoiceType

_REQUIRED_COLUMNS = {"invoice_id", "type", "counterparty", "issue_date", "due_date", "amount"}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={c: str(c).strip().lower().replace(" ", "_") for c in df.columns})


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


def _parse_date(raw: object, row_num: int, field: str) -> date:
    try:
        return pd.to_datetime(str(raw)).date()
    except (TypeError, ValueError) as exc:
        raise IngestionError(f"Row {row_num}: {field} '{raw}' is not a valid date") from exc


def load_invoices(path: str | Path) -> list[Invoice]:
    """Read a CSV/Excel file of AR/AP invoices into validated Invoice objects."""
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

    invoices: list[Invoice] = []
    for idx, row in df.iterrows():
        row_num = idx + 2  # +1 for 0-index, +1 for header row

        try:
            invoice_type = InvoiceType(str(row["type"]).strip().lower())
        except ValueError as exc:
            valid = ", ".join(t.value for t in InvoiceType)
            raise IngestionError(f"Row {row_num}: invalid type '{row['type']}' (expected one of: {valid})") from exc

        try:
            amount = float(row["amount"])
        except (TypeError, ValueError) as exc:
            raise IngestionError(f"Row {row_num}: amount '{row['amount']}' is not numeric") from exc

        amount_paid = 0.0
        if "amount_paid" in df.columns and pd.notna(row["amount_paid"]):
            try:
                amount_paid = float(row["amount_paid"])
            except (TypeError, ValueError) as exc:
                raise IngestionError(f"Row {row_num}: amount_paid '{row['amount_paid']}' is not numeric") from exc

        invoices.append(
            Invoice(
                client_id=str(row["client_id"]).strip(),
                invoice_id=str(row["invoice_id"]).strip(),
                type=invoice_type,
                counterparty=str(row["counterparty"]).strip(),
                issue_date=_parse_date(row["issue_date"], row_num, "issue_date"),
                due_date=_parse_date(row["due_date"], row_num, "due_date"),
                amount=amount,
                amount_paid=amount_paid,
            )
        )
    return invoices
