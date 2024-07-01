import pandas as pd
import os
import sys
import sqlite3
import datetime as dt
from time import sleep
from dotenv import load_dotenv

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import update_todaystocks_db, store_stock_data_sqldb
from Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils import (
    get_shortterm_stocks_df
)
from Executor.NSEStrategies.Equity.LongTerm.LongTermUtils import (
    get_longterm_stocks_df
)
import Executor.ExecutorUtils.ExeUtils as ExeUtils
from Executor.NSEStrategies.NSEStrategiesUtil import StrategyBase, update_signal_firebase
import Executor.NSEStrategies.Equity.ShortTerm.ShortTerm as ShortTerm
import Executor.NSEStrategies.Equity.LongTerm.LongTerm as LongTerm
import Executor.NSEStrategies.Equity.EquityStopLoss.EquityStopLoss as StopLoss

logger = LoggerSetup()
stock_pick_db_path = os.getenv("today_stock_data_db_path")


class PyStocks(StrategyBase):

    def get_general_params(self):
        return self.GeneralParams

    def get_entry_params(self):
        return self.EntryParams

    def get_exit_params(self):
        return self.ExitParams

    def get_raw_field(self, field_name: str):
        return super().get_raw_field(field_name)

pystocks_obj = PyStocks.load_from_db("PyStocks")
strategy_name = pystocks_obj.StrategyName
order_type = pystocks_obj.GeneralParams.OrderType
product_type = pystocks_obj.GeneralParams.ProductType
strategy_type = pystocks_obj.GeneralParams.StrategyType

def signals_to_fb(order_to_place, next_trade_prefix):
    """
    Log signals to Firebase.

    Args:
        order_to_place (list): List of orders to place.
        next_trade_prefix (str): Prefix for the next trade ID.

    Returns:
        dict: Logged signals.
    """
    for order in order_to_place:
        signals_to_log = {
            "TradeId": order["trade_id"],
            "Signal": "Long",
            "EntryTime": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "StrategyInfo": {
                "Direction": "Bullish",
            },
            "Status": "Open",
        }
        update_signal_firebase(strategy_name, signals_to_log, next_trade_prefix)
    return signals_to_log

def main():
    """
    Main function for the strategy.

    Returns:
        None
    """ 
    
    StopLoss.main()

    momentum_stocks_df, mean_reversion_stocks_df, ema_bb_confluence_stocks_df = get_shortterm_stocks_df()
    combo_stocks_df, ratio_stocks_df = get_longterm_stocks_df()
    update_todaystocks_db(momentum_stocks_df,mean_reversion_stocks_df,ema_bb_confluence_stocks_df,ratio_stocks_df,combo_stocks_df)

    desired_start_time_str = pystocks_obj.get_entry_params().EntryTime
    start_hour, start_minute, _ = map(int, desired_start_time_str.split(":"))
    now = dt.datetime.now()

    
    if now.date() in ExeUtils.holidays:
        logger.info("Skipping execution as today is a holiday.")
        return

    if now.time() < dt.time(9, 0):
        logger.info("Time is before 9:00 AM, Waiting to execute.")
    else:
        wait_time = dt.datetime(
            now.year, now.month, now.day, start_hour, start_minute
        ) - now

        if wait_time.total_seconds() > 0:
            logger.info(f"Waiting for {wait_time} before starting the bot")
            sleep(wait_time.total_seconds())

    
    ShortTerm.main()
    LongTerm.main()

if __name__ == "__main__":
    main()

