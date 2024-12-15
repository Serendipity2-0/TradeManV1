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

    def get_financial_data(self, stock_symbols: List[str]) -> pd.DataFrame:
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

                # Extract and calculate financial metrics
                financial_data = self._calculate_financial_metrics(stock, info, symbol)
                if financial_data:
                    data.append(financial_data)

            except Exception as e:
                logger.error(f"Error fetching financial data for {symbol}: {e}")

        return pd.DataFrame(data)

    def _calculate_financial_metrics(
        self, 
        stock: yf.Ticker, 
        info: Dict, 
        symbol: str
    ) -> Optional[Dict]:
        """
        Calculate financial metrics for a given stock.

        Args:
            stock: yfinance Ticker object
            info: Stock information dictionary
            symbol: Stock symbol

        Returns:
            Optional[Dict]: Dictionary containing calculated financial metrics
        """
        try:
            cashflow = stock.cashflow
            total_revenue = info.get("totalRevenue", np.nan)
            operating_cashflow = cashflow.loc["Operating Cash Flow"].iloc[0]
            total_debt = info.get("totalDebt", 0)
            book_value_per_share = info.get("bookValue", np.nan)
            shares_outstanding = info.get("sharesOutstanding", np.nan)
            revenue_growth = info.get("revenueGrowth", np.nan)

            # Validate required data
            required_fields = {
                "Total Revenue": total_revenue,
                "Operating Cash Flow": operating_cashflow,
                "Total Debt": total_debt,
                "Book Value per Share": book_value_per_share,
                "Shares Outstanding": shares_outstanding
            }

            missing_fields = [k for k, v in required_fields.items() if pd.isna(v)]
            if missing_fields:
                logger.warning(
                    f"Missing financial data for {symbol}: {', '.join(missing_fields)}"
                )
                return None

            # Calculate financial ratios
            operating_profit_margin = (operating_cashflow / total_revenue) if total_revenue and operating_cashflow else np.nan
            equity = (book_value_per_share * shares_outstanding) if book_value_per_share and shares_outstanding else np.nan
            debt_to_equity = (total_debt / equity) if equity and total_debt else np.nan

            # Calculate F-Score
            f_score = self._calculate_f_score(info, operating_profit_margin, debt_to_equity)

            return {
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
                "Gross Profit Growth": revenue_growth,
                "Piotroski F-Score": f_score,
                "Return on Equity": info.get("returnOnEquity", np.nan),
            }
        except Exception as e:
            logger.error(f"Error calculating financial metrics for {symbol}: {e}")
            return None

    def _calculate_f_score(
        self, 
        info: Dict, 
        operating_profit_margin: float, 
        debt_to_equity: float
    ) -> int:
        """
        Calculate Piotroski F-Score for a stock.

        Args:
            info: Stock information dictionary
            operating_profit_margin: Operating profit margin
            debt_to_equity: Debt to equity ratio

        Returns:
            int: Calculated F-Score
        """
        f_score = 0
        f_score += 1 if info.get("netIncomeToCommon", 0) > 0 else 0
        f_score += 1 if info.get("trailingEps", 0) > 0 else 0
        f_score += 1 if operating_profit_margin and operating_profit_margin > 0 else 0
        f_score += 1 if debt_to_equity and debt_to_equity < 1 else 0
        f_score += 1 if info.get("priceToBook", 3) < 3 else 0
        f_score += 1 if info.get("trailingPE", 20) < 20 else 0
        return f_score

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

                combined_data = self._prepare_combined_data(
                    stock_data_daily, stock_data_weekly
                )
                table_name = stock.replace(".", "_")
                
                self._create_stock_table(cursor, table_name)
                combined_data.to_sql(table_name, conn, if_exists="replace", index=False)

            conn.commit()
            conn.close()
            logger.info("Stock data has been successfully stored in the database.")

        except Exception as e:
            logger.error(f"Error storing stock data in SQLite DB: {e}")

    def _prepare_combined_data(
        self, 
        daily_data: pd.DataFrame, 
        weekly_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Prepare combined daily and weekly data.

        Args:
            daily_data: Daily OHLCV data
            weekly_data: Weekly OHLCV data

        Returns:
            pd.DataFrame: Combined data
        """
        return pd.DataFrame({
            "Date": daily_data.index.date,
            "DailyOpen": daily_data["Open"],
            "DailyHigh": daily_data["High"],
            "DailyLow": daily_data["Low"],
            "DailyClose": daily_data["Close"],
            "DailyVolume": daily_data["Volume"],
            "WeeklyOpen": weekly_data["Open"].reindex(
                daily_data.index, method="ffill"
            ),
            "WeeklyHigh": weekly_data["High"].reindex(
                daily_data.index, method="ffill"
            ),
            "WeeklyLow": weekly_data["Low"].reindex(
                daily_data.index, method="ffill"
            ),
            "WeeklyClose": weekly_data["Close"].reindex(
                daily_data.index, method="ffill"
            ),
            "WeeklyVolume": weekly_data["Volume"].reindex(
                daily_data.index, method="ffill"
            ),
        })

    def _create_stock_table(self, cursor: sqlite3.Cursor, table_name: str):
        """
        Create a stock table in the database.

        Args:
            cursor: SQLite cursor
            table_name: Name of the table to create
        """
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

    def store_financial_data_sqldb(self):
        """
        Fetches and stores financial data in the SQLite database.
        """
        logger.info("Fetching and storing financial data...")
        stock_codes = self.get_stock_codes()
        stock_financial_data_df = self.get_financial_data(stock_codes)
        
        if not stock_financial_data_df.empty:
            table_name = "financials"
            try:
                conn = sqlite3.connect(self.financial_db_path)
                stock_financial_data_df.to_sql(
                    table_name, conn, if_exists="replace", index=False
                )
                logger.debug(f"Data uploaded to {table_name} table in {self.financial_db_path}")
            except Exception as e:
                logger.error(f"Error uploading data to SQLite: {e}")
            finally:
                conn.close()

    def read_stock_data_from_db(self, db_path: str) -> Dict:
        """
        Reads data from the SQLite database and stores it in a dictionary.

        Args:
            db_path (str): The path to the SQLite database.

        Returns:
            dict: A dictionary containing stock data.
        """
        try:
            stock_data_dict = {}
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            for table in tables:
                stock_symbol = table[0]
                daily_data = pd.read_sql_query(
                    f"""
                    SELECT Date, DailyOpen AS Open, DailyHigh AS High, DailyLow AS Low,
                           DailyClose AS Close, DailyVolume AS Volume
                    FROM '{stock_symbol}'
                    """, 
                    conn
                )

                weekly_data = pd.read_sql_query(
                    f"""
                    SELECT Date, WeeklyOpen AS Open, WeeklyHigh AS High, WeeklyLow AS Low,
                           WeeklyClose AS Close, WeeklyVolume AS Volume
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

            conn.close()
            return stock_data_dict

        except Exception as e:
            logger.error(f"Error reading stock data from SQLite DB: {e}")
            return {}
