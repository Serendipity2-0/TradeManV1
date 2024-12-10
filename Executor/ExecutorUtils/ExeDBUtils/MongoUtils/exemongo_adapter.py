"""
This module provides MongoDB adapter functionality for the TradeMan application.
It includes methods for CRUD operations and specific data retrieval functions.
"""

import json
import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from db import db_config
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

# Initialize MongoDB client using configuration
mongo_config = db_config['mongo']
connection_string = f"mongodb://{mongo_config['user']}:{mongo_config['password']}@{mongo_config['host']}:{mongo_config['port']}"
client = MongoClient(connection_string)
db = client[mongo_config['name']]

# Collection names from environment variables
CLIENTS_DB = os.getenv("MONGO_USER_COLLECTION", "clients")
STRATEGIES_DB = os.getenv("MONGO_STRATEGY_COLLECTION", "strategies")
ADMIN_DB = os.getenv("MONGO_ADMIN_COLLECTION", "admin")

def fetch_collection_data_mongodb(collection, document_id=None):
    """
    Fetches data from a specified MongoDB collection.

    Args:
        collection (str): The name of the MongoDB collection.
        document_id (str, optional): The specific document ID within the collection. Defaults to None.

    Returns:
        list or dict: The data from the specified collection or document.
    """
    try:
        collection_ref = db[collection]
        if document_id is None:
            # Convert cursor to list and remove MongoDB _id field for compatibility
            data = list(collection_ref.find({}, {'_id': 0}))
            return {str(i): doc for i, doc in enumerate(data)} if data else None
        else:
            return collection_ref.find_one({"_id": document_id}, {'_id': 0})
    except Exception as e:
        logger.error(f"Error fetching data from MongoDB: {str(e)}")
        return None

def delete_fields_mongodb(collection, document_id, field_key=None):
    """
    Deletes specified fields from a MongoDB document.

    Args:
        collection (str): The name of the MongoDB collection.
        document_id (str): The specific document ID within the collection.
        field_key (str, optional): The specific field key to delete. Defaults to None.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        collection_ref = db[collection]
        if field_key is None:
            result = collection_ref.delete_one({"_id": document_id})
        else:
            result = collection_ref.update_one({"_id": document_id}, {"$unset": {field_key: ""}})
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error deleting fields in MongoDB: {str(e)}")
        return False

def update_fields_mongodb(collection, document_id, data, field_key=None):
    """
    Updates specified fields in a MongoDB document.

    Args:
        collection (str): The name of the MongoDB collection.
        document_id (str): The specific document ID within the collection.
        data (dict): The data to update.
        field_key (str, optional): The specific field key to update. Defaults to None.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        collection_ref = db[collection]
        update_data = {field_key: data} if field_key else data
        result = collection_ref.update_one(
            {"_id": document_id},
            {"$set": update_data},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        logger.error(f"Error updating fields in MongoDB: {str(e)}")
        return False

def push_orders_mongodb(collection, document_id, new_order, field_key=None):
    """
    Pushes new orders to a specified MongoDB document.

    Args:
        collection (str): The name of the MongoDB collection.
        document_id (str): The specific document ID within the collection.
        new_order (dict): The new order to add.
        field_key (str, optional): The specific field key to update. Defaults to None.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        collection_ref = db[collection]
        update_field = f"{field_key}.orders" if field_key else "orders"
        
        # First, get current orders
        doc = collection_ref.find_one({"_id": document_id})
        if doc is None:
            # Initialize with first order
            result = collection_ref.insert_one({
                "_id": document_id,
                update_field: [new_order]
            })
            return result.inserted_id is not None
        else:
            # Append to existing orders
            result = collection_ref.update_one(
                {"_id": document_id},
                {"$push": {update_field: new_order}}
            )
            return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error pushing orders to MongoDB: {str(e)}")
        return False

def get_client_by_tr_no(tr_no):
    """
    Retrieves client data based on trader number (Tr_No).

    Args:
        tr_no (str): The trader number.

    Returns:
        dict: The client data.
    """
    try:
        collection_ref = db[CLIENTS_DB]
        return collection_ref.find_one({"Tr_No": tr_no}, {'_id': 0})
    except Exception as e:
        logger.error(f"Error getting client by Tr_No from MongoDB: {str(e)}")
        return None

def get_strategy_by_name(strategy_name):
    """
    Retrieves strategy data based on strategy name.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        dict: The strategy data.
    """
    try:
        collection_ref = db[STRATEGIES_DB]
        return collection_ref.find_one({"StrategyName": strategy_name}, {'_id': 0})
    except Exception as e:
        logger.error(f"Error getting strategy by name from MongoDB: {str(e)}")
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
        try:
            with open(file_path, "w") as file:
                json.dump(client_data, file, indent=4)
            return f"Client data saved as JSON in {file_path}"
        except Exception as e:
            logger.error(f"Error saving client data to JSON: {str(e)}")
            return f"Error saving client data: {str(e)}"
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
        try:
            with open(file_path, "w") as file:
                json.dump(strategy_data, file, indent=4)
            return f"Strategy data saved as JSON in {file_path}"
        except Exception as e:
            logger.error(f"Error saving strategy data to JSON: {str(e)}")
            return f"Error saving strategy data: {str(e)}"
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
    try:
        with open(file_path, "r") as file:
            modified_data = json.load(file)
        
        collection_ref = db[CLIENTS_DB]
        result = collection_ref.update_one(
            {"Tr_No": tr_no},
            {"$set": modified_data}
        )
        
        if result.modified_count > 0:
            return f"Client data with Tr_No {tr_no} updated successfully from file {file_path}."
        return "Client not found to update."
    except Exception as e:
        logger.error(f"Error updating client from file: {str(e)}")
        return f"Error updating client: {str(e)}"

def update_strategy_by_name_from_file(strategy_name, file_path):
    """
    Updates strategy data from a JSON file based on strategy name.

    Args:
        strategy_name (str): The name of the strategy.
        file_path (str): The file path to the JSON data.

    Returns:
        str: Success or failure message.
    """
    try:
        with open(file_path, "r") as file:
            modified_data = json.load(file)
        
        collection_ref = db[STRATEGIES_DB]
        result = collection_ref.update_one(
            {"StrategyName": strategy_name},
            {"$set": modified_data}
        )
        
        if result.modified_count > 0:
            return f"Strategy data for {strategy_name} updated successfully from file {file_path}."
        return "Strategy not found to update."
    except Exception as e:
        logger.error(f"Error updating strategy from file: {str(e)}")
        return f"Error updating strategy: {str(e)}"

def upload_collection(collection, data):
    """
    Uploads data to a specified MongoDB collection.

    Args:
        collection (str): The name of the MongoDB collection.
        data (dict): The data to upload.

    Returns:
        str: Success or failure message.
    """
    try:
        collection_ref = db[collection]
        result = collection_ref.insert_one(data)
        return "Data uploaded successfully" if result.inserted_id else "Failed to upload data"
    except Exception as e:
        logger.error(f"Error uploading data to MongoDB: {str(e)}")
        return f"Error uploading data: {str(e)}"

def update_collection(collection, data):
    """
    Updates data in a specified MongoDB collection.

    Args:
        collection (str): The name of the MongoDB collection.
        data (dict): The data to update.

    Returns:
        str: Success or failure message.
    """
    try:
        collection_ref = db[collection]
        result = collection_ref.update_many({}, {"$set": data})
        return "Data updated successfully" if result.modified_count > 0 else "No documents updated"
    except Exception as e:
        logger.error(f"Error updating collection in MongoDB: {str(e)}")
        return f"Error updating collection: {str(e)}"
