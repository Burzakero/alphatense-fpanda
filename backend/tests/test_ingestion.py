from pathlib import Path

import pandas as pd
import pytest

from app.ingestion.parser import IngestionError, load_dataframe, load_financial_statements, parse_line_items
from app.models.domain import AccountCategory, Scenario

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_financials.csv"


def test_load_sample_csv_end_to_end():
    statements = load_financial_statements(SAMPLE_CSV)
    client_ids = {s.client_id for s in statements}

    assert "acme-ltd" in client_ids
    assert "beacon-partners" in client_ids
    # 2 clients x (6 actual periods + 1 budget period + 1 prior period) = 16 statements
    assert len(statements) == 16


def test_missing_required_column_raises(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("client_id,period,scenario,account,amount\nc1,2026-01,actual,Sales,100\n")

    with pytest.raises(IngestionError, match="category"):
        load_dataframe(bad_csv)


def test_client_name_only_derives_client_id(tmp_path):
    csv_path = tmp_path / "derive.csv"
    csv_path.write_text(
        "client_name,period,scenario,account,category,amount\n"
        "My Cool Client,2026-01,actual,Sales,revenue,500\n"
    )
    df = load_dataframe(csv_path)
    assert df.loc[0, "client_id"] == "my-cool-client"


def test_invalid_scenario_value_raises_with_row_number():
    df = pd.DataFrame(
        [{"client_id": "c1", "period": "2026-01", "scenario": "forecast", "account": "Sales",
          "category": "revenue", "amount": 100}]
    )
    with pytest.raises(IngestionError, match="Row 2"):
        parse_line_items(df)


def test_non_numeric_amount_raises():
    df = pd.DataFrame(
        [{"client_id": "c1", "period": "2026-01", "scenario": "actual", "account": "Sales",
          "category": "revenue", "amount": "not-a-number"}]
    )
    with pytest.raises(IngestionError, match="not numeric"):
        parse_line_items(df)


def test_parsed_line_item_types():
    df = load_dataframe(SAMPLE_CSV)
    items = parse_line_items(df)
    first = items[0]
    assert first.scenario in Scenario
    assert first.category in AccountCategory
    assert isinstance(first.amount, float)
