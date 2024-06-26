import pandas as pd
import os, sys
from dotenv import load_dotenv
from babel.numbers import format_currency
from datetime import date, datetime
import csv

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
PARAMS_UPDATE_LOG_CSV_PATH = os.getenv("PARAMS_UPDATE_LOG_CSV_PATH")
STRATEGIES_FB_COLLECTION = os.getenv("FIREBASE_STRATEGY_COLLECTION")
MARKET_INFO_FB_COLLECTION = os.getenv("MARKET_INFO_FB_COLLECTION")


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


def log_changes_via_webapp(updated_data, section_info=None):
    """
    The function `log_changes` logs updated data along with section information to a CSV file with date
    and time stamp.

    :param updated_data: The `updated_data` parameter is the data that has been updated and will be
    logged in the CSV file. It should be provided as an argument when calling the `log_changes` function
    :param section_info: Section_info is an optional parameter that can be passed to the log_changes
    function. It is used to provide additional information about the section being updated in the log
    entry. If section_info is provided, it will be included in the log entry under the "section_info"
    column in the CSV log file
    """
    filename = PARAMS_UPDATE_LOG_CSV_PATH
    headers = ["date", "updated_info", "section_info"]
    date_str = datetime.now().strftime("%d%b%y %I:%M%p")  # Format: 23Feb24 9:43AM

    with open(filename, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)

        # Write headers if file is being created for the first time
        if not os.path.isfile(filename):
            writer.writeheader()

        log_entry = {
            "date": date_str,
            "updated_info": str(updated_data),  # Corrected key to match header
            "section_info": section_info if section_info else "",
        }

        writer.writerow(log_entry)


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


def get_monthly_returns_data(
    user_stats: pd.DataFrame, page: int, page_size: int
) -> dict:
    """
    Calculates the paginated monthly returns for a given DataFrame of portfolio stats data.

    Args:
    user_stats (pd.DataFrame): The DataFrame of portfolio stats data.
    page: The page number.
    page_size: The number of items per page.

    Returns:
    dict: A dictionary containing the paginated DataFrame of monthly returns and the total number of items.
    """
    try:
        user_stats["exit_time"] = pd.to_datetime(
            user_stats["exit_time"], errors="coerce"
        )
        user_stats = user_stats.dropna(subset=["exit_time"])

        user_stats["Year"] = user_stats["exit_time"].dt.year
        user_stats["Month"] = user_stats["exit_time"].dt.strftime("%B")

        monthly_absolute_returns = (
            user_stats.groupby(["Year", "Month"])["net_pnl"]
            .sum()
            .reset_index()
            .rename(columns={"net_pnl": "Monthly Absolute Returns (Rs.)"})
        )

        monthly_absolute_returns[
            "Monthly Absolute Returns (Rs.)"
        ] = monthly_absolute_returns["Monthly Absolute Returns (Rs.)"].apply(
            lambda x: format_currency(x, "INR", locale="en_IN")
        )

        # Sort the DataFrame by Year and Month
        month_order = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        monthly_absolute_returns["Month"] = pd.Categorical(
            monthly_absolute_returns["Month"], categories=month_order, ordered=True
        )
        monthly_absolute_returns = monthly_absolute_returns.sort_values(
            ["Year", "Month"], ascending=[False, False]
        )

        # Calculate total number of items
        total_items = len(monthly_absolute_returns)

        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_data = monthly_absolute_returns.iloc[start_index:end_index]

        return {"items": paginated_data, "total_items": total_items}

    except Exception as e:
        logger.error(f"Error calculating monthly returns: {e}")
        return {
            "items": pd.DataFrame(
                columns=["Year", "Month", "Monthly Absolute Returns (Rs.)"]
            ),
            "total_items": 0,
        }


def get_weekly_cumulative_returns_data(
    user_stats: pd.DataFrame, page: int, page_size: int
) -> dict:
    """
    Calculates the paginated weekly cumulative returns for a given DataFrame of portfolio stats data.

    Args:
    user_stats (pd.DataFrame): The DataFrame of portfolio stats data.
    page: The page number.
    page_size: The number of items per page.

    Returns:
    dict: A dictionary containing the paginated DataFrame of weekly cumulative returns and the total number of items.
    """
    try:
        user_stats["Date"] = pd.to_datetime(user_stats["exit_time"])
        user_stats["Year"] = user_stats["Date"].dt.year
        user_stats["Month"] = user_stats["Date"].dt.month
        user_stats["Week_Ending_Date"] = (
            user_stats["Date"]
            + pd.to_timedelta((5 - user_stats["Date"].dt.weekday) % 7, unit="d")
        ).dt.normalize()

        weekly_absolute_returns = (
            user_stats.groupby("Week_Ending_Date")
            .agg(Weekly_Absolute_Returns=pd.NamedAgg(column="net_pnl", aggfunc="sum"))
            .reset_index()
        )

        weekly_absolute_returns[
            "Cumulative Absolute Returns (Rs.)"
        ] = weekly_absolute_returns["Weekly_Absolute_Returns"].cumsum()
        weekly_absolute_returns = weekly_absolute_returns.sort_values(
            by="Week_Ending_Date"
        )
        weekly_absolute_returns["Week_Ending_Date"] = weekly_absolute_returns[
            "Week_Ending_Date"
        ].dt.strftime("%d%b%y")
        weekly_absolute_returns.rename(
            columns={"Weekly_Absolute_Returns": "Weekly Absolute Returns (Rs.)"},
            inplace=True,
        )

        weekly_absolute_returns[
            "Weekly Absolute Returns (Rs.)"
        ] = weekly_absolute_returns["Weekly Absolute Returns (Rs.)"].apply(
            lambda x: format_currency(x, "INR", locale="en_IN")
        )
        weekly_absolute_returns[
            "Cumulative Absolute Returns (Rs.)"
        ] = weekly_absolute_returns["Cumulative Absolute Returns (Rs.)"].apply(
            lambda x: format_currency(x, "INR", locale="en_IN")
        )

        # Calculate total number of items
        total_items = len(weekly_absolute_returns)

        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_data = weekly_absolute_returns.iloc[start_index:end_index]

        return {"items": paginated_data, "total_items": total_items}

    except Exception as e:
        logger.error(f"Error calculating weekly returns: {e}")
        return {
            "items": pd.DataFrame(
                columns=[
                    "Week_Ending_Date",
                    "Weekly Absolute Returns (Rs.)",
                    "Cumulative Absolute Returns (Rs.)",
                ]
            ),
            "total_items": 0,
        }


def get_individual_strategy_data(
    tr_no: str, strategy_name: str, page: int, page_size: int
):
    try:
        USER_DB_FOLDER_PATH = os.getenv("USR_TRADELOG_DB_FOLDER")
        users_db_path = os.path.join(USER_DB_FOLDER_PATH, f"{tr_no}.db")

        conn = get_db_connection(users_db_path)
        strategies = ACTIVE_STRATEGIES + ["Holdings"]

        if strategy_name in strategies:
            # Calculate the offset
            offset = (page - 1) * page_size

            # Get the total count of items
            total_items = pd.read_sql_query(
                f"SELECT COUNT(*) as count FROM {strategy_name}", conn
            ).iloc[0]["count"]

            # Fetch paginated data
            data = pd.read_sql_query(
                f"SELECT * FROM {strategy_name} LIMIT {page_size} OFFSET {offset}", conn
            )

            if strategy_name == "Holdings":
                # Convert any potential NumPy types to Python native types
                data = data.astype(object).where(pd.notnull(data), None)
            else:
                data["exit_time"] = pd.to_datetime(data["exit_time"])
                # Convert any potential NumPy types to Python native types
                data = data.astype(object).where(pd.notnull(data), None)

            return {
                "items": data,
                "total_items": int(total_items),  # Ensure this is a Python int
            }
        else:
            logger.error(f"Strategy not found: {strategy_name}")
            return None
    except Exception as e:
        logger.error(f"Error calculating individual strategy data: {e}")
        raise


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


def equity_get_broker_bank_transactions_data(
    tr_no: str, from_date: date = None, to_date: date = None
):
    """
    Retrieves the broker and bank transactions data for a specific user by their user ID, filtered by a date range.

    Args:
        tr_no: The unique identifier of the user.
        from_date: Start date for filtering transactions(YYYY-MM-DD). Defaults to None.
        to_date: End date for filtering transactions(YYYY-MM-DD). Defaults to None.

    Returns:
        DataFrame: The broker and bank transactions data.
    """
    USER_DB_FOLDER_PATH = os.getenv("USR_TRADELOG_DB_FOLDER")
    users_db_path = os.path.join(USER_DB_FOLDER_PATH, f"{tr_no}.db")
    conn = get_db_connection(users_db_path)
    starting_capital = get_base_capital(tr_no)

    # Build the query dynamically based on whether date filters are provided
    where_clauses = []
    if from_date:
        where_clauses.append(f"posting_date >= '{from_date}'")
    if to_date:
        where_clauses.append(f"posting_date <= '{to_date}'")
    where_stmt = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Query modifications to include the date filters
    deposits = pd.read_sql_query(
        f"SELECT posting_date AS date, particulars, debit, credit FROM Deposits WHERE {where_stmt}",
        conn,
    )
    withdrawals = pd.read_sql_query(
        f"SELECT posting_date AS date, particulars, debit, credit FROM Withdrawals WHERE {where_stmt}",
        conn,
    )
    charges = pd.read_sql_query(
        f"SELECT posting_date AS date, particulars, debit, credit FROM Charges WHERE {where_stmt}",
        conn,
    )

    # Combine the data from all tables
    combined_data = pd.concat([deposits, withdrawals, charges], ignore_index=True)
    combined_data["date"] = pd.to_datetime(combined_data["date"])
    sorted_data = combined_data.sort_values(by="date", ascending=True).reset_index(
        drop=True
    )

    # Convert 'date' to a string in the desired format
    sorted_data["date"] = sorted_data["date"].dt.strftime("%Y-%m-%d")

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
