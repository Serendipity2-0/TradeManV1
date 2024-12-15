import os
import sys
import pandas as pd
import sqlite3
import yfinance as yf
from dotenv import load_dotenv
import numpy as np
import datetime as dt
from typing import List, Dict, Optional, Union

# Add current directory to system path
DIR = os.getcwd()
sys.path.append(DIR)

# Load environment variables
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

class DataFetcher:
    """
    A class to handle all data fetching and storage operations for equity data.
    
    This class provides methods to fetch stock data from various sources and store
    them in appropriate databases.
    """

    def __init__(self):
        """Initialize DataFetcher with environment variables."""
        self.financial_db_path = os.getenv("FINANCIAL_DB_PATH")
        self.tickers_url = os.getenv("TICKERS_URL")
        self.equity_stock_data_db_path = os.getenv("EQUITY_STOCK_DATA_DB_PATH")
        self.today_stock_data_db_path = os.getenv("TODAY_STOCK_DATA_DB_PATH")

    def get_stock_codes(self) -> List[str]:
        """
        Fetch stock codes from a CSV file specified in the environment variables.

        Returns:
            list: A list of stock symbols.
        """
        try:
            return list(pd.read_csv(self.tickers_url)["SYMBOL"].values)
        except Exception as e:
            logger.error(f"Error fetching stock codes: {e}")
            return []

    def get_stock_data(self, stock_code: str, period: str, duration: str) -> pd.DataFrame:
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
                tickers=f"{stock_code}{append_exchange}", 
                period=period, 
                interval=duration
            )
            data.index = pd.to_datetime(data.index)
            return data
        except Exception as e:
            logger.error(f"Error fetching data for {stock_code}: {e}")
            return pd.DataFrame()

    def read_stock_data_from_db(self, db_path: str) -> Dict:
        """
        Reads data from the SQLite database and stores it in a dictionary.
        Handles both OHLCV and financial data based on the database type.

        Args:
            db_path (str): The path to the SQLite database.

        Returns:
            dict: A dictionary containing stock data.
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check if this is the financial database
            if db_path == self.financial_db_path:
                return self._read_financial_data(conn)
            else:
                return self._read_ohlcv_data(conn)

        except Exception as e:
            logger.error(f"Error reading stock data from SQLite DB: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    def _read_financial_data(self, conn: sqlite3.Connection) -> Dict:
        """
        Read financial data from database.

        Args:
            conn: SQLite connection

        Returns:
            Dict: Dictionary containing financial data
        """
        try:
            # Read the financials table with proper column names
            query = """
            SELECT 
                Symbol,
                "Market Cap",
                "Total Revenue",
                "Net Income",
                EPS,
                "P/E Ratio",
                "P/B Ratio",
                "Dividend Yield",
                "Operating Cashflow",
                "Total Debt",
                Cash,
                EBITDA,
                "Operating Profit Margin",
                "Debt to Equity",
                "Gross Profit Growth",
                "Piotroski F-Score",
                "Return on Equity"
            FROM financials
            """
            df = pd.read_sql_query(query, conn)
            
            # Convert DataFrame to dictionary with symbol as key
            financial_data = {}
            for _, row in df.iterrows():
                symbol = row['Symbol']
                financial_data[symbol] = {
                    'market_cap': row['Market Cap'],
                    'total_revenue': row['Total Revenue'],
                    'net_income': row['Net Income'],
                    'eps': row['EPS'],
                    'pe_ratio': row['P/E Ratio'],
                    'pb_ratio': row['P/B Ratio'],
                    'dividend_yield': row['Dividend Yield'],
                    'operating_cashflow': row['Operating Cashflow'],
                    'total_debt': row['Total Debt'],
                    'cash': row['Cash'],
                    'ebitda': row['EBITDA'],
                    'operating_profit_margin': row['Operating Profit Margin'],
                    'debt_to_equity': row['Debt to Equity'],
                    'gross_profit_growth': row['Gross Profit Growth'],
                    'piotroski_f_score': row['Piotroski F-Score'],
                    'return_on_equity': row['Return on Equity']
                }
            
            return financial_data

        except Exception as e:
            logger.error(f"Error reading financial data: {e}")
            return {}

    def _read_ohlcv_data(self, conn: sqlite3.Connection) -> Dict:
        """
        Read OHLCV data from database.

        Args:
            conn: SQLite connection

        Returns:
            Dict: Dictionary containing OHLCV data
        """
        try:
            stock_data_dict = {}
            cursor = conn.cursor()

            # Get list of tables (stock symbols)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            for table in tables:
                stock_symbol = table[0]
                
                # Read daily data
                daily_data = pd.read_sql_query(
                    f"""
                    SELECT 
                        DailyOpen as Open,
                        DailyHigh as High,
                        DailyLow as Low,
                        DailyClose as Close,
                        DailyVolume as Volume
                    FROM '{stock_symbol}'
                    """, 
                    conn
                )

                # Read weekly data
                weekly_data = pd.read_sql_query(
                    f"""
                    SELECT 
                        WeeklyOpen as Open,
                        WeeklyHigh as High,
                        WeeklyLow as Low,
                        WeeklyClose as Close,
                        WeeklyVolume as Volume
                    FROM '{stock_symbol}'
                    """, 
                    conn
                )

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

            return stock_data_dict

        except Exception as e:
            logger.error(f"Error reading OHLCV data: {e}")
            return {}

    def store_financial_data_sqldb(self):
        """
        Fetches and stores financial data in the SQLite database.
        """
        logger.info("Fetching and storing financial data...")
        stock_codes = self.get_stock_codes()
        stock_financial_data_df = self.get_financial_data(stock_codes)
        
        if not stock_financial_data_df.empty:
            try:
                conn = sqlite3.connect(self.financial_db_path)
                stock_financial_data_df.to_sql(
                    "financials", conn, if_exists="replace", index=False
                )
                logger.debug(f"Data uploaded to financials table in {self.financial_db_path}")
            except Exception as e:
                logger.error(f"Error uploading data to SQLite: {e}")
            finally:
                conn.close()

    def store_ohlcv_stock_data_sqldb(self):
        """
        Fetches stock data and stores it in the SQLite database.
        """
        try:
            logger.info("Fetching and storing OHLCV data...")
            stock_symbols = self.get_stock_codes()

            conn = sqlite3.connect(self.equity_stock_data_db_path)
            cursor = conn.cursor()

            for stock in stock_symbols:
                stock_data_daily = self.get_stock_data(stock, period="1y", duration="1d")
                stock_data_weekly = self.get_stock_data(stock, period="2y", duration="1wk")

                if (stock_data_daily is None or stock_data_daily.empty) or (
                    stock_data_weekly is None or stock_data_weekly.empty
                ):
                    logger.warning(f"No OHLCV data found for {stock}")
                    continue

                combined_data = pd.DataFrame({
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
                })

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
