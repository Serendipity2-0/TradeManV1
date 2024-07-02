import os
import sys
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

# Add the script directory to the system path
SCRIPT_DIR = (
    r"C:\Users\phchi\OneDrive\Desktop\TradeManV1\Executor\NSEStrategies\Equity\LongTerm"
)
sys.path.append(SCRIPT_DIR)

from LongTermUtils import (
    get_longterm_stocks_df,
    perform_ratio_strategy,
    perform_combo_strategy,
)

# Mock environment variables
os.environ["LONG_RATIO"] = "Long_Ratio"
os.environ["LONG_COMBO"] = "Long_Combo"
os.environ[
    "financial_db_path"
] = r"C:\Users\phchi\OneDrive\Desktop\TradeManV1\Data\financial_data.db"


@pytest.fixture
def stock_codes():
    return ["AAPL", "GOOGL", "MSFT"]


@pytest.fixture
def financial_data():
    return pd.DataFrame(
        {
            "Symbol": ["AAPL", "GOOGL", "MSFT"],
            "Market Cap": [15e9, 20e9, 30e9],
            "P/E Ratio": [15, 18, 25],
            "P/B Ratio": [2, 1.5, 4],
            "Dividend Yield": [0.03, 0.02, 0.01],
            "Piotroski F-Score": [8, 6, 7],
            "Operating Profit Margin": [0.2, 0.25, 0.1],
            "Debt to Equity": [0.4, 0.3, 0.6],
            "Gross Profit Growth": [0.15, 0.2, 0.05],
        }
    )


@patch("LongTermUtils.get_stock_codes")
@patch("LongTermUtils.get_financial_data")
@patch("LongTermUtils.sqlite3.connect")
def test_get_longterm_stocks_df(
    mock_connect,
    mock_get_financial_data,
    mock_get_stock_codes,
    stock_codes,
    financial_data,
):
    mock_get_stock_codes.return_value = stock_codes
    mock_get_financial_data.return_value = financial_data

    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock the to_sql function
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None

    # Mock the behavior of writing to SQL
    with patch.object(pd.DataFrame, "to_sql") as mock_to_sql:
        mock_to_sql.side_effect = lambda *args, **kwargs: print(
            "Mock to_sql called with args:", args, "kwargs:", kwargs
        )
        result_combo, result_ratio = get_longterm_stocks_df()

    assert (
        result_combo is not None
    ), "The function returned None, expected a DataFrame for combo strategy"
    assert (
        result_ratio is not None
    ), "The function returned None, expected a DataFrame for ratio strategy"

    print("Result Combo DataFrame:\n", result_combo)
    print("Result Ratio DataFrame:\n", result_ratio)

    assert "Symbol" in result_combo.columns, "Combo strategy missing 'Symbol' column"
    assert (
        "Long_Combo" in result_combo.columns
    ), "Combo strategy missing 'Long_Combo' column"

    assert "Symbol" in result_ratio.columns, "Ratio strategy missing 'Symbol' column"
    assert (
        "Long_Ratio" in result_ratio.columns
    ), "Ratio strategy missing 'Long_Ratio' column"


@patch("LongTermUtils.pd.read_sql")
def test_perform_ratio_strategy(mock_read_sql, financial_data):
    mock_read_sql.return_value = financial_data

    result = perform_ratio_strategy(db_path="mock_financial_db_path")

    assert result is not None, "The function returned None, expected a DataFrame"
    assert "Symbol" in result.columns, "Ratio strategy missing 'Symbol' column"
    assert "Long_Ratio" in result.columns, "Ratio strategy missing 'Long_Ratio' column"

    shortlisted = result[result["Long_Ratio"] == 1]
    assert not shortlisted.empty, "Expected some shortlisted stocks for ratio strategy"
    assert all(shortlisted["Market Cap"] > 10e9)
    assert all(shortlisted["P/E Ratio"] < 20)
    assert all(shortlisted["P/B Ratio"] < 3)
    assert all(shortlisted["Dividend Yield"] > 0.02)


@patch("LongTermUtils.pd.read_sql")
def test_perform_combo_strategy(mock_read_sql, financial_data):
    mock_read_sql.return_value = financial_data

    result = perform_combo_strategy(db_path="mock_financial_db_path")

    assert result is not None, "The function returned None, expected a DataFrame"
    assert "Symbol" in result.columns, "Combo strategy missing 'Symbol' column"
    assert "Long_Combo" in result.columns, "Combo strategy missing 'Long_Combo' column"

    shortlisted = result[result["Long_Combo"] == 1]
    assert not shortlisted.empty, "Expected some shortlisted stocks for combo strategy"
    assert all(shortlisted["Market Cap"] > 10e9)
    assert all(shortlisted["Piotroski F-Score"] >= 7)
    assert all(shortlisted["P/E Ratio"] < 20)
    assert all(shortlisted["P/B Ratio"] < 3)
    assert all(shortlisted["Operating Profit Margin"] > 0.15)
    assert all(shortlisted["Debt to Equity"] < 0.5)
    assert all(shortlisted["Gross Profit Growth"] > 0.1)
