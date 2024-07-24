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
EOD_JSON_DIR = os.getenv("EOD_JSON_DIR")


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


def download_firebase_json(path, status):
    # Get the current date and time
    now = datetime.datetime.now()
    date_time = now.strftime("%d%b")

    # Set the reference for the data download
    ref = db.reference(path)  # Replace with your desired reference path

    # Download the data
    data = ref.get()

    # Save the data to a file with the current date and time
    file_name = f"{date_time}_{status}.json"
    with open(f"{EOD_JSON_DIR}/{file_name}", "w") as file:
        json.dump(data, file, indent=4)
