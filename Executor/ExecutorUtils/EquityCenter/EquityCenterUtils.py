import os
import sys
import pandas as pd
import sqlite3
import yfinance as yf
from dotenv import load_dotenv
import numpy as np
import datetime as dt
from time import sleep

# Add current directory to system path
DIR = os.getcwd()
sys.path.append(DIR)

# Load environment variables
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeUtils import holidays
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    send_messsage_via_discord,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
    Instrument as instrument_obj,
    get_single_ltp,
)

logger = LoggerSetup()
SHORT_MOMENTUM = "Short_Momentum"
SHORT_EMABBCONFLUENCE = "Short_EMABBConfluence"
SHORT_MEANREVERSION = "Short_MeanReversion"
MID_TFMOMENTUM = "Mid_tfMomentum"
MID_TFEMA = "Mid_tfEma"
LONG_RATIO = "Long_Ratio"
LONG_COMBO = "Long_Combo"
FINANCIAL_DB_PATH = os.getenv("FINANCIAL_DB_PATH")
TICKERS_URL = os.getenv("TICKERS_URL")
EQUITY_STOCK_DATA_DB_PATH = os.getenv("EQUITY_STOCK_DATA_DB_PATH")
TODAY_STOCK_DATA_DB_PATH = os.getenv("TODAY_STOCK_DATA_DB_PATH")


def get_stock_codes():
    """
    Fetch stock codes from a CSV file specified in the environment variables.

    Returns:
        list: A list of stock symbols.
    """
    try:
        url = TICKERS_URL
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
        data.index = pd.to_datetime(data.index)  # Ensure the index is DateTime
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {stock_code}: {e}")
        return pd.DataFrame()


def get_financial_data(stock_symbols):
    """
    Fetch financial data for given stock symbols and add additional calculated metrics.

    Args:
        stock_symbols (list): List of stock symbols.

    Returns:
        DataFrame: DataFrame containing financial data with additional metrics.
    """
    data = []
    for symbol in stock_symbols:
        try:
            stock = yf.Ticker(f"{symbol}.NS")
            info = stock.info

            if info is None or info == {}:
                logger.warning(f"No financial data found for {symbol}")
                continue
            # Extract necessary financial information
            cashflow = stock.cashflow
            total_revenue = info.get("totalRevenue", np.nan)
            operating_cashflow = cashflow.loc["Operating Cash Flow"].iloc[0]
            total_debt = info.get("totalDebt", 0)
            book_value_per_share = info.get("bookValue", np.nan)
            shares_outstanding = info.get("sharesOutstanding", np.nan)
            revenue_growth = info.get("revenueGrowth", np.nan)

            if (
                total_revenue is np.nan
                or operating_cashflow is np.nan
                or total_debt is np.nan
                or book_value_per_share is np.nan
                or shares_outstanding is np.nan
            ):
                missing_data = []
                if total_revenue is np.nan:
                    missing_data.append("Total Revenue")
                if operating_cashflow is np.nan:
                    missing_data.append("Operating Cash Flow")
                if total_debt is np.nan:
                    missing_data.append("Total Debt")
                if book_value_per_share is np.nan:
                    missing_data.append("Book Value per Share")
                if shares_outstanding is np.nan:
                    missing_data.append("Shares Outstanding")

                logger.warning(
                    f"Missing financial data for {symbol}: {', '.join(missing_data)}"
                )
                continue
            # Calculate Operating Profit Margin
            operating_profit_margin = (
                (operating_cashflow / total_revenue)
                if total_revenue and operating_cashflow
                else np.nan
            )

            # Estimate Debt to Equity Ratio
            equity = (
                (book_value_per_share * shares_outstanding)
                if book_value_per_share and shares_outstanding
                else np.nan
            )
            debt_to_equity = (total_debt / equity) if equity and total_debt else np.nan

            # Gross Profit Growth (approximated)
            gross_profit_growth = revenue_growth  # Simplified assumption

            # Simplified Piotroski F-Score calculation
            f_score = 0
            f_score += (
                1 if info.get("netIncomeToCommon", 0) > 0 else 0
            )  # Positive net income
            f_score += 1 if info.get("trailingEps", 0) > 0 else 0  # Positive EPS
            f_score += (
                1 if operating_profit_margin and operating_profit_margin > 0 else 0
            )  # Positive operating profit margin
            f_score += (
                1 if debt_to_equity and debt_to_equity < 1 else 0
            )  # Low debt to equity
            f_score += (
                1 if info.get("priceToBook", 3) < 3 else 0
            )  # Price to book ratio < 3
            f_score += (
                1 if info.get("trailingPE", 20) < 20 else 0
            )  # Price to earnings ratio < 20

            # Construct the financial dictionary
            financials = {
                "Symbol": symbol,
                "Market Cap": info.get("marketCap", np.nan),
                "Total Revenue": total_revenue,
                "Net Income": info.get("netIncomeToCommon", np.nan),
                "EPS": info.get("trailingEps", np.nan),
                "P/E Ratio": info.get("trailingPE", np.nan),
                "P/B Ratio": info.get("priceToBook", np.nan),
                "Dividend Yield": info.get("dividendYield", np.nan),
                "Operating Cashflow": operating_cashflow,
                "Total Debt": total_debt,
                "Cash": info.get("totalCash", np.nan),
                "EBITDA": info.get("ebitda", np.nan),
                "Operating Profit Margin": operating_profit_margin,
                "Debt to Equity": debt_to_equity,
                "Gross Profit Growth": gross_profit_growth,
                "Piotroski F-Score": f_score,
                "Return on Equity": info.get("returnOnEquity", np.nan),
            }

            data.append(financials)
        except Exception as e:
            logger.error(f"Error fetching financial data for {symbol}: {e}")

    return pd.DataFrame(data)


def calculate_sma(data, window=20):
    """Calculate Simple Moving Average (SMA)"""
    return data.rolling(window=window).mean()


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


def store_ohlcv_stock_data_sqldb():
    """
    Fetches stock data and selects top picks based on various strategies.
    Exports selected stocks to CSV files for short term, mid term, and long term picks.
    """
    try:
        logger.info("Fetching and storing OHLCV data...")
        stock_symbols = get_stock_codes()

        db_path = EQUITY_STOCK_DATA_DB_PATH
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for stock in stock_symbols:
            stock_data_daily = get_stock_data(stock, period="1y", duration="1d")
            stock_data_weekly = get_stock_data(stock, period="2y", duration="1wk")

            if (stock_data_daily is None or stock_data_daily.empty) or (
                stock_data_weekly is None or stock_data_weekly.empty
            ):
                logger.warning(f"No OHLCV data found for {stock}")
                continue
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


def store_financial_data_sqldb():
    """
    Fetches stock data and selects top picks based on various strategies.
    Exports selected stocks to CSV files for short term, mid term, and long term picks.
    """
    logger.info("Fetching and storing financial data...")
    stock_codes = get_stock_codes()
    stock_financial_data_df = get_financial_data(stock_codes)
    if not stock_financial_data_df.empty:
        # SQLite database path
        table_name = "financials"
        try:
            conn = sqlite3.connect(FINANCIAL_DB_PATH)
            stock_financial_data_df.to_sql(
                table_name, conn, if_exists="replace", index=False
            )
            logger.debug(f"Data uploaded to {table_name} table in {FINANCIAL_DB_PATH}")
        except Exception as e:
            logger.error(f"Error uploading data to SQLite: {e}")
        finally:
            conn.close()


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


def safe_merge(df1, df2, on, how):
    if df1 is None:
        return df2
    if df2 is None:
        return df1
    return pd.merge(df1, df2, on=on, how=how)


def merge_dataframes(
    momentum_df,
    mean_reversion_df,
    ema_bb_df,
    ratio_df,
    combo_df,
    tfmomentum_df,
    tfema_df,
):
    """
    Merge the DataFrames from different strategies into one comprehensive DataFrame.
    """
    try:
        combined_df = safe_merge(
            momentum_df, mean_reversion_df, on="Symbol", how="outer"
        )
        combined_df = safe_merge(combined_df, ema_bb_df, on="Symbol", how="outer")
        combined_df = safe_merge(combined_df, ratio_df, on="Symbol", how="outer")
        combined_df = safe_merge(combined_df, combo_df, on="Symbol", how="outer")
        combined_df = safe_merge(combined_df, tfmomentum_df, on="Symbol", how="outer")
        combined_df = safe_merge(combined_df, tfema_df, on="Symbol", how="outer")

        # Handle '_Drop' columns from multiple merges
        combined_df = combined_df[
            [col for col in combined_df.columns if not col.endswith("_Drop")]
        ]

        # Fill NaN values with appropriate defaults
        defaults = {
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
            "AthLtpRatio": 0,
            "WeeklyLower_band": 0,
            "Market Cap": 0,
            "P/E Ratio": 0,
            "P/B Ratio": 0,
            "Dividend Yield": 0,
            "Piotroski F-Score": 0,
            "Operating Profit Margin": 0,
            "Debt to Equity": 0,
            "Gross Profit Growth": 0,
            SHORT_MOMENTUM: 0,
            SHORT_MEANREVERSION: 0,
            SHORT_EMABBCONFLUENCE: 0,
            LONG_RATIO: 0,
            LONG_COMBO: 0,
            MID_TFMOMENTUM: 0,
            MID_TFEMA: 0,
        }
        combined_df.fillna(defaults, inplace=True)

        return combined_df
    except Exception as e:
        logger.error(f"Error merging DataFrames: {e}")
        return pd.DataFrame()


def update_todaystocks_db(
    momentum_stocks_df,
    mean_reversion_stocks_df,
    ema_bb_confluence_stocks_df,
    ratio_stocks_df=None,
    combo_stocks_df=None,
    tfmomentum_stocks_df=None,
    tfema_stocks_df=None,
):
    """
    Stores the combined DataFrame to a SQL database.

    Args:
        combined_df (DataFrame): Combined DataFrame of all stocks from different
                                 strategies.
    """
    try:

        merged_df = merge_dataframes(
            momentum_df=momentum_stocks_df,
            mean_reversion_df=mean_reversion_stocks_df,
            ema_bb_df=ema_bb_confluence_stocks_df,
            ratio_df=ratio_stocks_df,
            combo_df=combo_stocks_df,
            tfmomentum_df=tfmomentum_stocks_df,
            tfema_df=tfema_stocks_df,
        )
        # Connect to the TodayStocks.db database (create it if it doesn't exist)
        db_path = TODAY_STOCK_DATA_DB_PATH
        conn = sqlite3.connect(db_path)

        # Write the DataFrame to a table in the SQL database
        merged_df.to_sql("CombinedStocks", conn, if_exists="replace", index=False)

        # Commit and close the connection
        conn.commit()
        conn.close()

        logger.info(
            "Stock data has been successfully stored in the TodayStocks.db database."
        )
    except Exception as e:
        logger.error(f"Error updating TodayStocks DB: {e}")


def calculate_ema(data, window):
    """
    Calculate Exponential Moving Average (EMA).

    Args:
        data (pandas.Series): The input data.
        window (int): The window size for calculating EMA.

    Returns:
        pandas.Series: The EMA values.
    """
    return data.ewm(span=window, adjust=False).mean()


def get_asm_gsm_list():
    """
    Get the ASM/GSM list from the database.

    Returns:
        list: The ASM/GSM list.
    """
    try:
        dir = os.getenv("ASM_GSM_LIST_DIR")
        today = dt.datetime.now().strftime("%Y-%m-%d")
        asm_gsm_list_path = os.path.join(dir, f"merged_asm_gsm_{today}.csv")
        asm_gsm_list = pd.read_csv(asm_gsm_list_path)
        symbol_list = asm_gsm_list["SYMBOL"].tolist()
        return symbol_list
    except Exception as e:
        logger.error(f"Error while getting ASM/GSM list: {e}")
        return []


def check_symbol_in_list(symbol_list, symbol):
    """
    Check if the symbol is in the list.

    Args:
        symbol_list (list): The list of symbols.
        symbol (str): The symbol to check.

    Returns:
        bool: True if the symbol is in the list, False otherwise.
    """
    symbol_list = [s.upper() for s in symbol_list]
    symbol = symbol.upper()

    return symbol in symbol_list or symbol.split("-")[0] in symbol_list


def check_symbol_for_erros(symbol, exchange_token, holdings_symbol_list=None):
    """
    Check if the symbol is in the list.

    Args:
        symbol_list (list): The list of symbols.
        symbol (str): The symbol to check.

    Returns:
        bool: True if the symbol is in the list, False otherwise.
    """
    try:
        if holdings_symbol_list is not None:
            if check_symbol_in_list(holdings_symbol_list, symbol):
                logger.debug(f"{symbol} is already in holdings, skipping")
                return False
        if check_symbol_in_list(get_asm_gsm_list(), symbol):
            logger.debug(f"{symbol} is in ASM/GSM list, skipping")
            return False
        if exchange_token is None:
            logger.debug(f"Exchange token not found for {symbol}, skipping")
            return False
        return True
    except Exception as e:
        logger.error(f"Error while checking symbol for errors: {e}")
        return False


def is_today_holiday():
    """
    Check if today is a holiday.

    Returns:
        bool: True if today is a holiday, False otherwise.
    """
    now = dt.datetime.now()
    return now.date() in holidays


def should_wait_for_start_time(desired_start_time_str):
    """
    Check if the current time is before the desired start time.

    Args:
        desired_start_time_str (str): The desired start time in the format "HH:MM".

    Returns:
        bool: True if the current time is before the desired start time, False otherwise.
    """
    now = dt.datetime.now()
    start_hour, start_minute, _ = map(int, desired_start_time_str.split(":"))
    if now.time() < dt.time(9, 0):
        logger.info("Time is before 9:00 AM, Waiting to execute.")
        return True
    wait_time = (
        dt.datetime(now.year, now.month, now.day, start_hour, start_minute) - now
    )
    if wait_time.total_seconds() > 0:
        logger.info(f"Waiting for {wait_time} before starting the bot")
        sleep(wait_time.total_seconds())
        return True
    return False


def get_selected_stocks(strategy_name, today_stocks_df):
    """
    Get the selected stocks for the strategy.

    Args:
        strategy_name (str): The name of the strategy.
        today_stocks_df (DataFrame): The DataFrame of today's stocks.

    Returns:
        tuple: A tuple containing the symbol list and the strategy setups.
    """
    symbol_list = today_stocks_df["Symbol"].tolist()
    strategy_prefix = strategy_name[:-4]
    strategy_setups = [
        col for col in today_stocks_df.columns if col.startswith(f"{strategy_prefix}_")
    ]
    logger.warning(f"Selected stocks for {strategy_name}: {strategy_setups}")
    return symbol_list, strategy_setups


def send_signals_via_discord(setup_symbol_list, setup_name, strategy_name, TRADE_MODE):
    """
    Send the signals via Discord.

    Args:
        setup_symbol_list (list): The list of symbols.
        setup_name (str): The name of the setup.
        strategy_name (str): The name of the strategy.
        TRADE_MODE (str): The trade mode.

    Returns:
        None
    """
    valid_count = 0  # Counter for valid messages sent
    for symbol in setup_symbol_list:
        exchange_token = instrument_obj().get_exchange_token_by_name(symbol, "NSE")
        if not check_symbol_for_erros(symbol, exchange_token):
            continue  # Skip sending a message if the symbol has errors

        ltp = get_single_ltp(exchange_token=exchange_token, segment="NSE")
        ltp = round(ltp * 20) / 20  # Adjust the LTP by rounding to the nearest 0.05
        message = (
            f"{TRADE_MODE} Trade for {strategy_name}\n"
            f"Setup : {setup_name}\n"
            f"Symbol : {symbol}\n"
            f"Ltp : {ltp} \n"
        )
        send_messsage_via_discord(message, strategy_name)
        valid_count += 1
        if valid_count >= 3:
            break

    if valid_count < 3:
        additional_message = f"{valid_count} stocks were selected for {setup_name}."
        send_messsage_via_discord(additional_message, strategy_name)
