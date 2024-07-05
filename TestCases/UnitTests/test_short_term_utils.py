import os
import sys
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)


from Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils import (
    perform_EmaBB_Confluence_strategy,
    perform_mean_reversion_strategy,
    perform_momentum_strategy,
    get_shortterm_stocks_df,
)

# Mock environment variables
os.environ["SHORT_EMABBCONFLUENCE"] = "Short_EMABBConfluence"
os.environ["SHORT_MOMENTUM"] = "Short_Momentum"
os.environ["SHORT_MEANREVERSION"] = "Short_MeanReversion"


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


@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.indicator_bollinger_bands")
@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.indicator_50ema")
def test_perform_EmaBB_Confluence_strategy(
    mock_indicator_50ema, mock_indicator_bollinger_bands, stock_data_dict
):
    mock_indicator_bollinger_bands.return_value = pd.DataFrame(
        {
            "MA": [3, 4, 5, 6, 7],
            "Lower_band": [1, 2, 3, 4, 5],
            "Close": [4, 5, 6, 7, 8],
            "Open": [1, 2, 3, 4, 5],
            "High": [5, 6, 7, 8, 9],
            "Low": [0, 1, 2, 3, 4],
        }
    )
    mock_indicator_50ema.return_value = pd.Series([3, 4, 5, 6, 7])

    result = perform_EmaBB_Confluence_strategy(stock_data_dict)
    assert "Symbol" in result.columns
    assert "DailyOpen" in result.columns
    assert "DailyClose" in result.columns
    assert "Short_EMABBConfluence" in result.columns


@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.indicator_rsi")
@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.indicator_bollinger_bands")
@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.check_if_above_50ema")
def test_perform_mean_reversion_strategy(
    mock_check_if_above_50ema,
    mock_indicator_bollinger_bands,
    mock_indicator_rsi,
    stock_data_dict,
):
    mock_indicator_bollinger_bands.return_value = pd.DataFrame(
        {
            "MA": [3, 4, 5, 6, 7],
            "Lower_band": [1, 2, 3, 4, 5],
            "Close": [4, 5, 6, 7, 8],
            "Open": [1, 2, 3, 4, 5],
            "High": [5, 6, 7, 8, 9],
            "Low": [0, 1, 2, 3, 4],
        }
    )
    mock_check_if_above_50ema.return_value = pd.DataFrame(
        {
            "Above_50_EMA": [True, True, True, True, True],
            "Close": [4, 5, 6, 7, 8],
            "Open": [1, 2, 3, 4, 5],
            "High": [5, 6, 7, 8, 9],
            "Low": [0, 1, 2, 3, 4],
        }
    )
    mock_indicator_rsi.return_value = pd.Series([30, 35, 40, 45, 50])

    result = perform_mean_reversion_strategy(stock_data_dict)
    assert "Symbol" in result.columns
    assert "DailyOpen" in result.columns
    assert "DailyClose" in result.columns
    assert "Short_MeanReversion" in result.columns


@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.indicator_rsi")
@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.indicator_bollinger_bands")
@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.check_if_above_50ema")
@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.indicator_macd")
def test_perform_momentum_strategy(
    mock_indicator_macd,
    mock_check_if_above_50ema,
    mock_indicator_bollinger_bands,
    mock_indicator_rsi,
    stock_data_dict,
):
    mock_indicator_bollinger_bands.return_value = pd.DataFrame(
        {
            "Upper_band": [7, 8, 9, 10, 11],
            "Close": [4, 5, 6, 7, 8],
            "Open": [1, 2, 3, 4, 5],
            "High": [5, 6, 7, 8, 9],
            "Low": [0, 1, 2, 3, 4],
        }
    )
    mock_check_if_above_50ema.return_value = pd.DataFrame(
        {
            "Above_50_EMA": [True, True, True, True, True],
            "Close": [4, 5, 6, 7, 8],
            "Open": [1, 2, 3, 4, 5],
            "High": [5, 6, 7, 8, 9],
            "Low": [0, 1, 2, 3, 4],
        }
    )
    mock_indicator_rsi.return_value = pd.Series([60, 65, 70, 75, 80])
    mock_indicator_macd.return_value = (
        pd.Series([1, 1.5, 2, 2.5, 3]),
        pd.Series([0.5, 1, 1.5, 2, 2.5]),
    )

    result = perform_momentum_strategy(stock_data_dict)
    assert "Symbol" in result.columns
    assert "DailyOpen" in result.columns
    assert "DailyClose" in result.columns
    assert "Short_Momentum" in result.columns


@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.read_stock_data_from_db")
@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.perform_momentum_strategy")
@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.perform_mean_reversion_strategy")
@patch("Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.perform_EmaBB_Confluence_strategy")
def test_get_shortterm_stocks_df(
    mock_perform_EmaBB_Confluence_strategy,
    mock_perform_mean_reversion_strategy,
    mock_perform_momentum_strategy,
    mock_read_stock_data_from_db,
):
    mock_read_stock_data_from_db.return_value = {
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

    mock_perform_momentum_strategy.return_value = pd.DataFrame(
        {"Symbol": ["AAPL"], "DailyOpen": [1], "DailyClose": [4], "Short_Momentum": [1]}
    )
    mock_perform_mean_reversion_strategy.return_value = pd.DataFrame(
        {
            "Symbol": ["AAPL"],
            "DailyOpen": [1],
            "DailyClose": [4],
            "Short_MeanReversion": [1],
        }
    )
    mock_perform_EmaBB_Confluence_strategy.return_value = pd.DataFrame(
        {
            "Symbol": ["AAPL"],
            "DailyOpen": [1],
            "DailyClose": [4],
            "Short_EMABBConfluence": [1],
        }
    )

    momentum_df, mean_reversion_df, ema_bb_confluence_df = get_shortterm_stocks_df()

    assert "Symbol" in momentum_df.columns
    assert "Symbol" in mean_reversion_df.columns
    assert "Symbol" in ema_bb_confluence_df.columns

    assert "Short_Momentum" in momentum_df.columns
    assert "Short_MeanReversion" in mean_reversion_df.columns
    assert "Short_EMABBConfluence" in ema_bb_confluence_df.columns
