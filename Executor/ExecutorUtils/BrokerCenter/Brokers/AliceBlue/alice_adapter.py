from pya3 import *
import os, sys

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

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

def aliceblue_todays_tradebook(user):
    alice = create_alice_obj(user)
    orders = alice.get_order_history('')
    return orders