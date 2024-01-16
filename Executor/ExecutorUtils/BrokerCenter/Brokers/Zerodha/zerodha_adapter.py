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
    kite = KiteConnect(api_key=user_details['ApiKey'])
    kite.set_access_token(user_details['SessionId'])
    instrument_dump = kite.instruments()
    kite_instrument_df = pd.DataFrame(instrument_dump)
    return kite_instrument_df