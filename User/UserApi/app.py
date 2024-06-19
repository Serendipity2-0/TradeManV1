import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)


import User.UserApi.schemas as schemas
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

CLIENTS_COLLECTION = os.getenv("FIREBASE_USER_COLLECTION")

# from UserDashboard.user_dashboard_utils import get_next_trader_number, update_new_client_data_to_db


def check_credentials(user_credentials: schemas.LoginUserDetails):
    """
    Checks the user credentials against the database.

    Args:
        user_credentials (schemas.LoginUserDetails): An object containing the user's credentials.

    Returns:
        bool: True if the credentials are valid, False otherwise.
    """
    users = fetch_collection_data_firebase(CLIENTS_COLLECTION)

    for trader_no, user in users.items():
        # Assuming user_name and password are top-level keys in each user dict
        if (
            user_credentials.Email == user["Profile"]["usr"]
            and user_credentials.Password == user["Profile"]["pwd"]
        ):
            return trader_no
    return None


def register_user(user_detail: schemas.UserDetails):
    """
    Registers a new user by adding the user details to the database.

    Args:
        user_detail (schemas.UserDetails): An object containing the user's details.
    """
    user_detail = dict(user_detail)
    logger.debug(user_detail)
    # update_new_client_data_to_db(get_next_trader_number(), user_detail)
    return {"message": "User registered successfully"}


def get_user_profile(tr_no: str):
    """
    Retrieves the user profile based on the trader number (tr_no).

    Args:
        tr_no (str): The trader number of the user.

    Returns:
        schemas.LoginUserDetails: An object containing the user's name, email, and phone number.

    Raises:
        KeyError: If the user with the given trader number is not found.
    """
    # Assume fetching user profile from a database
    users = fetch_collection_data_firebase(CLIENTS_COLLECTION)
    for user_id, user in users.items():
        if user["Tr_No"] == tr_no:
            strategies = []
            for strategy_name, strategy_data in user["Strategies"].items():
                strategies.append(strategy_name)
            profile_data = {
                "Name": user["Profile"]["Name"],
                "Email": user["Profile"]["Email"],
                "Phone": user["Profile"]["PhoneNumber"],
                "Date of Birth": user["Profile"]["DOB"],
                "Aadhar Card": user["Profile"]["AadharCardNo"],
                "Pan Card": user["Profile"]["PANCardNo"],
                "Bank Name": user["Profile"]["BankName"],
                "Bank Account Number": user["Profile"]["BankAccountNo"],
                "Broker Name": user["Broker"]["BrokerName"],
                "Strategies": strategies,
            }
            return profile_data
        else:
            raise KeyError("User not found")
