#TODO: call ordercenterutils to place sweep orders
# 1. sweep_sl_orders(): get orderDetails from broker and cancel all orders with "TRIGGER PENDING" and "MIS"/"NFO" status and keep the list to place counter_orders
                    # 2. call place_order_for_strategy with appropriate counter order details
# 2. sweep_hedge_orders(): get orderDetails from broker and make list of all "HO" without "HO_EX"
                    # 2. call place_order_for_strategy with appropriate counter order details
                    
import datetime as dt

import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as BrokerCenterUtils
import Executor.ExecutorUtils.OrderCenter.OrderCenterUtils as OrderCenterUtils


def create_counter_order(trade, user):
    # Placeholder for counter order creation logic
    # Modify as per your requirements
    counter_order = {
        "strategy": trade['strategy'],
        "signal": "Short",
        "base_symbol": trade['base_symbol'],
        "exchange_token": trade['exchange_token'],     
        "transaction_type": trade['transaction_type'], 
        "order_type": trade['order_type'], 
        "product_type": trade['product'],
        "order_mode": "Counter",
        "trade_id": trade['trade_id']
    }
    return counter_order

def sweep_sl_order():
    active_users = BrokerCenterUtils.fetch_active_users_from_firebase()
    all_sl_counter_orders = []

    for user in active_users:
        tradebook = BrokerCenterUtils.get_today_orders_for_brokers(user)
        sl_counter_orders = []

        if user['Broker']['BrokerName'] == 'ZERODHA':
            for trade in tradebook:
                if trade['status'] == 'TRIGGER PENDING' and trade['product'] == 'MIS':
                    counter_order = create_counter_order(trade, user)
                    sl_counter_orders.append(counter_order)

        elif user['Broker']['BrokerName'] == 'ALICEBLUE':
            for trade in tradebook:
                if trade['Status'] == 'trigger pending' and trade['Pcode'] == 'MIS':
                    counter_order = create_counter_order(trade, user)
                    sl_counter_orders.append(counter_order)

        all_sl_counter_orders.append(sl_counter_orders)

    # Place SL counter orders for each user
    for sl_counter_orders in all_sl_counter_orders:
        OrderCenterUtils.place_order_for_strategy(sl_counter_orders)

def sweep_hedge_orders():
    active_users = BrokerCenterUtils.fetch_active_users_from_firebase()
    all_hedge_counter_orders = []

    for user in active_users:
        tradebook = BrokerCenterUtils.get_today_orders_for_brokers(user)
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
sweep_hedge_orders()