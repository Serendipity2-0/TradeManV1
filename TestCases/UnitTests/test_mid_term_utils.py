import os
import sys
from dotenv import load_dotenv
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.NSEStrategies.Equity.MidTerm.MidTermUtils import (
    get_midterm_stocks_df,
    perform_tfmomentum_strategy,
    perform_tfema_strategy,
)

# Mock environment variables
os.environ["MID_TFMOMENTUM"] = "Mid_tfMomentum"
os.environ["MID_TFEMA"] = "Mid_tfEma"


@pytest.fixture
def stock_data_dict():
    return {
        "AAPL": {
            "daily_data": {
                "Open": [1, 2, 3, 4, 5],
                "High": [5, 6, 7, 8, 9],
                "Low": [0, 1, 2, 3, 4],
                "Close": [4, 5, 6, 7, 8],
                "Volume": [100, 200, 300, 400, 500],
            },
            "weekly_data": {
                "Open": [1, 2, 3, 4, 5],
                "High": [5, 6, 7, 8, 9],
                "Low": [0, 1, 2, 3, 4],
                "Close": [4, 5, 6, 7, 8],
                "Volume": [100, 200, 300, 400, 500],
            },
        }
    }


@pytest.fixture
def financial_data():
    return pd.DataFrame(
        {
            "Symbol": ["AAPL"],
            "Gross Profit Growth": [10**10],
            "Net Income": [10**9],
            "Total Revenue": [10**10],
            "Market Cap": [5000000000],
            "Return on Equity": [20],
        }
    )


@patch("Executor.NSEStrategies.Equity.MidTerm.MidTermUtils.read_stock_data_from_db")
@patch("Executor.NSEStrategies.Equity.MidTerm.MidTermUtils.calculate_sma")
@patch("Executor.NSEStrategies.Equity.MidTerm.MidTermUtils.indicator_rsi")
@patch("Executor.NSEStrategies.Equity.MidTerm.MidTermUtils.pd.read_sql_query")
def test_perform_tfmomentum_strategy(
    mock_read_sql_query,
    mock_indicator_rsi,
    mock_calculate_sma,
    mock_read_stock_data_from_db,
    stock_data_dict,
    financial_data,
):
    mock_read_stock_data_from_db.return_value = stock_data_dict
    mock_calculate_sma.return_value = pd.Series([4, 5, 6, 7, 8])
    mock_indicator_rsi.return_value = pd.Series([50, 51, 52, 53, 54])
    mock_read_sql_query.return_value = financial_data

    result = perform_tfmomentum_strategy()
    assert result is not None, "The function returned None, expected a DataFrame"
    assert "Symbol" in result.columns
    assert "SMA_20" in result.columns
    assert "RSI_14" in result.columns
    assert "Mid_tfMomentum" in result.columns


@patch("Executor.NSEStrategies.Equity.MidTerm.MidTermUtils.read_stock_data_from_db")
@patch("Executor.NSEStrategies.Equity.MidTerm.MidTermUtils.calculate_sma")
@patch("Executor.NSEStrategies.Equity.MidTerm.MidTermUtils.calculate_ema")
@patch("Executor.NSEStrategies.Equity.MidTerm.MidTermUtils.indicator_rsi")
@patch("Executor.NSEStrategies.Equity.MidTerm.MidTermUtils.pd.read_sql_query")
def test_perform_tfema_strategy(
    mock_read_sql_query,
    mock_indicator_rsi,
    mock_calculate_ema,
    mock_calculate_sma,
    mock_read_stock_data_from_db,
    stock_data_dict,
    financial_data,
):
    mock_read_stock_data_from_db.return_value = stock_data_dict
    mock_calculate_ema.side_effect = [pd.Series([4, 5, 6, 7, 8])] * 4
    mock_indicator_rsi.return_value = pd.Series([60, 61, 62, 63, 64])
    mock_calculate_sma.return_value = pd.Series([150, 160, 170, 180, 190])
    mock_read_sql_query.return_value = financial_data

    result = perform_tfema_strategy()
    assert result is not None, "The function returned None, expected a DataFrame"
    assert "Symbol" in result.columns
    assert "EMA_9" in result.columns
    assert "EMA_21" in result.columns
    assert "EMA_63" in result.columns
    assert "EMA_200" in result.columns
    assert "Mid_tfEma" in result.columns


@patch("Executor.NSEStrategies.Equity.MidTerm.MidTermUtils.perform_tfmomentum_strategy")
@patch("Executor.NSEStrategies.Equity.MidTerm.MidTermUtils.perform_tfema_strategy")
def test_get_midterm_stocks_df(
    mock_perform_tfema_strategy, mock_perform_tfmomentum_strategy
):
    mock_perform_tfmomentum_strategy.return_value = pd.DataFrame(
        {"Symbol": ["AAPL"], "SMA_20": [4], "RSI_14": [50], "Mid_tfMomentum": [1]}
    )
    mock_perform_tfema_strategy.return_value = pd.DataFrame(
        {
            "Symbol": ["AAPL"],
            "EMA_9": [4],
            "EMA_21": [5],
            "EMA_63": [6],
            "EMA_200": [7],
            "Mid_tfEma": [1],
        }
    )

    tfmomentum_df, tfema_df = get_midterm_stocks_df()

    assert "Symbol" in tfmomentum_df.columns
    assert "Symbol" in tfema_df.columns

    assert "Mid_tfMomentum" in tfmomentum_df.columns
    assert "Mid_tfEma" in tfema_df.columns
