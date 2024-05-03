import pandas as pd
import os,sys
from dotenv import load_dotenv
import datetime as dt
# Fetch stock symbols

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

import Executor.Strategies.PyStocks.PyStocksUtils as pystocksutils
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_users_for_strategies_from_firebase as fetch_active_users
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import fetch_sql_table_from_db as fetch_table_from_db
from Executor.Strategies.StrategiesUtil import StrategyBase
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument as instrument_obj, get_single_ltp
from Executor.Strategies.StrategiesUtil import (
    update_qty_user_firebase,
    assign_trade_id,
    update_signal_firebase,
    place_order_strategy_users,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()
pystocks_obj = StrategyBase.load_from_db("PyStocks")

strategy_name = pystocks_obj.StrategyName
order_type = pystocks_obj.GeneralParams.OrderType
product_type = pystocks_obj.GeneralParams.ProductType

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

def create_csv():
    try:
        pystocksutils.get_stockpicks_csv()
    except Exception as e:
        logger.error(f"Error in creating csv: {e}")

def main():

    #TODO: This is just done for short term
    df = pd.read_csv(os.getenv("best5_shortterm_path"))
    symbol_list = df['Symbol'].tolist()
    logger.debug(f"Symbol list: {symbol_list}")

    users = fetch_active_users("PyStocks")
    for user in users:
        holdings = fetch_table_from_db(user['Tr_No'], "Holdings")
        py_holdings = holdings[holdings['trade_id'].str.startswith('PS')] #TODO Remove hardcoded PS
        i = len(py_holdings)
        if len(py_holdings) <5: # Check if the user has less than 5 active PyStocks positions
            for symbol in symbol_list:
                exchange_token = instrument_obj().get_exchange_token_by_name(symbol,"NSE")
                ltp = get_single_ltp(exchange_token=exchange_token,segment="NSE")
                logger.debug(f"LTP for {symbol}: {ltp}")
                ltp = round(ltp * 20) / 20
                update_qty_user_firebase(strategy_name, ltp, 1)
                new_base = pystocks_obj.reload_strategy(strategy_name)
                order_details = [{
                    "strategy": strategy_name,
                    "signal": "Long",
                    "base_symbol": symbol,
                    "exchange_token": exchange_token,
                    "transaction_type": "BUY",
                    "order_type": order_type,
                    "product_type": product_type,
                    "order_mode": "MainEntry",
                    "trade_id": new_base.NextTradeId,
                    "limit_prc": ltp
                }]
                order_to_place = assign_trade_id(order_details)
                signals_to_fb(order_to_place, new_base.NextTradeId)
                logger.debug(f"Orders to place: {order_to_place}")
                # place_order_strategy_users(strategy_name, order_to_place)
                i=i+1
                if i == 5:
                    break
        


if __name__ == "__main__":
    create_csv()
    main()