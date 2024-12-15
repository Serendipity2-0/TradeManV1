"""
Initialize data for MidTerm strategy by:
1. Fetching and storing OHLCV data
2. Fetching and storing financial data
3. Calculating strategy signals
4. Updating TodayStocks database
"""

import os
import sys
from dotenv import load_dotenv
import pandas as pd

# Set up directory and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import (
    get_stock_data,
    get_financial_data,
    update_todaystocks_db,
)
from Executor.NSEStrategies.Equity.MidTerm.MidTermUtils import get_midterm_stocks_df
from Executor.NSEStrategies.Equity.MidTerm.MidTermConfig import (
    EQUITY_STOCK_DATA_DB_PATH,
    FINANCIAL_DB_PATH,
)

logger = LoggerSetup()

# Test stocks
TEST_STOCKS = ['63MOONS', 'A2ZINFRA', 'AAATECH']

def store_test_data():
    """
    Store a small set of test data for initial testing.
    Uses specific test stocks for testing.
    """
    try:
        logger.info(f"Using test stocks: {TEST_STOCKS}")

        # Store OHLCV data
        logger.info("Storing OHLCV data...")
        stock_data = {}
        import sqlite3
        conn = sqlite3.connect(EQUITY_STOCK_DATA_DB_PATH)
        cursor = conn.cursor()

        for i, stock in enumerate(TEST_STOCKS, 1):
            logger.info(f"Processing stock {i}/{len(TEST_STOCKS)}: {stock}")
            try:
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

            except Exception as e:
                logger.error(f"Error processing stock {stock}: {e}")
                continue

        conn.close()

        # Store financial data
        logger.info("Storing financial data...")
        stock_financial_data_df = get_financial_data(TEST_STOCKS)
        if not stock_financial_data_df.empty:
            conn = sqlite3.connect(FINANCIAL_DB_PATH)
            stock_financial_data_df.to_sql("financials", conn, if_exists="replace", index=False)
            conn.close()
            logger.info("Financial data stored successfully")

        logger.info("Test data stored successfully")
        return True

    except Exception as e:
        logger.error(f"Error storing test data: {e}")
        return False


def main():
    """
    Main function to initialize data for MidTerm strategy.
    """
    try:
        # Step 1: Store test data
        logger.info("Storing test data...")
        if not store_test_data():
            logger.error("Failed to store test data")
            return

        # Step 2: Calculate strategy signals
        logger.info("Calculating strategy signals...")
        tfmomentum_stocks_df, tfema_stocks_df = get_midterm_stocks_df()

        # Step 3: Update TodayStocks database
        logger.info("Updating TodayStocks database...")
        update_todaystocks_db(
            momentum_stocks_df=None,
            mean_reversion_stocks_df=None,
            ema_bb_confluence_stocks_df=None,
            ratio_stocks_df=None,
            combo_stocks_df=None,
            tfmomentum_stocks_df=tfmomentum_stocks_df,
            tfema_stocks_df=tfema_stocks_df,
        )

        logger.info("Data initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing data: {e}")
        raise


if __name__ == "__main__":
    main()
