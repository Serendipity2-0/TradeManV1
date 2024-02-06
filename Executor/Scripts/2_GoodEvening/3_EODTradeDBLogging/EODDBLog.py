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
)
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    calculate_taxes,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    append_df_to_sqlite,
    get_db_connection,
    read_strategy_table,
)
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    delete_fields_firebase,
    fetch_collection_data_firebase
)

def process_holdings(corresponding_exit_trade_id,corresponding_sl_trade_id,orders,entry_orders,hedge_orders,strategy_name,holdings,order,signal):
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
        Instrument as instru,
    )
    # Check if holding or completed trade
    is_holding = not any(
        corresponding_exit_trade_id == exit_order["trade_id"]
        for exit_order in orders
    )
    is_holding = is_holding and not any(
        corresponding_sl_trade_id == exit_order["trade_id"]
        for exit_order in orders
    )

    if is_holding:
        entry_price = sum([float(o["avg_prc"]) for o in entry_orders]) / len(
            entry_orders
        )
        hedge_entry_price = (
            sum(
                [
                    float(o["avg_prc"])
                    for o in hedge_orders
                    if "EN" in o["trade_id"]
                ]
            )
            / len([o for o in hedge_orders if "EN" in o["trade_id"]])
            if hedge_orders
            else 0.0
        )
        # TODO: Process differently for FUT orders
        margin_utilized = entry_price * order["qty"]

        holdings[strategy_name] = {
            "trade_id": order["trade_id"],
            "trading_symbol": instru().get_trading_symbol_by_exchange_token(
                str(order["exchange_token"])
            ),
            "signal": signal,
            "entry_time": datetime.strptime(
                order["time_stamp"], "%Y-%m-%d %H:%M"
            ),
            "entry_price": entry_price,
            "hedge_entry_price": hedge_entry_price,
            "qty": order["qty"],
            "margin_utilized": margin_utilized,
        }

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

# update_signals_firebase()
# TODO: Update holdings table in user db
# TODO: function to update dtd table in user
# TODO: function to update signal db using primary account db values

def delete_orders_from_firebase(orders, strategy_name, user):
    orders_firebase = fetch_collection_data_firebase("new_clients", user["Tr_No"])
    
    if "Strategies" in orders_firebase and strategy_name in orders_firebase["Strategies"]:
        if "TradeState" in orders_firebase["Strategies"][strategy_name]:
            strategy_orders = orders_firebase["Strategies"][strategy_name]["TradeState"]["orders"]
        else:
            logger.error(f"TradeState not found for strategy {strategy_name}.")
            return
    else:
        logger.error(f"Strategy {strategy_name} not found.")
        return

    # Debug: Print the total number of orders fetched from Firebase for the strategy
    print(f"Total orders fetched for {strategy_name}: {len(strategy_orders)}")

    # Right before identifying indices to delete, print all fetched order IDs
    # print("Fetched Order IDs:", [o.get("order_id") for o in strategy_orders if o is not None])


    order_ids_to_delete = {order["order_id"] for order in orders}

    # Debug: Print the order IDs that are intended to be deleted
    print(f"Order IDs to delete: {order_ids_to_delete}")

    indices_to_delete = []
    for index, value in enumerate(strategy_orders):
        if isinstance(value, dict):
            print(f"Order at Index {index}: ID {value.get('order_id', 'ID not found')}, intended for deletion: {'Yes' if value.get('order_id') in order_ids_to_delete else 'No'}")
        else:
            print(f"Order at Index {index}: Encountered unexpected data type (not a dict), Value: {value}")
        if value is not None and "order_id" in value and value["order_id"] in order_ids_to_delete:
            indices_to_delete.append(index)
            # Debug: Print each order found for deletion
            print(f"Marked for deletion: Index {index}, Order ID {value['order_id']}")

    # Debug: Print indices that are marked for deletion
    print(f"Indices marked for deletion: {indices_to_delete}")

    for index in sorted(indices_to_delete, reverse=True):
        try:
            # Debug: Log the attempt to delete specific index and order ID
            print(f"Attempting to delete at index: {index}, Order ID: {strategy_orders[index]['order_id']}")
            delete_fields_firebase("new_clients", user["Tr_No"], f"Strategies/{strategy_name}/TradeState/orders/{index}")
            # Debug: Log successful deletion
            print(f"Successfully deleted order at index: {index}")
        except Exception as e:
            logger.error(f"Error deleting order at index {index}: {e}")
            # Debug: Log failure to delete
            print(f"Failed to delete order at index: {index}, Error: {e}")

def seggregate_orders_by_type(orders):
    entry_orders = [o for o in orders if "EN" in o["trade_id"] and "HO" not in o["trade_id"]]
    exit_orders = [o for o in orders if "EX" in o["trade_id"] and "HO" not in o["trade_id"]]
    hedge_orders = [o for o in orders if "HO" in o["trade_id"]]
    return entry_orders, exit_orders, hedge_orders

def process_orders_for_strategy(strategy_orders):
    processed_trades = {}
    for order in strategy_orders:
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

    tax = calculate_taxes(
                    user["Broker"]["BrokerName"],
                    signal,
                    qty,
                    entry_price,
                    exit_price,
                    len(exit_orders),
                )
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
    delete_orders_from_firebase(entry_orders, strategy_name, user)
    print("Done deleting entry orders")
    sleep(3)
    delete_orders_from_firebase(exit_orders, strategy_name, user)
    print("Done deleting exit orders")
    sleep(3)
    delete_orders_from_firebase(hedge_orders, strategy_name, user)
    print("Done deleting hedge orders")
    
    return trade_details

def fetch_and_prepare_holdings_data(user):
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
        Instrument as instru,
    )
    holdings_data = []
    strategies = user.get("Strategies", {})
    
    # Iterate through each strategy
    for strategy_name, strategy_details in strategies.items():
        # Check if there are orders in the TradeState
        strategy_orders = strategy_details.get("TradeState", {}).get("orders", [])
        if strategy_orders:
            # If orders are present, consider it as a holding and process
            for order in strategy_orders:
                entry_orders = [o for o in order if "EN" in o["trade_id"] and "HO" not in o["trade_id"]]
                hedge_orders = [o for o in order if "HO" in o["trade_id"]]
                trading_symbol = instru().get_trading_symbol_by_exchange_token(str(order.get("exchange_token")))
                entry_price = sum([float(o["avg_prc"]) for o in entry_orders]) / len(entry_orders) if entry_orders else 0
                hedge_entry_price = sum([float(o["avg_prc"]) for o in hedge_orders if "EN" in o["trade_id"]]) / len([o for o in hedge_orders if "EN" in o["trade_id"]]) if hedge_orders else 0

            holding = {
                "trade_id": order.get("trade_id"),
                "signal": "Short" if "_SH_" in order.get("trade_id") else "Long",
                "trading_symbol": trading_symbol,
                "entry_time": datetime.strptime(order.get("time_stamp"), "%Y-%m-%d %H:%M"),
                "entry_price": entry_price,
                "hedge_entry_price": hedge_entry_price,
                "qty": order.get("qty", 0),
                "margin_utilized": entry_price * order.get("qty", 0),
                "tax": 0.0
            }
            holdings_data.append(holding)
    
    return holdings_data

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
                # Append trade details to the database
                # print(f"Processed trade details for {trade_prefix}: {trade_details}")
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
                # append_df_to_sqlite(conn, df, strategy_name, decimal_columns)
                holdings_data = fetch_and_prepare_holdings_data(user)
                if holdings_data:
                    holdings_df = pd.DataFrame(holdings_data)
                    print(holdings_df)
                    # append_df_to_sqlite(conn, holdings_df, "Holdings", decimal_columns)
        conn.close()

process_n_log_trade()

