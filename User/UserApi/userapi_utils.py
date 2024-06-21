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
    try:
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
            logger.error(
                "No data frames to concatenate. Check table column consistency."
            )
            return None
    except Exception as e:
        logger.error(f"Error fetching portfolio stats: {e}")
        return None


def get_monthly_returns_data(user_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the monthly returns for a given DataFrame of portfolio stats data.

    Args:
    user_stats (pd.DataFrame): The DataFrame of portfolio stats data.

    Returns:
    pd.DataFrame: The DataFrame of monthly returns.
    with the columns 'Year', 'Month', and 'Monthly Absolute Returns (Rs.)'.
    """
    try:
        # Convert 'exit_time' to datetime
        user_stats["exit_time"] = pd.to_datetime(
            user_stats["exit_time"], errors="coerce"
        )
        user_stats = user_stats.dropna(
            subset=["exit_time"]
        )  # Drop rows where 'exit_time' could not be converted

        # Extract 'Year' and 'Month'
        user_stats["Year"] = user_stats["exit_time"].dt.year
        user_stats["Month"] = user_stats["exit_time"].dt.strftime("%B")

        # Ensure 'net_pnl' is in standard float format
        user_stats["net_pnl"] = user_stats["net_pnl"].astype(float)

        # Group by 'Year' and 'Month' and sum 'net_pnl'
        monthly_absolute_returns = user_stats.groupby(
            ["Year", "Month"], as_index=False
        )["net_pnl"].sum()

        # Rename columns for clarity
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

        logger.debug(f"Calculated monthly returns:\n{monthly_absolute_returns}")

        return monthly_absolute_returns

    except Exception as e:
        logger.error(f"Error calculating monthly returns: {e}")
        return pd.DataFrame(columns=["Year", "Month", "Monthly Absolute Returns (Rs.)"])


def get_weekly_cumulative_returns_data(user_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the weekly cumulative returns for a given DataFrame of portfolio stats data.

    Args:
    portfolio_stats_data (pd.DataFrame): The DataFrame of portfolio stats data.

    Returns:
    pd.DataFrame: The DataFrame of weekly cumulative returns.
    with the columns 'Week_Ending_Date', 'Weekly Absolute Returns' and 'Cumulative Absolute Returns (Rs.)'
    """
    try:
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
        weekly_absolute_returns = weekly_absolute_returns.sort_values(
            by="Week_Ending_Date"
        )

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
        weekly_absolute_returns[
            "Weekly Absolute Returns (Rs.)"
        ] = weekly_absolute_returns["Weekly Absolute Returns (Rs.)"].apply(
            lambda x: format_currency(x, "INR", locale="en_IN")
        )

        # Apply Indian currency formatting to the 'Cumulative Absolute Returns (Rs.)'
        weekly_absolute_returns[
            "Cumulative Absolute Returns (Rs.)"
        ] = weekly_absolute_returns["Cumulative Absolute Returns (Rs.)"].apply(
            lambda x: format_currency(x, "INR", locale="en_IN")
        )

        return weekly_absolute_returns
    except Exception as e:
        logger.error(f"Error calculating weekly returns: {e}")
        return pd.DataFrame(
            columns=["Week_Ending_Date", "Weekly Absolute Returns (Rs.)"]
        )


def get_individual_strategy_data(tr_no: str, strategy_name: str):
    """
    Retrieves the individual strategy data for a specific user by their user ID and strategy name.

    Args:
    user_id: The unique identifier of the user.
    strategy_name: The name of the strategy.

    Returns:
    dict: The individual strategy data.
    """
    try:
        # Assume fetching user profile from a database
        USER_DB_FOLDER_PATH = os.getenv("USR_TRADELOG_DB_FOLDER")
        users_db_path = os.path.join(USER_DB_FOLDER_PATH, f"{tr_no}.db")

        conn = get_db_connection(users_db_path)
        strategies = ACTIVE_STRATEGIES + ["Holdings"]

        if strategy_name in strategies:
            data = pd.read_sql_query(f"SELECT * FROM {strategy_name}", conn)
            if strategy_name == "Holdings":
                return data
            else:
                data["exit_time"] = pd.to_datetime(data["exit_time"])
                return data
        else:
            logger.error(f"Strategy not found: {strategy_name}")
            return None
    except Exception as e:
        logger.error(f"Error calculating individual strategy data: {e}")


def get_base_capital(tr_no: str):
    """
    Retrieves the base capital for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    float: The base capital.
    """
    try:
        # Assume fetching user profile from a database
        user = fetch_collection_data_firebase(CLIENTS_COLLECTION, document=tr_no)
        return user["Accounts"]["CurrentBaseCapital"]

    except Exception as e:
        logger.error(f"Error calculating base capital: {e}")
        return 0.0


def get_broker_bank_transactions_data(tr_no: str):
    """
    Retrieves the broker and bank transactions data for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    dict: The broker and bank transactions data.
    """
    # Assume fetching user profile from a database
    USER_DB_FOLDER_PATH = os.getenv("USR_TRADELOG_DB_FOLDER")
    users_db_path = os.path.join(USER_DB_FOLDER_PATH, f"{tr_no}.db")
    conn = get_db_connection(users_db_path)
    starting_capital = get_base_capital(tr_no)

    # Read the tables into pandas DataFrames
    deposits = pd.read_sql_query(
        "SELECT posting_date AS date, particulars, debit, credit FROM Deposits", conn
    )
    withdrawals = pd.read_sql_query(
        "SELECT posting_date AS date, particulars, debit, credit FROM Withdrawals", conn
    )
    charges = pd.read_sql_query(
        "SELECT posting_date AS date, particulars, debit, credit FROM Charges", conn
    )

    # Combine the data from all tables
    combined_data = pd.concat([deposits, withdrawals, charges], ignore_index=True)

    # Convert 'date' to datetime and sort
    combined_data["date"] = pd.to_datetime(combined_data["date"])
    sorted_data = combined_data.sort_values(by="date", ascending=True).reset_index(
        drop=True
    )

    # Initialize running balance column
    sorted_data["running balance"] = 0.0  # Initialize as float

    # Set the first row's running balance
    sorted_data.at[0, "running balance"] = (
        starting_capital + sorted_data.at[0, "credit"] - sorted_data.at[0, "debit"]
    )

    # Compute running balance for the rest of the DataFrame
    for i in range(1, len(sorted_data)):
        sorted_data.at[i, "running balance"] = (
            sorted_data.at[i - 1, "running balance"]
            + sorted_data.at[i, "credit"]
            - sorted_data.at[i, "debit"]
        )

    # Add empty columns for 'tags' and 'comments'
    sorted_data["tags"] = None  # Assuming you want to fill this later or keep it empty
    sorted_data["comments"] = None

    # Close the database connection
    conn.close()

    return sorted_data
