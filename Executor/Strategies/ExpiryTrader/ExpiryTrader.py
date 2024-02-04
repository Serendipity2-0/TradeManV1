import os
import sys
import datetime as dt
from time import sleep
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from loguru import logger

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


from Executor.Strategies.StrategiesUtil import StrategyBase
from Executor.Strategies.StrategiesUtil import (
    update_qty_user_firebase,
    assign_trade_id,
    update_signal_firebase,
    place_order_strategy_users,
    calculate_stoploss,
    calculate_transaction_type_sl,
    calculate_trigger_price,
)

import Executor.ExecutorUtils.ExeUtils as ExeUtils
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)


class ExpiryTrader(StrategyBase):
    def get_general_params(self):
        return self.GeneralParams

    def get_entry_params(self):
        return self.EntryParams

    def get_exit_params(self):
        return self.ExitParams

    def get_raw_field(self, field_name: str):
        return super().get_raw_field(field_name)


# Testing the class with ExpiryTrader data
expiry_trader_obj = ExpiryTrader.load_from_db("ExpiryTrader")
instrument_obj = InstrumentCenterUtils.Instrument()

hedge_transaction_type = expiry_trader_obj.get_general_params().HedgeTransactionType
main_transaction_type = expiry_trader_obj.get_general_params().MainTransactionType

# Extract strategy parameters
base_symbol, today_expiry_token = expiry_trader_obj.determine_expiry_index()
strategy_name = expiry_trader_obj.StrategyName
next_trade_prefix = expiry_trader_obj.NextTradeId
prediction = expiry_trader_obj.MarketInfoParams.TradeView
order_type = expiry_trader_obj.get_general_params().OrderType
product_type = expiry_trader_obj.get_general_params().ProductType

strike_prc_multiplier = expiry_trader_obj.get_strike_multiplier(base_symbol)
hedge_multiplier = expiry_trader_obj.get_hedge_multiplier(base_symbol)
stoploss_multiplier = expiry_trader_obj.get_stoploss_multiplier(base_symbol)
desired_start_time_str = expiry_trader_obj.get_entry_params().EntryTime

start_hour, start_minute, start_second = map(int, desired_start_time_str.split(":"))

main_strikeprc = expiry_trader_obj.calculate_current_atm_strike_prc(
    base_symbol, today_expiry_token, prediction, strike_prc_multiplier
)
hedge_strikeprc = expiry_trader_obj.get_hedge_strikeprc(
    base_symbol, today_expiry_token, prediction, hedge_multiplier
)
main_option_type = expiry_trader_obj.get_option_type(prediction, "OS")
hedge_option_type = expiry_trader_obj.get_hedge_option_type(prediction)

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

update_qty_user_firebase(strategy_name, ltp, lot_size)

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
    },
]

orders_to_place = assign_trade_id(orders_to_place)
logger.info("orders_to_place", orders_to_place)


def message_for_orders(trade_type, prediction, main_trade_symbol, hedge_trade_symbol):
    message = (
        f"{trade_type} Trade for {strategy_name}\n"
        f"Direction : {prediction}\n"
        f"Main Trade : {main_trade_symbol}\n"
        f"Hedge Trade {hedge_trade_symbol} \n"
    )
    logger.info(message)
    discord_bot(message, strategy_name)


def main():
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

        for order in orders_to_place:
            if order.get("order_mode") == "MO":
                main_trade_id = order.get("trade_id")

        signals_to_log = {
            "TradeId": main_trade_id,
            "Signal": "Short",
            "EntryTime": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "StrategyInfo": {
                "Direction": prediction,
            },
            "Status": "Open",
        }

        update_signal_firebase(strategy_name, signals_to_log, next_trade_prefix)

        message_for_orders("Live", prediction, main_trade_symbol, hedge_trade_symbol)

        place_order_strategy_users(strategy_name, orders_to_place)


if __name__ == "__main__":
    main()
