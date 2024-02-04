from datetime import datetime
import os,sys
from dotenv import load_dotenv
import pandas as pd

DIR = os.getcwd()
sys.path.append(DIR)

ENV_PATH = os.path.join(DIR, 'trademan.env')
load_dotenv(ENV_PATH)

from loguru import logger
ERROR_LOG_PATH = os.getenv('ERROR_LOG_PATH')
logger.add(ERROR_LOG_PATH,level="TRACE", rotation="00:00",enqueue=True,backtrace=True, diagnose=True)


db_dir = os.getenv('DB_DIR')

# from Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter import aliceblue_todays_tradebook
# from Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter import zerodha_todays_tradebook
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (fetch_collection_data_firebase,
                                    update_fields_firebase)
import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as BrokerCenterUtils
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import dump_df_to_sqlite, get_db_connection


def get_todays_date():
    return datetime.now().strftime("%Y-%m-%d")

def create_user_transaction_db_entry(trade,broker):
    avg_price_key = BrokerCenterUtils.get_avg_prc_broker_key(broker)
    order_id_key = BrokerCenterUtils.get_order_id_broker_key(broker)
    trading_symbol_key = BrokerCenterUtils.get_trading_symbol_broker_key(broker)
    qty_key = BrokerCenterUtils.get_qty_broker_key(broker)
    time_stamp_key = BrokerCenterUtils.get_time_stamp_broker_key(broker)
    trade_id_key = BrokerCenterUtils.get_trade_id_broker_key(broker)
    trade_id = trade[trade_id_key]
    if trade_id == None:
        trade_id = 0
    
    time_stamp = BrokerCenterUtils.convert_to_standard_format(trade[time_stamp_key])

    return {'order_id':trade[order_id_key],'trading_symbol':trade[trading_symbol_key], 'time_stamp':time_stamp, 'avg_prc':trade[avg_price_key],'qty':trade[qty_key],'trade_id':trade_id}

def get_update_path(order_id,strategies):
    for strategy_key, strategy_data in strategies.items():
        trade_state = strategy_data.get('TradeState', {})
        orders_from_firebase = trade_state.get('orders', [])
        for i,order in enumerate(orders_from_firebase):
            if str(order['order_id']) == order_id:
                return f"Strategies/{strategy_key}/TradeState/orders/{i}"


def daily_tradebook_validator():
    active_users = BrokerCenterUtils.fetch_active_users_from_firebase()
    matched_orders = set()
    unmatched_orders = set()

    for user in active_users:
        db_path = os.path.join(db_dir, f"{user['Tr_No']}.db")
        conn = get_db_connection(db_path)
        strategies = user.get('Strategies', {})
        today = get_todays_date()

        user_tradebook = BrokerCenterUtils.get_today_orders_for_brokers(user)
        processed_order_ids = set()

        order_ids = set()
        for strategy_key, strategy_data in strategies.items():
            trade_state = strategy_data.get('TradeState', {})
            orders_from_firebase = trade_state.get('orders', [])

            avg_price_key = BrokerCenterUtils.get_avg_prc_broker_key(user['Broker']['BrokerName'])
            order_id_key = BrokerCenterUtils.get_order_id_broker_key(user['Broker']['BrokerName'])
            
            if not orders_from_firebase:
                logger.error(f"No orders found for user: {user['Tr_No']}")
                continue

            for order in orders_from_firebase:
                order_id_str = str(order['order_id'])
                order_date_timestamp = order.get('time_stamp', '').split(' ')[0]
                if order_date_timestamp == today:
                    order_ids.add(order_id_str)


        for trade in user_tradebook:
            trade_order_id = str(trade[order_id_key])
            processed_order_ids.add(trade_order_id)

            if trade_order_id in order_ids:
                avg_prc = trade[avg_price_key]
                update_path = get_update_path(trade_order_id,strategies)
                update_fields_firebase('new_clients', user['Tr_No'], {'avg_prc': avg_prc}, update_path)
                matched_orders.add(trade_order_id)
            else:
                unmatched_details = create_user_transaction_db_entry(trade,user['Broker']['BrokerName'])
                unmatched_details = pd.DataFrame([unmatched_details])
                decimal_columns = ['avg_prc']
                dump_df_to_sqlite(conn,unmatched_details,'user_transactions',decimal_columns)
                unmatched_orders.add(trade_order_id)

        conn.close()

        logger.debug("Matched Orders:", list(matched_orders))
        logger.debug("Unmatched Orders:", list(unmatched_orders))
        #clear the lists after iterating through each user
        matched_orders.clear()
        unmatched_orders.clear()
        

daily_tradebook_validator()


