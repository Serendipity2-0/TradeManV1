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
    download_firebase_json,
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
from TradebookValidatorUtils import (
    check_strategy_path,
    check_strategy_orders,
    verify_firebase_orders,
)

EQUITY_STRATEGY_LIST = os.getenv("EQUITY_STRATEGY_LIST")
EQUITY_STRATEGY_LIST = EQUITY_STRATEGY_LIST.split(",")

DERIVATIVES_STRATEGY_LIST = os.getenv("DERIVATIVES_STRATEGY_LIST")
DERIVATIVES_STRATEGY_LIST = DERIVATIVES_STRATEGY_LIST.split(",")


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
    :return: A string representing the update path for the order, or None if not found.
    """
    try:
        for asset_class, asset_data in strategies.items():
            if asset_class == "Equity":
                for term in asset_data.keys():
                    if term in asset_data:
                        for strategy_key, strategy_data in asset_data[term].items():
                            path = check_strategy_path(
                                asset_class, term, strategy_key, strategy_data, order_id
                            )
                            if path:
                                return path
            elif asset_class == "Derivatives":
                for strategy in DERIVATIVES_STRATEGY_LIST:
                    if strategy in asset_data:
                        path = check_strategy_path(
                            asset_class, None, strategy, asset_data[strategy], order_id
                        )
                        if path:
                            return path
            else:
                logger.info(f"Unsupported asset class: {asset_class}")

        logger.info(f"No matching order found for order_id: {order_id}")
        return None
    except Exception as e:
        logger.error(f"Error in get_update_path: {e}")
        return None


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
        for asset_class, asset_data in strategies.items():

            if asset_class == "Equity":
                for term, term_data in asset_data.items():
                    logger.debug(f"Processing term: {term}")
                    for strategy_key, strategy_data in term_data.items():
                        order_ids.update(
                            check_strategy_orders(
                                user,
                                asset_class,
                                term,
                                strategy_key,
                                strategy_data,
                                today,
                            )
                        )
            elif asset_class == "Derivatives":
                for strategy_key, strategy_data in asset_data.items():
                    if strategy_key in DERIVATIVES_STRATEGY_LIST:
                        order_ids.update(
                            check_strategy_orders(
                                user,
                                asset_class,
                                None,
                                strategy_key,
                                strategy_data,
                                today,
                            )
                        )
            else:
                logger.info(f"Unsupported asset class: {asset_class}")

        if not order_ids:
            logger.info(
                f"No orders found today for user: {user['Broker']['BrokerUsername']}"
            )
        else:
            logger.info(
                f"Found {len(order_ids)} orders for user: {user['Broker']['BrokerUsername']}"
            )
        return order_ids
    except Exception as e:
        logger.error(
            f"Error in get_order_ids_from_strategies for user: {user['Broker']['BrokerUsername']}. Error: {e}"
        )
        return set()


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
        db_path = os.path.join(CLIENTS_TRADE_SQL_DB, f"{user['Tr_No']}_UserTrades.db")
        conn = get_db_connection(db_path)
        strategies = user.get("Strategies", {})

        user_tradebook = BrokerCenterUtils.get_today_orders_for_brokers(user)
        processed_order_ids = set()
        order_ids = get_order_ids_from_strategies(user, strategies)

        try:
            if not user_tradebook:
                logger.info(
                    f"No tradebook found for user: {user['Broker']['BrokerUsername']}"
                )
                continue

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
                    logger.debug(
                        f"Updating order: {trade_order_id} with avg_prc: {avg_prc} at path: {update_path}"
                    )
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
    2. Iterates through each strategy (Equity, Derivatives) for each user.
    3. For Equity, navigates through the nested structure to find TradeState.
    4. For Derivatives, directly accesses TradeState if present.
    5. Identifies orders with 'avg_prc' equal to '' and deletes them from Firebase.
    6. Logs the progress and any errors encountered during the process.
    """
    active_users = BrokerCenterUtils.fetch_active_users_from_firebase()
    try:
        for user in active_users:
            logger.debug(
                f"Clearing extra orders for user: {user['Broker']['BrokerUsername']}"
            )
            strategies = user.get("Strategies", {})
            if strategies:
                for strategy_key, strategy_data in strategies.items():
                    logger.debug(f"Clearing extra orders for strategy: {strategy_key}")

                    def process_trade_state(trade_state, path_prefix):
                        orders_from_firebase = trade_state.get("orders", [])
                        orders_to_delete = [
                            i
                            for i, order in enumerate(orders_from_firebase)
                            if order is not None and order.get("avg_prc") == ""
                        ]
                        for i in orders_to_delete:
                            order_path = f"{path_prefix}/orders/{i}"
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

                    if strategy_key == "Equity":
                        for term_key, term_data in strategy_data.items():
                            for setup_key, setup_data in term_data.items():
                                if (
                                    isinstance(setup_data, dict)
                                    and "TradeState" in setup_data
                                ):
                                    trade_state = setup_data.get("TradeState", {})
                                    path_prefix = f"Strategies/Equity/{term_key}/{setup_key}/TradeState"
                                    process_trade_state(trade_state, path_prefix)
                    elif strategy_key == "Derivatives":
                        for setup_key, setup_data in strategy_data.items():
                            if (
                                isinstance(setup_data, dict)
                                and "TradeState" in setup_data
                            ):
                                trade_state = setup_data.get("TradeState", {})
                                path_prefix = (
                                    f"Strategies/Derivatives/{setup_key}/TradeState"
                                )
                                process_trade_state(trade_state, path_prefix)
                verify_firebase_orders(user)
    except Exception as e:
        logger.error(f"Error in clear_extra_orders_firebase: {e}")


def main():
    """
    The main function orchestrates the tradebook validation process by performing the following steps:
    1. Downloads the JSON data for the clients' user Firebase database before validating the tradebook.
    2. Calls the function to validate the tradebook for all active users.
    3. Calls the function to clear extra orders from Firebase.
    """
    download_firebase_json(CLIENTS_USER_FB_DB, "before_daily_tradebook_validator")
    daily_tradebook_validator()
    clear_extra_orders_firebase()


if __name__ == "__main__":
    main()
