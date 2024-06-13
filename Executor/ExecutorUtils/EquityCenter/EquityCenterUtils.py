import os
import sys
import pandas as pd
import sqlite3
import yfinance as yf
from dotenv import load_dotenv

# Add current directory to system path
DIR = os.getcwd()
sys.path.append(DIR)

# Load environment variables
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup  # noqa: E402

logger = LoggerSetup()


def get_stock_codes():
    """
    Fetch stock codes from a CSV file specified in the environment variables.

    Returns:
        list: A list of stock symbols.
    """
    try:
        url = os.getenv("tickers_url")
        return list(pd.read_csv(url)["SYMBOL"].values)
    except Exception as e:
        logger.error(f"Error fetching stock codes: {e}")
        return []


def get_stock_data(stock_code, period, duration):
    """
    Fetch historical stock data using the yfinance library.

    Args:
        stock_code (str): The stock symbol.
        period (str): The period of data to fetch (e.g., '1y' for one year).
        duration (str): The duration of each data point (e.g., '1d' for daily).

    Returns:
        DataFrame: A DataFrame containing the historical stock data.
    """
    try:
        append_exchange = ".NS"
        data = yf.download(
            tickers=f"{stock_code}{append_exchange}", period=period, interval=duration
        )
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {stock_code}: {e}")
        return pd.DataFrame()


def get_financial_data(stock_symbols):
    """
    Fetch financial data for given stock symbols.

    Args:
        stock_symbols (list): List of stock symbols.

    Returns:
        DataFrame: DataFrame containing financial data.
    """
    data = []
    for symbol in stock_symbols:
        try:
            stock = yf.Ticker(f"{symbol}.NS")
            info = stock.info
            financials = {
                "Symbol": symbol,
                "Market Cap": info.get("marketCap"),
                "Total Revenue": info.get("totalRevenue"),
                "Net Income": info.get("netIncomeToCommon"),
                "EPS": info.get("trailingEps"),
                "P/E Ratio": info.get("trailingPE"),
                "P/B Ratio": info.get("priceToBook"),
                "Dividend Yield": info.get("dividendYield"),
                "Operating Income": info.get("operatingIncome"),
                "Total Debt": info.get("totalDebt"),
                "Cash": info.get("totalCash"),
                "EBITDA": info.get("ebitda"),
            }
            data.append(financials)
        except Exception as e:
            logger.error(f"Error fetching financial data for {symbol}: {e}")
    return pd.DataFrame(data)


def indicator_5ema(stock_data):
    """
    Calculate the 5-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 5-period EMA.
    """
    try:
        return stock_data["Close"].ewm(span=5, min_periods=0, adjust=False).mean()
    except Exception as e:
        logger.error(f"Error calculating 5 EMA: {e}")
        return pd.Series()


def indicator_13ema(stock_data):
    """
    Calculate the 13-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 13-period EMA.
    """
    try:
        return stock_data["Close"].ewm(span=13, min_periods=0, adjust=False).mean()
    except Exception as e:
        logger.error(f"Error calculating 13 EMA: {e}")
        return pd.Series()


def indicator_26ema(stock_data):
    """
    Calculate the 26-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 26-period EMA.
    """
    try:
        return stock_data["Close"].ewm(span=26, min_periods=0, adjust=False).mean()
    except Exception as e:
        logger.error(f"Error calculating 26 EMA: {e}")
        return pd.Series()


def indicator_50ema(stock_data):
    """
    Calculate the 50-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 50-period EMA.
    """
    try:
        return stock_data["Close"].ewm(span=50, min_periods=0, adjust=False).mean()
    except Exception as e:
        logger.error(f"Error calculating 50 EMA: {e}")
        return pd.Series()


def indicator_rsi(data, rsi_length, rsi_source):
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
        return pd.Series()


def indicator_bollinger_bands(data, window):
    """
    Calculate the Bollinger Bands for the stock data.

    Args:
        data (DataFrame): The stock data.
        window (int): The period for calculating Bollinger Bands.

    Returns:
        DataFrame: The original DataFrame with added columns for Bollinger Bands.
    """
    try:
        data["MA"] = data["Close"].rolling(window=window).mean()
        data["Std_dev"] = data["Close"].rolling(window=window).std()
        data["Upper_band"] = data["MA"] + (data["Std_dev"] * 2)
        data["Lower_band"] = data["MA"] - (data["Std_dev"] * 2)
        return data
    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands: {e}")
        return data


def indicator_macd(data, fast_length=12, slow_length=26, signal_length=9):
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
    try:
        data["EMA_fast"] = data["Close"].ewm(span=fast_length, adjust=False).mean()
        data["EMA_slow"] = data["Close"].ewm(span=slow_length, adjust=False).mean()
        data["MACD"] = data["EMA_fast"] - data["EMA_slow"]
        data["Signal_line"] = data["MACD"].ewm(span=signal_length, adjust=False).mean()
        return data["MACD"], data["Signal_line"]
    except Exception as e:
        logger.error(f"Error calculating MACD: {e}")
        return pd.Series(), pd.Series()


def indicator_atr(stock_data, window):
    """
    Calculate the Average True Range (ATR) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.
        window (int): The period for calculating ATR.

    Returns:
        Series: A Series containing the ATR values.
    """
    try:
        stock_data["HL"] = stock_data["High"] - stock_data["Low"]
        stock_data["HC"] = abs(stock_data["High"] - stock_data["Close"].shift())
        stock_data["LC"] = abs(stock_data["Low"] - stock_data["Close"].shift())
        stock_data["TR"] = stock_data[["HL", "HC", "LC"]].max(axis=1)
        stock_data["ATR"] = stock_data["TR"].rolling(window=window).mean()
        return stock_data["ATR"]
    except Exception as e:
        logger.error(f"Error calculating ATR: {e}")
        return pd.Series()


def check_if_above_50ema(stock_data):
    """
    Strategy to identify stocks trading above their 50-period EMA.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        DataFrame: The original DataFrame with an additional column indicating
                   whether the stock is above 50 EMA.
    """
    try:
        if stock_data is not None and not stock_data.empty:
            stock_data["EMA_50"] = indicator_50ema(stock_data)
            stock_data["Above_50_EMA"] = stock_data["Close"] > stock_data["EMA_50"]
            return stock_data
        else:
            return None
    except Exception as e:
        logger.error(f"Error checking if above 50 EMA: {e}")
        return stock_data


def store_stock_data_sqldb():
    """
    Fetches stock data and selects top picks based on various strategies.
    Exports selected stocks to CSV files for short term, mid term, and long term picks.
    """
    try:
        stock_symbols = get_stock_codes()

        db_path = os.getenv("equity_stock_data_db_path")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for stock in stock_symbols:
            stock_data_daily = get_stock_data(stock, period="1y", duration="1d")
            stock_data_weekly = get_stock_data(stock, period="2y", duration="1wk")

            if stock_data_daily is not None and stock_data_weekly is not None:
                combined_data = pd.DataFrame(
                    {
                        "Date": stock_data_daily.index.date,
                        "DailyOpen": stock_data_daily["Open"],
                        "DailyHigh": stock_data_daily["High"],
                        "DailyLow": stock_data_daily["Low"],
                        "DailyClose": stock_data_daily["Close"],
                        "DailyVolume": stock_data_daily["Volume"],
                        "WeeklyOpen": stock_data_weekly["Open"].reindex(
                            stock_data_daily.index, method="ffill"
                        ),
                        "WeeklyHigh": stock_data_weekly["High"].reindex(
                            stock_data_daily.index, method="ffill"
                        ),
                        "WeeklyLow": stock_data_weekly["Low"].reindex(
                            stock_data_daily.index, method="ffill"
                        ),
                        "WeeklyClose": stock_data_weekly["Close"].reindex(
                            stock_data_daily.index, method="ffill"
                        ),
                        "WeeklyVolume": stock_data_weekly["Volume"].reindex(
                            stock_data_daily.index, method="ffill"
                        ),
                    }
                )

                table_name = stock.replace(".", "_")
                cursor.execute(
                    f"""
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
                    """
                )

                combined_data.to_sql(table_name, conn, if_exists="replace", index=False)

        conn.commit()
        conn.close()

        logger.info("Stock data has been successfully stored in the database.")
    except Exception as e:
        logger.error(f"Error storing stock data in SQLite DB: {e}")


def read_stock_data_from_db(db_path):
    """
    Reads data from the SQLite database and stores it in a dictionary.

    Args:
        db_path (str): The path to the SQLite database.

    Returns:
        dict: A dictionary containing stock data.
    """
    try:
        stock_data_dict = {}

        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch the list of tables (stock symbols)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        for table in tables:
            stock_symbol = table[0]

            # Read daily data
            daily_query = f"""
            SELECT Date, DailyOpen AS Open, DailyHigh AS High, DailyLow AS Low,
                   DailyClose AS Close, DailyVolume AS Volume
            FROM '{stock_symbol}'
            """
            daily_data = pd.read_sql_query(daily_query, conn)

            # Read weekly data
            weekly_query = f"""
            SELECT Date, WeeklyOpen AS Open, WeeklyHigh AS High, WeeklyLow AS Low,
                   WeeklyClose AS Close, WeeklyVolume AS Volume
            FROM '{stock_symbol}'
            """
            weekly_data = pd.read_sql_query(weekly_query, conn)

            # Populate the dictionary with data
            stock_data_dict[stock_symbol] = {
                "daily_data": {
                    "Open": daily_data["Open"].tolist(),
                    "High": daily_data["High"].tolist(),
                    "Low": daily_data["Low"].tolist(),
                    "Close": daily_data["Close"].tolist(),
                    "Volume": daily_data["Volume"].tolist(),
                },
                "weekly_data": {
                    "Open": weekly_data["Open"].tolist(),
                    "High": weekly_data["High"].tolist(),
                    "Low": weekly_data["Low"].tolist(),
                    "Close": weekly_data["Close"].tolist(),
                    "Volume": weekly_data["Volume"].tolist(),
                },
            }

        # Close the connection
        conn.close()

        return stock_data_dict
    except Exception as e:
        logger.error(f"Error reading stock data from SQLite DB: {e}")
        return {}


def merge_dataframes(momentum_df, mean_reversion_df, ema_bb_df):
    """
    Merge the DataFrames from different strategies into one comprehensive DataFrame.

    Args:
        momentum_df (DataFrame): DataFrame of momentum stocks.
        mean_reversion_df (DataFrame): DataFrame of mean reversion stocks.
        ema_bb_df (DataFrame): DataFrame of EMA-BB confluence stocks.

    Returns:
        DataFrame: Combined DataFrame with all strategies.
    """
    try:
        # First, merge the momentum and mean reversion DataFrames on 'Symbol'
        combined_df = pd.merge(
            momentum_df,
            mean_reversion_df,
            on="Symbol",
            how="outer",
            suffixes=("", "_Drop"),
        )

        # Drop the '_Drop' suffix columns from the first merge
        for col in combined_df.columns:
            if col.endswith("_Drop"):
                combined_df.drop(columns=[col], inplace=True)

        # Merge the combined DataFrame with the EMA-BB DataFrame
        combined_df = pd.merge(
            combined_df, ema_bb_df, on="Symbol", how="outer", suffixes=("", "_Drop")
        )

        # Drop the '_Drop' suffix columns from the second merge
        for col in combined_df.columns:
            if col.endswith("_Drop"):
                combined_df.drop(columns=[col], inplace=True)

        # Fill NaN values with appropriate defaults
        combined_df.fillna(
            {
                "DailyOpen": 0,
                "DailyHigh": 0,
                "DailyLow": 0,
                "DailyClose": 0,
                "WeeklyOpen": 0,
                "WeeklyHigh": 0,
                "WeeklyLow": 0,
                "WeeklyClose": 0,
                "DailyRSI": 0,
                "DailyUpper_band": 0,
                "DailyAbove_50_EMA": 0,
                "DailyMACD": 0,
                "DailySignal_Line": 0,
                "DailyEMA_50": 0,
                "DailyMA": 0,
                "DailyLower_band": 0,
                "WeeklyMA": 0,
                "WeeklyLower_band": 0,
                "Short_Momentum": 0,
                "Short_MeanReversion": 0,
                "Short_EMABBConfluence": 0,
            },
            inplace=True,
        )

        return combined_df
    except Exception as e:
        logger.error(f"Error merging DataFrames: {e}")
        return pd.DataFrame()


def update_todaystocks_db(combined_df):
    """
    Stores the combined DataFrame to a SQL database.

    Args:
        combined_df (DataFrame): Combined DataFrame of all stocks from different
                                 strategies.
    """
    try:
        # Connect to the TodayStocks.db database (create it if it doesn't exist)
        db_path = os.getenv("today_stock_data_db_path")
        conn = sqlite3.connect(db_path)

        # Write the DataFrame to a table in the SQL database
        combined_df.to_sql("CombinedStocks", conn, if_exists="replace", index=False)

        # Commit and close the connection
        conn.commit()
        conn.close()

        logger.info(
            "Stock data has been successfully stored in the TodayStocks.db database."
        )
    except Exception as e:
        logger.error(f"Error updating TodayStocks DB: {e}")


if __name__ == "__main__":
    store_stock_data_sqldb()
