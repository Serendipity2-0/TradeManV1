import firebase_admin
from firebase_admin import credentials, initialize_app, get_app
from firebase_admin import db
import json
import datetime
import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import app

cred_filepath = os.getenv("FIREBASE_CRED_PATH")
firebase_db_url = os.getenv("FIREBASE_DATABASE_URL")
CLIENTS_DB = os.getenv("FIREBASE_USER_COLLECTION")
STRATEGIES_DB = os.getenv("FIREBASE_STRATEGY_COLLECTION")
ADMIN_DB = os.getenv("FIREBASE_ADMIN_COLLECTION")


def upload_new_client_data_to_firebase(trader_number, user_dict):
    """
    Uploads new client data to Firebase based on trader number.

    Args:
        trader_number (str): The trader number.
        user_dict (dict): The user data to upload.

    Returns:
        str: Success message.
    """
    ref = db.reference(CLIENTS_DB)
    new_ref = ref.child(trader_number)
    new_ref.set(user_dict)
    return "Data uploaded successfully"
