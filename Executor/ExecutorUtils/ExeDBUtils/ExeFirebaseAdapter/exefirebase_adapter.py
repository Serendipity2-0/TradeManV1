import json
import os
import sys

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, db

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

cred_filepath = os.getenv("FIREBASE_CRED_PATH")
firebase_db_url = os.getenv("FIREBASE_DATABASE_URL")
CLIENTS_DB = os.getenv("FIREBASE_USER_COLLECTION")

cred = credentials.Certificate(cred_filepath)
firebase_admin.initialize_app(cred, {"databaseURL": firebase_db_url})


def fetch_collection_data_firebase(collection, document=None):
    ref = db.reference(collection)
    if document is None:
        return ref.get()
    else:
        data = ref.child(document).get()
        return data


# delete the values in the firebase
def delete_fields_firebase(collection, document, field_key=None):
    if field_key is None:
        ref = db.reference(f"{collection}/{document}")
    else:
        ref = db.reference(f"{collection}/{document}/{field_key}")
    ref.delete()


def update_fields_firebase(collection, document, data, field_key=None):
    if field_key is None:
        ref = db.reference(f"{collection}/{document}")
    else:
        ref = db.reference(f"{collection}/{document}/{field_key}")
    ref.update(data)


def push_orders_firebase(collection, document, new_order, field_key=None):
    # Reference to the specific document
    if field_key is None:
        ref = db.reference(f"{collection}/{document}")
    else:
        ref = db.reference(f"{collection}/{document}/{field_key}")

    # Retrieve the current data
    current_data = ref.get()
    if current_data is None:
        # If there's no existing data, create a new list
        orders = [new_order]
    else:
        # If existing data is a dictionary, convert to a list
        if isinstance(current_data, dict):
            orders = list(current_data.values())
        else:
            # If it's already a list, just use it directly
            orders = current_data

        # Append the new order to the list
        orders.append(new_order)

    # Update Firebase with the modified list
    ref.set(orders)


# New function to get client by 'Tr_No'
def get_client_by_tr_no(tr_no):
    clients = fetch_collection_data_firebase(CLIENTS_DB)
    for client_key, client_data in clients.items():
        if client_data.get("Tr_No") == tr_no:
            return client_data
    return None


# New function to get strategy by 'StrategyName'
def get_strategy_by_name(strategy_name):
    strategies = fetch_collection_data_firebase("strategies")
    for strategy_key, strategy_data in strategies.items():
        if strategy_data.get("StrategyName") == strategy_name:
            return strategy_data
    return None


def download_client_as_json(tr_no, file_path):
    client_data = get_client_by_tr_no(tr_no)
    if client_data:
        with open(file_path, "w") as file:
            json.dump(client_data, file, indent=4)
        return f"Client data saved as JSON in {file_path}"
    else:
        return "Client not found."


def download_strategy_as_json(strategy_name, file_path):
    strategy_data = get_strategy_by_name(strategy_name)
    if strategy_data:
        with open(file_path, "w") as file:
            json.dump(strategy_data, file, indent=4)
        return f"Strategy data saved as JSON in {file_path}"
    else:
        return "Strategy not found."


def update_client_by_tr_no_from_file(tr_no, file_path):
    with open(file_path, "r") as file:
        modified_data = json.load(file)

    clients = fetch_collection_data_firebase(CLIENTS_DB)
    for client_key, client_data in clients.items():
        if client_data.get("Tr_No") == tr_no:
            update_fields_firebase(CLIENTS_DB, client_key, modified_data)
            return f"Client data with Tr_No {tr_no} updated successfully from file {file_path}."
    return "Client not found to update."


def update_strategy_by_name_from_file(strategy_name, file_path):
    with open(file_path, "r") as file:
        modified_data = json.load(file)

    strategies = fetch_collection_data_firebase("strategies")
    for strategy_key, strategy_data in strategies.items():
        if strategy_data.get("StrategyName") == strategy_name:
            update_fields_firebase("strategies", strategy_key, modified_data)
            return f"Strategy data for {strategy_name} updated successfully from file {file_path}."
    return "Strategy not found to update."


def update_maket_info_for_strategies():
    market_info = fetch_collection_data_firebase("market_info")
    strategies = fetch_collection_data_firebase("strategies")
    for strategy_key, strategy_data in strategies.items():
        strategy_data["market_info"] = market_info
        update_fields_firebase("strategies", strategy_key, strategy_data)
    return "Market info updated for all strategies."


def upload_client_data_to_firebase(user_dict):
    ref = db.reference("trademan_clients")
    ref.push(user_dict)
    return "Data uploaded successfully"
