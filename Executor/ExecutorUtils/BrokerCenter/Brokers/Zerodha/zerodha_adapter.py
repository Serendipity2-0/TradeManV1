from kiteconnect import KiteConnect
import pandas as pd

def zerodha_fetch_free_cash(user_details):
    kite = KiteConnect(api_key=user_details['ApiKey'])
    kite.set_access_token(user_details['SessionId'])
    # Fetch the account balance details
    balance_details = kite.margins(segment='equity')

    # Extract the 'cash' value
    cash_balance = balance_details.get('cash', 0)

    # If 'cash' key is not at the top level, we need to find where it is
    if cash_balance == 0 and 'cash' not in balance_details:
        # Look for 'cash' in nested dictionaries
        for key, value in balance_details.items():
            if isinstance(value, dict) and 'cash' in value:
                cash_balance = value.get('cash', 0)
                break
    return cash_balance

def get_csv_kite(user_details):
    kite = KiteConnect(api_key=user_details['Broker']['ApiKey'])
    kite.set_access_token(user_details['Broker']['SessionId'])
    instrument_dump = kite.instruments()
    instrument_df = pd.DataFrame(instrument_dump)
    return instrument_df 

def fetch_zerodha_holdings(api_key, access_token):
    kite = KiteConnect(api_key=api_key,access_token=access_token)
    holdings = kite.holdings()
    return holdings

def simplify_zerodha_order(detail):
    trade_symbol = detail['tradingsymbol']
    
    # Check if the tradingsymbol is of futures type
    if trade_symbol.endswith("FUT"):
        strike_price = 0
        option_type = "FUT"
    else:
        strike_price = int(trade_symbol[-7:-2])  # Convert to integer to store as number
        option_type = trade_symbol[-2:]

    trade_id = detail['tag']
    if trade_id.endswith('_entry'):
        order_type = "entry"
    elif trade_id.endswith('_exit'):
        order_type = "exit"
    
    return {
        'trade_id' : trade_id,  # This is the order_id for zerodha
        'avg_price': detail['average_price'],
        'qty': detail['quantity'],
        'time': detail["order_timestamp"].strftime("%d/%m/%Y %H:%M:%S"),
        'strike_price': strike_price,
        'option_type': option_type,
        'trading_symbol': trade_symbol,
        'trade_type': detail['transaction_type'],
        'order_type' : order_type
    }

def zerodha_todays_tradebook(user):
    kite = create_kite_obj(api_key=user['api_key'],access_token=user['access_token'])
    orders = kite.orders()
    return orders