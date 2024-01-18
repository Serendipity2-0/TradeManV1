import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, '.env')
load_dotenv(ENV_PATH)

ZERODHA = os.getenv('ZERODHA_BROKER')
ALICEBLUE = os.getenv('ALICEBLUE_BROKER')

# import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_login as alice_blue
# import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.kite_login as zerodha
import Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter as firebase_utils
import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter as alice_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter as zerodha_adapter

def place_order_for_broker(order_details,user_credentials):
    if order_details['broker'] == ZERODHA:
        return zerodha_adapter.place_order_zerodha(order_details,user_credentials)
    elif order_details['broker'] == ALICEBLUE:
        return alice_adapter.place_order_aliceblue(order_details,user_credentials)

def all_broker_login(active_users):
    for user in active_users:
        if user['Broker']['BrokerName'] == ZERODHA:
            print("Logging in for Zerodha")
            session_id = zerodha.login_in_zerodha(user['Broker'])
            print(f"Session id for {user['Broker']['BrokerUsername']}: {session_id}")
            firebase_utils.update_fields_firebase('new_clients',user['Tr_No'],{'SessionId':session_id}, 'Broker')          
        elif user['Broker']['BrokerName'] == ALICEBLUE:
            print("Logging in for AliceBlue")
            session_id = alice_blue.login_in_aliceblue(user['Broker'])
            print(f"Session id for {user['Broker']['BrokerUsername']}: {session_id}")
            firebase_utils.update_fields_firebase('new_clients',user['Tr_No'],{'SessionId':session_id}, 'Broker')
        else:
            print("Broker not supported") 
    return active_users

def fetch_active_users_from_firebase():
    active_users = []
    account_details = firebase_utils.fetch_collection_data_firebase('new_clients')
    for account in account_details:
        if account_details[account]['Active'] == True:
            active_users.append(account_details[account])
    return active_users

def fetch_primary_accounts_from_firebase(primary_account):
    #fetch the tr_no from .env file and fetch the primary account from firebase
    account_details = firebase_utils.fetch_collection_data_firebase('new_clients')
    for account in account_details:
        if account_details[account]['Tr_No'] == primary_account:
            return account_details[account]

def fetch_freecash_brokers(active_users):
    """Retrieves the cash margin available for a user based on their broker."""
    for user in active_users:
        if user['Broker']['BrokerName'] == ZERODHA:
            cash_margin = zerodha_adapter.zerodha_fetch_free_cash(user['Broker'])
        elif user['Broker']['BrokerName'] == ALICEBLUE:
            cash_margin = alice_adapter.alice_fetch_free_cash(user['Broker'])
        # Ensure cash_margin is a float
        return float(cash_margin) if cash_margin else 0.0
    return 0.0  # If user or broker not found

def download_csv_for_brokers(primary_account):
    if  primary_account['Broker']['BrokerName'] == ZERODHA:
        return zerodha_adapter.get_csv_kite(primary_account)  # Get CSV for this user
    elif primary_account['Broker']['BrokerName'] == ALICEBLUE:
        return alice_adapter.get_ins_csv_alice(primary_account)  # Get CSV for this user
    
def fetch_holdings_for_brokers(user):
    if  user['Broker']['BrokerName'] == ZERODHA:
        return zerodha_adapter.fetch_zerodha_holdings(user)  
    elif user['Broker']['BrokerName'] == ALICEBLUE:
        return alice_adapter.fetch_aliceblue_holdings(user)  
    
def fetch_user_credentials_firebase(broker_user_name):
    user_credentials = firebase_utils.fetch_collection_data_firebase('new_clients')
    for user in user_credentials:
        if user_credentials[user]['Broker']['BrokerUserName'] == broker_user_name:
            return user_credentials[user]['Broker']


