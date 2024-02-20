import os, sys
import urllib
from dotenv import load_dotenv
import numpy as np
import datetime as dt
from time import sleep

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

import Executor.Strategies.OvernightFutures.OvernightFutures_calc as OF_calc
from Executor.Strategies.StrategiesUtil import StrategyBase, base_symbol_token,update_qty_user_firebase,update_signal_firebase
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.ExeUtils import holidays
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    update_fields_firebase,
)
from Executor.Strategies.StrategiesUtil import (
    assign_trade_id,
    place_order_strategy_users,
)
from Executor.ExecutorUtils.InstrumentCenter.FNOInfoBase import FNOInfo

hedge_transcation_type = "BUY"
futures_option_type = "FUT"
futures_strikeprc = 0

strategy_obj = StrategyBase.load_from_db("OvernightFutures")
instrument_obj = InstrumentCenterUtils.Instrument()

strategy_name = strategy_obj.StrategyName
base_symbols = strategy_obj.Instruments
base_symbol = base_symbols[0]
instrument_token = base_symbol_token(base_symbol)

order_type = strategy_obj.GeneralParams.OrderType
product_type = strategy_obj.GeneralParams.ProductType


def get_strikeprc(instrument_token, strategy_index, prediction):
    strike_prc_multiplier = strategy_obj.EntryParams.SLMultiplier
    return strategy_obj.calculate_current_atm_strike_prc(
        base_symbol=strategy_index,
        token=instrument_token,
        prediction=prediction,
        strike_prc_multiplier=strike_prc_multiplier,
    )


try:
    proxyServer = urllib.request.getproxies()["http"]
except KeyError:
    proxyServer = ""

prediction, percentage = OF_calc.getNiftyPrediction(
    data=OF_calc.fetchLatestNiftyDaily(proxyServer=proxyServer), proxyServer=proxyServer
)
print(prediction)

strikeprc = get_strikeprc(instrument_token, base_symbol, prediction)
option_type = strategy_obj.get_option_type(prediction, "OS")
desired_start_time_str = strategy_obj.EntryParams.EntryTime
start_hour, start_minute, start_second = map(int, desired_start_time_str.split(":"))

weekly_expiry_type = instrument_obj.weekly_expiry_type()
monthly_expiry_type = instrument_obj.monthly_expiry_type()

weekly_expiry = instrument_obj.get_expiry_by_criteria(
    base_symbol, strikeprc, option_type, weekly_expiry_type
)
monthly_expiry = instrument_obj.get_expiry_by_criteria(
    base_symbol, 0, "FUT", monthly_expiry_type
)


hedge_exchange_token = instrument_obj.get_exchange_token_by_criteria(
    base_symbol, strikeprc, option_type, weekly_expiry
)
futures_exchange_token = instrument_obj.get_exchange_token_by_criteria(
    base_symbol, futures_strikeprc, futures_option_type, monthly_expiry
)
next_trade_prefix = strategy_obj.NextTradeId


future_trade_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
    futures_exchange_token
)
hedge_trade_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
    hedge_exchange_token
)

signal = "Long" if prediction == "Bullish" else "Short"

orders_to_place = [
    {
        "strategy": strategy_name,
        "signal": signal,
        "base_symbol": base_symbol,
        "exchange_token": hedge_exchange_token,
        "transaction_type": hedge_transcation_type,
        "order_type": order_type,
        "product_type": product_type,
        "order_mode": "HedgeEntry",
        "trade_id": next_trade_prefix,
    },
    {
        "strategy": strategy_name,
        "signal": signal,
        "base_symbol": base_symbol,
        "exchange_token": futures_exchange_token,
        "transaction_type": strategy_obj.get_transaction_type(prediction),
        "order_type": order_type,
        "product_type": product_type,
        "order_mode": "Main",
        "trade_id": next_trade_prefix,
    },
]


def message_for_orders(
    prediction, main_trade_symbol, hedge_trade_symbol, weekly_expiry, monthly_expiry
):
    strategy_name = strategy_obj.StrategyName

    message = (
        f"Trade for {strategy_name}\n"
        f"Percentage : {round((percentage[0]*100),2)}\n"
        f"Direction : {prediction}\n"
        f"Future : {main_trade_symbol} Expiry : {monthly_expiry}\n"
        f"Hedge : {hedge_trade_symbol} Expiry : {weekly_expiry}\n"
    )
    print(message)
    discord_bot(message, strategy_name)

def signal_to_log_firebase(orders_to_place,predicition):
    for order in orders_to_place:
            if order.get("order_mode") == "MO":
                main_trade_id = order.get("trade_id")
                main_trade_id_prefix = main_trade_id.split("_")[0]
    
    trade_signal = "Long" if predicition == "Bullish" else "Short"

    signals_to_log = {
            "TradeId": main_trade_id,
            "Signal": trade_signal,
            "EntryTime": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Orders" : orders_to_place,
            "StrategyInfo": {
                "trade_id": main_trade_id_prefix,
                "direction": predicition,
                "percentage":percentage[0]
            }
        }
    update_signal_firebase(strategy_obj.StrategyName, signals_to_log, next_trade_prefix)

def main():
    global hedge_exchange_token, futures_exchange_token, prediction, orders_to_place
    now = dt.datetime.now()

    lot_size = lot_size = FNOInfo().get_lot_size_by_base_symbol(strategy_obj.Instruments[0])
    avg_sl_points = strategy_obj.ExitParams.AvgSLPoints

    if now.date() in holidays:
        print("Skipping execution as today is a holiday.")
        return

    wait_time = (
        dt.datetime(now.year, now.month, now.day, start_hour, start_minute) - now
    )
    if wait_time.total_seconds() > 0:
        print(f"Waiting for {wait_time} before starting the bot")
        sleep(wait_time.total_seconds())

    message_for_orders(
        prediction,
        future_trade_symbol,
        hedge_trade_symbol,
        weekly_expiry,
        monthly_expiry,
    )
    orders_to_place = assign_trade_id(orders_to_place)
    print(orders_to_place)
    update_qty_user_firebase(strategy_name, avg_sl_points, lot_size)
    signal_to_log_firebase(orders_to_place,prediction)
    place_order_strategy_users(strategy_name, orders_to_place)

    hedge_exchange_token = np.int64(hedge_exchange_token)
    hedge_exchange_token = int(hedge_exchange_token)

    futures_exchange_token = np.int64(futures_exchange_token)
    futures_exchange_token = int(futures_exchange_token)

    extra_info = {
        "FuturesExchangeToken": futures_exchange_token,
        "HedgeExchangeToken": hedge_exchange_token,
        "Prediction": prediction,
    }
    update_fields_firebase("strategies", strategy_name, extra_info, "ExtraInformation")


if __name__ == "__main__":
    main()
