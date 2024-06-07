import pandas as pd
import yfinance as yf
import os
from dotenv import load_dotenv

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.Strategies.Equity.EquityBase import indicator_bollinger_bands, indicator_RSI, check_if_above_50EMA
logger = LoggerSetup()

def perform_mean_reversion_strategy(stock_data_dict):
    """
    Strategy to identify mean reversion stocks.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        DataFrame: A DataFrame with columns Symbol, DailyOpen, DailyHigh, DailyLow, DailyClose, 
                   WeeklyOpen, WeeklyHigh, WeeklyLow, WeeklyClose, DailyRSI, DailyLower_band, 
                   DailyAbove_50_EMA, WeeklyMA, WeeklyLower_band, Short_MeanReversion.
    """
    results = []

    for symbol, data in stock_data_dict.items():
        stock_data_daily = pd.DataFrame(data["daily_data"])
        stock_data_weekly = pd.DataFrame(data["weekly_data"])
        
        if stock_data_daily.empty or stock_data_weekly.empty:
            continue

        # Calculate RSI for daily data
        rsi_length_input = 14
        rsi_source_input = "Close"
        rsi_values = indicator_RSI(stock_data_daily, rsi_length_input, rsi_source_input)

        # Calculate Bollinger Bands for daily and weekly data
        bb_window = 20
        stock_data_daily = indicator_bollinger_bands(stock_data_daily, bb_window)
        stock_data_weekly = indicator_bollinger_bands(stock_data_weekly, bb_window)

        # Check if LTP is above 50 EMA for daily data
        stock_data_daily = check_if_above_50EMA(stock_data_daily)

        # Get the most recent data
        latest_daily_data = stock_data_daily.iloc[-1]
        latest_weekly_data = stock_data_weekly.iloc[-1]

        # Check the mean reversion condition
        if (
            rsi_values.iloc[-1] < 40
            and latest_daily_data["Above_50_EMA"]
            and latest_weekly_data["MA"] < latest_weekly_data["Close"]
            and stock_data_daily["Lower_band"].iloc[-2] < stock_data_daily["Lower_band"].iloc[-3]
            and latest_daily_data["Lower_band"] > stock_data_daily["Lower_band"].iloc[-2]
        ):
            # Collect today's OHLC for daily data
            daily_open = latest_daily_data["Open"]
            daily_high = latest_daily_data["High"]
            daily_low = latest_daily_data["Low"]
            daily_close = latest_daily_data["Close"]
            
            # Collect this week's OHLC for weekly data
            weekly_open = latest_weekly_data["Open"]
            weekly_high = latest_weekly_data["High"]
            weekly_low = latest_weekly_data["Low"]
            weekly_close = latest_weekly_data["Close"]
            
            # Collect indicator values for daily data
            daily_rsi = rsi_values.iloc[-1]
            daily_lower_band = latest_daily_data["Lower_band"]
            daily_above_50_ema = latest_daily_data["Above_50_EMA"]

            # Collect indicator values for weekly data
            weekly_ma = latest_weekly_data["MA"]
            weekly_lower_band = latest_weekly_data["Lower_band"]
            
            # Append to results
            results.append({
                "Symbol": symbol,
                "DailyOpen": daily_open,
                "DailyHigh": daily_high,
                "DailyLow": daily_low,
                "DailyClose": daily_close,
                "WeeklyOpen": weekly_open,
                "WeeklyHigh": weekly_high,
                "WeeklyLow": weekly_low,
                "WeeklyClose": weekly_close,
                "DailyRSI": daily_rsi,
                "DailyLower_band": daily_lower_band,
                "DailyAbove_50_EMA": daily_above_50_ema,
                "WeeklyMA": weekly_ma,
                "WeeklyLower_band": weekly_lower_band,
                "Short_MeanReversion": 1
            })
        else:
            # If not selected, still add stock with Short_MeanReversion = 0
            results.append({
                "Symbol": symbol,
                "DailyOpen": latest_daily_data["Open"],
                "DailyHigh": latest_daily_data["High"],
                "DailyLow": latest_daily_data["Low"],
                "DailyClose": latest_daily_data["Close"],
                "WeeklyOpen": latest_weekly_data["Open"],
                "WeeklyHigh": latest_weekly_data["High"],
                "WeeklyLow": latest_weekly_data["Low"],
                "WeeklyClose": latest_weekly_data["Close"],
                "DailyRSI": rsi_values.iloc[-1],
                "DailyLower_band": latest_daily_data["Lower_band"],
                "DailyAbove_50_EMA": latest_daily_data["Above_50_EMA"],
                "WeeklyMA": latest_weekly_data["MA"],
                "WeeklyLower_band": latest_weekly_data["Lower_band"],
                "Short_MeanReversion": 0
            })

    # Convert the list of results to a DataFrame
    columns = ["Symbol", "DailyOpen", "DailyHigh", "DailyLow", "DailyClose", 
               "WeeklyOpen", "WeeklyHigh", "WeeklyLow", "WeeklyClose",
               "DailyRSI", "DailyLower_band", "DailyAbove_50_EMA", 
               "WeeklyMA", "WeeklyLower_band", "Short_MeanReversion"]
    results_df = pd.DataFrame(results, columns=columns)

    return results_df

# Example usage (assuming stock_data_dict is already defined):
# stock_data_dict = read_stock_data_from_db('path_to_stock_data.db')
# df = perform_mean_reversion_strategy(stock_data_dict)
