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

# Environment-specific credentials path
if "GITHUB_WORKSPACE" in os.environ:
    # Path when running in GitHub Actions
    cred_filepath = "./firebase_credentials.json"
else:
    # Local development path from .env
    cred_filepath = os.getenv("FIREBASE_CRED_PATH")


firebase_db_url = os.getenv("FIREBASE_DATABASE_URL")
CLIENTS_DB = os.getenv("FIREBASE_USER_COLLECTION")
STRATEGIES_DB = os.getenv("FIREBASE_STRATEGY_COLLECTION")
ADMIN_DB = os.getenv("FIREBASE_ADMIN_COLLECTION")

cred = credentials.Certificate(cred_filepath)
firebase_admin.initialize_app(cred, {"databaseURL": firebase_db_url})


def fetch_collection_data_firebase(collection, document=None):
    """
    Fetches data from a specified Firebase collection.

    Args:
        collection (str): The name of the Firebase collection.
        document (str, optional): The specific document within the collection. Defaults to None.

    Returns:
        dict: The data from the specified collection/document.
    """
    ref = db.reference(collection)
    if document is None:
        return ref.get()
    else:
        data = ref.child(document).get()
        return data


def delete_fields_firebase(collection, document, field_key=None):
    """
    Deletes specified fields from a Firebase document.

    Args:
        collection (str): The name of the Firebase collection.
        document (str): The specific document within the collection.
        field_key (str, optional): The specific field key to delete. Defaults to None.

    Returns:
        None
    """
    if field_key is None:
        ref = db.reference(f"{collection}/{document}")
    else:
        ref = db.reference(f"{collection}/{document}/{field_key}")
    ref.delete()


def update_fields_firebase(collection, document, data, field_key=None):
    """
    Updates specified fields in a Firebase document.

    Args:
        collection (str): The name of the Firebase collection.
        document (str): The specific document within the collection.
        data (dict): The data to update.
        field_key (str, optional): The specific field key to update. Defaults to None.

    Returns:
        None
    """
    if field_key is None:
        ref = db.reference(f"{collection}/{document}")
    else:
        ref = db.reference(f"{collection}/{document}/{field_key}")
    ref.update(data)


def push_orders_firebase(collection, document, new_order, field_key=None):
    """
    Pushes new orders to a specified Firebase document.

    Args:
        collection (str): The name of the Firebase collection.
        document (str): The specific document within the collection.
        new_order (dict): The new order to add.
        field_key (str, optional): The specific field key to update. Defaults to None.

    Returns:
        None
    """
    if field_key is None:
        ref = db.reference(f"{collection}/{document}")
    else:
        ref = db.reference(f"{collection}/{document}/{field_key}")

    current_data = ref.get()
    if current_data is None:
        orders = [new_order]
    else:
        if isinstance(current_data, dict):
            orders = list(current_data.values())
        else:
            orders = current_data
        orders.append(new_order)

    ref.set(orders)


def get_client_by_tr_no(tr_no):
    """
    Retrieves client data based on trader number (Tr_No).

    Args:
        tr_no (str): The trader number.

    Returns:
        dict: The client data.
    """
    clients = fetch_collection_data_firebase(CLIENTS_DB)
    for client_key, client_data in clients.items():
        if client_data.get("Tr_No") == tr_no:
            return client_data
    return None


def get_strategy_by_name(strategy_name):
    """
    Retrieves strategy data based on strategy name.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        dict: The strategy data.
    """
    strategies = fetch_collection_data_firebase(STRATEGIES_DB)
    for strategy_key, strategy_data in strategies.items():
        if strategy_data.get("StrategyName") == strategy_name:
            return strategy_data
    return None


def download_client_as_json(tr_no, file_path):
    """
    Downloads client data as a JSON file based on trader number (Tr_No).

    Args:
        tr_no (str): The trader number.
        file_path (str): The file path to save the JSON data.

    Returns:
        str: Success or failure message.
    """
    client_data = get_client_by_tr_no(tr_no)
    if client_data:
        with open(file_path, "w") as file:
            json.dump(client_data, file, indent=4)
        return f"Client data saved as JSON in {file_path}"
    else:
        return "Client not found."


def download_strategy_as_json(strategy_name, file_path):
    """
    Downloads strategy data as a JSON file based on strategy name.

    Args:
        strategy_name (str): The name of the strategy.
        file_path (str): The file path to save the JSON data.

    Returns:
        str: Success or failure message.
    """
    strategy_data = get_strategy_by_name(strategy_name)
    if strategy_data:
        with open(file_path, "w") as file:
            json.dump(strategy_data, file, indent=4)
        return f"Strategy data saved as JSON in {file_path}"
    else:
        return "Strategy not found."


def update_client_by_tr_no_from_file(tr_no, file_path):
    """
    Updates client data from a JSON file based on trader number (Tr_No).

    Args:
        tr_no (str): The trader number.
        file_path (str): The file path to the JSON data.

    Returns:
        str: Success or failure message.
    """
    with open(file_path, "r") as file:
        modified_data = json.load(file)

    clients = fetch_collection_data_firebase(CLIENTS_DB)
    for client_key, client_data in clients.items():
        if client_data.get("Tr_No") == tr_no:
            update_fields_firebase(CLIENTS_DB, client_key, modified_data)
            return f"Client data with Tr_No {tr_no} updated successfully from file {file_path}."
    return "Client not found to update."


def update_strategy_by_name_from_file(strategy_name, file_path):
    """
    Updates strategy data from a JSON file based on strategy name.

    Args:
        strategy_name (str): The name of the strategy.
        file_path (str): The file path to the JSON data.

    Returns:
        str: Success or failure message.
    """
    with open(file_path, "r") as file:
        modified_data = json.load(file)

    strategies = fetch_collection_data_firebase("strategies")
    for strategy_key, strategy_data in strategies.items():
        if strategy_data.get("StrategyName") == strategy_name:
            update_fields_firebase("strategies", strategy_key, modified_data)
            return f"Strategy data for {strategy_name} updated successfully from file {file_path}."
    return "Strategy not found to update."


def upload_collection(collection, data):
    """
    Uploads data to a specified Firebase collection.

    Args:
        collection (str): The name of the Firebase collection.
        data (dict): The data to upload.

    Returns:
        str: Success message.
    """
    ref = db.reference(collection)
    ref.push(data)
    return "Data uploaded successfully"


def update_collection(collection, data):
    """
    Updates data in a specified Firebase collection.

    Args:
        collection (str): The name of the Firebase collection.
        data (dict): The data to update.

    Returns:
        str: Success message.
    """
    ref = db.reference(collection)
    ref.update(data)
    return "Data updated successfully"


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
