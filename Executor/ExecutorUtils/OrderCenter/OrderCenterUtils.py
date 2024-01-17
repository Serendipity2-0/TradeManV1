def get_trade_id(strategy_name, trade_type):
    global trade_id_state

    # Load strategy object
    _, strategy_path = get_strategy_json(strategy_name)
    strategy_obj = Strategy.Strategy.read_strategy_json(strategy_path)

    # Resolve strategy name to prefix
    strategy_prefix = strategy_prefix_map.get(strategy_name)
    if not strategy_prefix:
        raise ValueError(f"Unknown strategy name: {strategy_name}")

    # Initialize strategy in state if not present
    if strategy_prefix not in trade_id_state:
        trade_id_state[strategy_prefix] = 1

    # Generate trade ID for entry
    if trade_type.lower() == 'entry':
        current_id = trade_id_state[strategy_prefix]
        trade_id_state[strategy_prefix] += 1
        trade_id = f"{strategy_prefix}{current_id}_entry"
        next_trade_id = f"{strategy_prefix}{trade_id_state[strategy_prefix]}"
        # Save new trade ID in strategy JSON
        strategy_obj.set_next_trade_id(next_trade_id)
        strategy_obj.write_strategy_json(strategy_path)

    # Use the same ID for exit
    elif trade_type.lower() == 'exit':
        current_id = trade_id_state[strategy_prefix] - 1
        trade_id = f"{strategy_prefix}{current_id}_exit"

    # Add trade_id to today's orders after completion
    base_trade_id = f"{strategy_prefix}{current_id}"
    today_orders = strategy_obj.get_today_orders()
    if base_trade_id not in today_orders:
        today_orders.append(base_trade_id)
        strategy_obj.set_today_orders(today_orders)
        strategy_obj.write_strategy_json(strategy_path)

    # Save state after each ID generation
    save_current_state(trade_id_state)
    print(f"Generated trade ID: {trade_id}")
    return trade_id

def place_order_for_strategy(strategy_name, order_details):
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