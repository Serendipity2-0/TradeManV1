import os
import sys

from pymongo import MongoClient

import pandas as pd
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


# Initialize MongoDB client
client = MongoClient("mongodb://localhost:27017/")  # Adjust the connection string as needed
db = client["your_database_name"]  # Replace 'your_database_name' with your database name

def fetch_collection_data_mongodb(collection, document_id=None):
    collection_ref = db[collection]
    if document_id is None:
        return list(collection_ref.find())
    else:
        return collection_ref.find_one({"_id": document_id})

def delete_fields_mongodb(collection, document_id, field_key=None):
    collection_ref = db[collection]
    if field_key is None:
        collection_ref.delete_one({"_id": document_id})
    else:
        collection_ref.update_one({"_id": document_id}, {"$unset": {field_key: ""}})

def update_fields_mongodb(collection, document_id, data, field_key=None):
    collection_ref = db[collection]
    if field_key is None:
        collection_ref.update_one({"_id": document_id}, {"$set": data}, upsert=True)
    else:
        collection_ref.update_one({"_id": document_id}, {"$set": {field_key: data}}, upsert=True)

def push_orders_mongodb(collection, document_id, new_order, field_key=None):
    collection_ref = db[collection]
    if field_key is None:
        collection_ref.update_one({"_id": document_id}, {"$push": {"orders": new_order}}, upsert=True)
    else:
        collection_ref.update_one({"_id": document_id}, {"$push": {f"{field_key}.orders": new_order}}, upsert=True)

def get_client_by_tr_no(tr_no):
    clients = fetch_collection_data_mongodb(CLIENTS_DB)  # Ensure CLIENTS_DB is defined and points to your clients collection
    for client in clients:
        if client.get("Tr_No") == tr_no:
            return client
    return None

def get_strategy_by_name(strategy_name):
    strategies = fetch_collection_data_mongodb("strategies")
    for strategy in strategies:
        if strategy.get("StrategyName") == strategy_name:
            return strategy
    return None