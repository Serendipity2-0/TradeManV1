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
from Executor.NSEStrategies.NSEStrategiesUtil import update_signal_firebase
import Executor.NSEStrategies.Equity.ShortTerm.ShortTerm as ShortTerm
import Executor.NSEStrategies.Equity.MidTerm.MidTerm as MidTerm
import Executor.NSEStrategies.Equity.LongTerm.LongTerm as LongTerm


logger = LoggerSetup()
stock_pick_db_path = os.getenv("TODAY_STOCK_DATA_DB_PATH")


def signals_to_fb(strategy_name, order_to_place, next_trade_prefix):
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
            "Symbol": order["base_symbol"],
            "EntryTime": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "StrategyInfo": {
                "Direction": "Bullish",
            },
            "Status": "Open",
        }
        if order["setup"]:
            signals_to_log["Setup"] = order["setup"]
        update_signal_firebase(strategy_name, signals_to_log, next_trade_prefix)
    return signals_to_log


def main():
    """
    Main function for the strategy.

    Returns:
        None
    """

    ShortTerm.main()
    MidTerm.main()
    LongTerm.main()


if __name__ == "__main__":
    main()
