from pya3 import *
import os, sys

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)


def alice_fetch_free_cash(user_details):
    alice = Aliceblue(user_details['BrokerUsername'], user_details['ApiKey'],session_id=user_details['SessionId'])
    balance_details = alice.get_balance()  # This method might have a different name

    # Search for 'cashmarginavailable' in the balance_details
    for item in balance_details:
        if isinstance(item, dict) and 'cashmarginavailable' in item:
            cash_margin_available = item.get('cashmarginavailable', 0)
            return float(cash_margin_available)
        
def merge_csv_files(merge_column='Token'):
    #i will provide the folder path of the csv and the list of file names to be merged
    folder_path = os.path.join(DIR_PATH, 'SampleData')
    ins_files = ['NFO.csv', 'BFO.csv', 'NSE.csv']
    file_paths = [os.path.join(folder_path, file) for file in ins_files]
    # Initialize an empty DataFrame for the merged data
    merged_df = pd.DataFrame()

    for file_path in file_paths:
        # Read the current CSV file
        current_df = pd.read_csv(file_path)

        # Merge with the existing DataFrame
        if merged_df.empty:
            merged_df = current_df
        else:
            merged_df = pd.merge(merged_df, current_df, on=merge_column, how='outer', suffixes=('', '_dup'))

    # Remove duplicate columns generated from merging
    merged_df = merged_df.loc[:,~merged_df.columns.str.endswith('_dup')]
    return merged_df

def get_csv_alice(user_details):
    alice = Aliceblue(user_id=user_details['Broker']['BrokerUsername'], api_key=user_details['Broker']['ApiKey'], session_id=user_details['Broker']['SessionId'])
    alice.get_contract_master("NFO") #TODO rename the NFO.csv to alice_instruments.csv
    alice.get_contract_master("BFO") #TODO rename the NSE.csv to alice_instruments.csv
    alice_instrument_merged = merge_csv_files()
    return alice_instrument_merged