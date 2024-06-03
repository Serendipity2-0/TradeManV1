import pandas as pd
import os, sys
from dotenv import load_dotenv
import datetime as dt
from time import sleep

# Fetch stock symbols

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

import Executor.Strategies.PyStocks.PyStocksUtils as pystocksutils
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_users_for_strategies_from_firebase,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    fetch_sql_table_from_db as fetch_table_from_db,
)
from Executor.Strategies.StrategiesUtil import StrategyBase, fetch_strategy_users
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
    Instrument as instrument_obj,
    get_single_ltp,
)
from Executor.Strategies.StrategiesUtil import (
    update_qty_user_firebase,
    assign_trade_id,
    update_signal_firebase,
    place_order_single_user,
    fetch_qty_amplifier,
    fetch_strategy_amplifier,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
import Executor.ExecutorUtils.ExeUtils as ExeUtils

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
        The function `get_exit_params` returns the `ExitParams` attribute of the object.
        :return: The `ExitParams` attribute of the `self` object is being returned.
        """
        return self.ExitParams

    def get_raw_field(self, field_name: str):
        """
        The function `get_raw_field` returns the raw value of a specified field.

        :param field_name: The `get_raw_field` method takes a `field_name` parameter, which is expected to
        be a string representing the name of the field you want to retrieve
        :type field_name: str
        :return: The `get_raw_field` method is being called on the superclass using `super()`, passing in
        the `field_name` argument. The return value of this method call is being returned by the
        `get_raw_field` method in the current class.
        """
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


def create_top_stocks_csv():
    """
    Create a CSV file with the top stock picks.

    This function fetches the top stock picks using the `get_stockpicks_csv` function
    from the `pystocksutils` module and logs any errors encountered during the process.
    """
    try:
        pystocksutils.get_stockpicks_csv()
    except Exception as e:
        logger.error(f"Error in creating csv: {e}")


def main():
    """
    Main function to execute the PyStocks strategy.

    This function:
    1. Checks if today is a holiday.
    2. Waits until the desired start time before executing.
    3. Fetches the top stock symbols from a CSV file.
    4. Fetches the list of users to apply the strategy for.
    5. Places buy orders for the top stock symbols for each user if they have less than 5 holdings.
    """
    desired_start_time_str = pystocks_obj.get_entry_params().EntryTime
    start_hour, start_minute, start_second = map(int, desired_start_time_str.split(":"))
    now = dt.datetime.now()

    if now.date() in ExeUtils.holidays:
        logger.info("Skipping execution as today is a holiday.")
        return
    if now.time() < dt.time(9, 0):
        logger.info("Time is before 9:00 AM, Waiting to execute.")
    else:
        wait_time = (
            dt.datetime(now.year, now.month, now.day, start_hour, start_minute) - now
        )

        if wait_time.total_seconds() > 0:
            logger.info(f"Waiting for {wait_time} before starting the bot")
            sleep(wait_time.total_seconds())

        # Initialize a dictionary to hold trade IDs for each symbol
        trade_id_mapping = {}

        df = pd.read_csv(os.getenv("best5_shortterm_path"))
        symbol_list = df["Symbol"].tolist()
        logger.debug(f"Symbol list: {symbol_list}")

        users = fetch_strategy_users("PyStocks")
        for user in users:
            holdings = fetch_table_from_db(user["Tr_No"], "Holdings")
            py_holdings = holdings[holdings["trade_id"].str.startswith("PS")]
            current_holdings_count = len(py_holdings)
            logger.debug(
                f"Current holdings for user {user['Tr_No']}: {current_holdings_count}"
            )

            if current_holdings_count < 5:
                needed_orders = 5 - current_holdings_count
                for index, symbol in enumerate(symbol_list):
                    if needed_orders == 0:
                        break  # Stop processing if no more orders are needed

                    new_base = pystocks_obj.reload_strategy(pystocks_obj.StrategyName)
                    if symbol not in trade_id_mapping:
                        trade_id_mapping[symbol] = new_base.NextTradeId

                    trade_id = trade_id_mapping[symbol]

                    exchange_token = instrument_obj().get_exchange_token_by_name(
                        symbol, "NSE"
                    )
                    ltp = get_single_ltp(exchange_token=exchange_token, segment="NSE")
                    ltp = round(ltp * 20) / 20
                    order_details = [
                        {
                            "strategy": strategy_name,
                            "signal": "Long",
                            "base_symbol": symbol,
                            "exchange_token": exchange_token,
                            "transaction_type": "BUY",
                            "order_type": order_type,
                            "product_type": product_type,
                            "order_mode": "MainEntry",
                            "trade_id": trade_id,
                            "limit_prc": ltp,
                        }
                    ]
                    order_to_place = assign_trade_id(order_details)
                    qty_amplifier = fetch_qty_amplifier(strategy_name, strategy_type)
                    strategy_amplifier = fetch_strategy_amplifier(strategy_name)
                    update_qty_user_firebase(
                        strategy_name, ltp, 1, qty_amplifier, strategy_amplifier
                    )
                    signals_to_fb(order_to_place, trade_id)
                    order_status = place_order_single_user([user], order_to_place)
                    logger.debug(f"Orders placed for {symbol}: {order_to_place}")

                    # Should come up with a better way to check for failed orders
                    if user["Tr_No"] == "Tr00" and any(
                        order["order_status"] == "FAIL" for order in order_status
                    ):
                        # Reassign the trade ID to the next symbol if there is one
                        if index + 1 < len(symbol_list):
                            next_symbol = symbol_list[index + 1]
                            trade_id_mapping[next_symbol] = trade_id
                            logger.debug(
                                f"Trade ID {trade_id} reassigned from {symbol} to {next_symbol}"
                            )

                    needed_orders -= 1

                logger.debug(
                    f"Updated holdings count for user {user['Tr_No']} should be 5"
                )


if __name__ == "__main__":
    create_top_stocks_csv()
    main()
