import os
import sys
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

DIR = os.getcwd()
sys.path.append(DIR)

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

CLIENTS_TRADE_SQL_DB = os.getenv("USR_TRADELOG_DB_FOLDER")
CLIENTS_USER_FB_DB = os.getenv("FIREBASE_USER_COLLECTION")

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_utils import (
    download_json,
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
    """
    Returns today's date in 'YYYY-MM-DD' format.

    :return: A string representing today's date.
    """
    return datetime.now().strftime("%Y-%m-%d")


def create_user_transaction_db_entry(trade, broker):
    """
    Creates a dictionary entry for a user transaction based on the trade and broker details.

    :param trade: A dictionary containing trade details.
    :param broker: A string representing the broker's name.
    :return: A dictionary containing the user transaction details.
    """
    avg_price_key = BrokerCenterUtils.get_avg_prc_broker_key(broker)
    order_id_key = BrokerCenterUtils.get_order_id_broker_key(broker)
    trading_symbol_key = BrokerCenterUtils.get_trading_symbol_broker_key(broker)
    qty_key = BrokerCenterUtils.get_qty_broker_key(broker)
    time_stamp_key = BrokerCenterUtils.get_time_stamp_broker_key(broker)
    trade_id_key = BrokerCenterUtils.get_trade_id_broker_key(broker)

    trade_id = 0
    try:
        trade_id = trade[trade_id_key] or 0
    except Exception as e:
        logger.error(f"Error in creating user transaction db entry: {e}")

    try:
        time_stamp = BrokerCenterUtils.convert_to_standard_format(trade[time_stamp_key])
    except Exception as e:
        logger.error(f"Error converting timestamp: {e}")
        time_stamp = None

    return {
        "order_id": trade.get(order_id_key),
        "trading_symbol": trade.get(trading_symbol_key),
        "time_stamp": time_stamp,
        "avg_prc": trade.get(avg_price_key),
        "qty": trade.get(qty_key),
        "trade_id": trade_id,
    }


def get_update_path(order_id, strategies):
    """
    Retrieves the update path for a given order ID from the strategies.

    :param order_id: A string representing the order ID.
    :param strategies: A dictionary containing strategy details.
    :return: A string representing the update path for the order.
    """
    try:
        for strategy_key, strategy_data in strategies.items():
            trade_state = strategy_data.get("TradeState", {})
            orders_from_firebase = trade_state.get("orders", [])
            for i, order in enumerate(orders_from_firebase):
                if str(order["order_id"]) == order_id:
                    return f"Strategies/{strategy_key}/TradeState/orders/{i}"
    except Exception as e:
        logger.error(f"Error in get_update_path: {e}")


def get_order_ids_from_strategies(user, strategies):
    """
    Retrieves a set of order IDs from the strategies for a given user.

    :param user: A dictionary containing user details.
    :param strategies: A dictionary containing strategy details.
    :return: A set of order IDs.
    """
    today = get_todays_date()
    order_ids = set()
    logger.debug(f"Getting order ids for user: {user['Broker']['BrokerUsername']}")
    try:
        for strategy_key, strategy_data in strategies.items():
            trade_state = strategy_data.get("TradeState", {})
            orders_from_firebase = trade_state.get("orders", [])

            if not orders_from_firebase:
                logger.error(
                    f"No orders found for user: {user['Broker']['BrokerUsername']} for strategy: {strategy_key}"
                )
                continue

            for order in orders_from_firebase:
                if order is not None:
                    order_id_str = str(order["order_id"])
                    order_date_timestamp = order.get("time_stamp", "").split(" ")[0]
                    if order_date_timestamp == today:
                        order_ids.add(order_id_str)
        return order_ids
    except Exception as e:
        logger.error(
            f"Error in get_order_ids_from_strategies for user: {user['Broker']['BrokerUsername']}. Error: {e}"
        )


def daily_tradebook_validator():
    """
    Validates the tradebook for all active users by performing the following steps:
    1. Fetches active users from Firebase.
    2. Retrieves today's orders from brokers for each user.
    3. Matches the orders with the strategies and updates Firebase if matched.
    4. Logs unmatched orders into the user's SQLite database.
    5. Logs the progress and any errors encountered during the process.
    """
    active_users = BrokerCenterUtils.fetch_active_users_from_firebase()
    logger.debug(f"Validating tradebook for no of users: {len(active_users)}")
    matched_orders = set()
    unmatched_orders = set()

    for user in active_users:
        logger.debug(
            f"Validating tradebook for user: {user['Broker']['BrokerUsername']}"
        )
        db_path = os.path.join(CLIENTS_TRADE_SQL_DB, f"{user['Tr_No']}.db")
        conn = get_db_connection(db_path)
        strategies = user.get("Strategies", {})

        user_tradebook = BrokerCenterUtils.get_today_orders_for_brokers(user)
        processed_order_ids = set()
        order_ids = get_order_ids_from_strategies(user, strategies)

        try:
            for trade in user_tradebook:
                avg_price_key = BrokerCenterUtils.get_avg_prc_broker_key(
                    user["Broker"]["BrokerName"]
                )
                order_id_key = BrokerCenterUtils.get_order_id_broker_key(
                    user["Broker"]["BrokerName"]
                )
                trade_order_id = str(trade[order_id_key])
                processed_order_ids.add(trade_order_id)

                if trade_order_id in order_ids:
                    avg_prc = trade[avg_price_key]
                    update_path = get_update_path(trade_order_id, strategies)
                    update_fields_firebase(
                        BrokerCenterUtils.CLIENTS_USER_FB_DB,
                        user["Tr_No"],
                        {"avg_prc": avg_prc},
                        update_path,
                    )
                    matched_orders.add(trade_order_id)
                else:
                    unmatched_details = create_user_transaction_db_entry(
                        trade, user["Broker"]["BrokerName"]
                    )

                    try:
                        if (
                            unmatched_details["avg_prc"] is None
                            or not unmatched_details["avg_prc"]
                        ):
                            unmatched_details["avg_prc"] = 0.0
                        else:
                            unmatched_details["avg_prc"] = float(
                                unmatched_details["avg_prc"]
                            )
                    except ValueError:
                        unmatched_details["avg_prc"] = 0.0
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
        except Exception as e:
            logger.error(
                f"Error in daily_tradebook_validator for user: {user['Broker']['BrokerUsername']}. Error: {e}"
            )

        # clear the lists after iterating through each user
        matched_orders.clear()
        unmatched_orders.clear()


def clear_extra_orders_firebase():
    """
    Clears extra orders from Firebase for all active users by performing the following steps:
    1. Fetches active users from Firebase.
    2. Iterates through each strategy for each user.
    3. Identifies orders without 'avg_prc' and deletes them from Firebase.
    4. Logs the progress and any errors encountered during the process.
    """
    active_users = BrokerCenterUtils.fetch_active_users_from_firebase()
    for user in active_users:
        logger.debug(
            f"Clearing extra orders for user: {user['Broker']['BrokerUsername']}"
        )
        strategies = user.get("Strategies", {})
        if strategies:
            for strategy_key, strategy_data in strategies.items():
                logger.debug(f"Clearing extra orders for strategy: {strategy_key}")
                trade_state = strategy_data.get("TradeState", {})
                orders_from_firebase = trade_state.get("orders", [])
                orders_to_delete = [
                    i
                    for i, order in enumerate(orders_from_firebase)
                    if order is not None and not order.get("avg_prc")
                ]
                for i in orders_to_delete:
                    order_path = f"Strategies/{strategy_key}/TradeState/orders/{i}"
                    logger.debug(f"Deleting order at path: {order_path}")
                    try:
                        delete_fields_firebase(
                            BrokerCenterUtils.CLIENTS_USER_FB_DB,
                            user["Tr_No"],
                            order_path,
                        )
                    except Exception as e:
                        logger.error(
                            f"Error deleting order at path: {order_path}. Error: {str(e)}"
                        )


def main():
    """
    The main function orchestrates the tradebook validation process by performing the following steps:
    1. Downloads the JSON data for the clients' user Firebase database before validating the tradebook.
    2. Calls the function to validate the tradebook for all active users.
    3. Calls the function to clear extra orders from Firebase.
    """
    download_json(CLIENTS_USER_FB_DB, "before_daily_tradebook_validator")
    daily_tradebook_validator()
    clear_extra_orders_firebase()


if __name__ == "__main__":
    main()
