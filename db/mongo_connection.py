"""
This module provides a MongoConnection class for managing connections to a MongoDB database.

The MongoConnection class handles the initialization of the database connection
and provides methods to get specific collections. It uses the configuration from
db/__init__.py to ensure secure and flexible database access.

Classes:
    MongoConnection: Manages MongoDB database connections and collection access.

Usage:
    mongo = MongoConnection()
    collection = mongo.get_collection('your_collection_name')
    # Use the collection for database operations
    mongo.close()
"""

from pymongo import MongoClient
from . import db_config

class MongoConnection:
    def __init__(self):
        self._initialize()

    def _initialize(self):
        mongo_config = db_config['mongo']
        connection_string = f"mongodb://{mongo_config['user']}:{mongo_config['password']}@{mongo_config['host']}:{mongo_config['port']}/{mongo_config['name']}"

        self.client = MongoClient(connection_string)
        self.db = self.client[mongo_config['name']]

    def get_collection(self, collection_name):
        return self.db[collection_name]

    def close(self):
        self.client.close()

# Usage remains the same
