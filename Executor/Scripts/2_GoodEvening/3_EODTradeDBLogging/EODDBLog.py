import os
import sqlite3
import sys
from datetime import datetime
from time import sleep

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
STRATEGY_FB_DB = os.getenv("FIREBASE_STRATEGY_COLLECTION")

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
    download_json,
)

from Executor.Strategies.StrategiesUtil import StrategyBase


def update_signal_info():
    """
    Updates the signal information for all active strategies by fetching data from Firebase
    and appending it to the SQLite database.
    """
    active_strategies = fetch_list_of_strategies_from_firebase()
    signal_info_db_conn = get_db_connection(
        os.path.join(CLIENTS_TRADE_SQL_DB, "signal_info.db")
    )

    for strategy_name in active_strategies:
        logger.debug(f"Updating signal info for {strategy_name}")
        try:
            strategy_info = fetch_collection_data_firebase(
                STRATEGY_FB_DB, strategy_name
            )
            today_orders = strategy_info.get("TodayOrders", {})
            for order, values in today_orders.items():
                if values.get("StrategyInfo"):
                    strategy_info_dict = values.get("StrategyInfo")
                    df = pd.DataFrame([strategy_info_dict])
                    # Move trade_id column to the first column
                    df = df[
                        ["trade_id"] + [col for col in df.columns if col != "trade_id"]
                    ]
                    append_df_to_sqlite(signal_info_db_conn, df, strategy_name, [])
        except Exception as e:
            logger.error(f"Error updating signal info for {strategy_name}: {e}")
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

    signal_db_conn = get_db_connection(os.path.join(CLIENTS_TRADE_SQL_DB, "signal.db"))

    strategy_user_dict = {}
    list_of_strategies = fetch_list_of_strategies_from_firebase()

    for strategy in list_of_strategies:
        users = fetch_users_for_strategies_from_firebase(strategy)
        if len(users) > 0:  # Check if the users list is not empty
            selected_user = users[
                0
            ]  # Assuming selecting the first user meets the requirement
            strategy_user_dict[strategy] = selected_user["Tr_No"]

    for strategy_name, user in strategy_user_dict.items():
        db_path = os.path.join(CLIENTS_TRADE_SQL_DB, f"{user}.db")
        conn = get_db_connection(db_path)

        try:
            strategy_data = read_strategy_table(conn, strategy_name)
        except Exception as e:
            logger.error(
                f"Error reading strategy table for {strategy_name} in {user}.db: {e}"
            )
            continue

        today_signals = []  # Store signals for today's date

        for index, row in strategy_data.iterrows():
            if row is None or "exit_time" not in row or pd.isnull(row["exit_time"]):
                continue  # Skip if row is empty or exit_time is missing or null

            try:
                datetime_object = datetime.strptime(
                    row["exit_time"], "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:  # Handles incorrect date format or missing exit_time
                logger.error(
                    f"Error processing signal data for {strategy_name} in {user}.db"
                )
                continue

            if datetime_object.date() == datetime.today().date():
                signal_data = {
                    "trade_id": row["trade_id"],
                    "trading_symbol": row["trading_symbol"],
                    "signal": row["signal"],
                    "entry_time": row["entry_time"],
                    "exit_time": row["exit_time"],
                    "entry_price": row["entry_price"],
                    "exit_price": row.get(
                        "exit_price", 0
                    ),  # Use .get() for optional columns
                    "hedge_points": float(row.get("hedge_exit_price", 0))
                    - float(row.get("hedge_entry_price", 0)),
                    "trade_points": row.get("trade_points", 0),
                }
                today_signals.append(signal_data)

        # Log each trade for today
        if today_signals:
            df = pd.DataFrame(today_signals)
            decimal_columns = [
                "entry_price",
                "exit_price",
                "hedge_points",
                "trade_points",
            ]
            append_df_to_sqlite(
                signal_db_conn, df, strategy_name, decimal_columns
            )  # Assuming "signals" is your table name

        conn.close()

    signal_db_conn.close()
    return strategy_user_dict

    # fetch the users for the strategy


def clear_today_orders_firebase():
    """
    Clears today's orders from Firebase for all active strategies.
    """
    try:
        active_strategies = fetch_list_of_strategies_from_firebase()
        for strategy in active_strategies:
            delete_fields_firebase(STRATEGY_FB_DB, strategy, "TodayOrders")
    except Exception as e:
        logger.error(f"Error occurred while clearing today's orders from Firebase: {e}")


def convert_trade_state_to_list(orders_firebase, user_TR_No):
    """
    Converts the trade state of orders from a dictionary to a list format in Firebase.

    :param orders_firebase: A dictionary containing orders from Firebase.
    :param user_TR_No: A string representing the user's trade number.
    """
    strategies = orders_firebase.get("Strategies", {})
    for strategy_name, strategy_details in strategies.items():
        orders = strategy_details.get("TradeState", {}).get("orders", [])
        if isinstance(orders, dict):
            orders = list(orders.values())
            update_path = f"Strategies/{strategy_name}/TradeState/"
            try:
                update_fields_firebase(
                    CLIENTS_USER_FB_DB, user_TR_No, {"orders": orders}, update_path
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


def delete_orders_from_firebase(orders, strategy_name, user):
    """
    Deletes orders from Firebase for a given strategy and user.

    :param orders: A dictionary containing orders to delete.
    :param strategy_name: A string representing the strategy name.
    :param user: A dictionary containing user details.
    """
    try:
        entry_orders = orders["entry_orders"]
        exit_orders = orders["exit_orders"]
        hedge_orders = orders["hedge_orders"]
    except KeyError as e:
        logger.error(
            f"Error fetching orders to delete the orders for {strategy_name}: {e}"
        )
        return
    except Exception as e:
        logger.error(
            f"Error occurred while fetching orders to delete the orders for {strategy_name}: {e}"
        )
        return

    if not entry_orders or not exit_orders:
        logger.info("Entry or exit orders missing, skipping deletion.")
        return

    combined_orders = entry_orders + exit_orders + hedge_orders

    orders_firebase = fetch_collection_data_firebase(CLIENTS_USER_FB_DB, user["Tr_No"])

    if (
        "Strategies" in orders_firebase
        and strategy_name in orders_firebase["Strategies"]
        and "TradeState" in orders_firebase["Strategies"][strategy_name]
    ):
        strategy_orders = orders_firebase["Strategies"][strategy_name]["TradeState"][
            "orders"
        ]
    else:
        logger.info(f"Strategy {strategy_name} not found or missing TradeState.")
        return

    order_ids_to_delete = {order["order_id"] for order in combined_orders}
    try:
        keys_to_delete = get_keys_to_delete(strategy_orders, order_ids_to_delete)
    except Exception as e:
        logger.error(f"Error getting keys to delete for {strategy_name}: {e}")
        return

    if not keys_to_delete:
        logger.info("No matching orders found for deletion.")
        return

    for key in keys_to_delete:
        try:
            delete_path = f"Strategies/{strategy_name}/TradeState/orders/{key}"
            delete_fields_firebase(CLIENTS_USER_FB_DB, user["Tr_No"], delete_path)
        except Exception as e:
            logger.info(f"Error deleting order with key/index {key}: {e}")

    try:
        pending_orders_firebase = fetch_collection_data_firebase(
            CLIENTS_USER_FB_DB, user["Tr_No"]
        )
    except Exception as e:
        logger.error(
            f"Error fetching pending orders from Firebase for {strategy_name}: {e}"
        )
        return
    convert_trade_state_to_list(pending_orders_firebase, user["Tr_No"])

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
    for order in strategy_orders:
        try:
            if order is None:
                continue
            logger.debug(f"order[trade_id] : {order['trade_id']}")
            trade_prefix = order["trade_id"].split("_")[0]
            if trade_prefix not in processed_trades:
                processed_trades[trade_prefix] = {
                    "entry_orders": [],
                    "exit_orders": [],
                    "hedge_orders": [],
                }
            if "EN" in order["trade_id"] and "HO" not in order["trade_id"]:
                processed_trades[trade_prefix]["entry_orders"].append(order)
            elif "EX" in order["trade_id"] and "HO" not in order["trade_id"]:
                processed_trades[trade_prefix]["exit_orders"].append(order)
            elif "HO" in order["trade_id"]:
                processed_trades[trade_prefix]["hedge_orders"].append(order)
        except Exception as e:
            logger.error(f"Error processing order: {e}")
            continue
    logger.debug(f"processed_trades: {processed_trades}")
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
            raise ValueError("Invalid trade data: entry_orders or exit_orders is empty")

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
        logger.error(f"Error calculating trade details for {strategy_name}: {e}")
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
        db_path = os.path.join(CLIENTS_TRADE_SQL_DB, f"{user['Tr_No']}.db")
        conn = get_db_connection(db_path)
        all_holdings = []  # Reset for each user
        strategies = user.get("Strategies", {})
        try:
            for strategy_name, strategy_details in strategies.items():
                logger.debug(f"Checking the holdings for : {strategy_name}")
                strategy_orders = strategy_details.get("TradeState", {}).get(
                    "orders", []
                )
                if isinstance(strategy_orders, dict):  # Convert dict to list if needed
                    strategy_orders = list(strategy_orders.values())

                # continue if any object in the list is none

                # Separate main and hedge orders
                main_orders = [
                    order
                    for order in strategy_orders
                    if order is not None and "MO" in order.get("trade_id", "")
                ]
                hedge_orders = [
                    order
                    for order in strategy_orders
                    if order is not None and "HO" in order.get("trade_id", "")
                ]

                # Calculate the average price of hedge orders
                if hedge_orders:
                    avg_hedge_order_price = sum(
                        float(order["avg_prc"]) for order in hedge_orders
                    ) / len(hedge_orders)
                else:
                    avg_hedge_order_price = 0  # Default to 0 if no hedge orders

                # Process main orders
                for order in main_orders:
                    exchange = instru().get_exchange_by_exchange_token(
                        str(order.get("exchange_token"))
                    )
                    trading_symbol = instru().get_trading_symbol_by_exchange_token(
                        str(order.get("exchange_token")), exchange
                    )

                    entry_price = float(order["avg_prc"])
                    qty = order.get("qty", 0)

                    # Initialize margin_utilized to 0
                    option_margin_utilized = 0

                    # Check if the trade ID starts with "PS"
                    if order.get("trade_id", "").startswith("PS"):
                        # Calculate margin utilized based on entry price and quantity
                        option_margin_utilized = entry_price * qty
                        margin_utilized = (
                            option_margin_utilized  # For PS, use this directly
                        )
                    else:
                        # For other trade IDs, fetch the order margin and adjust by subtracting the PS margin
                        margin_utilized = (
                            get_order_margin([order], user["Broker"])
                            - option_margin_utilized
                        )

                    holding = {
                        "trade_id": order.get("trade_id"),
                        "signal": (
                            "Short" if "_SH_" in order.get("trade_id") else "Long"
                        ),
                        "trading_symbol": trading_symbol,
                        "entry_time": datetime.strptime(
                            order.get("time_stamp"), "%Y-%m-%d %H:%M"
                        ),
                        "entry_price": entry_price,
                        "qty": qty,
                        "margin_utilized": margin_utilized,
                        "tax": 0.0,
                        "hedge_entry_price": avg_hedge_order_price,
                    }

                    all_holdings.append(holding)

            # Dump the holdings for the current user into the database
            if all_holdings:
                holdings_df = pd.DataFrame(all_holdings)
                decimal_columns = [
                    "entry_price",
                    "hedge_entry_price",
                    "margin_utilized",
                    "tax",
                ]
                dump_df_to_sqlite(conn, holdings_df, "Holdings", decimal_columns)

            # Optionally close the DB connection if it's not used later
            conn.close()
        except Exception as e:
            logger.error(f"Error processing holdings data for {user['Tr_No']}: {e}")
            continue


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
        logger.debug(f"Processing trade for user: {user['Tr_No']}")
        db_path = os.path.join(
            CLIENTS_TRADE_SQL_DB, f"{user['Tr_No']}.db"
        )  # Ensure USR_TRADELOG_DB_FOLDER is defined
        conn = get_db_connection(db_path)
        if not user.get("Active"):
            continue

        try:
            strategies = user.get("Strategies", {})
            for strategy_name, strategy_details in strategies.items():
                strategy_orders = strategy_details.get("TradeState", {}).get(
                    "orders", []
                )
                if not strategy_orders:
                    logger.debug(f"No orders found for strategy: {strategy_name}")
                    continue

                segregated_orders = process_orders_for_strategy(strategy_orders)
                for trade_prefix, orders_group in segregated_orders.items():
                    multileg = StrategyBase.load_from_db(
                        strategy_name
                    ).ExtraInformation.MultiLeg
                    trade_details = calculate_trade_details(
                        orders_group, strategy_name, user, multileg
                    )
                    # Check if trade_details is None or empty before proceeding
                    if trade_details is None or not any(trade_details.values()):
                        logger.debug(
                            f"Skipping trade {trade_prefix} due to invalid trade details."
                        )
                        continue  # Skip this trade if trade_details is invalid

                    # Proceed with valid trade_details
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

                    # Check if DataFrame is properly formatted with expected columns
                    if not set(decimal_columns).issubset(df.columns):
                        logger.error(
                            f"DataFrame for {trade_prefix} does not have the expected structure, skipping..."
                        )
                        continue  # Skip appending this DataFrame to the database

                    append_df_to_sqlite(conn, df, strategy_name, decimal_columns)
                    # Delete orders from Firebase
                    delete_orders_from_firebase(orders_group, strategy_name, user)
            conn.close()
        except Exception as e:
            logger.error(f"Error processing and logging trade for {user['Tr_No']}: {e}")
            continue


def main():
    """
    The main function orchestrates the end-of-day processes for trading data.

    It performs the following steps:
    1. Fetches and prepares holdings data for all active users.
    2. Processes and logs trades.
    3. Updates signal information in Firebase.
    4. Clears today's orders from Firebase.
    """
    download_json(CLIENTS_USER_FB_DB, "before_eod_db_log")
    process_n_log_trade()
    sleep(5)
    fetch_and_prepare_holdings_data()
    sleep(5)
    update_signals_firebase()
    update_signal_info()
    clear_today_orders_firebase()
    sleep(5)


if __name__ == "__main__":
    main()
