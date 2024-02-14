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


db_dir = os.getenv("DB_DIR")

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_active_users_from_firebase,
    fetch_list_of_strategies_from_firebase,
    fetch_users_for_strategies_from_firebase,
    CLIENTS_DB,
    STRATEGY_DB
)
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    calculate_taxes,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    append_df_to_sqlite,
    get_db_connection,
    dump_df_to_sqlite
)
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    delete_fields_firebase,
    fetch_collection_data_firebase,
    update_fields_firebase
)

# i want a function to update the dict in the firebase db with the trades of today for the user and strategy
def update_signals_firebase():
    from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
        append_df_to_sqlite,
        get_db_connection,
        read_strategy_table,
    )

    signal_db_conn = get_db_connection(os.path.join(db_dir, "signal.db"))

    strategy_user_dict = {}
    list_of_strategies = fetch_list_of_strategies_from_firebase()

    for strategy in list_of_strategies:
        users = fetch_users_for_strategies_from_firebase(strategy)
        if users:  # Check if the users list is not empty
            selected_user = users[0]  # Assuming selecting the first user meets the requirement
            strategy_user_dict[strategy] = selected_user["Tr_No"]

    for strategy_name, user in strategy_user_dict.items():
        db_path = os.path.join(db_dir, f"{user}.db")
        conn = get_db_connection(db_path)

        try:
            strategy_data = read_strategy_table(conn, strategy_name)
        except Exception as e:
            print(f"Error reading strategy table for {strategy_name} in {user}.db: {e}")
            continue

        today_signals = []  # Store signals for today's date

        for index, row in strategy_data.iterrows():
            if row is None or 'exit_time' not in row or pd.isnull(row['exit_time']):
                continue  # Skip if row is empty or exit_time is missing or null
            
            try:
                datetime_object = datetime.strptime(row["exit_time"], "%Y-%m-%d %H:%M:%S")
            except ValueError:  # Handles incorrect date format or missing exit_time
                continue

            if datetime_object.date() == datetime.today().date():
                signal_data = {
                    "trade_id": row["trade_id"],
                    "trading_symbol": row["trading_symbol"],
                    "signal": row["signal"],
                    "entry_time": row["entry_time"],
                    "exit_time": row["exit_time"],
                    "entry_price": row["entry_price"],
                    "exit_price": row.get("exit_price", 0),  # Use .get() for optional columns
                    "hedge_points": float(row.get("hedge_exit_price", 0)) - float(row.get("hedge_entry_price", 0)),
                    "trade_points": row.get("trade_points", 0),
                }
                today_signals.append(signal_data)

        # Log each trade for today
        if today_signals:
            df = pd.DataFrame(today_signals)
            decimal_columns = ["entry_price", "exit_price", "hedge_points", "trade_points"]
            append_df_to_sqlite(signal_db_conn, df, strategy_name, decimal_columns)  # Assuming "signals" is your table name

        conn.close()

    signal_db_conn.close()
    return strategy_user_dict

    # fetch the users for the strategy

def clear_today_orders_firebase():
    active_strategies = fetch_list_of_strategies_from_firebase()
    for strategy in active_strategies:
        delete_fields_firebase(STRATEGY_DB, strategy, "TodayOrders")

def convert_trade_state_to_list(orders_firebase,user_TR_No):
    strategies = orders_firebase.get("Strategies", {})
    for strategy_name, strategy_details in strategies.items():
        orders = strategy_details.get("TradeState", {}).get("orders", [])
        if isinstance(orders, dict):
            orders = list(orders.values())
            update_path = f"Strategies/{strategy_name}/TradeState/"
            update_fields_firebase(CLIENTS_DB, user_TR_No, {"orders": orders}, update_path)

def delete_orders_from_firebase(orders, strategy_name, user):
    entry_orders = orders["entry_orders"]
    exit_orders = orders["exit_orders"]
    hedge_orders = orders["hedge_orders"]

    if not entry_orders or not exit_orders:
        print("Entry or exit orders missing, skipping deletion.")
        return

    combined_orders = entry_orders + exit_orders + hedge_orders

    orders_firebase = fetch_collection_data_firebase(CLIENTS_DB, user["Tr_No"])

    if "Strategies" in orders_firebase and strategy_name in orders_firebase["Strategies"] \
            and "TradeState" in orders_firebase["Strategies"][strategy_name]:
        strategy_orders = orders_firebase["Strategies"][strategy_name]["TradeState"]["orders"]
    else:
        print(f"Strategy {strategy_name} not found or missing TradeState.")
        return

    order_ids_to_delete = {order["order_id"] for order in combined_orders}

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
        print("Unexpected data structure for strategy_orders.")
        return

    if not keys_to_delete:
        print("No matching orders found for deletion.")
        return

    for key in keys_to_delete:
        try:
            if isinstance(strategy_orders, list):
                delete_path = f"Strategies/{strategy_name}/TradeState/orders/{key}"
            else:
                delete_path = f"Strategies/{strategy_name}/TradeState/orders/{key}"
            delete_fields_firebase(CLIENTS_DB, user["Tr_No"], delete_path)
        except Exception as e:
            print(f"Error deleting order with key/index {key}: {e}")
    pending_orders_firebase = fetch_collection_data_firebase(CLIENTS_DB, user["Tr_No"])
    convert_trade_state_to_list(pending_orders_firebase,user["Tr_No"])

    print("Deletion process completed.")

def seggregate_orders_by_type(orders):
    entry_orders = [o for o in orders if "EN" in o["trade_id"] and "HO" not in o["trade_id"]]
    exit_orders = [o for o in orders if "EX" in o["trade_id"] and "HO" not in o["trade_id"]]
    hedge_orders = [o for o in orders if "HO" in o["trade_id"]]
    return entry_orders, exit_orders, hedge_orders

def process_orders_for_strategy(strategy_orders):
    processed_trades = {}
    logger.debug(f"strategy_order{strategy_orders}")
    for order in strategy_orders:
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
        elif "HO" in order["trade_id"] :
            processed_trades[trade_prefix]["hedge_orders"].append(order)
    return processed_trades

def calculate_trade_details(trade_data, strategy_name, user):
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
        Instrument as instru,
    )
    logger.debug(f"Calculating trade details for {strategy_name}")
    entry_orders = trade_data["entry_orders"]
    exit_orders = trade_data["exit_orders"]
    if not entry_orders or not exit_orders:
        return
    hedge_orders = trade_data["hedge_orders"]
    entry_price = sum([float(o["avg_prc"]) for o in entry_orders]) / len(entry_orders) if entry_orders else 0
    exit_price = sum([float(o["avg_prc"]) for o in exit_orders]) / len(exit_orders) if exit_orders else 0
    if hedge_orders:
        hedge_entry_price = sum([float(o["avg_prc"]) for o in hedge_orders if "EN" in o["trade_id"]]) / len([o for o in hedge_orders if "EN" in o["trade_id"]]) if hedge_orders else 0
        hedge_exit_price = sum([float(o["avg_prc"]) for o in hedge_orders if "EX" in o["trade_id"]]) / len([o for o in hedge_orders if "EX" in o["trade_id"]]) if hedge_orders else 0  
    else:
        hedge_entry_price = 0
        hedge_exit_price = 0
    trade_id_prefix = entry_orders[0]["trade_id"].split("_")[0]
    exchange_token = [o["exchange_token"] for o in entry_orders if "MO" in o["trade_id"]][0]

    trading_symbol = instru().get_trading_symbol_by_exchange_token(str(exchange_token))
    signal = "Short" if "_SH_" in entry_orders[0]["trade_id"] else "Long"
    entry_time = min([o["time_stamp"] for o in entry_orders])
    exit_time = max([o["time_stamp"] for o in exit_orders])
    short_trade = (entry_price - exit_price) + (hedge_exit_price - hedge_entry_price)
    long_trade = (exit_price - entry_price) + (hedge_exit_price - hedge_entry_price)
    trade_points = short_trade if signal == "Short" else long_trade
    for order in entry_orders:
        if order["exchange_token"] == exchange_token:
            qty = sum([o["qty"] for o in entry_orders if o["exchange_token"] == exchange_token])
        else:
            qty = order["qty"]

    pnl = trade_points * qty

    tax = calculate_taxes(entry_orders,exit_orders,hedge_orders,user["Broker"]["BrokerName"])

    net_pnl = pnl - tax

    trade_details = {
                    "trade_id": trade_id_prefix,
                    "trading_symbol": trading_symbol,
                    "signal": signal,
                    "entry_time": datetime.strptime(entry_time, "%Y-%m-%d %H:%M"),
                    "exit_time": datetime.strptime(exit_time, "%Y-%m-%d %H:%M"),
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "hedge_entry_price": hedge_entry_price,
                    "hedge_exit_price": hedge_exit_price,
                    "trade_points": trade_points,
                    "qty": qty,
                    "pnl": pnl,
                    "tax": tax,
                    "net_pnl": net_pnl,
    }
    return trade_details

def fetch_and_prepare_holdings_data():
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
        Instrument as instru,
    )
    active_users = fetch_active_users_from_firebase()
    
    for user in active_users:
        db_path = os.path.join(db_dir, f"{user['Tr_No']}.db")
        conn = get_db_connection(db_path)
        all_holdings = []  # Reset for each user
        strategies = user.get("Strategies", {})

        for strategy_name, strategy_details in strategies.items():
            strategy_orders = strategy_details.get("TradeState", {}).get("orders", [])
            if isinstance(strategy_orders, dict):  # Convert dict to list if needed
                strategy_orders = list(strategy_orders.values())

            logger.debug(f"name : {strategy_name}")
            logger.debug(f"strategy_orders {strategy_orders}")

            #continue if any object in the list is none

            # Separate main and hedge orders
            main_orders = [order for order in strategy_orders if order is not None and "MO" in order.get("trade_id", "")]
            hedge_orders = [order for order in strategy_orders if order is not None and "HO" in order.get("trade_id", "")]


            # Calculate the average price of hedge orders
            if hedge_orders:
                avg_hedge_order_price = sum(float(order["avg_prc"]) for order in hedge_orders) / len(hedge_orders)
            else:
                avg_hedge_order_price = 0  # Default to 0 if no hedge orders
            
            # Process main orders
            for order in main_orders:
                trading_symbol = instru().get_trading_symbol_by_exchange_token(str(order.get("exchange_token")))
                entry_price = float(order["avg_prc"])
                qty = order.get("qty", 0)
                margin_utilized = entry_price * qty
                
                holding = {
                    "trade_id": order.get("trade_id"),
                    "signal": "Short" if "_SH_" in order.get("trade_id") else "Long",
                    "trading_symbol": trading_symbol,
                    "entry_time": datetime.strptime(order.get("time_stamp"), "%Y-%m-%d %H:%M"),
                    "entry_price": entry_price,
                    "qty": qty,
                    "margin_utilized": margin_utilized,
                    "tax": 0.0,
                    "hedge_entry_price": avg_hedge_order_price
                }
                
                all_holdings.append(holding)

        # Dump the holdings for the current user into the database
        if all_holdings:
            holdings_df = pd.DataFrame(all_holdings)
            decimal_columns = ["entry_price", "hedge_entry_price", "margin_utilized", "tax"]
            dump_df_to_sqlite(conn, holdings_df, "Holdings", decimal_columns)

        # Optionally close the DB connection if it's not used later
        conn.close()

def process_n_log_trade():
    active_users = fetch_active_users_from_firebase()

    for user in active_users:
        print(f"Processing trade for user: {user['Tr_No']}")
        db_path = os.path.join(db_dir, f"{user['Tr_No']}.db")  # Ensure db_dir is defined
        conn = get_db_connection(db_path)
        if not user.get("Active"):
            continue

        strategies = user.get("Strategies", {})
        for strategy_name, strategy_details in strategies.items():
            strategy_orders = strategy_details.get("TradeState", {}).get("orders", [])
            if not strategy_orders:
                print(f"No orders found for strategy: {strategy_name}")
                continue

            segregated_orders = process_orders_for_strategy(strategy_orders)
            for trade_prefix, orders_group in segregated_orders.items():
                trade_details = calculate_trade_details(orders_group, strategy_name, user)
                # Check if trade_details is None or empty before proceeding
                if trade_details is None or not any(trade_details.values()):
                    print(f"Skipping trade {trade_prefix} due to invalid trade details.")
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
                    print(f"DataFrame for {trade_prefix} does not have the expected structure, skipping...")
                    continue  # Skip appending this DataFrame to the database

                append_df_to_sqlite(conn, df, strategy_name, decimal_columns)
                # Delete orders from Firebase
                delete_orders_from_firebase(orders_group, strategy_name, user)
                
        conn.close()

def main():
    process_n_log_trade()
    fetch_and_prepare_holdings_data()
    update_signals_firebase()
    clear_today_orders_firebase()

if __name__ == "__main__":
    main()