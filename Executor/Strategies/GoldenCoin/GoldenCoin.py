import random, time
import os, sys
import datetime as dt
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
    calculate_transaction_type_sl,
)

import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)
from Executor.ExecutorUtils.ExeUtils import holidays

class GoldenCoin(StrategyBase):
    def get_general_params(self):
        return self.GeneralParams

    def get_entry_params(self):
        return self.EntryParams

    def get_exit_params(self):
        return self.ExitParams

    def get_raw_field(self, field_name: str):
        return super().get_raw_field(field_name)


goldencoin_strategy_obj = GoldenCoin.load_from_db("GoldenCoin")
instrument_obj = InstrumentCenterUtils.Instrument()
next_trade_prefix = goldencoin_strategy_obj.NextTradeId
desired_start_time_str = goldencoin_strategy_obj.get_entry_params().EntryTime
start_hour, start_minute, start_second = map(int, desired_start_time_str.split(":"))
window = goldencoin_strategy_obj.get_raw_field("EntryParams").get("Window")

def flip_coin():
    # Randomly choose between 'Heads' and 'Tails'
    result = random.choice(["Heads", "Tails"])
    return result


# Flipping the coin and printing the result

prediction = "Bullish" if flip_coin() == "Heads" else "Bearish"

def determine_strike_and_option():
    global prediction
    strike_price_multiplier = goldencoin_strategy_obj.EntryParams.StrikeMultiplier
    strategy_type = goldencoin_strategy_obj.GeneralParams.StrategyType
    base_symbol, _ = goldencoin_strategy_obj.determine_expiry_index()
    option_type = "CE" if prediction == "Bullish" else "PE"
    strike_prc = goldencoin_strategy_obj.calculate_current_atm_strike_prc(
        base_symbol=base_symbol,
        prediction=prediction,
        strike_prc_multiplier=strike_price_multiplier,
        strategy_type=strategy_type,
    )
    return base_symbol, strike_prc, option_type


def fetch_exchange_token(base_symbol, strike_prc, option_type):
    today_expiry = instrument_obj.get_expiry_by_criteria(
        base_symbol, strike_prc, option_type, "current_week"
    )
    exchange_token = instrument_obj.get_exchange_token_by_criteria(
        base_symbol, strike_prc, option_type, today_expiry
    )
    return exchange_token


def update_qty(base_symbol, strike_prc, option_type):
    exchange_token = fetch_exchange_token(base_symbol, strike_prc, option_type)
    token = instrument_obj.get_kite_token_by_exchange_token(exchange_token)
    ltp = InstrumentCenterUtils.get_single_ltp(token)
    lot_size = instrument_obj.get_lot_size_by_exchange_token(exchange_token)
    update_qty_user_firebase(goldencoin_strategy_obj.StrategyName, ltp, lot_size)


def create_order_details(exchange_token, base_symbol):
    stoploss_transaction_type = calculate_transaction_type_sl(
        goldencoin_strategy_obj.get_general_params().TransactionType
    )
    order_details = [
        {
            "strategy": goldencoin_strategy_obj.StrategyName,
            "signal": "Long",
            "base_symbol": base_symbol,
            "exchange_token": exchange_token,
            "transaction_type": goldencoin_strategy_obj.get_general_params().TransactionType,
            "order_type": goldencoin_strategy_obj.get_general_params().OrderType,
            "product_type": goldencoin_strategy_obj.get_general_params().ProductType,
            "order_mode": "Main",
            "trade_id": next_trade_prefix,
            "trade_mode": TRADE_MODE
        },
        {
            "strategy": goldencoin_strategy_obj.StrategyName,
            "signal": "Long",
            "base_symbol": base_symbol,
            "exchange_token": exchange_token,
            "transaction_type": stoploss_transaction_type,
            "order_type": "Stoploss",
            "product_type": goldencoin_strategy_obj.get_general_params().ProductType,
            "limit_prc": 0.1,
            "trigger_prc": 0.2,
            "order_mode": "SL",
            "trade_id": next_trade_prefix,
            "trade_mode": TRADE_MODE
        },
    ]
    return order_details


def send_signal_msg(base_symbol, strike_prc, option_type):
    message = (
        "GoldenCoin Order placed for "
        + base_symbol
        + " "
        + str(strike_prc)
        + " "
        + option_type
    )
    logger.info(message)
    discord_bot(message, goldencoin_strategy_obj.StrategyName)

def main():
    global start_hour, start_minute, window
    hour = int(start_hour)
    minute = int(start_minute)
    window = int(window)

    current_time = time.localtime()
    seconds_since_midnight = current_time.tm_hour * 3600 + current_time.tm_min * 60 + current_time.tm_sec

    # Calculate the total number of seconds until 11:30 AM
    seconds_until_11_30_am = (hour * 3600 + minute * 60) - seconds_since_midnight

    # The window is now from 11:30 AM to 11:35 AM, so it's 5 minutes long
    seconds_in_window = window * 60  # 5 minutes

    # Generate a random number of seconds to wait within this 5-minute window
    random_seconds = random.randint(0, seconds_in_window)

    # Check if today is the day after a holiday
    now = dt.datetime.now()

    if now.date() in holidays:
        logger.debug("Skipping execution as today is a holiday.")
        return

    # If it's already past 11:35 AM, no need to wait
    if seconds_until_11_30_am < 0:
        logger.debug("The window has already passed.")
    else:
        # Wait until 11:30 AM, then an additional random amount of time within the 5-minute window
        total_wait_seconds = max(seconds_until_11_30_am, 0) + random_seconds
        logger.debug(f"Waiting for {total_wait_seconds} seconds.")
        time.sleep(total_wait_seconds)

    base_symbol, strike_prc, option_type = determine_strike_and_option()
    exchange_token = fetch_exchange_token(base_symbol, strike_prc, option_type)
    update_qty(base_symbol, strike_prc, option_type)
    send_signal_msg(base_symbol, strike_prc, option_type)
    orders_to_place = create_order_details(exchange_token, base_symbol)
    orders_to_place = assign_trade_id(orders_to_place)
    logger.info(orders_to_place)

    main_trade_id = None

    for order in orders_to_place:
        if order.get("order_mode") == "MO":
            main_trade_id = order.get("trade_id")
            main_trade_id_prefix = main_trade_id.split("_")[0]

    signals_to_log = {
        "TradeId": main_trade_id,
        "Signal": "Long",
        "EntryTime": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Status": "Open",
        "Orders": orders_to_place,
        "StrategyInfo": {
            "trade_id": main_trade_id_prefix,
            "prediction": prediction,
        },
    }

    update_signal_firebase(
        goldencoin_strategy_obj.StrategyName, signals_to_log, next_trade_prefix
    )
    place_order_strategy_users(goldencoin_strategy_obj.StrategyName, orders_to_place)

if __name__ == "__main__":
    main()
