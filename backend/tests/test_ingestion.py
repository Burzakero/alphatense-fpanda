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


def test_category_synonym_is_mapped():
    df = pd.DataFrame(
        [{"client_id": "c1", "period": "2026-01", "scenario": "actual", "account": "COGS",
          "category": "Cost of Sales", "amount": 100}]
    )
    items = parse_line_items(df)
    assert items[0].category == AccountCategory.COGS


def test_unrecognized_category_still_raises_with_row_number():
    df = pd.DataFrame(
        [{"client_id": "c1", "period": "2026-01", "scenario": "actual", "account": "Sales",
          "category": "not-a-real-category", "amount": 100}]
    )
    with pytest.raises(IngestionError, match="Row 2"):
        parse_line_items(df)


def test_ambiguous_category_resolved_via_account_name():
    df = pd.DataFrame(
        [
            {"client_id": "c1", "period": "2026-01", "scenario": "actual", "account": "Depreciation",
             "category": "Non Operating", "amount": -941.53},
            {"client_id": "c1", "period": "2026-01", "scenario": "actual", "account": "Interest",
             "category": "Non Operating", "amount": -372.71},
            {"client_id": "c1", "period": "2026-01", "scenario": "actual", "account": "Interest Income",
             "category": "Other", "amount": 150},
        ]
    )
    items = parse_line_items(df)
    assert items[0].category == AccountCategory.OTHER_EXPENSE
    assert items[0].amount == 941.53  # negative cost normalized to positive
    assert items[1].category == AccountCategory.OTHER_EXPENSE
    assert items[2].category == AccountCategory.OTHER_INCOME
    assert items[2].amount == 150  # income is untouched, not a cost category


def test_ambiguous_category_without_account_hint_still_raises():
    df = pd.DataFrame(
        [{"client_id": "c1", "period": "2026-01", "scenario": "actual", "account": "Miscellaneous",
          "category": "Non Operating", "amount": 100}]
    )
    with pytest.raises(IngestionError, match="ambiguous"):
        parse_line_items(df)


def test_negative_cost_amount_is_normalized_to_positive():
    df = pd.DataFrame(
        [{"client_id": "c1", "period": "2026-01", "scenario": "actual", "account": "COGS",
          "category": "cogs", "amount": -20063.13}]
    )
    items = parse_line_items(df)
    assert items[0].amount == 20063.13


def test_parsed_line_item_types():
    df = load_dataframe(SAMPLE_CSV)
    items = parse_line_items(df)
    first = items[0]
    assert first.scenario in Scenario
    assert first.category in AccountCategory
    assert isinstance(first.amount, float)
