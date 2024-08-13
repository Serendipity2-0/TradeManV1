import os
import sys
from datetime import datetime
from time import sleep
from typing import List, Dict, Any
from functools import reduce
from operator import getitem
import pandas as pd
from dotenv import load_dotenv
import traceback

DIR = os.getcwd()
sys.path.append(DIR)

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

CLIENTS_TRADE_SQL_DERIVATIVES_DB = os.getenv("USR_TRADELOG_DERIVATIVES_DB_FOLDER")
CLIENTS_TRADE_SQL_EQUITY_DB = os.getenv("USR_TRADELOG_EQUITY_DB_FOLDER")
CLIENTS_USER_FB_DB_COLLECTION = os.getenv("FIREBASE_USER_COLLECTION")
STRATEGY_FB_DB_COLLECTION = os.getenv("FIREBASE_STRATEGY_COLLECTION")
EQUITY_STRATEGY_LIST = os.getenv("EQUITY_STRATEGY_LIST")
DERIVATIVES_STRATEGY_LIST = os.getenv("DERIVATIVES_STRATEGY_LIST")

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_active_users_from_firebase,
    fetch_list_of_strategies_from_firebase,
    fetch_users_for_strategies_from_firebase,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    append_df_to_sqlite,
    get_db_connection,
    dump_df_to_sqlite,
)
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    delete_fields_firebase,
    fetch_collection_data_firebase,
    update_fields_firebase,
)
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_utils import (
    download_firebase_json,
)

from Executor.NSEStrategies.NSEStrategiesUtil import StrategyBase


def update_signal_info():
    """
    Updates the signal information for all active strategies by fetching data from Firebase
    and appending it to the SQLite database.
    """
    active_strategies = fetch_list_of_strategies_from_firebase()

    for strategy_name in active_strategies:
        if strategy_name in DERIVATIVES_STRATEGY_LIST:
            signal_info_db_conn = get_db_connection(
                os.path.join(
                    CLIENTS_TRADE_SQL_DERIVATIVES_DB, "signal_derivatives_info.db"
                )
            )
        elif strategy_name in EQUITY_STRATEGY_LIST:
            signal_info_db_conn = get_db_connection(
                os.path.join(CLIENTS_TRADE_SQL_EQUITY_DB, "signal_equity_info.db")
            )
        logger.debug(f"Updating signal info for {strategy_name}")
        try:
            strategy_info = fetch_collection_data_firebase(
                STRATEGY_FB_DB_COLLECTION, strategy_name
            )
            if strategy_info is None:
                logger.warning(
                    f"No data found for strategy {strategy_name}. Skipping..."
                )
                continue

            today_orders = strategy_info.get("TodayOrders", {})
            if not today_orders:
                logger.warning(
                    f"No orders found for {strategy_name} today. Skipping..."
                )
                continue
            for order, values in today_orders.items():
                if values.get("StrategyInfo"):
                    strategy_info_dict = values.get("StrategyInfo")
                    df = pd.DataFrame([strategy_info_dict])
                    if "trade_id" not in df.columns:
                        df["trade_id"] = None  # or some default value
                    df = df[
                        ["trade_id"] + [col for col in df.columns if col != "trade_id"]
                    ]
                    append_df_to_sqlite(signal_info_db_conn, df, strategy_name, [])
        except Exception as e:
            logger.error(f"Error updating signal info for {strategy_name}: {e}")
            logger.error(traceback.format_exc())
            continue


def update_signals_firebase():
    """
    Updates the signals in Firebase by fetching data from SQLite database and appending the data
    back to Firebase.

    :return: A dictionary mapping strategy names to user trade numbers.
    """
    from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
        append_df_to_sqlite,
        get_db_connection,
        read_strategy_table,
    )

    strategy_user_dict = {
        strategy: users[0]["Tr_No"]
        for strategy in fetch_list_of_strategies_from_firebase()
        if (users := fetch_users_for_strategies_from_firebase(strategy))
    }

    today = datetime.today().date()
    decimal_columns = ["entry_price", "exit_price", "hedge_points", "trade_points"]

    for strategy_name, user in strategy_user_dict.items():
        if strategy_name in DERIVATIVES_STRATEGY_LIST:
            db_folder = CLIENTS_TRADE_SQL_DERIVATIVES_DB
            db_path = os.path.join(db_folder, f"{user}_derivatives.db")
            signal_db_path = os.path.join(db_folder, "signal_derivatives.db")
        elif strategy_name in EQUITY_STRATEGY_LIST:
            db_folder = CLIENTS_TRADE_SQL_EQUITY_DB
            db_path = os.path.join(db_folder, f"{user}_equity.db")
            signal_db_path = os.path.join(db_folder, "signal_equity.db")
        else:
            logger.error(f"Strategy {strategy_name} not found in any strategy list")
            continue

        try:
            with get_db_connection(db_path) as conn:
                strategy_data = read_strategy_table(conn, strategy_name)

            today_signals = []

            for _, row in strategy_data.iterrows():
                if pd.isnull(row.get("exit_time")):
                    continue

                try:
                    exit_time = datetime.strptime(row["exit_time"], "%Y-%m-%d %H:%M:%S")
                    if exit_time.date() == today:
                        signal_data = {
                            "trade_id": row["trade_id"],
                            "trading_symbol": row["trading_symbol"],
                            "signal": row["signal"],
                            "entry_time": row["entry_time"],
                            "exit_time": row["exit_time"],
                            "entry_price": row["entry_price"],
                            "exit_price": row.get("exit_price", 0),
                            "hedge_points": float(row.get("hedge_exit_price", 0))
                            - float(row.get("hedge_entry_price", 0)),
                            "trade_points": row.get("trade_points", 0),
                        }
                        today_signals.append(signal_data)
                except ValueError:
                    logger.error(
                        f"Error processing signal data for {strategy_name} in {user}.db"
                    )
                    continue

            if today_signals:
                df = pd.DataFrame(today_signals)
                with get_db_connection(signal_db_path) as signal_db_conn:
                    append_df_to_sqlite(
                        signal_db_conn, df, strategy_name, decimal_columns
                    )

        except Exception as e:
            logger.error(
                f"Error processing strategy {strategy_name} for user {user}: {e}"
            )
            logger.error(traceback.format_exc())
    return strategy_user_dict

    # fetch the users for the strategy


def clear_today_orders_firebase():
    """
    Clears today's orders from Firebase for all active strategies.
    """
    try:
        active_strategies = fetch_list_of_strategies_from_firebase()
        for strategy in active_strategies:
            delete_fields_firebase(STRATEGY_FB_DB_COLLECTION, strategy, "TodayOrders")
    except Exception as e:
        logger.error(f"Error occurred while clearing today's orders from Firebase: {e}")


def convert_trade_state_to_list(
    orders_firebase, user_TR_No, setup_name=None
):  # TODO:Fix here
    """
    Converts the trade state of orders from a dictionary to a list format in Firebase.

    :param orders_firebase: A dictionary containing orders from Firebase.
    :param user_TR_No: A string representing the user's trade number.
    """
    for trade_type in ["Derivatives", "Equity"]:
        strategies = orders_firebase.get("Strategies", {}).get(trade_type, {})
        for strategy_name, strategy_detail in strategies.items():
            if trade_type == "Equity":
                for setup_name, setup_detail in strategy_detail.items():
                    if setup_name == "AllocationPercent":
                        continue
                    orders = setup_detail.get("TradeState", {}).get("orders", [])
                    if isinstance(orders, dict):
                        orders = list(orders.values())
                        if setup_name:
                            update_path = f"Strategies/Equity/{strategy_name}/{setup_name}/TradeState/"
                        else:
                            update_path = (
                                f"Strategies/Derivatives/{strategy_name}/TradeState/"
                            )
                        try:
                            update_fields_firebase(
                                CLIENTS_USER_FB_DB_COLLECTION,
                                user_TR_No,
                                {"orders": orders},
                                update_path,
                            )
                        except Exception as e:
                            logger.error(
                                f"Error updating trade state for strategy {strategy_name}: {e}"
                            )
                    else:
                        logger.error(
                            f"Unexpected data structure for strategy {strategy_name} orders."
                        )
            else:
                orders = strategy_detail.get("TradeState", {}).get("orders", [])
                if isinstance(orders, dict):
                    orders = list(orders.values())
                    if setup_name:
                        update_path = f"Strategies/Equity/{strategy_name}/{setup_name}/TradeState/"
                    else:
                        update_path = (
                            f"Strategies/Derivatives/{strategy_name}/TradeState/"
                        )
                    try:
                        update_fields_firebase(
                            CLIENTS_USER_FB_DB_COLLECTION,
                            user_TR_No,
                            {"orders": orders},
                            update_path,
                        )
                    except Exception as e:
                        logger.error(
                            f"Error updating trade state for strategy {strategy_name}: {e}"
                        )
                else:
                    logger.error(
                        f"Unexpected data structure for strategy {strategy_name} orders."
                    )


def get_keys_to_delete(strategy_orders, order_ids_to_delete):
    """
    Retrieves the keys of orders to delete from the strategy orders.

    :param strategy_orders: A list or dictionary containing strategy orders.
    :param order_ids_to_delete: A set of order IDs to delete.
    :return: A list of keys to delete.
    """
    keys_to_delete = []
    if isinstance(strategy_orders, list):
        for index, order_details in enumerate(strategy_orders):
            if order_details and order_details.get("order_id") in order_ids_to_delete:
                keys_to_delete.append(index)
    elif isinstance(strategy_orders, dict):
        for key, order_details in strategy_orders.items():
            if order_details and order_details.get("order_id") in order_ids_to_delete:
                keys_to_delete.append(key)
    else:
        logger.error("Unexpected data structure for strategy_orders.")
    return keys_to_delete


def delete_orders_from_firebase(orders, strategy_name, user, setup_name=None):
    """
    Deletes orders from Firebase for a given strategy and user.

    :param orders: A dictionary containing orders to delete.
    :param strategy_name: A string representing the strategy name.
    :param user: A dictionary containing user details.
    :param setup_name: An optional string representing the setup name.
    """
    try:
        combined_orders = (
            orders["entry_orders"] + orders["exit_orders"] + orders["hedge_orders"]
        )
    except KeyError as e:
        logger.error(f"Error fetching orders to delete for {strategy_name}: {e}")
        return
    except Exception as e:
        logger.error(
            f"Error occurred while fetching orders to delete for {strategy_name}: {e}"
        )
        return

    if not combined_orders:
        logger.info("Entry or exit orders missing, skipping deletion.")
        return

    try:
        orders_firebase = fetch_collection_data_firebase(
            CLIENTS_USER_FB_DB_COLLECTION, user["Tr_No"]
        )
    except Exception as e:
        logger.error(f"Error fetching Firebase data for {user['Tr_No']}: {e}")
        return

    try:
        if setup_name:
            strategy_orders = orders_firebase["Strategies"]["Equity"][strategy_name][
                setup_name
            ]["TradeState"]["orders"]
        else:
            strategy_orders = orders_firebase["Strategies"]["Derivatives"][
                strategy_name
            ]["TradeState"]["orders"]
    except KeyError:
        logger.info(f"Strategy {strategy_name} not found or missing TradeState.")
        return

    order_ids_to_delete = {order["order_id"] for order in combined_orders}
    keys_to_delete = get_keys_to_delete(strategy_orders, order_ids_to_delete)

    if not keys_to_delete:
        logger.info("No matching orders found for deletion.")
        return

    for key in keys_to_delete:
        try:
            if setup_name:
                delete_path = f"Strategies/Equity/{strategy_name}/{setup_name}/TradeState/orders/{key}"
            else:
                delete_path = (
                    f"Strategies/Derivatives/{strategy_name}/TradeState/orders/{key}"
                )
            delete_fields_firebase(
                CLIENTS_USER_FB_DB_COLLECTION, user["Tr_No"], delete_path
            )
        except Exception as e:
            logger.info(f"Error deleting order with ID {key}: {e}")

    try:
        fetch_collection_data_firebase(CLIENTS_USER_FB_DB_COLLECTION, user["Tr_No"])
    except Exception as e:
        logger.error(
            f"Error fetching pending orders from Firebase for {strategy_name}: {e}"
        )
        return

    logger.success("Deletion process completed.")


def calculate_tax_from_firebasedb(entry_orders, exit_orders, hedge_orders):
    """
    Calculates the total tax from entry, exit, and hedge orders.

    :param entry_orders: A list of entry orders.
    :param exit_orders: A list of exit orders.
    :param hedge_orders: A list of hedge orders.
    :return: The total tax calculated from the orders.
    """
    tax = sum(order["tax"] for order in entry_orders)
    tax += sum(order["tax"] for order in exit_orders)
    tax += sum(order["tax"] for order in hedge_orders)
    return tax


def seggregate_orders_by_type(orders):
    """
    Segregates orders by their type into entry, exit, and hedge orders.

    :param orders: A list of orders.
    :return: A tuple containing lists of entry orders, exit orders, and hedge orders.
    """

    try:

        entry_orders = [
            o
            for o in orders
            if "trade_id" in o and "EN" in o["trade_id"] and "HO" not in o["trade_id"]
        ]
        exit_orders = [
            o
            for o in orders
            if "trade_id" in o and "EX" in o["trade_id"] and "HO" not in o["trade_id"]
        ]
        hedge_orders = [o for o in orders if "trade_id" in o and "HO" in o["trade_id"]]
        return entry_orders, exit_orders, hedge_orders
    except Exception as e:
        logger.error(f"Error segregating orders: {e}")
        return


def process_orders_for_strategy(strategy_orders):
    """
    Processes orders for a given strategy and organizes them into entry, exit, and hedge orders.

    :param strategy_orders: A list of strategy orders.
    :return: A dictionary containing processed trades organized by trade prefix.
    """
    processed_trades = {}

    # Convert to list if input is a dictionary
    if isinstance(strategy_orders, dict):
        orders_to_process = list(strategy_orders.values())
    elif isinstance(strategy_orders, list):
        orders_to_process = strategy_orders
    else:
        raise TypeError("strategy_orders must be either a dictionary or a list")

    for order in orders_to_process:
        if not isinstance(order, dict) or "trade_id" not in order:
            logger.warning(f"Skipping invalid order: {order}")
            continue

        try:
            trade_id = order["trade_id"]
            logger.debug(f"Processing order with trade_id: {trade_id}")

            trade_prefix = trade_id.split("_")[0]

            if trade_prefix not in processed_trades:
                processed_trades[trade_prefix] = {
                    "entry_orders": [],
                    "exit_orders": [],
                    "hedge_orders": [],
                }

            if "HO" in trade_id:
                processed_trades[trade_prefix]["hedge_orders"].append(order)
            elif "EN" in trade_id:
                processed_trades[trade_prefix]["entry_orders"].append(order)
            elif "EX" in trade_id:
                processed_trades[trade_prefix]["exit_orders"].append(order)
            else:
                logger.warning(f"Unrecognized order type in trade_id: {trade_id}")

        except Exception as e:
            logger.error(f"Error processing order: {e}")
            logger.error(traceback.format_exc())

    logger.debug(f"Processed trades: {processed_trades}")
    return processed_trades


def calculate_trade_details(trade_data, strategy_name, user, multileg=False):
    """
    Calculates the details of a trade for a given strategy and user.

    :param trade_data: A dictionary containing trade data.
    :param strategy_name: A string representing the strategy name.
    :param user: A dictionary containing user details.
    :param multileg: A boolean indicating if the trade is multileg.
    :return: A dictionary containing the calculated trade details.
    """
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
        Instrument as instru,
    )

    logger.debug(f"Calculating trade details for {strategy_name}")
    try:
        entry_orders = trade_data["entry_orders"]
        exit_orders = trade_data["exit_orders"]
        if not entry_orders or not exit_orders:
            raise ValueError(
                "Invalid trade data: entry_orders or exit_orders are empty"
            )

        hedge_orders = trade_data["hedge_orders"]

        if multileg:
            entry_price = (
                sum([float(o["avg_prc"]) for o in entry_orders]) if entry_orders else 0
            )
            exit_price = (
                sum([float(o["avg_prc"]) for o in exit_orders]) if exit_orders else 0
            )
            hedge_entry_price = (
                sum(
                    [float(o["avg_prc"]) for o in hedge_orders if "EN" in o["trade_id"]]
                )
                if hedge_orders
                else 0
            )
            hedge_exit_price = (
                sum(
                    [float(o["avg_prc"]) for o in hedge_orders if "EX" in o["trade_id"]]
                )
                if hedge_orders
                else 0
            )
        else:
            entry_price = (
                sum([float(o["avg_prc"]) for o in entry_orders]) / len(entry_orders)
                if entry_orders
                else 0
            )
            exit_price = (
                sum([float(o["avg_prc"]) for o in exit_orders]) / len(exit_orders)
                if exit_orders
                else 0
            )
            hedge_entry_price = (
                sum(
                    [float(o["avg_prc"]) for o in hedge_orders if "EN" in o["trade_id"]]
                )
                / len([o for o in hedge_orders if "EN" in o["trade_id"]])
                if hedge_orders
                else 0
            )
            hedge_exit_price = (
                sum(
                    [float(o["avg_prc"]) for o in hedge_orders if "EX" in o["trade_id"]]
                )
                / len([o for o in hedge_orders if "EX" in o["trade_id"]])
                if hedge_orders
                else 0
            )

        trade_id_prefix = entry_orders[0]["trade_id"].split("_")[0]
        exchange_token = [
            o["exchange_token"] for o in entry_orders if "MO" in o["trade_id"]
        ][0]

        trading_symbol = instru().get_trading_symbol_by_exchange_token(
            str(exchange_token)
        )
        signal = "Short" if "_SH_" in entry_orders[0]["trade_id"] else "Long"
        entry_time = min([o["time_stamp"] for o in entry_orders])
        exit_time = max([o["time_stamp"] for o in exit_orders])
        short_trade = (entry_price - exit_price) + (
            hedge_exit_price - hedge_entry_price
        )
        long_trade = (exit_price - entry_price) + (hedge_exit_price - hedge_entry_price)
        trade_points = short_trade if signal == "Short" else long_trade
        for order in entry_orders:
            if order["exchange_token"] == exchange_token:
                qty = sum(
                    [
                        o["qty"]
                        for o in entry_orders
                        if o["exchange_token"] == exchange_token
                    ]
                )
            else:
                qty = order["qty"]

        pnl = trade_points * qty

        tax = calculate_tax_from_firebasedb(entry_orders, exit_orders, hedge_orders)

        net_pnl = pnl - tax

        trade_details = {
            "trade_id": trade_id_prefix,
            "trading_symbol": trading_symbol,
            "signal": signal,
            "entry_time": datetime.strptime(entry_time, "%Y-%m-%d %H:%M"),
            "exit_time": datetime.strptime(exit_time, "%Y-%m-%d %H:%M"),
            "entry_price": float(entry_price),
            "exit_price": float(exit_price),
            "hedge_entry_price": float(hedge_entry_price),
            "hedge_exit_price": float(hedge_exit_price),
            "trade_points": float(trade_points),
            "qty": qty,
            "pnl": float(pnl),
            "tax": float(tax),
            "net_pnl": float(net_pnl),
        }
        return trade_details
    except Exception as e:
        logger.info(f"Error calculating trade details for {strategy_name}: {e}")
        return None


def fetch_and_prepare_holdings_data():
    """
    Fetches and prepares holdings data for all active users.

    For each user:
    1. Fetches the user's strategies from Firebase.
    2. Separates main and hedge orders.
    3. Calculates the average price of hedge orders.
    4. Processes main orders and calculates the margin utilized.
    5. Dumps the holdings data into the user's SQLite database.
    """
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
        Instrument as instru,
    )
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import get_order_margin

    active_users = fetch_active_users_from_firebase()

    for user in active_users:
        connections = {
            "Derivatives": get_db_connection(
                os.path.join(
                    CLIENTS_TRADE_SQL_DERIVATIVES_DB, f"{user['Tr_No']}_derivatives.db"
                )
            ),
            "Equity": get_db_connection(
                os.path.join(CLIENTS_TRADE_SQL_EQUITY_DB, f"{user['Tr_No']}_equity.db")
            ),
        }

        holdings_data = {"Equity": [], "Derivatives": []}
        decimal_columns = ["entry_price", "hedge_entry_price", "margin_utilized", "tax"]

        try:
            for trade_type in ["Derivatives", "Equity"]:
                strategies = user.get("Strategies", {}).get(trade_type, {})

                for strategy_name, strategy_detail in strategies.items():
                    if trade_type == "Equity":
                        for setup_name, setup_detail in strategy_detail.items():
                            if setup_name == "AllocationPercent":
                                continue
                            strategy_orders = setup_detail.get("TradeState", {}).get(
                                "orders", []
                            )
                            logger.debug(
                                f"Checking the holdings for : {strategy_name} for setup : {setup_name}"
                            )
                            process_holdings_orders(
                                strategy_orders,
                                strategy_name,
                                setup_name,
                                trade_type,
                                holdings_data,
                                user,
                            )
                    elif trade_type == "Derivatives":  # Derivatives
                        strategy_orders = strategy_detail.get("TradeState", {}).get(
                            "orders", []
                        )
                        logger.debug(f"Checking the holdings for : {strategy_name}")
                        process_holdings_orders(
                            strategy_orders,
                            strategy_name,
                            None,
                            trade_type,
                            holdings_data,
                            user,
                        )
                    else:
                        logger.error(f"Trade type {trade_type} not supported")

            for type_key, connection in connections.items():
                if holdings_data[type_key]:
                    holdings_df = pd.DataFrame(holdings_data[type_key])
                    dump_df_to_sqlite(
                        connection, holdings_df, "Holdings", decimal_columns
                    )

        except Exception as e:
            logger.error(f"Error processing holdings data for {user['Tr_No']}: {e}")
        finally:
            # Close all connections
            for connection in connections.values():
                if connection:
                    connection.close()


def process_holdings_orders(
    strategy_orders, strategy_name, setup_name, trade_type, holdings_data, user
):
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
        Instrument as instru,
    )
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import get_order_margin

    # write detailed documentation for this function
    """
    Processes orders for holdings and appends them to the holdings data.

    For each User:
    1. Fetches the user's strategies from Firebase.
    2. Separates main and hedge orders.
    3. Calculates the average price of hedge orders.
    4. Processes main orders and calculates the margin utilized.
    5. Dumps the holdings data into the user's SQLite database.
    """
    try:
        if isinstance(strategy_orders, dict):
            orders_to_filter = strategy_orders.values()
        elif isinstance(strategy_orders, list):
            orders_to_filter = strategy_orders
        else:
            raise TypeError("strategy_orders must be either a dictionary or a list")

        main_orders = []
        hedge_orders = []

        for order in orders_to_filter:
            if not isinstance(order, dict):
                continue
            trade_id = order.get("trade_id", "")
            if "MO" in trade_id:
                main_orders.append(order)
            elif "HO" in trade_id:
                hedge_orders.append(order)

        avg_hedge_order_price = (
            sum(float(order["avg_prc"]) for order in hedge_orders) / len(hedge_orders)
            if hedge_orders
            else 0
        )

        for order in main_orders:
            exchange = instru().get_exchange_by_exchange_token(
                str(order.get("exchange_token"))
            )
            trading_symbol = instru().get_trading_symbol_by_exchange_token(
                str(order.get("exchange_token")), exchange
            )
            # Check if avg_prc is empty or not a valid float
            if not order.get("avg_prc") or not order["avg_prc"].strip():
                logger.warning(f"Invalid avg_prc for order: {order}")
                continue  # Skip this order and move to the next one

            try:
                entry_price = float(order["avg_prc"])
            except ValueError:
                logger.error(f"Unable to convert avg_prc to float: {order['avg_prc']}")
                continue  # Skip this order and move to the next one

            setup_name = order.get("setup")
            entry_price = float(order["avg_prc"])
            qty = order.get("qty", 0)
            margin_utilized = (
                entry_price * qty
                if setup_name
                else get_order_margin([order], user["Broker"])
            )

            holding = {
                "trade_id": order.get("trade_id"),
                "signal": "Short" if "_SH_" in order.get("trade_id") else "Long",
                "trading_symbol": trading_symbol,
                "entry_time": datetime.strptime(
                    order.get("time_stamp"), "%Y-%m-%d %H:%M"
                ),
                "entry_price": entry_price,
                "qty": qty,
                "margin_utilized": margin_utilized,
                "tax": order.get("tax", 0.0),
                "hedge_entry_price": avg_hedge_order_price,
            }

            if setup_name:
                holding["setup"] = setup_name  # Assign setup_name only for Equity

            holdings_data[trade_type].append(holding)
    except Exception as e:
        logger.error(f"Error processing orders for {strategy_name}: {e}")
        logger.error(traceback.format_exc())


def process_n_log_trade():
    """
    Processes and logs trades for all active users.

    For each user:
    1. Fetches the user's strategies from Firebase.
    2. Processes orders for each strategy.
    3. Calculates trade details and appends them to the user's SQLite database.
    4. Deletes processed orders from Firebase.
    """
    active_users = fetch_active_users_from_firebase()

    for user in active_users:
        if not user.get("Active"):
            continue

        logger.debug(f"Processing trade for user: {user['Tr_No']}")

        connections = {
            "Derivatives": None,
            "Equity": None,
        }  # Initialize connections outside the loop

        try:
            for trade_type in ["Derivatives", "Equity"]:
                if connections[trade_type] is None:
                    db_path = os.path.join(
                        CLIENTS_TRADE_SQL_DERIVATIVES_DB
                        if trade_type == "Derivatives"
                        else CLIENTS_TRADE_SQL_EQUITY_DB,
                        f"{user['Tr_No']}_{trade_type.lower()}.db",
                    )
                    connections[trade_type] = get_db_connection(db_path)

                strategies = user.get("Strategies", {}).get(trade_type, {})
                for strategy_name, strategy_details in strategies.items():
                    if trade_type == "Equity":
                        for setup_name in strategy_details:
                            if setup_name == "AllocationPercent":
                                continue
                            process_strategy(
                                strategy_name,
                                strategy_details[setup_name],
                                user,
                                connections[trade_type],
                                setup_name,
                            )
                    elif trade_type == "Derivatives":
                        process_strategy(
                            strategy_name,
                            strategy_details,
                            user,
                            connections[trade_type],
                        )

        except Exception as e:
            logger.error(f"Error processing and logging trade for {user['Tr_No']}: {e}")
            logger.error(traceback.format_exc())

    # Close all connections after processing all users
    for conn in connections.values():
        if conn:
            conn.close()


def process_strategy(
    strategy_name, strategy_orders_details, user, connection, setup_name=None
):
    strategy_orders = strategy_orders_details.get("TradeState", {}).get("orders", [])
    segregated_orders = process_orders_for_strategy(strategy_orders)

    for trade_prefix, orders_group in segregated_orders.items():
        multileg = StrategyBase.load_from_db(strategy_name).ExtraInformation.MultiLeg
        trade_details = calculate_trade_details(
            orders_group, strategy_name, user, multileg
        )

        if trade_details is None or not any(trade_details.values()):
            logger.debug(f"Skipping trade {trade_prefix} due to invalid trade details.")
            continue

        df = pd.DataFrame([trade_details])
        decimal_columns = [
            "pnl",
            "tax",
            "entry_price",
            "exit_price",
            "hedge_entry_price",
            "hedge_exit_price",
            "trade_points",
            "net_pnl",
        ]

        if set(decimal_columns).issubset(df.columns):
            append_df_to_sqlite(connection, df, strategy_name, decimal_columns)
            delete_orders_from_firebase(orders_group, strategy_name, user, setup_name)
        else:
            logger.error(
                f"DataFrame for {trade_prefix} does not have the expected structure, skipping..."
            )


def update_portfolio_values():
    active_users = fetch_active_users_from_firebase()
    for user in active_users:
        logger.debug(f"User: {user['Tr_No']}")
        portfolio_values = calculate_portfolio_values(user)
        update_firebase_portfolio(user["Tr_No"], portfolio_values)


def calculate_portfolio_values(user: Dict[str, Any]) -> Dict[str, float]:
    segments = ["Equity", "Derivatives", "Debt"]
    fields = ["FreeCash", "Holdings", "AccountValue"]

    portfolio_values = {f"Portfolio_{field}": 0.0 for field in fields}

    for segment in segments:
        for field in fields:
            portfolio_values[f"Portfolio_{field}"] += safe_get(
                user, ["Accounts", segment, f"{segment}_{field}"], 0
            )

    return portfolio_values


def safe_get(dct: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    try:
        return reduce(getitem, keys, dct)
    except (KeyError, TypeError):
        return default


def update_firebase_portfolio(tr_no: str, portfolio_values: Dict[str, float]):
    update_path = "Accounts/Portfolio"
    update_fields_firebase(
        CLIENTS_USER_FB_DB_COLLECTION, tr_no, portfolio_values, update_path
    )


def main():
    """
    The main function orchestrates the end-of-day processes for trading data.

    It performs the following steps:
    1. Fetches and prepares holdings data for all active users.
    2. Processes and logs trades.
    3. Updates signal information in Firebase.
    4. Clears today's orders from Firebase.
    """
    download_firebase_json(CLIENTS_USER_FB_DB_COLLECTION, "before_eod_db_log")
    process_n_log_trade()
    sleep(5)
    fetch_and_prepare_holdings_data()
    sleep(5)
    update_signals_firebase()
    update_signal_info()
    clear_today_orders_firebase()
    sleep(5)
    update_portfolio_values()


if __name__ == "__main__":
    main()
