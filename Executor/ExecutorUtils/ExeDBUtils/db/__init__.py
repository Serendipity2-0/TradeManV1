"""
This module initializes the database configuration by loading environment variables.
It provides a configuration dictionary that can be imported and used in other modules.
"""

import os
from dotenv import load_dotenv

# Get the project root directory (4 levels up from this file)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
# Construct the path to the environment file
ENV_PATH = os.path.join(PROJECT_ROOT, "trademan.env")

# Load environment variables from the specified file
load_dotenv(ENV_PATH)

db_config = {
    "postgres": {
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT", "5432"),
        "name": os.getenv("DB_NAME"),
    },
    "mongo": {
        'user': os.getenv('MONGO_USER', 'admin'),
        'password': os.getenv('MONGO_PASSWORD', 'admin'),
        'host': os.getenv('MONGO_HOST', 'localhost'),
        'port': os.getenv('MONGO_PORT', '27017'),
        'name': os.getenv('MONGO_DB', 'trademan'),
    }
}
