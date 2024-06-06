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
from Executor.Strategies.Equity.ShortTerm.EmaBBConfluenceStrategy import perform_EmaBB_Confluence_strategy
from Executor.Strategies.Equity.ShortTerm.MomentumStrategy import perform_momentum_strategy
from Executor.Strategies.Equity.ShortTerm.MeanReversionStrategy import perform_mean_reversion_strategy
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
    global momentum_stocks
    global mean_reversion_stocks
    global ema_bb_confluence_stocks
    momentum_stocks = perform_momentum_strategy(stock_data_dict)
    mean_reversion_stocks = perform_mean_reversion_strategy(stock_data_dict)
    ema_bb_confluence_stocks = perform_EmaBB_Confluence_strategy(stock_data_dict)

    