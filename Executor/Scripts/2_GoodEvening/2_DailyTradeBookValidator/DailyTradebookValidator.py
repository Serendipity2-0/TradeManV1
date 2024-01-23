from datetime import datetime

from alice_adapter import aliceblue_todays_tradebook
from exefirebase_adapter import (fetch_collection_data_firebase,
                                 update_fields_firebase)
from zerodha_adapter import zerodha_todays_tradebook

import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as BrokerCenterUtils


def get_todays_date():
    return datetime.now().strftime("%Y-%m-%d")

def daily_tradebook_validator():
    active_users = fetch_collection_data_firebase('new_clients')
    matched_orders = []
    unmatched_orders = []

    for user in active_users.values():
        if not user.get('Active'):
            continue

        strategies = user.get('Strategies', [])
        today = get_todays_date()

        for strategy in strategies:
            trade_state = strategy.get('TradeState', {})
            orders = trade_state.get('orders', [])

            for order in orders:
                if order['timestamp'].startswith(today):
                    user_tradebook = BrokerCenterUtils.get_today_orders_for_brokers(user)
                    avg_price_key = 'Avgprc' if user['Broker']['BrokerName'] == 'ALICEBLUE' else 'average_price'

                    for trade in user_tradebook:
                        if trade['order_id'] == order['order_id']:
                            avg_prc = trade[avg_price_key]
                            update_path = f"Strategies/{strategy['StrategyName']}/TradeState/orders"
                            update_fields_firebase('new_clients', user['Tr_No'], {'avg_prc': avg_prc}, update_path)
                            matched_orders.append(order['order_id'])
                            break
                    else:
                        unmatched_orders.append(order['order_id'])

    print("Matched Orders:", matched_orders)
    print("Unmatched Orders:", unmatched_orders)

daily_tradebook_validator()
