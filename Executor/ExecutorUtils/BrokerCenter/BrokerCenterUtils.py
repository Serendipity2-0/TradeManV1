import os
import sys

from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, '.env')
load_dotenv(ENV_PATH)

ZERODHA = os.getenv('ZERODHA_BROKER')
ALICEBLUE = os.getenv('ALICEBLUE_BROKER')

import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter as alice_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_login as alice_blue
import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.kite_login as zerodha
import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter as zerodha_adapter
import Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter as firebase_utils


def place_order_for_brokers(order_details,user_credentials):
    if order_details['broker'] == ZERODHA:
        return zerodha_adapter.kite_place_orders_for_users(order_details,user_credentials)
    elif order_details['broker'] == ALICEBLUE:
        return alice_adapter.ant_place_orders_for_users(order_details,user_credentials)

def modify_order_for_brokers(order_details,user_credentials):
    if order_details['broker'] == ZERODHA:
        return zerodha_adapter.kite_modify_orders_for_users(order_details,user_credentials)
    elif order_details['broker'] == ALICEBLUE:
        return alice_adapter.ant_modify_orders_for_users(order_details,user_credentials)

def all_broker_login(active_users):
    for user in active_users:
        if user['Broker']['BrokerName'] == ZERODHA:
            print("Logging in for Zerodha")
            session_id = zerodha.login_in_zerodha(user['Broker'])
            firebase_utils.update_fields_firebase('new_clients',user['Tr_No'],{'SessionId':session_id}, 'Broker')          
        elif user['Broker']['BrokerName'] == ALICEBLUE:
            print("Logging in for AliceBlue")
            session_id = alice_blue.login_in_aliceblue(user['Broker'])
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
        if user_credentials[user]['Broker']['BrokerUsername'] == broker_user_name:
            return user_credentials[user]['Broker']
        
def get_today_orders_for_brokers(user):
    import json
    with open('/Users/amolkittur/Desktop/TradeManV1/SampleData/kite_orders.json') as f:
        kite_data = json.load(f)
    with open('/Users/amolkittur/Desktop/TradeManV1/SampleData/aliceblue_orders.json') as f:
        alice_data = json.load(f)

    if  user['Broker']['BrokerName'] == ZERODHA:
        # return zerodha_adapter.zerodha_todays_tradebook(user['Broker'])
        return kite_data
    
    elif user['Broker']['BrokerName'] == ALICEBLUE:
        # return alice_adapter.aliceblue_todays_tradebook(user['Broker'])
        return alice_data
    
def create_counter_order_details(tradebook,user):
    counter_order_details = []
    for trade in tradebook:
        if user['Broker']['BrokerName'] == ZERODHA:
            if trade['status'] == 'TRIGGER PENDING' and trade['product'] == 'MIS':
                # cancel_order = zerodha_adapter.create_cancel_order(trade, user)
                counter_order = zerodha_adapter.kite_create_sl_counter_order(trade, user)
                counter_order_details.append(counter_order)
        elif user['Broker']['BrokerName'] == ALICEBLUE:
            if trade['Status'] == 'trigger pending' and trade['Pcode'] == 'MIS':
                # cancel_order = alice_adapter.create_cancel_order(trade, user)
                counter_order = alice_adapter.ant_create_counter_order(trade, user)
                counter_order_details.append(counter_order)
    return counter_order_details

def create_hedge_counter_order_details(tradebook,user):
    hedge_counter_order = []
    for trade in tradebook:
        if user['Broker']['BrokerName'] == ZERODHA:
            if trade['status'] == 'COMPLETE' and trade['product'] == 'MIS' and 'HO_EN' in trade['tag'] and 'HO_EX' not in trade['tag']:
                counter_order = zerodha_adapter.kite_create_hedge_counter_order(trade, user)
                hedge_counter_order.append(counter_order)
        elif user['Broker']['BrokerName'] == ALICEBLUE:
            if trade['Status'] == 'complete' and trade['Pcode'] == 'MIS' and 'HO_EN' in trade['ordersource'] and 'HO_EX' not in trade['ordersource']:
                counter_order = alice_adapter.ant_create_hedge_counter_order(trade, user)
                hedge_counter_order.append(counter_order)
    return hedge_counter_order

def get_avg_prc_broker_key(broker_name):
    if broker_name == ZERODHA:
        return 'average_price'
    elif broker_name == ALICEBLUE:
        return 'Avgprc'
    
def get_order_id_broker_key(broker_name):
    if broker_name == ZERODHA:
        return 'order_id'
    elif broker_name == ALICEBLUE:
        return 'Nstordno'