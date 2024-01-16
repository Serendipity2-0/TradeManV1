import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, '.env')
load_dotenv(ENV_PATH)

ZERODHA = os.getenv('ZERODHA_BROKER')
ALICEBLUE = os.getenv('ALICEBLUE_BROKER')

import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_login as alice_blue
import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.kite_login as zerodha
import Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter as firebase_utils

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
