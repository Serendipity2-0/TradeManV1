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
from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import (
    merge_dataframes,
    update_todaystocks_db,
)
import Executor.Strategies.Equity.ShortTerm.ShortTerm as ShortTerm
import Executor.Strategies.Equity.LongTerm.LongTerm as LongTerm


logger = LoggerSetup()


def main():
    (
        momentum_stocks_df,
        mean_reversion_stocks_df,
        ema_bb_confluence_stocks_df,
    ) = ShortTerm.main()
    combo_stocks_df, ratio_stocks_df = LongTerm.main()
    merged_df = merge_dataframes(
        momentum_df=momentum_stocks_df,
        mean_reversion_df=mean_reversion_stocks_df,
        ema_bb_df=ema_bb_confluence_stocks_df,
        ratio_df=ratio_stocks_df,
        combo_df=combo_stocks_df,
    )
    update_todaystocks_db(combined_df=merged_df)


if __name__ == "__main__":
    main()
