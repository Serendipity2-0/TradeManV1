import json
import os
import sys

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, db

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, '.env')
load_dotenv(ENV_PATH)

cred_filepath = os.getenv('FIREBASE_CRED_PATH')
firebase_db_url = os.getenv('FIREBASE_DATABASE_URL')

cred = credentials.Certificate(cred_filepath)
firebase_admin.initialize_app(cred, {
    'databaseURL': firebase_db_url
})

def fetch_collection_data_firebase(collection, document=None):
    ref = db.reference(collection)
    if document is None:
        return ref.get()
    else:
        data = ref.child(document).get()
        return data

def update_fields_firebase(collection, document, data, field_key=None):
    if field_key is None:
        ref = db.reference(f'{collection}/{document}')
    else:
        ref = db.reference(f'{collection}/{document}/{field_key}')
    ref.update(data)

# New function to get client by 'Tr_No'
def get_client_by_tr_no(tr_no):
    clients = fetch_collection_data_firebase('new_clients')
    for client_key, client_data in clients.items():
        if client_data.get('Tr_No') == tr_no:
            return client_data
    return None

# New function to get strategy by 'StrategyName'
def get_strategy_by_name(strategy_name):
    strategies = fetch_collection_data_firebase('strategies')
    for strategy_key, strategy_data in strategies.items():
        if strategy_data.get('StrategyName') == strategy_name:
            return strategy_data
    return None

def download_client_as_json(tr_no, file_path):
    client_data = get_client_by_tr_no(tr_no)
    if client_data:
        with open(file_path, 'w') as file:
            json.dump(client_data, file, indent=4)
        return f"Client data saved as JSON in {file_path}"
    else:
        return "Client not found."

def download_strategy_as_json(strategy_name, file_path):
    strategy_data = get_strategy_by_name(strategy_name)
    if strategy_data:
        with open(file_path, 'w') as file:
            json.dump(strategy_data, file, indent=4)
        return f"Strategy data saved as JSON in {file_path}"
    else:
        return "Strategy not found."

def update_client_by_tr_no_from_file(tr_no, file_path):
    with open(file_path, 'r') as file:
        modified_data = json.load(file)
    
    clients = fetch_collection_data_firebase('new_clients')
    for client_key, client_data in clients.items():
        if client_data.get('Tr_No') == tr_no:
            update_fields_firebase('new_clients', client_key, modified_data)
            return f"Client data with Tr_No {tr_no} updated successfully from file {file_path}."
    return "Client not found to update."

def update_strategy_by_name_from_file(strategy_name, file_path):
    with open(file_path, 'r') as file:
        modified_data = json.load(file)
    
    strategies = fetch_collection_data_firebase('strategies')
    for strategy_key, strategy_data in strategies.items():
        if strategy_data.get('StrategyName') == strategy_name:
            update_fields_firebase('strategies', strategy_key, modified_data)
            return f"Strategy data for {strategy_name} updated successfully from file {file_path}."
    return "Strategy not found to update."

# result = download_client_as_json('Tr00', 'Tr00.json')
# print(result)

# result = download_strategy_as_json('AmiPy', 'AmiPy.json')
# print(result)


# Update client data from a JSON file
# update_result = update_client_by_tr_no_from_file('Tr00', 'Tr00.json')
# print(update_result)

# # Update strategy data from a JSON file
# update_result = update_strategy_by_name_from_file('AmiPy', 'AmiPy.json')
# print(update_result)


