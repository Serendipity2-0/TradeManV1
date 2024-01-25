import datetime

import pandas as pd
from kiteconnect import KiteConnect

from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument
from Executor.Strategies.StrategiesUtil import get_strategy_name_from_trade_id, get_strategy_name_from_trade_id


def create_kite_obj(user_details=None,api_key=None,access_token=None):
    if api_key and access_token:
        return KiteConnect(api_key=api_key,access_token=access_token)
    elif user_details:
        return KiteConnect(api_key=user_details['ApiKey'],access_token=user_details['SessionId'])
    else:
        raise ValueError("Either user_details or api_key and access_token must be provided")

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
    instrument_df['exchange_token'] = instrument_df['exchange_token'].astype(str)
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
    kite = create_kite_obj(api_key=user['ApiKey'],access_token=user['SessionId'])
    orders = kite.orders()
    return orders

def kite_place_orders_for_users(orders_to_place, users_credentials):
    results = {
        "avg_prc": None,
        "exchange_token": None,
        "order_id": None,
        "qty": None,
        "time_stamp": None,
        "trade_id": None,
        "message": None
    }

    kite = create_kite_obj(user_details=users_credentials)  # Create a KiteConnect instance with user's broker credentials
    order_id = None

    strategy = orders_to_place['strategy']
    exchange_token = orders_to_place['exchange_token']
    qty = orders_to_place.get('qty', 1)  # Default quantity to 1 if not specified
    product = orders_to_place.get('product_type')

    transaction_type = calculate_transaction_type(kite,orders_to_place.get('transaction_type'))
    order_type = calculate_order_type(kite,orders_to_place.get('order_type'))
    product_type = calculate_product_type(kite,product)
    if product == 'CNC':
        segment_type = kite.EXCHANGE_NSE
        trading_symbol = Instrument().get_trading_symbol_by_exchange_token(exchange_token, "NSE")
    else:
        segment_type = Instrument().get_segment_by_exchange_token(exchange_token)
        trading_symbol = Instrument().get_trading_symbol_by_exchange_token(exchange_token)
    
    limit_prc = orders_to_place.get('limit_prc', None) 
    trigger_price = orders_to_place.get('trigger_prc', None)

    if limit_prc is not None:
        limit_prc = round(float(limit_prc), 2)
        if limit_prc < 0:
            limit_prc = 1.0
    else:
        limit_prc = 0.0
    
    if trigger_price is not None:
        trigger_price = round(float(trigger_price), 2)
        if trigger_price < 0:
            trigger_price = 1.5

    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=segment_type, 
            price=limit_prc,
            tradingsymbol=trading_symbol,
            transaction_type=transaction_type, 
            quantity=qty,
            trigger_price=trigger_price,
            product=product_type,
            order_type=order_type,
            tag=orders_to_place.get('trade_id', None)
        )
        
        print(f"Order placed. ID is: {order_id}")

        # Assuming 'avg_prc' can be fetched from a method or is returned in order history/details
        message = f"Order placed successfully for {orders_to_place['username']}"
        # avg_prc = fetch_avg_price(kite, order_id['NOrdNo'])  # This function needs to be defined

        

    except Exception as e:
        message = f"Order placement failed: {e} for {orders_to_place['username']}"
        print(message)
        results.update({
            "message": message
            # Additional error details can be added here if needed
        })
    
    results ={
            "exchange_token": exchange_token,
            "order_id": order_id,
            "qty": qty,
            "time_stamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "trade_id": orders_to_place.get('trade_id', ''),
            "message": message
        }
    return results

    
def calculate_transaction_type(kite,transaction_type):
    if transaction_type == 'BUY':
        transaction_type = kite.TRANSACTION_TYPE_BUY
    elif transaction_type == 'SELL':
        transaction_type = kite.TRANSACTION_TYPE_SELL
    else:
        raise ValueError("Invalid transaction_type in order_details")
    return transaction_type

def calculate_order_type(kite,order_type):
    if order_type == 'Stoploss':
        order_type = kite.ORDER_TYPE_SL
    elif order_type == 'Market':
        order_type = kite.ORDER_TYPE_MARKET
    elif order_type == 'Limit':
        order_type = kite.ORDER_TYPE_LIMIT
    else:
        raise ValueError("Invalid order_type in order_details")
    return order_type

def calculate_product_type(kite,product_type):
    if product_type == 'NRML':
        product_type = kite.PRODUCT_NRML
    elif product_type == 'MIS':
        product_type = kite.PRODUCT_MIS
    elif product_type == 'CNC':
        product_type = kite.PRODUCT_CNC
    else:
        raise ValueError("Invalid product_type in order_details")
    return product_type

def calculate_segment_type(kite, segment_type):
    # Prefix to indicate the exchange type
    prefix = "EXCHANGE_"
    
    # Construct the attribute name
    attribute_name = prefix + segment_type
    
    # Get the attribute from the kite object, or raise an error if it doesn't exist
    if hasattr(kite, attribute_name):
        return getattr(kite, attribute_name)
    else:
        raise ValueError(f"Invalid segment_type '{segment_type}' in order_details")

def get_avg_prc(kite,order_id):
    if not order_id:
        raise Exception("Order_id not found")
    
    order_history = kite.order_history(order_id=order_id)
    for order in order_history:
        if order.get('status') == 'COMPLETE':
            avg_prc = order.get('average_price', 0.0)
            break 
    return avg_prc

def get_order_details(user):
    kite = create_kite_obj(api_key=user['api_key'],access_token=user['access_token'])
    orders = kite.orders()
    return orders

def create_counter_order(trade, user):
    strategy_name = get_strategy_name_from_trade_id(trade['tag'])
    exchange_token = Instrument().get_exchange_token_by_token(trade['instrument_token'])
    counter_order = {
        "strategy": strategy_name,
        "signal": get_strategy_name_from_trade_id(trade['tag']),
        "base_symbol": "NIFTY",   #WARNING: dummy base symbol 
        "exchange_token": exchange_token,     
        "transaction_type": trade['transaction_type'], 
        "order_type": 'MARKET',
        "product_type": trade['product'],
        "trade_id": trade['tag'],
        "order_mode": "Counter",
        "qty": trade['quantity']
    }
    return counter_order

def create_cancel_order(trade, user):
    kite = create_kite_obj(user_details=user['Broker'])
    kite.cancel_order(variety=kite.VARIETY_REGULAR, order_id=trade['order_id'])
    