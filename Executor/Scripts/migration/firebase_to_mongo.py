"""
This script migrates data from Firebase JSON export to MongoDB.
It reads the JSON file and writes the data to MongoDB collections.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add project root to path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.ExeDBUtils.MongoUtils.exemongo_adapter import (
    db,
    CLIENTS_DB as MONGO_CLIENTS_DB,
    STRATEGIES_DB as MONGO_STRATEGIES_DB,
    ADMIN_DB as MONGO_ADMIN_DB
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

def load_firebase_data(json_file):
    """
    Load data from Firebase JSON export file.

    Args:
        json_file (str): Path to the Firebase JSON export file

    Returns:
        dict: The loaded JSON data
    """
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error loading JSON file: {str(e)}")
        return None

def migrate_collection(data, collection_name, mongo_collection):
    """
    Migrates data from Firebase JSON to MongoDB.

    Args:
        data (dict): The Firebase collection data
        collection_name (str): Name of the collection in Firebase JSON
        mongo_collection (str): Name of the MongoDB collection

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if collection_name not in data:
            logger.warning(f"Collection {collection_name} not found in Firebase data")
            return True

        collection_data = data[collection_name]
        if not collection_data:
            logger.warning(f"No data found in collection: {collection_name}")
            return True

        # Convert Firebase data format to MongoDB format
        mongo_data = []
        for key, value in collection_data.items():
            # Add Firebase key as document_id
            if isinstance(value, dict):
                value['document_id'] = key
                mongo_data.append(value)
            else:
                # Handle non-dict values (like NextTradeManId)
                mongo_data.append({'key': key, 'value': value})

        # Insert into MongoDB
        logger.info(f"Inserting {len(mongo_data)} documents into MongoDB collection: {mongo_collection}")
        collection = db[mongo_collection]
        
        # Drop existing collection to avoid duplicates
        collection.drop()
        
        # Insert new data
        if mongo_data:
            result = collection.insert_many(mongo_data)
            logger.info(f"Successfully inserted {len(result.inserted_ids)} documents")
            return True
        return True

    except Exception as e:
        logger.error(f"Error migrating collection {collection_name}: {str(e)}")
        return False

def main():
    """
    Main function to migrate all collections from Firebase JSON to MongoDB.
    """
    # Path to Firebase JSON export
    json_file = os.path.join(DIR_PATH, "trademanv1-default-rtdb-export.json")
    
    # Load Firebase data
    firebase_data = load_firebase_data(json_file)
    if not firebase_data:
        logger.error("Failed to load Firebase data")
        return

    # Collection mappings
    collections_mapping = [
        ('trademan_clients', MONGO_CLIENTS_DB),
        ('strategies', MONGO_STRATEGIES_DB),
        ('admin', MONGO_ADMIN_DB)
    ]

    success = True
    for firebase_col, mongo_col in collections_mapping:
        logger.info(f"Starting migration of {firebase_col} to {mongo_col}")
        if not migrate_collection(firebase_data, firebase_col, mongo_col):
            success = False
            logger.error(f"Failed to migrate {firebase_col}")
        else:
            logger.info(f"Successfully migrated {firebase_col} to {mongo_col}")

    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration completed with errors")

if __name__ == "__main__":
    main()
