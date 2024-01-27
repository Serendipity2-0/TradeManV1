import os
import sys
import datetime as dt

from pya3 import *

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)


from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import \
    discord_bot
from Executor.Strategies.StrategiesUtil import get_strategy_name_from_trade_id, get_signal_from_trade_id,calculate_transaction_type_sl

#This function fetches the available free cash balance for a user from the Aliceblue trading platform.
def alice_fetch_free_cash(user_details):
    alice = Aliceblue(user_details['BrokerUsername'], user_details['ApiKey'],session_id=user_details['SessionId'])
    balance_details = alice.get_balance()  # This method might have a different name

    # Search for 'cashmarginavailable' in the balance_details
    for item in balance_details:
        if isinstance(item, dict) and 'cashmarginavailable' in item:
            cash_margin_available = item.get('cashmarginavailable', 0)
            return float(cash_margin_available)
        
def merge_ins_csv_files():
    columns_to_keep = [
    "Exch", "Exchange Segment", "Symbol", "Token",
    "Instrument Type", "Option Type", "Strike Price",
    "Instrument Name", "Formatted Ins Name", "Trading Symbol",
    "Expiry Date", "Lot Size", "Tick Size"
    ]

    folder_path = os.path.join(DIR_PATH, 'SampleData')#TODO: Change this file location to the actual location of the instrument csv files
    ins_files = ['NFO.csv', 'BFO.csv', 'NSE.csv']
    file_paths = [os.path.join(folder_path, file) for file in ins_files]
    
    nfo_df = pd.read_csv(file_paths[0])
    bfo_df = pd.read_csv(file_paths[1])
    nse_df = pd.read_csv(file_paths[2])

    # Add empty columns for 'Option Type', 'Strike Price', and 'Expiry Date' to NSE DataFrame
    nse_df['Option Type'] = None
    nse_df['Strike Price'] = None
    nse_df['Expiry Date'] = None

    # Filter each DataFrame to keep only the specified columns
    nfo_df_filtered = nfo_df[columns_to_keep]
    nse_df_filtered = nse_df[columns_to_keep]
    bfo_df_filtered = bfo_df[columns_to_keep]

    # Merge the DataFrames
    merged_df = pd.concat([nfo_df_filtered, nse_df_filtered, bfo_df_filtered], ignore_index=True)
    merged_df['Token'] = merged_df['Token'].astype(str)
    merged_df.to_csv('merged_alice_ins.csv', index=False)
    return merged_df



#This function downloads the instrument csv files from Aliceblue trading platform
def get_ins_csv_alice(user_details):
    alice = Aliceblue(user_id=user_details['Broker']['BrokerUsername'], api_key=user_details['Broker']['ApiKey'], session_id=user_details['Broker']['SessionId'])
    alice.get_contract_master("NFO") #TODO rename the NFO.csv to alice_instruments.csv
    alice.get_contract_master("BFO") #TODO rename the NSE.csv to alice_instruments.csv
    alice.get_contract_master("NSE") #TODO rename the BFO.csv to alice_instruments.csv
    alice_instrument_merged = merge_ins_csv_files()
    return alice_instrument_merged

#This function fetches the holdings in the user account
def fetch_aliceblue_holdings(username, api_key,session_id):
    alice = Aliceblue(username, api_key,session_id)
    holdings = alice.get_holding_positions()
    return holdings

def simplify_aliceblue_order(detail):
    if detail['optionType'] == 'XX':
        strike_price = 0
        option_type = "FUT"
    else:
        strike_price = int(detail['strikePrice'])
        option_type = detail['optionType']

    trade_id = detail['remarks']

    if trade_id.endswith('_entry'):
        order_type = "entry"
    elif trade_id.endswith('_exit'):
        order_type = "exit"

    return {
        'trade_id' : trade_id,
        'avg_price': float(detail['Avgprc']),
        'qty': int(detail['Qty']),
        'time': detail['OrderedTime'],
        'strike_price': strike_price,
        'option_type': option_type,
        'trading_symbol': detail['Trsym'],
        'trade_type': 'BUY' if detail['Trantype'] == 'B' else 'SELL',
        'order_type' : order_type
    }

def create_alice_obj(user_details):
    return Aliceblue(user_id=user_details['BrokerUsername'],api_key=user_details['ApiKey'],session_id=user_details['SessionId'])

def aliceblue_todays_tradebook(user):
    alice = create_alice_obj(user)
    orders = alice.get_order_history('')
    return orders

def calculate_transaction_type(transaction_type):
    if transaction_type == 'BUY':
        transaction_type = TransactionType.Buy
    elif transaction_type == 'SELL':
        transaction_type = TransactionType.Sell
    else:
        raise ValueError("Invalid transaction_type in order_details")
    return transaction_type

def calculate_order_type(order_type):
    if order_type.lower() == 'stoploss':
        order_type = OrderType.StopLossLimit
    elif order_type.lower() == 'market' or order_type.lower() == 'mis':
        order_type = OrderType.Market
    elif order_type.lower() == 'limit':
        order_type = OrderType.Limit
    else:
        raise ValueError("Invalid order_type in order_details")
    return order_type

def calculate_product_type(product_type):
    if product_type == 'NRML':
        product_type = ProductType.Normal
    elif product_type == 'MIS':
        product_type = ProductType.Intraday
    elif product_type == 'CNC':
        product_type = ProductType.Delivery
    else:
        raise ValueError("Invalid product_type in order_details")
    return product_type

def get_order_status(alice, order_id):
    order_status = alice.get_order_history(order_id)
    if order_status['reporttype'] != 'fill' : 
        return "FAIL"

def ant_place_orders_for_users(orders_to_place, users_credentials):
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument as Instru
    results = {
        "exchange_token": None,
        "order_id": None,
        "qty": None,
        "time_stamp": None,
        "trade_id": None,
        "message": None
    }

    alice = create_alice_obj(users_credentials)  # Create an Aliceblue instance with user's broker credentials
    strategy = orders_to_place['strategy']
    exchange_token = orders_to_place['exchange_token']
    qty = orders_to_place.get('qty', 1)  # Default quantity to 1 if not specified
    product = orders_to_place.get('product_type')
    transaction_type = calculate_transaction_type(orders_to_place.get('transaction_type'))
    order_type = calculate_order_type(orders_to_place.get('order_type'))
    product_type = calculate_product_type(product)

    if product == 'CNC':
        segment = 'NSE'
    else:
        segment = Instru().get_segment_by_exchange_token(exchange_token)

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
        order_id = alice.place_order(transaction_type = transaction_type, 
                                        instrument = alice.get_instrument_by_token(segment, int(exchange_token)),
                                        quantity = qty ,
                                        order_type = order_type,
                                        product_type = product_type,
                                        price = limit_prc,
                                        trigger_price = trigger_price,
                                        stop_loss = None,
                                        square_off = None,
                                        trailing_sl = None,
                                        is_amo = False,
                                        order_tag = orders_to_place.get('trade_id', None))
        
        print(f"Order placed. ID is: {order_id}")
        order_status = get_order_status(alice, order_id['NOrdNo'])
        if order_status == "FAIL":
            order_history = alice.get_order_history(order_id['NOrdNo'])
            message = f"Order placement failed, Reason: {order_history['RejReason']} for {orders_to_place['username']}"
        else:
            message = "Order placed successfully"
        
        discord_bot(message, strategy)

        # Assuming 'avg_prc' can be fetched from a method or is returned in order history/details
        avg_prc = 0
        # avg_prc = fetch_avg_price(alice, order_id['NOrdNo'])  # This function needs to be defined

        results = {
            "exchange_token": exchange_token,
            "order_id": order_id['NOrdNo'],
            "qty": qty,
            "time_stamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "trade_id": orders_to_place.get('trade_id', ''),
            "message": message
        }

    except Exception as e:
        print(f"An error occurred: {e}")

    return results

def ant_modify_orders_for_users(order_details,user_credentials):
    alice = create_alice_obj(user_credentials)
    order_id = place_order_calc.retrieve_order_id(
            order_details.get('account_name'),
            order_details.get('strategy'),
            order_details.get('transaction_type'),
            order_details.get('exchange_token')
        ) 

    transaction_type = alice_utils.calculate_transaction_type(order_details.get('transaction_type'))
    order_type = alice_utils.calculate_order_type(order_details.get('order_type'))
    product_type = alice_utils.calculate_product_type(order_details.get('product_type'))
    segment = order_details.get('segment')
    exchange_token = order_details.get('exchange_token')
    qty = int(order_details.get('qty'))
    new_stoploss = order_details.get('limit_prc', 0.0)
    trigger_price = order_details.get('trigger_prc', None)
    #TODO modify the code so that it modifies orders greater than max qty
    try:
        modify_order =  alice.modify_order(transaction_type = transaction_type,
                    order_id=str(order_id),
                    instrument = alice.get_instrument_by_token(segment, exchange_token),
                    quantity = qty,
                    order_type = order_type,
                    product_type = product_type,
                    price=new_stoploss,
                    trigger_price = trigger_price)
        print("alice modify_order",modify_order)
    except Exception as e:
        message = f"Order placement failed: {e} for {order_details['account_name']}"
        print(message)
        discord.discord_bot(message, order_details.get('strategy'))
        return None

def ant_create_counter_order(trade,user):
    strategy_name = get_strategy_name_from_trade_id(trade['remarks'])
    counter_order = {
        "strategy": strategy_name,
        "signal": get_signal_from_trade_id(trade['remarks']),
        "base_symbol": "NIFTY",   #WARNING: dummy base symbol 
        "exchange_token": trade['token'],     
        "transaction_type": "BUY" if trade['Trantype'] == 'B' else "SELL", 
        "order_type": 'MARKET',
        "product_type": trade['Pcode'],
        "trade_id": trade['remarks'],
        "order_mode": "Counter",
        "qty": trade['Qty']
    }
    return counter_order

def ant_create_hedge_counter_order(trade,user):
    counter_order = {
        "strategy": get_strategy_name_from_trade_id(trade['remarks']),
        "signal": get_signal_from_trade_id(trade['remarks']),
        "base_symbol": "NIFTY",   #WARNING: dummy base symbol 
        "exchange_token": int(trade['token']),     
        "transaction_type": calculate_transaction_type_sl(trade['Trantype']), 
        "order_type": 'MARKET',
        "product_type": trade['Pcode'],
        "trade_id": trade['remarks'],
        "order_mode": "Hedge",
        "qty": trade['Qty']
    }
    return counter_order