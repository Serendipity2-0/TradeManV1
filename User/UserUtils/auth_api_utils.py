"""
Authentication and user management utility functions.
"""

import os
from typing import Dict, Optional
from dotenv import load_dotenv
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    update_fields_firebase,
)

DIR_PATH = os.getcwd()
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

logger = LoggerSetup()

CLIENTS_COLLECTION = os.getenv("FIREBASE_USER_COLLECTION")

def check_credentials(user_credentials: Dict) -> Optional[str]:
    """
    Verify user credentials and return trader number if valid.

    Args:
        user_credentials (Dict): Dictionary containing user credentials.
            Expected keys: 'email', 'password'

    Returns:
        Optional[str]: Trader number if credentials are valid, None otherwise.
    """
    try:
        users_data = fetch_collection_data_firebase(CLIENTS_COLLECTION)
        
        for tr_no, user_data in users_data.items():
            profile = user_data.get("Profile", {})
            if (profile.get("Email") == user_credentials["email"] and 
                profile.get("Password") == user_credentials["password"]):
                return tr_no
        return None
    except Exception as e:
        logger.error(f"Error checking credentials: {e}")
        return None

def store_profile_data(user_id: str, profile_data: Dict) -> Dict:
    """
    Store user profile data in Firebase.

    Args:
        user_id (str): The user's ID.
        profile_data (Dict): The profile data to store.

    Returns:
        Dict: The stored profile data.
    """
    try:
        update_fields_firebase(CLIENTS_COLLECTION, user_id, profile_data, "Profile")
        return profile_data
    except Exception as e:
        logger.error(f"Error storing profile data: {e}")
        raise

def store_broker_data(user_id: str, broker_data: Dict) -> Dict:
    """
    Store user broker data in Firebase.

    Args:
        user_id (str): The user's ID.
        broker_data (Dict): The broker data to store.

    Returns:
        Dict: The stored broker data.
    """
    try:
        update_fields_firebase(CLIENTS_COLLECTION, user_id, broker_data, "Broker")
        return broker_data
    except Exception as e:
        logger.error(f"Error storing broker data: {e}")
        raise

def store_accounts_data(user_id: str, accounts_data: Dict) -> Dict:
    """
    Store user accounts data in Firebase.

    Args:
        user_id (str): The user's ID.
        accounts_data (Dict): The accounts data to store.

    Returns:
        Dict: The stored accounts data.
    """
    try:
        update_fields_firebase(CLIENTS_COLLECTION, user_id, accounts_data, "Accounts")
        return accounts_data
    except Exception as e:
        logger.error(f"Error storing accounts data: {e}")
        raise

def store_strategies_data(user_id: str, strategies_data: Dict) -> Dict:
    """
    Store user strategies data in Firebase.

    Args:
        user_id (str): The user's ID.
        strategies_data (Dict): The strategies data to store.

    Returns:
        Dict: The stored strategies data.
    """
    try:
        update_fields_firebase(CLIENTS_COLLECTION, user_id, strategies_data, "Strategies")
        return strategies_data
    except Exception as e:
        logger.error(f"Error storing strategies data: {e}")
        raise

def update_tr_no(user_id: str, tr_no: str) -> Dict:
    """
    Update user's trader number in Firebase.

    Args:
        user_id (str): The user's ID.
        tr_no (str): The trader number to set.

    Returns:
        Dict: The updated trader number data.
    """
    try:
        tr_no_data = {"Tr_No": tr_no}
        update_fields_firebase(CLIENTS_COLLECTION, user_id, tr_no_data)
        return tr_no_data
    except Exception as e:
        logger.error(f"Error updating trader number: {e}")
        raise

def merge_and_register_user(user_id: str) -> Dict:
    """
    Merge and register user data in Firebase.

    Args:
        user_id (str): The user's ID.

    Returns:
        Dict: The merged and registered user data.
    """
    try:
        user_data = fetch_collection_data_firebase(CLIENTS_COLLECTION, user_id)
        if not user_data:
            raise ValueError(f"No data found for user {user_id}")
        return user_data
    except Exception as e:
        logger.error(f"Error merging and registering user: {e}")
        raise

def get_user_profile(tr_no: str) -> Dict:
    """
    Get user profile data from Firebase.

    Args:
        tr_no (str): The trader number.

    Returns:
        Dict: The user profile data.
    """
    try:
        user_data = fetch_collection_data_firebase(CLIENTS_COLLECTION, tr_no)
        if not user_data:
            raise ValueError(f"No data found for user {tr_no}")
        return user_data.get("Profile", {})
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise
