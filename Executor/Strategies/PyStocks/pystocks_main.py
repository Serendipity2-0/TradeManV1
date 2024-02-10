import pandas as pd
import os,sys
from dotenv import load_dotenv
import datetime as dt

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.Strategies.StrategiesUtil import StrategyBase
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument as instrument_obj, get_single_ltp

from Executor.Strategies.StrategiesUtil import (
    update_qty_user_firebase,
    assign_trade_id,
    update_signal_firebase,
    place_order_strategy_users,
)
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


pystocks_obj = StrategyBase.load_from_db("PyStocks")

#1. Read the /Users/amolkittur/Desktop/TradeManV1/shortterm_best5.csv file
#2. Prepare the order_deatils dictionary with the Symbol in the csv file
#3. Place orders

#1. Read the /Users/amolkittur/Desktop/TradeManV1/shortterm_best5.csv file
df = pd.read_csv(os.getenv("best5_shortterm_path"))

symbol_list = df['Symbol'].tolist()
logger.debug(f"Symbol list: {symbol_list}")

#2. Prepare the order_deatils dictionary with the Symbol in the csv file

strategy_name = pystocks_obj.StrategyName

# exchange_token = instrument_obj().get_exchange_token_by_name("CROWN","NSE")
# logger.debug(f"Exchange token: {exchange_token}")

def signals_to_fb(order_to_place, next_trade_prefix):
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


for symbol in symbol_list:
    exchange_token = instrument_obj().get_exchange_token_by_name(symbol,"NSE")
    ltp = get_single_ltp(exchange_token=exchange_token,segment="NSE")
    logger.debug(f"LTP for {symbol}: {ltp}")
    update_qty_user_firebase(strategy_name, ltp, 1)
    new_base = pystocks_obj.reload_strategy(strategy_name)
    order_details = [{
        "strategy": strategy_name,
        "signal": "Long",
        "base_symbol": symbol,
        "exchange_token": exchange_token,
        "transaction_type": "BUY",
        "order_type": "LIMIT",
        "product_type": "CNC",
        "order_mode": "MainEntry",
        "trade_id": new_base.NextTradeId
    }]
    order_to_place = assign_trade_id(order_details)
    signals_to_fb(order_to_place, new_base.NextTradeId)
    logger.debug(f"Orders to place: {order_to_place}")
    place_order_strategy_users(strategy_name, order_to_place)
