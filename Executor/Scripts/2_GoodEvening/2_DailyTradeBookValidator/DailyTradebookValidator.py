from datetime import datetime
import os,sys

DIR = os.getcwd()
sys.path.append(DIR)

# from Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter import aliceblue_todays_tradebook
# from Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter import zerodha_todays_tradebook
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (fetch_collection_data_firebase,
                                    update_fields_firebase)
import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as BrokerCenterUtils


def get_todays_date():
    return datetime.now().strftime("%Y-%m-%d")

def daily_tradebook_validator():
    active_users = BrokerCenterUtils.fetch_active_users_from_firebase()
    matched_orders = []
    unmatched_orders = []

    for user in active_users:
        strategies = [user.get('Strategies', [])]
        today = get_todays_date()

        user_tradebook = BrokerCenterUtils.get_today_orders_for_brokers(user)
        for strategy in strategies:
            for strategy_key, strategy_data in strategy.items():
                trade_state = strategy_data.get('TradeState', [])
                orders = trade_state.get('orders', [])

            for order in orders:
                #get the index of the order
                ind = orders.index(order)
                for key, value in order.items():
                    if key == 'time_stamp':
                        order_date_timestamp = value.split(' ')[0]
                if order_date_timestamp == today:
                    avg_price_key = BrokerCenterUtils.get_avg_prc_broker_key(user['Broker']['BrokerName'])
                    order_id_key = BrokerCenterUtils.get_order_id_broker_key(user['Broker']['BrokerName'])

                    for trade in user_tradebook:
                        if trade[order_id_key] == str(order['order_id']):
                            avg_prc = trade[avg_price_key]
                            update_path = f"Strategies/{strategy_key}/TradeState/orders/{ind}"
                            update_fields_firebase('new_clients', user['Tr_No'], {'avg_prc': avg_prc}, update_path)
                            matched_orders.append(order['order_id'])
                            break
                        else:
                            unmatched_orders.append(order['order_id'])

    print("Matched Orders:", matched_orders)
    print("Unmatched Orders:", unmatched_orders)

daily_tradebook_validator()
