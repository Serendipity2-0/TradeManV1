import pandas as pd
import yfinance as yf
import os
from dotenv import load_dotenv
import sys
import sqlite3

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.Strategies.Equity.LongTerm.LonTermUtils import (
    perform_ratio_strategy,
    perform_combo_strategy,
)
from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import (
    get_financial_data,
    get_stock_codes,
)

logger = LoggerSetup()


def main():
    stock_codes = get_stock_codes()
    stock_codes = stock_codes[:20]
    stock_financial_data_df = get_financial_data(stock_codes)
    if not stock_financial_data_df.empty:
        # SQLite database path
        financial_db_path = os.getenv("financial_db_path")
        table_name = "financials"
        try:
            conn = sqlite3.connect(financial_db_path)
            stock_financial_data_df.to_sql(
                table_name, conn, if_exists="replace", index=False
            )
            logger.debug(f"Data uploaded to {table_name} table in {financial_db_path}")
        except Exception as e:
            logger.error(f"Error uploading data to SQLite: {e}")
        finally:
            conn.close()

        combo_stocks_df = perform_combo_strategy(db_path=financial_db_path)
        ratio_stocks_df = perform_ratio_strategy(db_path=financial_db_path)
        return combo_stocks_df, ratio_stocks_df


if __name__ == "__main__":
    main()
