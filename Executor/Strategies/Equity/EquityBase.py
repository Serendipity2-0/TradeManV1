import pandas as pd
import json
import sqlite3
import yfinance as yf
import os
from dotenv import load_dotenv
import sys

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()
    
def get_stock_codes():
    """
    Fetch stock codes from a CSV file specified in the environment variables.

    Returns:
        list: A list of stock symbols.
    """
    url = os.getenv("tickers_url")
    return list(pd.read_csv(url)["SYMBOL"].values)


def get_stock_data(stockCode, period, duration):
    """
    Fetch historical stock data using the yfinance library.

    Args:
        stockCode (str): The stock symbol.
        period (str): The period of data to fetch (e.g., '1y' for one year).
        duration (str): The duration of each data point (e.g., '1d' for daily).

    Returns:
        DataFrame: A DataFrame containing the historical stock data.
    """
    try:
        append_exchange = ".NS"
        data = yf.download(
            tickers=stockCode + append_exchange, period=period, interval=duration
        )
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {stockCode}: {e}")
        return None
    


def indicator_5EMA(stock_data):
    """
    Calculate the 5-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 5-period EMA.
    """
    return stock_data["Close"].ewm(span=5, min_periods=0, adjust=False).mean()


def indicator_13EMA(stock_data):
    """
    Calculate the 13-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 13-period EMA.
    """
    return stock_data["Close"].ewm(span=13, min_periods=0, adjust=False).mean()


def indicator_26EMA(stock_data):
    """
    Calculate the 26-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 26-period EMA.
    """
    return stock_data["Close"].ewm(span=26, min_periods=0, adjust=False).mean()


def indicator_50EMA(stock_data):
    """
    Calculate the 50-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 50-period EMA.
    """
    return stock_data["Close"].ewm(span=50, min_periods=0, adjust=False).mean()


def indicator_RSI(data, rsi_length, rsi_source):
    """
    Calculate the Relative Strength Index (RSI) for the stock data.

    Args:
        data (DataFrame): The stock data.
        rsi_length (int): The period for calculating RSI.
        rsi_source (str): The source column for RSI calculation (e.g., 'Close').

    Returns:
        Series: A Series containing the RSI values.
    """
    try:
        delta = data[rsi_source].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=rsi_length).mean()
        avg_loss = loss.rolling(window=rsi_length).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except Exception as e:
        logger.error(f"Error calculating RSI: {e}")
        pass


def indicator_bollinger_bands(data, window):
    """
    Calculate the Bollinger Bands for the stock data.

    Args:
        data (DataFrame): The stock data.
        window (int): The period for calculating Bollinger Bands.

    Returns:
        DataFrame: The original DataFrame with added columns for Bollinger Bands.
    """
    data["MA"] = data["Close"].rolling(window=window).mean()
    data["Std_dev"] = data["Close"].rolling(window=window).std()
    data["Upper_band"] = data["MA"] + (data["Std_dev"] * 2)
    data["Lower_band"] = data["MA"] - (data["Std_dev"] * 2)
    return data


def indicator_MACD(data, fast_length=12, slow_length=26, signal_length=9):
    """
    Calculate the Moving Average Convergence Divergence (MACD) for the stock data.

    Args:
        data (DataFrame): The stock data.
        fast_length (int): The period for the fast EMA.
        slow_length (int): The period for the slow EMA.
        signal_length (int): The period for the signal line.

    Returns:
        tuple: A tuple containing the MACD line and the signal line.
    """
    data["EMA_fast"] = data["Close"].ewm(span=fast_length, adjust=False).mean()
    data["EMA_slow"] = data["Close"].ewm(span=slow_length, adjust=False).mean()
    data["MACD"] = data["EMA_fast"] - data["EMA_slow"]
    data["Signal_line"] = data["MACD"].ewm(span=signal_length, adjust=False).mean()
    return data["MACD"], data["Signal_line"]


def indicator_atr(stock_data, window):
    """
    Calculate the Average True Range (ATR) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.
        window (int): The period for calculating ATR.

    Returns:
        Series: A Series containing the ATR values.
    """
    stock_data["HL"] = stock_data["High"] - stock_data["Low"]
    stock_data["HC"] = abs(stock_data["High"] - stock_data["Close"].shift())
    stock_data["LC"] = abs(stock_data["Low"] - stock_data["Close"].shift())
    stock_data["TR"] = stock_data[["HL", "HC", "LC"]].max(axis=1)
    stock_data["ATR"] = stock_data["TR"].rolling(window=window).mean()
    return stock_data["ATR"]

def check_if_above_50EMA(stock_data):
    """
    Strategy to identify stocks trading above their 50-period EMA.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        DataFrame: The original DataFrame with an additional column indicating whether the stock is above 50 EMA.
    """
    if stock_data is not None and not stock_data.empty:
        stock_data["EMA_50"] = indicator_50EMA(stock_data)
        stock_data["Above_50_EMA"] = stock_data["Close"] > stock_data["EMA_50"]
        return stock_data
    else:
        return None
    
def get_stockpicks_csv():
    """
    Fetches stock data and selects top picks based on various strategies.
    Exports selected stocks to CSV files for short term, mid term, and long term picks.
    """
    stock_symbols = get_stock_codes()
    counter = 0

    # Connect to the SQLite database
    conn = sqlite3.connect('stock_data.db')
    cursor = conn.cursor()

    for stock in stock_symbols:
        if counter >= 20:
            break

        # Fetch daily and weekly data
        stock_data_daily = get_stock_data(stock, period="1y", duration="1d")
        stock_data_weekly = get_stock_data(stock, period="2y", duration="1wk")
        
        if stock_data_daily is not None and stock_data_weekly is not None:
            # Create a DataFrame to store combined data
            combined_data = pd.DataFrame({
                'Date': stock_data_daily.index,
                'DailyOpen': stock_data_daily['Open'],
                'DailyHigh': stock_data_daily['High'],
                'DailyLow': stock_data_daily['Low'],
                'DailyClose': stock_data_daily['Close'],
                'DailyVolume': stock_data_daily['Volume'],
                'WeeklyOpen': stock_data_weekly['Open'].reindex(stock_data_daily.index, method='ffill'),
                'WeeklyHigh': stock_data_weekly['High'].reindex(stock_data_daily.index, method='ffill'),
                'WeeklyLow': stock_data_weekly['Low'].reindex(stock_data_daily.index, method='ffill'),
                'WeeklyClose': stock_data_weekly['Close'].reindex(stock_data_daily.index, method='ffill'),
                'WeeklyVolume': stock_data_weekly['Volume'].reindex(stock_data_daily.index, method='ffill')
            })

            # Create table for each stock if it doesn't exist
            table_name = stock.replace('.', '_')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS "{table_name}" (
                    Date TEXT,
                    DailyOpen REAL,
                    DailyHigh REAL,
                    DailyLow REAL,
                    DailyClose REAL,
                    DailyVolume INTEGER,
                    WeeklyOpen REAL,
                    WeeklyHigh REAL,
                    WeeklyLow REAL,
                    WeeklyClose REAL,
                    WeeklyVolume INTEGER
                )
            ''')

            # Insert data into the table
            combined_data.to_sql(table_name, conn, if_exists='replace', index=False)

            counter += 1

    # Commit and close the connection
    conn.commit()
    conn.close()

    print("Stock data has been successfully stored in the database.")

# Call the function to execute the process
get_stockpicks_csv()