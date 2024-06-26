import datetime as dt
import math
import os
import sys
import time
from dotenv import load_dotenv

DIR = os.getcwd()
sys.path.append(DIR)

load_dotenv(os.path.join(DIR, "trademan.env"))
db_dir = os.getenv("DB_DIR")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


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
    CLIENTS_USER_FB_DB,
    get_orders_tax
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    fetch_qty_for_holdings_sqldb,
)

def calculate_qty_for_strategies(capital, risk, avg_sl_points, lot_size, qty_amplifier=None, strategy_amplifier=None):
    logger.info(f"Calculating quantity for strategy with capital: {capital}, risk: {risk}, avg_sl_points: {avg_sl_points}, lot_size: {lot_size}")
    try:
        # Set default multipliers if amplifiers are not provided
        qty_multiplier = 1 + (qty_amplifier / 100) if qty_amplifier is not None else 1   #qty_multiplier is fetcched from the marketinfo
        strategy_multiplier = 1 + (strategy_amplifier / 100) if strategy_amplifier is not None else 1 #strategy_multiplier is fetched from the strategy

        if avg_sl_points is not None:
            # Calculate the base raw quantity
            raw_quantity = ((risk / 100) * capital) / avg_sl_points

            # Adjust raw quantity with multipliers
            raw_quantity *= (qty_multiplier * strategy_multiplier)

            # Calculate the number of lots
            number_of_lots = raw_quantity / lot_size

            # Round up to the nearest whole number of lots
            number_of_lots = math.ceil(number_of_lots)

            # Calculate the final quantity as a multiple of lot size
            quantity = int(number_of_lots * lot_size)
            logger.debug(f"Final adjusted quantity: {quantity}")
        else:
            # For other strategies, adjust risk according to multipliers before calculating lots
            adjusted_risk = risk / (qty_multiplier * strategy_multiplier)
            lots = capital / (adjusted_risk / 100)
            quantity = math.ceil(lots) * lot_size
            logger.debug(f"Quantity calculated using default strategy without avg_sl_points: {quantity}")

        return quantity
    except ZeroDivisionError as e:
        logger.error(f"Error calculating quantity for strategy due to division by zero: {e}")
        return 0
    except Exception as e:
        logger.error(f"General error calculating quantity for strategy: {e}")
        return 0


def place_order_for_strategy(strategy_users, order_details, order_qty_mode:str=None):
    for user in strategy_users:
        logger.debug(f"Placing orders for user {user['Broker']['BrokerUsername']}")
        all_order_statuses = []  # To store the status of all orders

        for order in order_details:
            order_with_user_and_broker = order.copy()
            try:
                if order_qty_mode == "Sweep":
                    order_with_user_and_broker.update(
                        {
                            "broker": user["Broker"]["BrokerName"],
                            "username": user["Broker"]["BrokerUsername"],
                        }
                    )
                elif order_qty_mode == "Holdings":
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
            except Exception as e:
                logger.error(f"Error updating order with user and broker: {e}")
                continue

            try:
                # logger.debug(f"Order with user and broker: {order_with_user_and_broker}")
                max_qty = FNOInfo().get_max_order_qty_by_base_symbol(
                    order_with_user_and_broker.get("base_symbol")
                )
                user_credentials = fetch_user_credentials_firebase(
                    user["Broker"]["BrokerUsername"]
                )

                order_qty = int(order_with_user_and_broker["qty"])
            except Exception as e:
                logger.error(f"Error fetching max qty for base symbol: {e}")
                continue

            if max_qty:
                # logger.debug(f"Max qty for {order_with_user_and_broker.get('base_symbol')} is {max_qty} so splitting orders.")
                # Split and place orders if necessary
                try:
                    while order_qty > 0:
                        current_qty = min(order_qty, max_qty)
                        order_to_place = order_with_user_and_broker.copy()
                        order_to_place["qty"] = current_qty

                        # logger.debug(f"Placing order for {order_to_place}")
                        order_to_place["tax"] = get_orders_tax(order_to_place, user_credentials)
                        order_status = place_order_for_brokers(order_to_place, user_credentials)
                        all_order_statuses.append(order_status)

                        if "Hedge" in order_to_place.get("order_mode", ""):
                            time.sleep(1)
                        order_qty -= current_qty
                except Exception as e:
                    logger.error(f"Error splitting orders and order not placed: {e}")
            else:
                # Place the order
                # logger.debug(f"Placing order for {order_with_user_and_broker}")
                try:
                    order_with_user_and_broker["tax"] = get_orders_tax(order_with_user_and_broker, user_credentials)
                    order_status = place_order_for_brokers(order_with_user_and_broker, user_credentials)
                    all_order_statuses.append(order_status)
                except Exception as e:
                    logger.error(f"Error placing order with no max_qty: {e}")

        # Update Firebase with order status
            update_path = f"Strategies/{order.get('strategy')}/TradeState/orders"
            logger.debug(f"update_path: {update_path}")

            if order_qty_mode == "Sweep":
                for data in all_order_statuses:
                    try:
                        push_orders_firebase(CLIENTS_USER_FB_DB, user["Tr_No"], data, update_path)
                    except Exception as e:
                        logger.error(f"Error updating firebase with order status: {e}")
                all_order_statuses.clear() 

        if order_qty_mode != "Sweep":
            for data in all_order_statuses:
                try:
                    push_orders_firebase(CLIENTS_USER_FB_DB, user["Tr_No"], data, update_path)
                except Exception as e:
                    logger.error(f"Error updating firebase with order status: {e}")
            

        # Send notification if any orders failed # TODO: check for Zerodha exact fail msgs and send notifications accordingly
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
        logger.debug(f"Modifying orders for user {users['Broker']['BrokerUsername']}")
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
            try:
                modify_order_for_brokers(order_with_user_and_broker, user_credentials)
            except Exception:
                logger.error(f"Error modifying order for user: {users['Broker']['BrokerUsername']}")
    pass


def retrieve_order_id(account_name, strategy, exchange_token: int):
    # retrieve the order id from firebase for the given account name, strategy name and trade id
    order_ids = {}
    user_details = fetch_strategy_details_for_user(account_name)
    for strategy_name in user_details:
        if strategy_name == strategy:
            try:
                for trade in user_details[strategy_name]["TradeState"]["orders"]:
                    if trade is not None and trade["exchange_token"] == exchange_token and trade["trade_id"].endswith("EX"):
                        order_ids[trade["order_id"]] = trade["qty"]
            except Exception as e:
                logger.error(f"Error retrieving order id for user: {account_name} and strategy: {strategy} : {e}")
    return order_ids
