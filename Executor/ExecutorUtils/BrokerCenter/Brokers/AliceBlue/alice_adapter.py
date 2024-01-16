from pya3 import *


def alice_fetch_free_cash(user_details):
    alice = Aliceblue(user_details['BrokerUsername'], user_details['ApiKey'],session_id=user_details['SessionId'])
    balance_details = alice.get_balance()  # This method might have a different name

    # Search for 'cashmarginavailable' in the balance_details
    for item in balance_details:
        if isinstance(item, dict) and 'cashmarginavailable' in item:
            cash_margin_available = item.get('cashmarginavailable', 0)
            return float(cash_margin_available)
        
def get_csv_alice(user_details):
    alice = Aliceblue(user_id=user_details['BrokerUsername'], api_key=user_details['ApiKey'], session_id=user_details['SessionId'])
    alice.get_contract_master("NFO") #TODO rename the NFO.csv to alice_instruments.csv
    alice.get_contract_master("BFO") #TODO rename the NSE.csv to alice_instruments.csv

# def convert_instrument_csv_to_df():
#     alice_instrument_df = pd.read_csv('alice_instruments.csv')
#     return alice_instrument_df