#TODO: call ordercenterutils to place sweep orders
# 1. sweep_sl_orders(): get orderDetails from broker and cancel all orders with "TRIGGER PENDING" and "MIS"/"NFO" status and keep the list to place counter_orders
                    # 2. call place_order_for_strategy with appropriate counter order details
# 2. sweep_hedge_orders(): get orderDetails from broker and make list of all "HO" without "HO_EX"
                    # 2. call place_order_for_strategy with appropriate counter order details
                    
import datetime as dt
import os,sys

DIR = os.getcwd()
sys.path.append(DIR)

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import get_today_orders_for_brokers,create_counter_order_details
import Executor.ExecutorUtils.OrderCenter.OrderCenterUtils as OrderCenterUtils


def sweep_sl_order():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_users_from_firebase
    active_users = fetch_active_users_from_firebase()

    all_sl_counter_orders = []

    for user in active_users:
        tradebook = get_today_orders_for_brokers(user)
        counter_order_details = create_counter_order_details(tradebook, user)
        print('counter_order_details',counter_order_details)
        # for order in counter_order_details:
        #     BrokerCenterUtils.place_order_for_strategy(order, user['Broker'])


    # Place SL counter orders for each user
    for sl_counter_orders in all_sl_counter_orders:
        OrderCenterUtils.place_order_for_strategy(active_users,sl_counter_orders)
def sweep_hedge_orders():
    active_users = fetch_active_users_from_firebase()
    all_hedge_counter_orders = []

    for user in active_users:
        tradebook = get_today_orders_for_brokers(user)
        hedge_counter_orders = []

        for trade in tradebook:
            if user['Broker']['BrokerName'] == 'ZERODHA':
                # Check conditions for Zerodha orders
                if 'HO_EN' in trade['tag'] and 'HO_EX' not in trade['tag'] and trade['product'] == 'MIS':
                    counter_order = create_counter_order(trade, user)
                    hedge_counter_orders.append(counter_order)

            elif user['Broker']['BrokerName'] == 'ALICEBLUE':
                # Check conditions for Aliceblue orders
                if 'HO_EN' in trade['ordersource'] and 'HO_EX' not in trade['ordersource'] and trade['Pcode'] == 'MIS':
                    counter_order = create_counter_order(trade, user)
                    hedge_counter_orders.append(counter_order)

        all_hedge_counter_orders.append(hedge_counter_orders)

    # Place hedge counter orders for each user
    for hedge_counter_orders in all_hedge_counter_orders:
        OrderCenterUtils.place_order_for_strategy(hedge_counter_orders)

# Execute the functions
sweep_sl_order()
# sweep_hedge_orders()