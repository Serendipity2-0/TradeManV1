from dotenv import load_dotenv
import os, sys


DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_strategies_all_users
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import fetch_collection_data_firebase, upload_new_client_data_to_firebase

ACTIVE_STRATEGIES =  fetch_active_strategies_all_users()
ADMIN_DB = os.getenv("FIREBASE_ADMIN_COLLECTION")

def get_next_trader_number():
    admin_data = fetch_collection_data_firebase(ADMIN_DB)
    return admin_data.get("NextTradeManId", 0)

def update_new_client_data_to_db(trader_number, user_dict):
    upload_new_client_data_to_firebase(trader_number, user_dict)

