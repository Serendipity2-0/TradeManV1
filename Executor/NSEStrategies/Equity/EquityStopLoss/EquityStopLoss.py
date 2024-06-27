import os
import sys
from dotenv import load_dotenv
import datetime

# Load holdings data
DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

import Executor.ExecutorUtils.ExeUtils as ExeUtils
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_users_for_strategies_from_firebase as fetch_active_users,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    fetch_sql_table_from_db as fetch_table_from_db,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import get_single_ltp

from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument
from Executor.NSEStrategies.NSEStrategiesUtil import (
    StrategyBase,
    assign_trade_id,
    place_order_single_user,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


class PyStocks(StrategyBase):
    def get_general_params(self):
        """
        The function `get_general_params` returns the `GeneralParams` attribute of the object.
        :return: The method `get_general_params` is returning the attribute `GeneralParams` of the object
        `self`.
        """
        return self.GeneralParams

    def get_entry_params(self):
        """
        The `get_entry_params` function returns the `EntryParams` attribute of the object.
        :return: The `EntryParams` attribute of the `self` object is being returned.
        """
        return self.EntryParams

    def get_exit_params(self):
        """
        The `get_exit_params` function returns the `ExitParams` attribute of the object.
        :return: The `ExitParams` attribute of the `self` object is being returned.
        """
        return self.ExitParams

    def get_raw_field(self, field_name: str):
        """
        The function `get_raw_field` returns the raw value of a specified field.

        :param field_name: The `field_name` parameter in the `get_raw_field` method is a string that
        represents the name of the field you want to retrieve from the object
        :type field_name: str
        :return: The `get_raw_field` method is being called on the superclass using `super()`, passing in
        the `field_name` argument. The method is returning the raw value of the field specified by the
        `field_name` parameter.
        """
        return super().get_raw_field(field_name)


pystocks_obj = PyStocks.load_from_db("PyStocks")

stoploss_multiplier = pystocks_obj.EntryParams.SLMultiplier
strategy_name = pystocks_obj.StrategyName
transaction_type = pystocks_obj.get_raw_field("GeneralParams").get("SlTransactionType")
product_type = pystocks_obj.GeneralParams.ProductType
order_type = pystocks_obj.get_raw_field("GeneralParams").get("SlOrderType")
trade_mode = os.getenv("TRADE_MODE")

users = fetch_active_users("PyStocks")

to_date = datetime.date.today()
# Calculate previous day's date
from_date = to_date - datetime.timedelta(days=1)


def main():
    """
    Main function to execute the stop-loss strategy for the PyStocks strategy.

    This function performs the following steps:
    1. Checks if today is a holiday and skips execution if it is.
    2. Iterates through all active users and their holdings for the PyStocks strategy.
    3. Calculates the stop-loss price for each holding based on the current market price and the entry price.
    4. Places stop-loss orders if the calculated stop-loss price needs to be updated.
    """
    now = datetime.datetime.now()
    if now.date() in ExeUtils.holidays:
        logger.info("Skipping execution as today is a holiday.")
        return
    for user in users:
        holdings = fetch_table_from_db(user["Tr_No"], "Holdings")
        py_holdings = holdings[
            holdings["trade_id"].str.startswith("PS")
        ]  # TODO Remove hardcoded PS
        for index, row in py_holdings.iterrows():
            symbol = row["trading_symbol"]
            exchange_token = Instrument().get_exchange_token_by_name(symbol, "NSE")
            ltp = get_single_ltp(exchange_token=exchange_token, segment="NSE")
            buy_price = float(row["entry_price"])
            per_change = (ltp - buy_price) / buy_price * 100
            sl = buy_price - (buy_price * stoploss_multiplier / 100)

            trade_id = row["trade_id"]
            trade_id = trade_id.split("_")
            trade_id = trade_id[0]

            if (
                per_change // stoploss_multiplier > 0
                and per_change // stoploss_multiplier != 1
            ):
                for interation in range(int(per_change // stoploss_multiplier)):
                    sl = sl + (buy_price * stoploss_multiplier / 100)

                    sl = round(sl, 1)
            logger.debug("LTP", ltp, "Buy Price", buy_price, "SL", sl)
            order_details = [
                {
                    "strategy": strategy_name,
                    "signal": "Long",
                    "base_symbol": symbol,
                    "exchange_token": exchange_token,
                    "transaction_type": transaction_type,
                    "order_type": order_type,
                    "product_type": product_type,
                    "order_mode": "SL",
                    "trade_id": trade_id,
                    "trade_mode": trade_mode,
                    "limit_prc": sl,
                    "trigger_prc": sl + 0.3,
                }
            ]
            order_to_place = assign_trade_id(order_details)
            logger.debug(f"Orders to place: {order_to_place}")
            place_order_single_user([user], order_to_place)

