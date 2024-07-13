import os
import sys
import pytest
import pandas as pd
import sqlite3
import yfinance as yf
from unittest.mock import patch, MagicMock
import numpy as np
from dotenv import load_dotenv

# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import (
    get_stock_codes,
    get_stock_data,
    get_financial_data,
    calculate_sma,
    indicator_5ema,
    indicator_13ema,
    indicator_26ema,
    indicator_50ema,
    indicator_rsi,
    indicator_bollinger_bands,
    indicator_macd,
    indicator_atr,
    check_if_above_50ema,
    store_stock_data_sqldb,
    read_stock_data_from_db,
    merge_dataframes,
    update_todaystocks_db,
    calculate_ema,
)


# Test for get_stock_codes
@patch("Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.pd.read_csv")
@patch("Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.os.getenv")
def test_get_stock_codes(mock_getenv, mock_read_csv):
    mock_getenv.return_value = "mock_url"
    mock_read_csv.return_value = pd.DataFrame({"SYMBOL": ["AAPL", "GOOGL"]})
    result = get_stock_codes()
    assert result == ["AAPL", "GOOGL"]


# Test for get_stock_data
@patch("Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.yf.download")
def test_get_stock_data(mock_download):
    mock_download.return_value = pd.DataFrame(
        {
            "Open": [1, 2],
            "Close": [2, 3],
            "High": [3, 4],
            "Low": [1, 1],
            "Volume": [100, 200],
        }
    )
    result = get_stock_data("AAPL", "1y", "1d")
    assert not result.empty


# Test for get_financial_data
@patch("Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.yf.Ticker")
def test_get_financial_data(mock_ticker):
    mock_info = MagicMock()
    mock_info.info = {
        "totalRevenue": 1000,
        "operatingCashflow": 200,
        "totalDebt": 500,
        "bookValue": 50,
        "sharesOutstanding": 10,
        "revenueGrowth": 0.1,
        "netIncomeToCommon": 100,
        "trailingEps": 10,
        "priceToBook": 1,
        "trailingPE": 10,
        "marketCap": 10000,
        "dividendYield": 0.02,
        "totalCash": 300,
        "ebitda": 150,
        "returnOnEquity": 0.15,
    }
    mock_ticker.return_value = mock_info
    result = get_financial_data(["AAPL"])
    assert result.at[0, "Symbol"] == "AAPL"
    assert result.at[0, "Total Revenue"] == 1000


# Test for calculate_sma
def test_calculate_sma():
    data = pd.Series([1, 2, 3, 4, 5, 6])
    result = calculate_sma(data, window=3)
    assert len(result) == 6
    assert result.iloc[-1] == 5


# Test for indicator_5ema
def test_indicator_5ema():
    stock_data = pd.DataFrame({"Close": [1, 2, 3, 4, 5]})
    result = indicator_5ema(stock_data)
    assert len(result) == 5
    assert not result.isnull().values.any()


# Test for indicator_13ema
def test_indicator_13ema():
    stock_data = pd.DataFrame({"Close": [1, 2, 3, 4, 5]})
    result = indicator_13ema(stock_data)
    assert len(result) == 5
    assert not result.isnull().values.any()


# Test for indicator_26ema
def test_indicator_26ema():
    stock_data = pd.DataFrame({"Close": [1, 2, 3, 4, 5]})
    result = indicator_26ema(stock_data)
    assert len(result) == 5
    assert not result.isnull().values.any()


# Test for indicator_50ema
def test_indicator_50ema():
    stock_data = pd.DataFrame({"Close": [1, 2, 3, 4, 5]})
    result = indicator_50ema(stock_data)
    assert len(result) == 5
    assert not result.isnull().values.any()


# Test for indicator_rsi
def test_indicator_rsi():
    stock_data = pd.DataFrame({"Close": [1, 2, 3, 4, 5]})
    result = indicator_rsi(stock_data, rsi_length=2, rsi_source="Close")
    assert len(result) == 5
    # Allow NaN in the first position as it's expected with RSI calculation
    assert result.isnull().iloc[0]  # First value should be NaN
    assert not result.isnull().iloc[1:].any()  # No NaNs in the rest of the values


# Test for indicator_bollinger_bands
def test_indicator_bollinger_bands():
    stock_data = pd.DataFrame({"Close": [1, 2, 3, 4, 5]})
    result = indicator_bollinger_bands(stock_data, window=2)
    assert "Upper_band" in result.columns
    assert "Lower_band" in result.columns


# Test for indicator_macd
def test_indicator_macd():
    stock_data = pd.DataFrame({"Close": [1, 2, 3, 4, 5]})
    macd, signal_line = indicator_macd(stock_data)
    assert len(macd) == 5
    assert len(signal_line) == 5


# Test for indicator_atr
def test_indicator_atr():
    stock_data = pd.DataFrame({"High": [2, 3, 4], "Low": [1, 1, 2], "Close": [1, 2, 3]})
    result = indicator_atr(stock_data, window=2)
    assert len(result) == 3
    # Allow NaN in the first position as it's expected with rolling mean
    assert result.isnull().iloc[0]  # First value should be NaN
    assert not result.isnull().iloc[1:].any()  # No NaNs in the rest of the values


# Test for check_if_above_50ema
def test_check_if_above_50ema():
    stock_data = pd.DataFrame({"Close": [1, 2, 3, 4, 5]})
    result = check_if_above_50ema(stock_data)
    assert "Above_50_EMA" in result.columns


@patch("Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.get_stock_codes")
@patch("Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.get_stock_data")
@patch("Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.sqlite3.connect")
def test_store_stock_data_sqldb(
    mock_connect, mock_get_stock_data, mock_get_stock_codes
):
    mock_get_stock_codes.return_value = ["AAPL"]
    mock_get_stock_data.return_value = pd.DataFrame(
        {
            "Open": [1, 2],
            "Close": [2, 3],
            "High": [3, 4],
            "Low": [1, 1],
            "Volume": [100, 200],
            "Date": pd.to_datetime(["2023-01-01", "2023-01-02"]),
        }
    ).set_index("Date")
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_connect.return_value = mock_conn

    store_stock_data_sqldb()

    # Print actual calls for debugging
    print(mock_cursor.execute.call_args_list)

    # Ensure the table creation and data insertion is called
    expected_columns = [
        "Date",
        "DailyOpen",
        "DailyHigh",
        "DailyLow",
        "DailyClose",
        "DailyVolume",
        "WeeklyOpen",
        "WeeklyHigh",
        "WeeklyLow",
        "WeeklyClose",
        "WeeklyVolume",
    ]
    called = False

    for call in mock_cursor.execute.call_args_list:
        sql = call[0][0]
        if all(col in sql for col in expected_columns):
            called = True
            break

    assert (
        called
    ), f"Expected SQL call not found in {mock_cursor.execute.call_args_list}"
    assert mock_conn.commit.called


# Test for read_stock_data_from_db
@patch("Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.sqlite3.connect")
def test_read_stock_data_from_db(mock_connect):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = mock_conn.cursor()
    mock_cursor.fetchall.return_value = [("AAPL",)]

    mock_read_sql_query = MagicMock(
        side_effect=[
            pd.DataFrame(
                {
                    "Open": [1, 2],
                    "High": [3, 4],
                    "Low": [1, 1],
                    "Close": [2, 3],
                    "Volume": [100, 200],
                }
            ),
            pd.DataFrame(
                {
                    "Open": [1, 2],
                    "High": [3, 4],
                    "Low": [1, 1],
                    "Close": [2, 3],
                    "Volume": [100, 200],
                }
            ),
        ]
    )

    with patch(
        "Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.pd.read_sql_query",
        mock_read_sql_query,
    ):
        result = read_stock_data_from_db("mock_db_path")
        assert "AAPL" in result
        assert "daily_data" in result["AAPL"]
        assert "weekly_data" in result["AAPL"]


# Test for merge_dataframes
def test_merge_dataframes():
    df1 = pd.DataFrame({"Symbol": ["AAPL"], "DailyOpen": [1]})
    df2 = pd.DataFrame({"Symbol": ["AAPL"], "DailyClose": [2]})
    df3 = pd.DataFrame({"Symbol": ["AAPL"], "DailyHigh": [3]})
    df4 = pd.DataFrame({"Symbol": ["AAPL"], "DailyLow": [4]})
    df5 = pd.DataFrame({"Symbol": ["AAPL"], "WeeklyOpen": [5]})
    df6 = pd.DataFrame({"Symbol": ["AAPL"], "WeeklyClose": [6]})
    df7 = pd.DataFrame({"Symbol": ["AAPL"], "WeeklyHigh": [7]})

    result = merge_dataframes(df1, df2, df3, df4, df5, df6, df7)

    assert "DailyOpen" in result.columns
    assert "DailyClose" in result.columns
    assert "DailyHigh" in result.columns
    assert "DailyLow" in result.columns
    assert "WeeklyOpen" in result.columns
    assert "WeeklyClose" in result.columns
    assert "WeeklyHigh" in result.columns

    assert result["DailyOpen"].iloc[0] == 1
    assert result["DailyClose"].iloc[0] == 2
    assert result["DailyHigh"].iloc[0] == 3
    assert result["DailyLow"].iloc[0] == 4
    assert result["WeeklyOpen"].iloc[0] == 5
    assert result["WeeklyClose"].iloc[0] == 6
    assert result["WeeklyHigh"].iloc[0] == 7


# Test for update_todaystocks_db
@patch("Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.sqlite3.connect")
def test_update_todaystocks_db(mock_connect):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    df = pd.DataFrame({"Symbol": ["AAPL"], "DailyOpen": [1], "DailyClose": [2]})
    update_todaystocks_db(df, df, df, df, df, df, df)
    mock_conn.cursor().execute.assert_called()


# Test for calculate_ema
def test_calculate_ema():
    data = pd.Series([1, 2, 3, 4, 5])
    result = calculate_ema(data, window=2)
    assert len(result) == 5
    assert not result.isnull().values.any()
