from pya3 import *
import os, sys

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import discord_bot

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

    folder_path = os.path.join(DIR_PATH, 'SampleData')
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
    return Aliceblue(user_id=user_details['username'],api_key=user_details['api_key'],session_id=user_details['session_id'])

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
    if order_type == 'Stoploss':
        order_type = OrderType.StopLossLimit
    elif order_type == 'Market':
        order_type = OrderType.Market
    elif order_type == 'Limit':
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

def alice_place_order(order_details,user_credentials):
    """
    Place an order with Aliceblue broker.

    Args:
        alice (Aliceblue): The Aliceblue instance.
        order_details (dict): The details of the order.
        qty (int): The quantity of the order.

    Returns:
        float: The average price of the order.

    Raises:
        Exception: If the order placement fails.
    """  
    alice = create_alice_obj(user_credentials)
    strategy = order_details.get('strategy')
    exchange_token = order_details.get('exchange_token')
    qty = int(order_details.get('qty'))
    product = order_details.get('product_type')

    transaction_type = calculate_transaction_type(order_details.get('transaction_type'))
    order_type = calculate_order_type(order_details.get('order_type'))
    product_type = calculate_product_type(product)
    if product == 'CNC':
        segment = 'NSE'
    else:
        segment = Instrument().get_segment_by_exchange_token(exchange_token)


    limit_prc = order_details.get('limit_prc', None) 
    trigger_price = order_details.get('trigger_prc', None)

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
                                        order_tag = order_details.get('trade_id', None))
        
        print(f"Order placed. ID is: {order_id}")

        order_status = get_order_status(alice, order_id['NOrdNo'])
        if order_status == "FAIL":
            order_history = alice.get_order_history(order_id['NOrdNo'])
            message = (f"Order placement failed, Reason: {order_history['RejReason']} for {order_details['account_name']}")
            discord.discord_bot(message,strategy)

        return order_id['NOrdNo']
  
    except Exception as e:
        discord.discord_bot(e,strategy)
        return None

def update_alice_stoploss(order_details,alice= None):
    user_details = general_calc.assign_user_details(order_details.get('account_name'))
    if alice is None:
        alice = alice_utils.create_alice_obj(user_details)
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
    
def sweep_alice_orders(userdetails):
    try:
        alice = alice_utils.create_alice_obj(userdetails)
        orders = alice.get_order_history('')
        positions = alice.get_daywise_positions()
    except Exception as e:
        print(f"Failed to fetch orders and positions: {e}")
        return None

    if len(positions) == 2:
        print("No positions found")
    else:    
        buy_orders = []
        sell_orders = []

        token_quantities = {position['Token']: abs(int(position['Netqty'])) for position in positions if position['Pcode'] == 'MIS' and position['realisedprofitloss']=='0.00'}

        for token, quantity in token_quantities.items():
            base_symbol = Instrument().get_base_symbol_by_exchange_token(int(token))
            max_qty = FNOInfo().get_max_order_qty_by_base_symbol(base_symbol)  # Fetch max qty for the token
            remaining_qty = quantity

            for order in orders:
                if token == order['token'] and order['remarks'] is not None and order['Status'] == 'complete':
                    while remaining_qty > 0:
                        current_qty = min(remaining_qty, max_qty)
                        sweep_order = {
                            'trade_id': order['remarks'],
                            'exchange_token': int(order['token']),
                            'transaction_type': order['Trantype'],
                            'qty': current_qty
                        }
                        order_details = place_order_calc.create_sweep_order_details(userdetails, sweep_order)
                        if order_details['transaction_type'] == 'BUY':
                            buy_orders.append(order_details)
                        else:
                            sell_orders.append(order_details)
                        remaining_qty -= current_qty

        for pending_order in orders:
            if orders[0]['stat'] == 'Not_Ok':
                print("No orders found")
            elif pending_order['Status'] == 'trigger pending':
                print(pending_order['Nstordno'])
                alice.cancel_order(pending_order['Nstordno'])

        # Process BUY orders first
        for buy_order in buy_orders:
            print("Placing BUY order:", buy_order)
            process_aliceblue_order(buy_order, alice)
            sleep(0.1)

        # Then process SELL orders
        for sell_order in sell_orders:
            print("Placing SELL order:", sell_order)
            process_aliceblue_order(sell_order, alice)
            sleep(0.1)
