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

# Set up directory and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import (
    store_ohlcv_stock_data_sqldb,
    store_financial_data_sqldb,
    update_todaystocks_db,
)
from Executor.NSEStrategies.Equity.MidTerm.MidTermUtils import get_midterm_stocks_df

logger = LoggerSetup()

def main():
    """
    Main function to initialize data for MidTerm strategy.
    """
    try:
        # Step 1: Store OHLCV data
        logger.info("Storing OHLCV data...")
        store_ohlcv_stock_data_sqldb()

        # Step 2: Store financial data
        logger.info("Storing financial data...")
        store_financial_data_sqldb()

        # Step 3: Calculate strategy signals
        logger.info("Calculating strategy signals...")
        tfmomentum_stocks_df, tfema_stocks_df = get_midterm_stocks_df()

        # Step 4: Update TodayStocks database
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
