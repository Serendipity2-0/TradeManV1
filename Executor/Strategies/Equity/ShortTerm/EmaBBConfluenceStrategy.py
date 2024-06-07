import pandas as pd
import yfinance as yf
import os
from dotenv import load_dotenv

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.Strategies.Equity.EquityBase import indicator_bollinger_bands, indicator_50EMA
logger = LoggerSetup()

def perform_EmaBB_Confluence_strategy(stock_data_dict):
    """
    Strategy to identify stocks with EMA and Bollinger Bands confluence.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        DataFrame: A DataFrame with columns Symbol, DailyOpen, DailyHigh, DailyLow, DailyClose, 
                   WeeklyOpen, WeeklyHigh, WeeklyLow, WeeklyClose, DailyEMA_50, DailyMA, 
                   DailyLower_band, Short_EMABBConfluence.
    """
    results = []

    for symbol, data in stock_data_dict.items():
        stock_data_daily = pd.DataFrame(data["daily_data"])
        stock_data_weekly = pd.DataFrame(data["weekly_data"])
        
        if stock_data_daily.empty or stock_data_weekly.empty:
            continue

        # Calculate Bollinger Bands for daily and weekly data
        bb_window = 20
        stock_data_daily = indicator_bollinger_bands(stock_data_daily, bb_window)
        stock_data_weekly = indicator_bollinger_bands(stock_data_weekly, bb_window)

        # Calculate 50 EMA for daily data
        stock_data_daily["EMA_50"] = indicator_50EMA(stock_data_daily)

        # Get the most recent row of data
        latest_daily_data = stock_data_daily.iloc[-1]
        latest_weekly_data = stock_data_weekly.iloc[-1]

        # Check the confluence condition
        if (
            latest_daily_data["EMA_50"] <= latest_daily_data["Lower_band"]
            and latest_daily_data["Close"] < latest_daily_data["MA"]
            and stock_data_daily["Lower_band"].iloc[-2] < stock_data_daily["Lower_band"].iloc[-3]
            and latest_daily_data["Lower_band"] > stock_data_daily["Lower_band"].iloc[-2]
        ):
            bollinger_close_to_ema = abs(latest_daily_data["Lower_band"] - latest_daily_data["EMA_50"]) < 0.05 * latest_daily_data["Close"]
            if bollinger_close_to_ema:
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
                daily_ema_50 = latest_daily_data["EMA_50"]
                daily_ma = latest_daily_data["MA"]
                daily_lower_band = latest_daily_data["Lower_band"]
                
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
                    "DailyEMA_50": daily_ema_50,
                    "DailyMA": daily_ma,
                    "DailyLower_band": daily_lower_band,
                    "Short_EMABBConfluence": 1
                })
        else:
            # If not selected, still add stock with Short_EMABBConfluence = 0
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
                "DailyEMA_50": latest_daily_data["EMA_50"],
                "DailyMA": latest_daily_data["MA"],
                "DailyLower_band": latest_daily_data["Lower_band"],
                "Short_EMABBConfluence": 0
            })

    # Convert the list of results to a DataFrame
    columns = ["Symbol", "DailyOpen", "DailyHigh", "DailyLow", "DailyClose", 
               "WeeklyOpen", "WeeklyHigh", "WeeklyLow", "WeeklyClose",
               "DailyEMA_50", "DailyMA", "DailyLower_band", "Short_EMABBConfluence"]
    results_df = pd.DataFrame(results, columns=columns)

    return results_df

# Example usage (assuming stock_data_dict is already defined):
# stock_data_dict = read_stock_data_from_db('path_to_stock_data.db')
# df = perform_EmaBB_Confluence_strategy(stock_data_dict)
# print(df)
