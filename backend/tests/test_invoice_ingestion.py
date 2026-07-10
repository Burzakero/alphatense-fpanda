from pathlib import Path

import pytest

from app.ingestion.invoices import load_invoices
from app.ingestion.parser import IngestionError
from app.models.domain import InvoiceType

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_invoices.csv"


def test_load_sample_invoices_end_to_end():
    invoices = load_invoices(SAMPLE_CSV)
    client_ids = {inv.client_id for inv in invoices}

    assert "acme-ltd" in client_ids
    assert "beacon-partners" in client_ids
    assert len(invoices) == 14
    assert any(inv.type == InvoiceType.AR for inv in invoices)
    assert any(inv.type == InvoiceType.AP for inv in invoices)


def test_amount_paid_defaults_to_zero_when_column_missing(tmp_path):
    csv_path = tmp_path / "invoices.csv"
    csv_path.write_text(
        "client_id,invoice_id,type,counterparty,issue_date,due_date,amount\n"
        "c1,INV-1,ar,Acme,2026-01-01,2026-02-01,500\n"
    )
    invoices = load_invoices(csv_path)
    assert invoices[0].amount_paid == 0.0
    assert invoices[0].balance == 500.0


def test_client_name_only_derives_client_id(tmp_path):
    csv_path = tmp_path / "invoices.csv"
    csv_path.write_text(
        "client_name,invoice_id,type,counterparty,issue_date,due_date,amount\n"
        "My Cool Client,INV-1,ar,Acme,2026-01-01,2026-02-01,500\n"
    )
    invoices = load_invoices(csv_path)
    assert invoices[0].client_id == "my-cool-client"


def test_missing_required_column_raises(tmp_path):
    csv_path = tmp_path / "invoices.csv"
    csv_path.write_text("client_id,invoice_id,type,counterparty,issue_date\nc1,INV-1,ar,Acme,2026-01-01\n")
    with pytest.raises(IngestionError, match="due_date"):
        load_invoices(csv_path)


def test_invalid_type_raises(tmp_path):
    csv_path = tmp_path / "invoices.csv"
    csv_path.write_text(
        "client_id,invoice_id,type,counterparty,issue_date,due_date,amount\n"
        "c1,INV-1,unknown,Acme,2026-01-01,2026-02-01,500\n"
    )
    with pytest.raises(IngestionError, match="Row 2"):
        load_invoices(csv_path)


def test_invalid_date_raises(tmp_path):
    csv_path = tmp_path / "invoices.csv"
    csv_path.write_text(
        "client_id,invoice_id,type,counterparty,issue_date,due_date,amount\n"
        "c1,INV-1,ar,Acme,2026-01-01,not-a-date,500\n"
    )
    with pytest.raises(IngestionError, match="due_date"):
        load_invoices(csv_path)


def test_non_numeric_amount_raises(tmp_path):
    csv_path = tmp_path / "invoices.csv"
    csv_path.write_text(
        "client_id,invoice_id,type,counterparty,issue_date,due_date,amount\n"
        "c1,INV-1,ar,Acme,2026-01-01,2026-02-01,not-a-number\n"
    )
    with pytest.raises(IngestionError, match="not numeric"):
        load_invoices(csv_path)
