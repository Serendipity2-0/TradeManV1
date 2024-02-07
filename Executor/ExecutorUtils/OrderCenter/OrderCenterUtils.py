import datetime as dt
import math
import os
import sys
import time
from loguru import logger
from dotenv import load_dotenv

DIR = os.getcwd()
sys.path.append(DIR)

load_dotenv(os.path.join(DIR, "trademan.env"))
db_dir = os.getenv("DB_DIR")

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    push_orders_firebase,
)
from Executor.ExecutorUtils.InstrumentCenter.FNOInfoBase import FNOInfo
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_user_credentials_firebase,
    place_order_for_brokers,
    modify_order_for_brokers,
    fetch_strategy_details_for_user,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    fetch_qty_for_holdings_sqldb,
)

def calculate_qty_for_strategies(capital, risk, avg_sl_points, lot_size):
    if avg_sl_points is not None:
        raw_quantity = ((risk / 100) * capital) / avg_sl_points
        # Calculate the number of lots
        number_of_lots = raw_quantity / lot_size
        #ceil the number of lots
        number_of_lots = math.ceil(number_of_lots)

        # Calculate the quantity as a multiple of lot_size
        quantity = int(number_of_lots * lot_size)
    else:
        # For other strategies, risk values represent the capital allocated
        lots = capital / (risk / 100)
        quantity = math.ceil(lots) * lot_size
    return quantity


def place_order_for_strategy(strategy_users, order_details, order_qty_mode:str=None):
    for user in strategy_users:
        all_order_statuses = []  # To store the status of all orders
        #TODO: for holdings fetch the qty from db
        for order in order_details:
            order_with_user_and_broker = order.copy()
            if order_qty_mode == "Sweep":
                order_with_user_and_broker.update(
                    {
                        "broker": user["Broker"]["BrokerName"],
                        "username": user["Broker"]["BrokerUsername"],
                    }
                )
            elif order_qty_mode == "Holdings":
                logger.debug(f"Fetching qty for trade_id {order.get('trade_id')}")
                qty = fetch_qty_for_holdings_sqldb(user['Tr_No'], order.get("trade_id"))
                logger.debug(f"Qty for trade_id {order.get('trade_id')} is {qty}")
                order_with_user_and_broker.update(
                    {
                        "broker": user["Broker"]["BrokerName"],
                        "username": user["Broker"]["BrokerUsername"],
                        "qty": int(qty),
                    }
                )
            else:
                order_with_user_and_broker.update(
                    {
                        "broker": user["Broker"]["BrokerName"],
                        "username": user["Broker"]["BrokerUsername"],
                        "qty": user["Strategies"][order.get("strategy")]["Qty"],
                    }
                )

            max_qty = FNOInfo().get_max_order_qty_by_base_symbol(
                order_with_user_and_broker.get("base_symbol")
            )
            user_credentials = fetch_user_credentials_firebase(
                user["Broker"]["BrokerUsername"]
            )

            order_qty = order_with_user_and_broker["qty"]

            # Split and place orders if necessary
            while order_qty > 0:
                current_qty = min(order_qty, max_qty)
                order_to_place = order_with_user_and_broker.copy()
                order_to_place["qty"] = current_qty

                order_status = place_order_for_brokers(order_to_place, user_credentials)
                all_order_statuses.append(order_status)

                if "Hedge" in order_to_place.get("order_mode", ""):
                    time.sleep(1)
                order_qty -= current_qty

        # Update Firebase with order status
        update_path = f"Strategies/{order.get('strategy')}/TradeState/orders"
        for data in all_order_statuses:
            push_orders_firebase("new_clients", user["Tr_No"], data, update_path)
        # update_fields_firebase('new_clients', user['Tr_No'], all_order_statuses, update_path)

        # Send notification if any orders failed # TODO: check for exact fail msgs and send notifications accordingly
        for status in all_order_statuses:
            if status.get("message", "") == "Order placement failed":
                discord_bot(
                    f"Order failed for user {user['Broker']['BrokerUsername']} in strategy {order.get('strategy')}",
                    order.get("strategy"),
                )
    return all_order_statuses


def modify_orders_for_strategy(strategy_users, order_details):
    # Update the order details with the username and broker details for each order and pass it to modify_order_for_brokers
    for users in strategy_users:
        for order in order_details:
            user_credentials = fetch_user_credentials_firebase(
                users["Broker"]["BrokerUsername"]
            )
            order_with_user_and_broker = order.copy()
            order_with_user_and_broker.update(
                {
                    "broker": users["Broker"]["BrokerName"],
                    "username": users["Broker"]["BrokerUsername"],
                }
            )
            modify_order_for_brokers(order_with_user_and_broker, user_credentials)
    pass


def retrieve_order_id(account_name, strategy, exchange_token: int):
    # retrieve the order id from firebase for the given account name, strategy name and trade id
    order_ids = {}
    user_details = fetch_strategy_details_for_user(account_name)
    for strategy_name in user_details:
        if strategy_name == strategy:
            for trade in user_details[strategy_name]["TradeState"]["orders"]:
                if trade["exchange_token"] == exchange_token and trade["trade_id"].endswith("EX"):
                    order_ids[trade["order_id"]] = trade["qty"]
    return order_ids


# TODO: sweep_orders from user/strategies/todayorders for sweep order enabled strategies
def place_sweep_orders_for_strategy(strategy_users, order_details):
    # get list of sweep enabled strategies from Strategies collection using 'SweepEnabled' field from StrategyCard
    # match with {username}/"Strategies"/{strategy_name}/"StrategyName" value

    # call place_order_for_strategy with appropriate details
    pass


# TODO: place morning SL orders for user/strategies/todayorders for morning_sl enabled strategies
def place_morning_sl_orders_for_strategy(strategy_users, order_details):
    # get morning_sl enabled order_ids and prepare a counter order_details
    # call place_order_for_strategy with appropriate details
    pass
