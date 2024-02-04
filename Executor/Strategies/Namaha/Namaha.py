import os
import sys
import datetime as dt
from time import sleep
from dotenv import load_dotenv
import random

from pprint import pprint

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from Executor.Strategies.StrategiesUtil import StrategyBase
from Executor.Strategies.StrategiesUtil import (
    update_qty_user_firebase,
    assign_trade_id,
    update_signal_firebase,
    place_order_strategy_users,
)

import Executor.ExecutorUtils.ExeUtils as ExeUtils
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)


class Namaha(StrategyBase):
    def get_general_params(self):
        return self.GeneralParams

    def get_entry_params(self):
        return self.EntryParams

    def get_exit_params(self):
        return self.ExitParams

    def get_raw_field(self, field_name: str):
        return super().get_raw_field(field_name)


strategy_obj = Namaha.load_from_db("Namaha")
instrument_obj = InstrumentCenterUtils.Instrument()

start_hour, start_minute, start_second = map(
    int, strategy_obj.get_entry_params().EntryTime.split(":")
)


def message_for_orders(
    trade_type, prediction, main_trade_symbol, hedge_trade_symbol, strategy_name
):
    # TODO: add noftication for the orders
    message = (
        f"{trade_type} Trade for {strategy_name}\n"
        f"Direction : {prediction}\n"
        f"Main Trade : {main_trade_symbol}\n"
        f"Hedge Trade {hedge_trade_symbol} \n"
    )
    print(message)
    discord_bot(message, strategy_name)


next_trade_prefix = strategy_obj.NextTradeId
strategy_name = strategy_obj.StrategyName


def namaha():
    global next_trade_prefix, strategy_name, prediction
    hedge_transaction_type = strategy_obj.GeneralParams.HedgeTransactionType
    main_transaction_type = strategy_obj.GeneralParams.MainTransactionType

    # Extract strategy parameters
    base_symbol, today_expiry_token = strategy_obj.determine_expiry_index()
    prediction = strategy_obj.get_general_params().TradeView
    order_type = strategy_obj.get_general_params().OrderType
    product_type = strategy_obj.get_general_params().ProductType
    strategy_type = strategy_obj.get_general_params().StrategyType

    strike_prc_multiplier = strategy_obj.get_strike_multiplier(base_symbol)
    hedge_multiplier = strategy_obj.get_hedge_multiplier(base_symbol)
    stoploss_mutiplier = strategy_obj.get_stoploss_multiplier(base_symbol)

    main_strikeprc = strategy_obj.calculate_current_atm_strike_prc(
        base_symbol, today_expiry_token, prediction, strike_prc_multiplier
    )
    hedge_strikeprc = strategy_obj.get_hedge_strikeprc(
        base_symbol, today_expiry_token, prediction, hedge_multiplier
    )
    main_option_type = strategy_obj.get_option_type(prediction, strategy_type)
    hedge_option_type = strategy_obj.get_hedge_option_type(prediction)

    today_expiry = instrument_obj.get_expiry_by_criteria(
        base_symbol, main_strikeprc, main_option_type, "current_week"
    )
    hedge_exchange_token = instrument_obj.get_exchange_token_by_criteria(
        base_symbol, hedge_strikeprc, hedge_option_type, today_expiry
    )
    main_exchange_token = instrument_obj.get_exchange_token_by_criteria(
        base_symbol, main_strikeprc, main_option_type, today_expiry
    )

    main_trade_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
        main_exchange_token
    )
    hedge_trade_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
        hedge_exchange_token
    )

    ltp = InstrumentCenterUtils.get_single_ltp(exchange_token=main_exchange_token)
    lot_size = instrument_obj.get_lot_size_by_exchange_token(main_exchange_token)

    update_qty_user_firebase(strategy_name, ltp, lot_size)
    message_for_orders(
        "Live", prediction, main_trade_symbol, hedge_trade_symbol, strategy_name
    )

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
            "transaction_type": hedge_transaction_type,
            "order_type": "Stoploss",
            "product_type": product_type,
            "stoploss_mutiplier": stoploss_mutiplier,
            "order_mode": "SL",
            "trade_id": next_trade_prefix,
        },
    ]

    orders_to_place = assign_trade_id(orders_to_place)
    return orders_to_place


def main():
    global strategy_name
    desired_start_time_str = strategy_obj.get_entry_params().EntryTime
    start_hour, start_minute, start_second = map(int, desired_start_time_str.split(":"))
    now = dt.datetime.now()

    if now.date() in ExeUtils.holidays:
        print("Skipping execution as today is a holiday.")
        return

    if now.time() < dt.time(9, 0):
        print("Time is before 9:00 AM, Waiting to execute.")
    else:
        wait_time = (
            dt.datetime(now.year, now.month, now.day, start_hour, start_minute) - now
        )

        if wait_time.total_seconds() > 0:
            print(f"Waiting for {wait_time} before starting the bot")
            sleep(wait_time.total_seconds())

        signals_to_log = {
            "TradeId": next_trade_prefix,
            "Signal": "Short",
            "EntryTime": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "StrategyInfo": {
                "Direction": strategy_obj.get_general_params().TradeView,
            },
            "Status": "Open",
        }

        update_signal_firebase(strategy_name, signals_to_log)
        orders_to_place = namaha()
        print(orders_to_place)
        # place_order_strategy_users(strategy_name,orders_to_place)


if __name__ == "__main__":
    main()
