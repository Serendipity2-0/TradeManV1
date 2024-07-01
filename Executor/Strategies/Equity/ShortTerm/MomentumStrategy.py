import pandas as pd
import yfinance as yf
import os
from dotenv import load_dotenv

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.Strategies.Equity.EquityBase import indicator_bollinger_bands,indicator_MACD,indicator_RSI,check_if_above_50EMA
logger = LoggerSetup()

def perform_momentum_strategy(stock_data_dict):
    """
    Strategy to identify momentum stocks.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        list: A list of selected stocks based on momentum strategy.
    """
    global selected_stocks
    selected_stocks = []
    for symbol in stock_data_dict.keys():
        stock_data_daily = stock_data_dict[symbol]["daily_data"]
        if stock_data_daily is not None and not stock_data_daily.empty:
            # Calculate RSI
            rsi_length_input = 14
            rsi_source_input = "Close"
            rsi_values = indicator_RSI(
                stock_data_daily, rsi_length_input, rsi_source_input
            )

            # Calculate Bollinger Bands
            bb_window = 20
            stock_data_daily = indicator_bollinger_bands(stock_data_daily, bb_window)

            # Check if LTP is above 50 EMA
            stock_data_daily = check_if_above_50EMA(stock_data_daily)

            macd, signal_line = indicator_MACD(stock_data_daily)

            # Apply momentum Strategy conditions
            if rsi_values.iloc[-1] > 50 and stock_data_daily["Above_50_EMA"].iloc[-1]:
                if (
                    stock_data_daily["Upper_band"].iloc[-1]
                    < stock_data_daily["Close"].iloc[-1]
                ):
                    if macd.iloc[-1] > signal_line.iloc[-1]:  # Condition 4
                        all_time_high = stock_data_daily["High"].max()
                        last_traded_price = stock_data_daily["Close"].iloc[-1]
                        ratio_ATH_LTP = all_time_high / last_traded_price
                        selected_stocks.append([symbol, ratio_ATH_LTP])
    return selected_stocks