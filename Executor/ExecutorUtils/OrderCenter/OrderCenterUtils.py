import datetime as dt
import os, sys
import math
import os,sys

DIR = os.getcwd()
sys.path.append(DIR)

from Executor.ExecutorUtils.InstrumentCenter.FNOInfoBase import FNOInfo
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_user_credentials_firebase,place_order_for_broker

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
    #TODO: Once the order is placed it should log the lld in the firebase(user/strategy/tradestate/orders)
    
    for user in strategy_users:
        for order in order_details:
            # Add the username and broker to the order details
            order_with_user_and_broker = order.copy()  # Create a shallow copy to avoid modifying the original order
            order_with_user_and_broker.update({
                "broker": user['Broker']['BrokerName'],
                "username": user['Broker']['BrokerUserName'],
                "qty" : user['Strategies'][order.get('strategy')]['qty']
            })

            # Fetch the max order quantity for the specific base_symbol
            max_qty = FNOInfo().get_max_order_qty_by_base_symbol(order_with_user_and_broker.get('base_symbol'))
            user_credentials = fetch_user_credentials_firebase(user['Broker']['BrokerUserName'])
            # Split the order if the quantity exceeds the maximum
            while order_qty > 0:
                current_qty = min(order_qty, max_qty)
                order_to_place = order_with_user_and_broker.copy()
                order_to_place["qty"] = current_qty
                place_order_for_broker(order_to_place,user_credentials)
                if 'Hedge' in order_to_place.get('order_mode', []):
                    sleep(1)
                order_qty -= current_qty
                    
def log_usr_ordr_firebase(order_id, order_details):
    # Getting the json data and path for the user
    user_data, json_path = get_orders_json(order_details['account_name'])
    # Creating the order_dict structure
    order_dict = {
        "order_id": order_id,
        "qty": int(order_details['qty']),
        "timestamp": str(dt.datetime.now()),
        "exchange_token": int(order_details['exchange_token']),
        "trade_id" : order_details['trade_id']
    }
    # Checking for 'signal' and 'transaction_type' and setting the trade_type accordingly
    trade_type = order_details.get('signal', order_details.get('transaction_type'))
    
    # Constructing the user_data JSON structure
    orders = user_data.setdefault('orders', {})
    strategy_orders = orders.setdefault(order_details.get("strategy"), {})
    order_type_list = strategy_orders.setdefault(trade_type, [])
    order_type_list.append(order_dict)
    write_json_file(json_path, user_data)