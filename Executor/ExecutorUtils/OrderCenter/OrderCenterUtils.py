import datetime as dt
import math
import os
import sys
import time

DIR = os.getcwd()
sys.path.append(DIR)

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_user_credentials_firebase, place_order_for_brokers)
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import \
    update_fields_firebase
from Executor.ExecutorUtils.InstrumentCenter.FNOInfoBase import FNOInfo
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import \
    discord_bot


def calculate_qty_for_strategies(capital, risk, avg_sl_points, lot_size):
    if avg_sl_points is not None:
        raw_quantity = (risk * capital) / avg_sl_points   #avg_sl_points can be ltp/price_ref/avg trade points
        quantity = int((raw_quantity // lot_size) * lot_size)
        if quantity == 0:
            quantity = lot_size
    else:
        # For other strategies, risk values represent the capital allocated
        lots = capital / risk
        quantity = math.ceil(lots) * lot_size
    return quantity

def place_order_for_strategy(strategy_users, order_details):
    for user in strategy_users:
        all_order_statuses = []  # To store the status of all orders

        for order in order_details:
            order_with_user_and_broker = order.copy()
            order_with_user_and_broker.update({
                "broker": user['Broker']['BrokerName'],
                "username": user['Broker']['BrokerUserName'],
                "qty": user['Strategies'][order.get('strategy')]['qty']
            })

            max_qty = FNOInfo().get_max_order_qty_by_base_symbol(order_with_user_and_broker.get('base_symbol'))
            user_credentials = fetch_user_credentials_firebase(user['Broker']['BrokerUserName'])

            order_qty = order_with_user_and_broker["qty"]

            # Split and place orders if necessary
            while order_qty > 0:
                current_qty = min(order_qty, max_qty)
                order_to_place = order_with_user_and_broker.copy()
                order_to_place["qty"] = current_qty

                order_status = place_order_for_brokers(order_to_place, user_credentials)
                all_order_statuses.append(order_status)

                if 'Hedge' in order_to_place.get('order_mode', ''):
                    time.sleep(1)
                order_qty -= current_qty

        # Update Firebase with order status
        update_path = f"{user['Broker']['BrokerUserName']}/Strategies/{order.get('strategy')}/TradeState/orders"
        update_fields_firebase('users', user['Broker']['BrokerUserName'], all_order_statuses, update_path)

        # Send notification if any orders failed # TODO: check for exact fail msgs and send notifications accordingly
        for status in all_order_statuses:
            if status.get('message', '') == 'Order placement failed':
                discord_bot(f"Order failed for user {user['Broker']['BrokerUserName']} in strategy {order.get('strategy')}", order.get('strategy'))


    return all_order_statuses

#TODO: sweep_orders from user/strategies/todayorders for sweep order enabled strategies
def place_sweep_orders_for_strategy(strategy_users, order_details):
    # get sweep enabled order_ids and prepare a counter order_details
    # call place_order_for_strategy with appropriate details
    pass

#TODO: place morning SL orders for user/strategies/todayorders for morning_sl enabled strategies
def place_morning_sl_orders_for_strategy(strategy_users, order_details):
    # get morning_sl enabled order_ids and prepare a counter order_details
    # call place_order_for_strategy with appropriate details
    pass