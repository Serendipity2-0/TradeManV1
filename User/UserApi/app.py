import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# importing packages
import User.UserApi.schemas as schemas
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from User.UserApi.userapi_utils import (
    ACTIVE_STRATEGIES,
    get_next_trader_number,
    update_new_client_data_to_db,
    all_users_data,
    create_portfolio_stats,
    get_monthly_returns_data,
    get_weekly_cumulative_returns_data,
)

logger = LoggerSetup()


def check_credentials(user_credentials: schemas.LoginUserDetails):
    """
    Checks the user credentials against the database.

    Args:
        user_credentials (schemas.LoginUserDetails): An object containing the user's credentials.

    Returns:
        trader_no if the credentials are valid, None otherwise.
    """
    users_data = all_users_data()

    for trader_no, user in users_data.items():
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
    update_new_client_data_to_db(get_next_trader_number(), user_detail)
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
    users_data = all_users_data()
    for user_id, user in users_data.items():
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


def get_portfolio_stats(tr_no: str):
    """
    Retrieves the portfolio stats view for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    dict: The portfolio stats view.
    """
    # Assume fetching user profile from a database
    USER_DB_FOLDER_PATH = os.getenv("DB_DIR")
    users_db_path = os.path.join(USER_DB_FOLDER_PATH, f"{tr_no}.db")
    user_stats = create_portfolio_stats(users_db_path)
    # TODO: Check if latest account value is required for plotting the graph
    return user_stats


def monthly_returns_data(tr_no: str):
    """
    Retrieves the monthly returns data for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    dict: The monthly returns data.
    """
    # Assume fetching user profile from a database
    USER_DB_FOLDER_PATH = os.getenv("DB_DIR")
    users_db_path = os.path.join(USER_DB_FOLDER_PATH, f"{tr_no}.db")
    user_stats = create_portfolio_stats(users_db_path)
    return get_monthly_returns_data(user_stats)


def weekly_cummulative_returns(tr_no: str):
    """
    Retrieves the weekly cummulative returns data for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    dict: The weekly cummulative returns data.
    """
    # Assume fetching user profile from a database
    USER_DB_FOLDER_PATH = os.getenv("DB_DIR")
    users_db_path = os.path.join(USER_DB_FOLDER_PATH, f"{tr_no}.db")
    user_stats = create_portfolio_stats(users_db_path)
    return get_weekly_cumulative_returns_data(user_stats)
