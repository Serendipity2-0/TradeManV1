import os, sys
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
import pandas as pd
from babel.numbers import format_currency

# Load environment variables
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

USR_TRADELOG_DB_FOLDER = os.getenv("USR_TRADELOG_DB_FOLDER")
user_collection_firebase = os.getenv("FIREBASE_USER_COLLECTION")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    get_db_connection,
    fetch_holdings_value_for_user_sqldb,
)
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_active_users_from_firebase,
    fetch_active_strategies_all_users,
    fetch_freecash_for_user,
    fetch_holdings_value_for_user_broker,
)
from Executor.ExecutorUtils.ExeUtils import get_previous_trading_day
from Executor.ExecutorUtils.NotificationCenter.Telegram.telegram_adapter import (
    send_telegram_message,
)


# Function to find the start date of the current complete week
def get_current_week_range():
    """
    Finds and returns the start date and end date of the current complete week.

    :return: A tuple containing the start and end date of the current week.
    """
    """Finds and returns the start date of the current complete week."""
    today = datetime.now()
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=4)
    return start_date, end_date


def check_table_exists(conn, table_name):
    """
    Checks if a table exists in the SQLite database.

    :param conn: SQLite database connection object.
    :param table_name: The name of the table to check.
    :return: True if the table exists, False otherwise.
    """
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
    cur = conn.cursor()
    cur.execute(query, (table_name,))
    return cur.fetchone() is not None


def get_current_week_trades(user, active_strategies, start_date, end_date):
    """
    Fetches the trades for the current week for a given user and active strategies.

    :param user: A dictionary containing user details.
    :param active_strategies: A list of active strategies.
    :param start_date: The start date of the current week.
    :param end_date: The end date of the current week.
    :return: A dictionary with strategy names as keys and net PnL as values.
    """
    trades = {}
    db_path = os.path.join(USR_TRADELOG_DB_FOLDER, f"{user['Tr_No']}.db")
    conn = get_db_connection(db_path)
    if conn is not None:
        for strategy in active_strategies:
            if not check_table_exists(conn, strategy):
                continue
            query = f"SELECT * FROM {strategy} WHERE exit_time BETWEEN '{start_date}' AND '{end_date}'"
            result = pd.read_sql_query(query, conn)
            result["net_pnl"] = result["net_pnl"].astype(float)
            net_pnl_sum = result["net_pnl"].sum()
            trades[strategy] = round(net_pnl_sum, 2)
        logger.debug(f"Trades: {trades}")
        conn.close()
    else:
        logger.error("Failed to establish a database connection.")
    return trades


def get_current_week_fb_values(user):
    """
    Fetches the current week's free cash, holdings, and account values from Firebase.

    :param user: A dictionary containing user details.
    :return: A dictionary with free cash, holdings, and account values.
    """
    fb_values = {}
    previous_trading_day_fb_format = get_previous_trading_day(date.today())
    fb_values["FreeCash"] = round(
        user["Accounts"][f"{previous_trading_day_fb_format}_FreeCash"], 2
    )
    fb_values["Holdings"] = round(
        user["Accounts"][f"{previous_trading_day_fb_format}_Holdings"], 2
    )
    fb_values["AccountValue"] = round(
        user["Accounts"][f"{previous_trading_day_fb_format}_AccountValue"], 2
    )
    return fb_values


def send_telegram_message_to_user(user, user_details, start_date, end_date):
    """
    Sends a weekly summary message to the user via Telegram.

    :param user: A dictionary containing user details.
    :param user_details: A dictionary containing the user's financial details.
    :param start_date: The start date of the current week.
    :param end_date: The end date of the current week.
    """
    start_date = start_date.strftime("%d-%m-%Y")
    end_date = end_date.strftime("%d-%m-%Y")
    user_name = user["Profile"]["Name"]
    message = f"Weekly Summary for {user_name} ({start_date} to {end_date})\n\n"
    for strategy, pnl in user_details["trades"].items():
        message += f"{strategy}: {format_currency(pnl,'INR', locale='en_IN')}\n"
    message += f"\nNet PnL: {format_currency(round((sum(user_details['trades'].values())),2),'INR', locale='en_IN')}\n\n"
    message += f"Free Cash: {format_currency(user_details['broker_freecash'],'INR', locale='en_IN')}\n"
    message += f"TradeMan Holdings: {format_currency(user_details['broker_holdings'],'INR', locale='en_IN')}\n"
    message += f"TradeMan Account Value: {format_currency(user_details['account_value'],'INR', locale='en_IN')}\n"
    message += f"Broker Account Value: {format_currency(user_details['broker_account_value'],'INR', locale='en_IN')}\n"
    message += f"Difference: {format_currency(user_details['difference'],'INR', locale='en_IN')}\n"
    if user_details["commission"]:
        message += f"Commission: {format_currency(user_details['commission'],'INR', locale='en_IN')}\n\n"
    if user_details["drawdown"]:
        message += f"Drawdown: {format_currency(user_details['drawdown'],'INR', locale='en_IN')}\n\n"
    message += "Best regards,\nTradeMan"

    logger.debug(f"Message: {message}")
    send_telegram_message(user["Profile"]["PhoneNumber"], message)


# Function to calculate commission and drawdown
def calculate_commission_and_drawdown(user, actual_account_value):
    """
    Calculates the commission and drawdown for the user based on the actual account value.

    :param user: A dictionary containing user details.
    :param actual_account_value: The actual account value of the user.
    :return: A tuple containing the commission and drawdown values.
    """
    commission = None
    drawdown = None

    user_base_capital = user["Accounts"]["CurrentBaseCapital"]

    if actual_account_value > user_base_capital:
        # Commission is positive when there's a profit
        commission = actual_account_value - user_base_capital
    elif actual_account_value < user_base_capital:
        # Drawdown is negative when there's a loss
        drawdown = actual_account_value - user_base_capital

    return commission, drawdown


def update_financials_in_firebase(user_id, account_value, freecash, holdings):
    """
    Updates the financial information in Firebase Realtime Database for a given user under temp_clients.

    :param user_id: The user's ID.
    :param account_value: The new account value.
    :param freecash: The free cash value.
    :param holdings: The holdings value.
    """
    from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
        update_fields_firebase,
    )

    """
    Updates the financial information in Firebase Realtime Database for a given user under temp_clients.
    """
    today_date_str = datetime.now().strftime("%d%b%y")  # Format: 19Apr24
    updates = {
        f"{today_date_str}_AccountValue": account_value,
        f"{today_date_str}_FreeCash": freecash,
        f"{today_date_str}_Holdings": holdings,
    }

    update_fields_firebase(user_collection_firebase, user_id, updates, "Accounts")


# Main function to execute the script for generating weekly reports
def main():
    """
    Main function to generate weekly reports for all active users.

    This function fetches active users and strategies, calculates weekly trades, updates financials in Firebase,
    and sends weekly summary messages to users via Telegram.
    """
    # Check if today is Saturday to update account values
    active_users = fetch_active_users_from_firebase()
    start_date, end_date = get_current_week_range()
    active_strategies = fetch_active_strategies_all_users()
    for user in active_users:
        user_id = user["Tr_No"]
        try:
            # Fetch holdings and free cash values
            holdings_value = fetch_holdings_value_for_user_sqldb(user)
            broker_freecash = fetch_freecash_for_user(user)
            broker_holdings = fetch_holdings_value_for_user_broker(user)

            # Calculate the new account value
            new_account_value = round(holdings_value + broker_freecash, 2)

            # Update financials in Firebase
            update_financials_in_firebase(
                user_id, new_account_value, broker_freecash, holdings_value
            )
            user_details = {
                "trades": get_current_week_trades(
                    user, active_strategies, start_date, end_date
                ),
                "fb_values": get_current_week_fb_values(user),
                "broker_freecash": broker_freecash,
                "broker_holdings": broker_holdings,
            }
            user_details["account_value"] = new_account_value
            commission, drawdown = calculate_commission_and_drawdown(
                user, new_account_value
            )
            user_details["broker_account_value"] = round(
                user_details["broker_freecash"] + user_details["broker_holdings"], 2
            )
            user_details["difference"] = round(
                user_details["account_value"]
                - user_details["fb_values"]["AccountValue"],
                2,
            )
            if drawdown:
                user_details["drawdown"] = round(drawdown, 2)
                user_details["commission"] = None
            if commission:
                user_details["commission"] = round(commission, 2)
                user_details["drawdown"] = None

            send_telegram_message_to_user(user, user_details, start_date, end_date)
        except Exception as e:
            logger.error(
                f"Error updating financials for user {user_id} in Firebase: {e}"
            )


if __name__ == "__main__":
    main()
