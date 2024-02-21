import os
import sys
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

DIR = os.getcwd()
sys.path.append(DIR)

ENV_PATH = os.path.join(DIR, "trademan.env")
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

CLIENTS_TRADE_SQL_DB = os.getenv("DB_DIR")
CLIENTS_USER_FB_DB = os.getenv("FIREBASE_USER_COLLECTION")

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_utils import (
    download_json
)
import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as BrokerCenterUtils
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    update_fields_firebase,
    delete_fields_firebase,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    append_df_to_sqlite,
    get_db_connection,
)


def get_todays_date():
    return datetime.now().strftime("%Y-%m-%d")

def create_user_transaction_db_entry(trade, broker):
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

    return {
        "order_id": trade[order_id_key],
        "trading_symbol": trade[trading_symbol_key],
        "time_stamp": time_stamp,
        "avg_prc": trade[avg_price_key],
        "qty": trade[qty_key],
        "trade_id": trade_id,
    }


def get_update_path(order_id, strategies):
    logger.debug(f"Finding update path for order_id: {order_id}")
    for strategy_key, strategy_data in strategies.items():
        trade_state = strategy_data.get("TradeState", {})
        orders_from_firebase = trade_state.get("orders", [])
        for i, order in enumerate(orders_from_firebase):
            try:
                logger.debug(f"Checking order: {order}")
                if str(order["order_id"]) == order_id:
                    return f"Strategies/{strategy_key}/TradeState/orders/{i}"
            except Exception as e:
                logger.error(f"Error while finding update path: {e}")
                continue

#TODO: Break down this function into smaller functions
def daily_tradebook_validator():
    active_users = BrokerCenterUtils.fetch_active_users_from_firebase()
    logger.debug(f"Validating tradebook for no of users: {len(active_users)}")
    matched_orders = set()
    unmatched_orders = set()
    today = get_todays_date()

    for user in active_users:
        logger.debug(f"Validating tradebook for user: {user['Broker']['BrokerUsername']}")
        db_path = os.path.join(CLIENTS_TRADE_SQL_DB, f"{user['Tr_No']}.db")
        conn = get_db_connection(db_path)
        strategies = user.get("Strategies", {})

        user_tradebook = BrokerCenterUtils.get_today_orders_for_brokers(user)
        processed_order_ids = set()
        order_ids = set()
        for strategy_key, strategy_data in strategies.items():
            trade_state = strategy_data.get("TradeState", {})
            orders_from_firebase = trade_state.get("orders", [])

            avg_price_key = BrokerCenterUtils.get_avg_prc_broker_key(
                user["Broker"]["BrokerName"]
            )
            order_id_key = BrokerCenterUtils.get_order_id_broker_key(
                user["Broker"]["BrokerName"]
            )

            if not orders_from_firebase:
                logger.error(f"No orders found for user: {user['Broker']['BrokerUsername']} for strategy: {strategy_key}")
                continue

            for order in orders_from_firebase:
                if order is None:
                    continue
                order_id_str = str(order["order_id"])
                order_date_timestamp = order.get("time_stamp", "").split(" ")[0]
                if order_date_timestamp == today:
                    order_ids.add(order_id_str)

        for trade in user_tradebook:
            trade_order_id = str(trade[order_id_key])
            processed_order_ids.add(trade_order_id)

            if trade_order_id in order_ids:
                avg_prc = trade[avg_price_key]
                update_path = get_update_path(trade_order_id, strategies)
                update_fields_firebase(
                    BrokerCenterUtils.CLIENTS_USER_FB_DB, user["Tr_No"], {"avg_prc": avg_prc}, update_path
                )
                matched_orders.add(trade_order_id)
            else:
                unmatched_details = create_user_transaction_db_entry(
                    trade, user["Broker"]["BrokerName"]
                )

                if float(unmatched_details["avg_prc"]) == 0.0:
                    continue

                unmatched_details = pd.DataFrame([unmatched_details])
                decimal_columns = ["avg_prc"]
                append_df_to_sqlite(
                    conn, unmatched_details, "UserTransactions", decimal_columns
                )
                unmatched_orders.add(trade_order_id)

        conn.close()

        logger.debug(f"Matched Orders: {matched_orders}")
        logger.debug(f"Unmatched Orders: {unmatched_orders}")

        # clear the lists after iterating through each user
        matched_orders.clear()
        unmatched_orders.clear()


def clear_extra_orders_firebase():
    active_users = BrokerCenterUtils.fetch_active_users_from_firebase()
    for user in active_users:
        logger.debug(f"Clearing extra orders for user: {user['Broker']['BrokerUsername']}")
        strategies = user.get("Strategies", {})
        for strategy_key, strategy_data in strategies.items():
                trade_state = strategy_data.get("TradeState", {})
                orders_from_firebase = trade_state.get("orders", [])
                # i want to delete all the dicts which do not have avg_price field in them
                orders_to_delete = []
                for i, order in enumerate(orders_from_firebase):
                    if order is not None and float(order.get("avg_prc", 0.0)) == 0.0:
                        orders_to_delete.append(i)
                for i in orders_to_delete:
                    order_path = f"Strategies/{strategy_key}/TradeState/orders/{i}"
                    print(f"Deleting order at path: {order_path}")
                    delete_fields_firebase(BrokerCenterUtils.CLIENTS_USER_FB_DB, user["Tr_No"], order_path)

def main():
    download_json(CLIENTS_USER_FB_DB, "before_daily_tradebook_validator")
    daily_tradebook_validator()
    clear_extra_orders_firebase()

if __name__ == "__main__":
    main()