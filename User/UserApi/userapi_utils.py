import pandas as pd
import os, sys
from dotenv import load_dotenv
from babel.numbers import format_currency


DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)


from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    upload_new_client_data_to_firebase,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_active_strategies_all_users,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import get_db_connection
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_utils import get_db_table_names


logger = LoggerSetup()


ACTIVE_STRATEGIES = fetch_active_strategies_all_users()
ADMIN_DB = os.getenv("FIREBASE_ADMIN_COLLECTION")
CLIENTS_COLLECTION = os.getenv("FIREBASE_USER_COLLECTION")


def all_users_data():
    """
    Fetches all user data from the Firebase database.

    Returns:
    dict: A dictionary containing all user data.
    """
    users_data = fetch_collection_data_firebase(CLIENTS_COLLECTION)
    return users_data


def get_next_trader_number():
    """
    Retrieves the next trader number from the admin database.

    Returns:
    int: The next trader number.
    """
    admin_data = fetch_collection_data_firebase(ADMIN_DB)
    return admin_data.get("NextTradeManId", 0)


def update_new_client_data_to_db(trader_number, user_dict):
    """
    Updates the user's data in the Firebase database.

    Args:
    trader_number (int): The new user's trader number.
    user_dict (dict): The user's data as a dictionary.
    """
    upload_new_client_data_to_firebase(trader_number, user_dict)


def create_portfolio_stats(db_path):
    """
    Fetches portfolio stats for all active users from a Firebase database.

    Args:
    db_path (str): The path to the Firebase database file.

    Returns:
    pd.DataFrame: The portfolio stats data as a pandas DataFrame.
    with the columns 'exit_time', 'trade_id', and 'net_pnl'.
    """

    dtd_data_list = []  # Use a list to collect DataFrame fragments
    conn = get_db_connection(db_path)
    table_names = get_db_table_names(conn)

    user_strategy_table_names = [
        table for table in table_names if table in ACTIVE_STRATEGIES
    ]

    for table in user_strategy_table_names:
        data = pd.read_sql_query(f"SELECT * FROM {table}", conn)

        # Check if required columns exist in the table
        required_columns = ["exit_time", "trade_id", "net_pnl"]
        if all(item in data.columns for item in required_columns):
            dtd_data_list.append(data[required_columns])
        else:
            missing_cols = set(required_columns) - set(data.columns)
            logger.error(f"Missing columns {missing_cols} in table {table}")

    if dtd_data_list:  # Only concatenate if there are data frames in the list
        dtd_data = pd.concat(
            dtd_data_list, ignore_index=True
        )  # Concatenate all DataFrame fragments
        return dtd_data
    else:
        logger.error("No data frames to concatenate. Check table column consistency.")
        return None


def get_monthly_returns_data(user_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the monthly returns for a given DataFrame of portfolio stats data.

    Args:
    portfolio_stats_data (pd.DataFrame): The DataFrame of portfolio stats data.

    Returns:
    pd.DataFrame: The DataFrame of monthly returns.
    with the columns 'Year', 'Month', and 'Monthly Absolute Returns (Rs.)'.
    """
    # Convert 'exit_time' to datetime and extract 'Year' and 'Month'
    user_stats["exit_time"] = pd.to_datetime(user_stats["exit_time"])
    user_stats["Year"] = user_stats["exit_time"].dt.year
    user_stats["Month"] = user_stats["exit_time"].dt.strftime("%B")

    monthly_absolute_returns = (
        user_stats.groupby(["Year", "Month"])["net_pnl"].sum().reset_index()
    )
    monthly_absolute_returns.columns = [
        "Year",
        "Month",
        "Monthly Absolute Returns (Rs.)",
    ]
    # Apply currency formatting using Babel
    monthly_absolute_returns[
        "Monthly Absolute Returns (Rs.)"
    ] = monthly_absolute_returns["Monthly Absolute Returns (Rs.)"].apply(
        lambda x: format_currency(x, "INR", locale="en_IN")
    )
    return monthly_absolute_returns


def get_weekly_cumulative_returns_data(user_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the weekly cumulative returns for a given DataFrame of portfolio stats data.

    Args:
    portfolio_stats_data (pd.DataFrame): The DataFrame of portfolio stats data.

    Returns:
    pd.DataFrame: The DataFrame of weekly cumulative returns.
    with the columns 'Week_Ending_Date', 'Weekly Absolute Returns' and 'Cumulative Absolute Returns (Rs.)'
    """
    user_stats["Date"] = pd.to_datetime(user_stats["exit_time"])
    user_stats["Year"] = user_stats["Date"].dt.year
    user_stats["Month"] = user_stats["Date"].dt.month
    # Calculate week ending (Saturday) date correctly and remove the time component
    user_stats["Week_Ending_Date"] = (
        user_stats["Date"]
        + pd.to_timedelta((5 - user_stats["Date"].dt.weekday) % 7, unit="d")
    ).dt.normalize()  # This removes the time part, normalizing to midnight

    # Group by Week_Ending_Date and sum net_pnl for each group
    weekly_absolute_returns = (
        user_stats.groupby("Week_Ending_Date")
        .agg(Weekly_Absolute_Returns=pd.NamedAgg(column="net_pnl", aggfunc="sum"))
        .reset_index()
    )

    # Calculate cumulative returns
    weekly_absolute_returns[
        "Cumulative Absolute Returns (Rs.)"
    ] = weekly_absolute_returns["Weekly_Absolute_Returns"].cumsum()

    # Sort by Week_Ending_Date for clarity
    weekly_absolute_returns = weekly_absolute_returns.sort_values(by="Week_Ending_Date")

    # Format Week_Ending_Date for readability
    weekly_absolute_returns["Week_Ending_Date"] = weekly_absolute_returns[
        "Week_Ending_Date"
    ].dt.strftime("%d%b%y")

    # Rename columns appropriately
    weekly_absolute_returns.rename(
        columns={"Weekly_Absolute_Returns": "Weekly Absolute Returns (Rs.)"},
        inplace=True,
    )

    # Apply Indian currency formatting to the 'Weekly Absolute Returns (Rs.)'
    weekly_absolute_returns["Weekly Absolute Returns (Rs.)"] = weekly_absolute_returns[
        "Weekly Absolute Returns (Rs.)"
    ].apply(lambda x: format_currency(x, "INR", locale="en_IN"))

    # Apply Indian currency formatting to the 'Cumulative Absolute Returns (Rs.)'
    weekly_absolute_returns[
        "Cumulative Absolute Returns (Rs.)"
    ] = weekly_absolute_returns["Cumulative Absolute Returns (Rs.)"].apply(
        lambda x: format_currency(x, "INR", locale="en_IN")
    )

    return weekly_absolute_returns
