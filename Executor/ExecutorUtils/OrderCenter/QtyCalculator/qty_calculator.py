
def calculate_quantity_based_on_ltp(ltp, strategy_name, base_symbol):
    active_users_file = os.path.join(DIR_PATH, 'MarketUtils', 'active_users.json')
    indices_lot_sizes = {"NIFTY": 50, "BANKNIFTY": 15, "FINNIFTY": 40, "MIDCPNIFTY": 75, "SENSEX": 10}

    _, strategy_path = place_order_calc.get_strategy_json(strategy_name)
    strategy_obj = StrategyBase.Strategy.read_strategy_json(strategy_path)
    instruments = strategy_obj.get_instruments()

    if base_symbol not in instruments:
        print(f"{base_symbol} is not traded in {strategy_name}.")
        return

    try:
        active_users = general_calc.read_json_file(active_users_file)
    except FileNotFoundError:
        print(f"The file {active_users_file} does not exist.")
        return


    for user in active_users:
        # if user['account_name'] != base_symbol:
        #     continue
        if strategy_name in user['qty']:
            print(user['account_name'], "already has a quantity for", strategy_name)
            
        
            user_details, _ = general_calc.get_user_details(user['account_name'])
            capital = user['expected_morning_balance']
            percentage_risk = user_details['percentage_risk'].get(strategy_name, 0)

            if percentage_risk <= 0:
                print(f"No risk allocated for strategy {strategy_name} or invalid risk value for user {base_symbol}.")
                return

            lot_size = indices_lot_sizes.get(base_symbol, 1)
            risk = percentage_risk if percentage_risk < 1 else percentage_risk / capital
            raw_quantity = (risk * capital) / ltp
            quantity = int((raw_quantity // lot_size) * lot_size)
            print(f"Quantity for {base_symbol} is {quantity}")
            if quantity == 0:
                quantity = lot_size

            # Update the quantity in the user's data
            user['qty'] = user.get('qty', {})
            user['qty'][strategy_name] = quantity

        # Save the updated active users back to the file
        general_calc.write_json_file(active_users_file, active_users)