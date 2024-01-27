import datetime as dt
import os,sys

DIR = os.getcwd()
sys.path.append(DIR)

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import get_today_orders_for_brokers,create_counter_order_details, create_hedge_counter_order_details
import Executor.ExecutorUtils.OrderCenter.OrderCenterUtils as OrderCenterUtils

def sweep_sl_order():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_users_from_firebase
    active_users = fetch_active_users_from_firebase()

    for user in active_users:
        tradebook = get_today_orders_for_brokers(user)
        counter_order_detail = create_counter_order_details(tradebook, user)
        OrderCenterUtils.place_order_for_strategy([user],counter_order_detail)

def sweep_hedge_orders():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_users_from_firebase
    active_users = fetch_active_users_from_firebase()

    for user in active_users:
        tradebook = get_today_orders_for_brokers(user)
        hedge_counter_order_details = create_hedge_counter_order_details(tradebook, user)
        OrderCenterUtils.place_order_for_strategy([user],hedge_counter_order_details)

# Execute the functions
sweep_sl_order()
sweep_hedge_orders()