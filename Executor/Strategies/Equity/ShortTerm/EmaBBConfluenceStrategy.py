import pandas as pd
import yfinance as yf
import os
from dotenv import load_dotenv

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.Strategies.Equity.EquityBase import indicator_bollinger_bands,indicator_50EMA
logger = LoggerSetup()


def perform_EmaBB_Confluence_strategy(stock_data_dict):
    """
    Strategy to identify stocks with EMA and Bollinger Bands confluence.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        list: A list of selected stocks based on EMA and Bollinger Bands confluence strategy.
    """
    global selected_stocks
    selected_stocks = []
    for symbol in stock_data_dict.keys():
        stock_data_daily = stock_data_dict[symbol]["daily_data"]
        if stock_data_daily is not None and not stock_data_daily.empty:
            bb_window = 20
            stock_data_daily = indicator_bollinger_bands(stock_data_daily, bb_window)
            stock_data_daily["EMA_50"] = indicator_50EMA(stock_data_daily)
            if (
                stock_data_daily["EMA_50"].iloc[-1]
                <= stock_data_daily["Lower_band"].iloc[-1]
            ):
                if stock_data_daily["Close"].iloc[-1] < stock_data_daily["MA"].iloc[-1]:
                    if (
                        stock_data_daily["Lower_band"].iloc[-2]
                        < stock_data_daily["Lower_band"].iloc[-3]
                    ):
                        if (
                            stock_data_daily["Lower_band"].iloc[-1]
                            > stock_data_daily["Lower_band"].iloc[-2]
                        ):
                            bollinger_close_to_ema = (
                                abs(
                                    stock_data_daily["Lower_band"].iloc[-1]
                                    - stock_data_daily["EMA_50"].iloc[-1]
                                )
                                < 0.05 * stock_data_daily["Close"].iloc[-1]
                            )
                            if bollinger_close_to_ema:
                                all_time_high = stock_data_daily["High"].max()
                                last_traded_price = stock_data_daily["Close"].iloc[-1]
                                ratio_ATH_LTP = all_time_high / last_traded_price
                                selected_stocks.append([symbol, ratio_ATH_LTP])
                                break
    return selected_stocks