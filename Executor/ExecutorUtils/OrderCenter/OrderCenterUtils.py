import datetime as dt
import os, sys
import math


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

    

def place_order_for_strategy(strategy_name, order_details):
    #TODO: Once the order is placed it should log the lld in the firebase(user/strategy/tradestate/orders)
    #TODO: Add order_tag for main order in this format MP12_main_long_entry and MP12_main_long_exit
    #TODO: Add order_tag for hedge order in this format MP12_hedge_long_entry and MP12_hedge_long_exit
    active_users = Broker.get_active_subscribers(strategy_name)  
    for broker, usernames in active_users.items():
        for username in usernames:
            for order in order_details:
                # Add the username and broker to the order details
                order_with_user_and_broker = order.copy()  # Create a shallow copy to avoid modifying the original order
                order_with_user_and_broker.update({
                    "broker": broker,
                    "username": username
                })

                # Now get the quantity with the updated order details
                order_qty = place_order_calc.get_qty(order_with_user_and_broker)

                # Fetch the max order quantity for the specific base_symbol
                max_qty = place_order_calc.read_max_order_qty_for_symbol(order_with_user_and_broker.get('base_symbol'))

                # Split the order if the quantity exceeds the maximum
                while order_qty > 0:
                    current_qty = min(order_qty, max_qty)
                    order_to_place = order_with_user_and_broker.copy()
                    order_to_place["qty"] = current_qty
                    place_order_for_broker(order_to_place)
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