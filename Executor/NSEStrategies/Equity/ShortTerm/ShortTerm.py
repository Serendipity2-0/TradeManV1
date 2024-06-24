import pandas as pd
import yfinance as yf
import os
from dotenv import load_dotenv
import sys

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.Strategies.Equity.ShortTerm.ShortTermUtils import (
    perform_EmaBB_Confluence_strategy,
    perform_mean_reversion_strategy,
    perform_momentum_strategy,
)
from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import (
    read_stock_data_from_db,
    update_todaystocks_db,
    merge_dataframes,
)

logger = LoggerSetup()


def main():
    """
    Retrieves short term momentum, mean reversion and EMA-BB confluence stocks.
    Combines and sorts stocks by ATH to LTP ratio.
    Exports sorted list to CSV and returns top picks.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        list: A sorted list of short term stock picks.
    """
    # Example usage
    db_path = os.getenv("equity_stock_data_db_path")
    stock_data_dict = read_stock_data_from_db(db_path)
    momentum_stocks_df = perform_momentum_strategy(stock_data_dict)
    mean_reversion_stocks_df = perform_mean_reversion_strategy(stock_data_dict)
    ema_bb_confluence_stocks_df = perform_EmaBB_Confluence_strategy(stock_data_dict)
    return momentum_stocks_df, mean_reversion_stocks_df, ema_bb_confluence_stocks_df


if "__main__" == __name__:
    main()
