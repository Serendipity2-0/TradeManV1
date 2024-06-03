import os
import sys
import datetime as dt
from time import sleep
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

TRADE_MODE = os.getenv("TRADE_MODE")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

from Executor.Strategies.StrategiesUtil import StrategyBase
from Executor.Strategies.StrategiesUtil import (
    update_qty_user_firebase,
    assign_trade_id,
    update_signal_firebase,
    place_order_strategy_users,
    calculate_stoploss,
    calculate_transaction_type_sl,
    calculate_trigger_price,
    fetch_qty_amplifier,
    fetch_strategy_amplifier,
)

import Executor.ExecutorUtils.ExeUtils as ExeUtils
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)


class Namaha(StrategyBase):
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
        The `get_raw_field` function returns the raw value of a specified field.

        :param field_name: The `get_raw_field` method takes a parameter `field_name` of type `str`, which
        represents the name of the field you want to retrieve from the object
        :type field_name: str
        :return: The `get_raw_field` method is returning the raw value of the field specified by the
        `field_name` parameter.
        """
        return super().get_raw_field(field_name)


namaha_obj = Namaha.load_from_db("Namaha")
instrument_obj = InstrumentCenterUtils.Instrument()


def message_for_orders(trade_type, prediction, main_trade_symbol, hedge_trade_symbol):
    """
    Sends a message with the trade details to Discord.

    Args:
        trade_type (str): The type of the trade (e.g., 'Live').
        prediction (str): The market prediction.
        main_trade_symbol (str): The main trade symbol.
        hedge_trade_symbol (str): The hedge trade symbol.
    """
    message = (
        f"{trade_type} Trade for {strategy_name}\n"
        f"Direction : {prediction}\n"
        f"Main Trade : {main_trade_symbol}\n"
        f"Hedge Trade {hedge_trade_symbol} \n"
    )
    logger.info(message)
    discord_bot(message, strategy_name)


hedge_transaction_type = namaha_obj.get_general_params().HedgeTransactionType
main_transaction_type = namaha_obj.get_general_params().MainTransactionType

# Extract strategy parameters
base_symbol, today_expiry_token = namaha_obj.determine_expiry_index()
strategy_name = namaha_obj.StrategyName
next_trade_prefix = namaha_obj.NextTradeId
prediction = namaha_obj.MarketInfoParams.TradeView
order_type = namaha_obj.get_general_params().OrderType
product_type = namaha_obj.get_general_params().ProductType

strike_prc_multiplier = namaha_obj.EntryParams.StrikeMultiplier
hedge_multiplier = namaha_obj.EntryParams.HedgeMultiplier
stoploss_multiplier = namaha_obj.EntryParams.SLMultiplier
desired_start_time_str = namaha_obj.get_entry_params().EntryTime
strategy_type = namaha_obj.GeneralParams.StrategyType

logger.debug(
    f"Values from Firebase for {strategy_name}: {base_symbol}, {today_expiry_token}, {prediction}, {order_type}, {product_type}, {strike_prc_multiplier}, {hedge_multiplier}, {stoploss_multiplier}, {desired_start_time_str}, {strategy_type}"
)

start_hour, start_minute, start_second = map(int, desired_start_time_str.split(":"))

main_strikeprc = namaha_obj.calculate_current_atm_strike_prc(
    base_symbol, today_expiry_token, prediction, strike_prc_multiplier, strategy_type
)
hedge_strikeprc = namaha_obj.get_hedge_strikeprc(
    base_symbol, today_expiry_token, prediction, hedge_multiplier
)
main_option_type = namaha_obj.get_option_type(prediction, "OS")
hedge_option_type = namaha_obj.get_hedge_option_type(prediction)

today_expiry = instrument_obj.get_expiry_by_criteria(
    base_symbol, main_strikeprc, main_option_type, "current_week"
)
hedge_exchange_token = instrument_obj.get_exchange_token_by_criteria(
    base_symbol, hedge_strikeprc, hedge_option_type, today_expiry
)
main_exchange_token = instrument_obj.get_exchange_token_by_criteria(
    base_symbol, main_strikeprc, main_option_type, today_expiry
)

ltp = InstrumentCenterUtils.get_single_ltp(exchange_token=main_exchange_token)
lot_size = instrument_obj.get_lot_size_by_exchange_token(main_exchange_token)

qty_amplifier = fetch_qty_amplifier(strategy_name, strategy_type)
strategy_amplifier = fetch_strategy_amplifier(strategy_name)
update_qty_user_firebase(
    strategy_name, ltp, lot_size, qty_amplifier, strategy_amplifier
)

main_trade_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
    main_exchange_token
)
hedge_trade_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
    hedge_exchange_token
)

stoploss_transaction_type = calculate_transaction_type_sl(main_transaction_type)
limit_prc = calculate_stoploss(
    ltp, main_transaction_type, stoploss_multiplier=stoploss_multiplier
)
logger.debug(
    f"stoploss_transaction_type: {stoploss_transaction_type}, limit_prc: {limit_prc}"
)
trigger_prc = calculate_trigger_price(stoploss_transaction_type, limit_prc)

orders_to_place = [
    {
        "strategy": strategy_name,
        "signal": "Short",
        "base_symbol": base_symbol,
        "exchange_token": hedge_exchange_token,
        "transaction_type": hedge_transaction_type,
        "order_type": order_type,
        "product_type": product_type,
        "order_mode": "HedgeEntry",
        "trade_id": next_trade_prefix,
        "trade_mode": TRADE_MODE,
    },
    {
        "strategy": strategy_name,
        "signal": "Short",
        "base_symbol": base_symbol,
        "exchange_token": main_exchange_token,
        "transaction_type": main_transaction_type,
        "order_type": order_type,
        "product_type": product_type,
        "order_mode": "Main",
        "trade_id": next_trade_prefix,
        "trade_mode": TRADE_MODE,
    },
    {
        "strategy": strategy_name,
        "signal": "Short",
        "base_symbol": base_symbol,
        "exchange_token": main_exchange_token,
        "transaction_type": stoploss_transaction_type,
        "order_type": "Stoploss",
        "product_type": product_type,
        "limit_prc": limit_prc,
        "trigger_prc": trigger_prc,
        "order_mode": "SL",
        "trade_id": next_trade_prefix,
        "trade_mode": TRADE_MODE,
    },
]

orders_to_place = assign_trade_id(orders_to_place)
logger.debug(f"orders_to_place for {strategy_name}: {orders_to_place}")


def main():
    """
    Main function to execute the trading strategy.

    This function performs the following steps:
    1. Checks if today is a holiday and skips execution if it is.
    2. Waits until the desired start time if the current time is before 9:00 AM.
    3. Calculates the wait time before starting the bot and sleeps for that duration.
    4. Logs the trade details to Firebase.
    5. Sends the trade details to Discord.
    6. Places the orders for the strategy.
    """
    global strategy_name, prediction
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

        main_trade_id = None
        logger.info(f"orders_to_place{orders_to_place}")

        for order in orders_to_place:
            if order.get("order_mode") == "MO":
                main_trade_id = order.get("trade_id")
                main_trade_id_prefix = main_trade_id.split("_")[0]

        signals_to_log = {
            "TradeId": main_trade_id,
            "Signal": "Short",
            "EntryTime": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Orders": orders_to_place,
            "StrategyInfo": {
                "direction": prediction,
                "sl_multipler": stoploss_multiplier,
                "strike_multipler": strike_prc_multiplier,
                "hedge_multipler": hedge_multiplier,
                "trade_id": main_trade_id_prefix,
            },
            "Status": "Open",
        }

        update_signal_firebase(strategy_name, signals_to_log, next_trade_prefix)

        message_for_orders("Live", prediction, main_trade_symbol, hedge_trade_symbol)

        place_order_strategy_users(strategy_name, orders_to_place)


if __name__ == "__main__":
    main()
