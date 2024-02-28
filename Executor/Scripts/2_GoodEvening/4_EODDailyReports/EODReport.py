import os, sys
from datetime import datetime, timedelta,date
from dotenv import load_dotenv
import pandas as pd
from babel.numbers import format_currency
from loguru import logger
from dotenv import load_dotenv

# Define constants and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_utils import (
    download_json
)
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_active_users_from_firebase,
    fetch_active_strategies_all_users
    )
from Executor.ExecutorUtils.NotificationCenter.Telegram.telegram_adapter import (
    send_telegram_message,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import get_db_connection
from Executor.ExecutorUtils.ExeUtils import get_previous_trading_day

CLIENTS_TRADE_SQL_DB = os.getenv("DB_DIR")
CLIENTS_USER_FB_DB = os.getenv("FIREBASE_USER_COLLECTION")
today_string = datetime.now().strftime("%Y-%m-%d")

def get_today_trades(user_tables,active_stratgies):
    global today_string
    # got to user db and find table names matching Active Strategies and get trades for today
    
    today_trades = []
    try:
        for strategy in active_stratgies:
            logger.debug(f"Fetching today's trades for: {strategy}")
            for table in user_tables:
                if strategy in list(table.keys())[0]:
                    trades = table[strategy]
                    # if row is None or 'exit_time' not in row or pd.isnull(row['exit_time'])
                    if trades.empty or "exit_time" not in trades.columns or trades["exit_time"].isnull().all():
                        continue
                    # in the table the exit_time column is in this format '2021-08-25 15:30:00'. so i want convert it to '2021-08-25' and then compare it with today_string if matched append it to today_trades
                    trades["exit_time"] = trades["exit_time"].apply(
                        lambda x: x.split(" ")[0]
                    )
                    if today_string in trades["exit_time"].values:
                        today_trades.extend(
                            trades[trades["exit_time"] == today_string].to_dict("records")
                        )
        return today_trades
    except Exception as e:
        logger.error(f"Error in get_today_trades: {e}")
        return today_trades


def get_additions_withdrawals(user_tables):
    global today_string
    # key = Transactions and get the sum of the "amount" column for today under transaction_date which is in this format '2021-08-25 15:30:00'
    additions_withdrawals = 0
    try:
        for table in user_tables:
            if list(table.keys())[0] == "Transactions":
                transactions = table["Transactions"]
                transactions["transaction_date"] = transactions["transaction_date"].apply(
                    lambda x: x.split(" ")[0]
                )
                if today_string in transactions["transaction_date"].values:
                    additions_withdrawals = transactions[
                        transactions["transaction_date"] == today_string
                    ]["amount"].sum()
        return round(additions_withdrawals)
    except Exception as e:
        logger.error(f"Error in get_additions_withdrawals: {e}")
        return round(additions_withdrawals)


def get_new_holdings(user_tables):
    # go to "Holdings" table and get net sum of "MarginUtilized" column
    new_holdings = 0
    try:
        for table in user_tables:
            if list(table.keys())[0] == "Holdings":
                holdings = table["Holdings"]
                #iterate through the rows and convert it to float and get the sum of the "MarginUtilized" column 
                new_holdings = sum(float(holding) for holding in holdings["margin_utilized"])

        logger.info(f"new_holdings{new_holdings}")

        return round(float(new_holdings))
    except Exception as e:
        logger.error(f"Error in get_new_holdings: {e}")
        return round(new_holdings)


def update_account_keys_fb(
    tr_no,
    today_fb_format,
    new_account,
    new_free_cash,
    new_holdings,
    previous_trading_day_fb_format,
):
    from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
        update_fields_firebase,
        delete_fields_firebase,
    )

    try:
        logger.debug(f"Updating account keys for {tr_no} in Firebase")
        # use this method to update the account keys in the firebase update_fields_firebase(collection, document, data, field_key=None)
        update_fields_firebase(
            CLIENTS_USER_FB_DB,
            tr_no,
            {
                f"{today_fb_format}_AccountValue": new_account,
                f"{today_fb_format}_FreeCash": new_free_cash,
                f"{today_fb_format}_Holdings": new_holdings,
            },
            "Accounts",
        )
    except Exception as e:
        logger.error(f"Error in update_account_keys_fb: {e}")


# Main function to generate and send the report
def main():
    download_json(CLIENTS_USER_FB_DB, "before_eod_report")
    active_users = fetch_active_users_from_firebase()
    active_stratgies = fetch_active_strategies_all_users()

    for user in active_users:
        user_tables = []
        try:
            user_db_path = os.path.join(CLIENTS_TRADE_SQL_DB, f"{user['Tr_No']}.db")
            user_db_conn = get_db_connection(user_db_path)
            # get all the tables in the user db with table name as key and table df as value
            for table in user_db_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall():
                user_table = {}
                # create user table_df without the index column from sql table and append it to user_tables as a dict with table name as key and table df as value
                user_table[table[0]] = pd.read_sql_query(
                    f"SELECT * FROM {table[0]}", user_db_conn
                )
                user_tables.append(user_table)
        except Exception as e:
            logger.error(f"Error in fetching user tables: {e}")
            continue

        try:
            # Placeholder values, replace with actual queries and Firebase fetches
            today_trades = get_today_trades(user_tables,active_stratgies)
            gross_pnl = sum(float(trade["pnl"]) for trade in today_trades)
            expected_tax = sum(float(trade["tax"]) for trade in today_trades)

            today_fb_format = datetime.now().strftime("%d%b%y")

            previous_trading_day_fb_format = get_previous_trading_day(date.today())

            previous_free_cash = user["Accounts"][
                f"{previous_trading_day_fb_format}_FreeCash"
            ]
            previous_holdings = user["Accounts"][
                f"{previous_trading_day_fb_format}_Holdings"
            ]
            previous_account = user["Accounts"][
                f"{previous_trading_day_fb_format}_AccountValue"
            ]
        except Exception as e:
            logger.error(f"Error in fetching account values: {e}")
            continue

        # Assuming no additions/withdrawals for simplicity, replace with actual logic to calculate
        try:
            # additions_withdrawals = get_additions_withdrawals(user_tables)
            additions_withdrawals = 0   #TODO : get the actual additions_withdrawals

            new_free_cash = round(previous_free_cash + gross_pnl - expected_tax)
            new_holdings = get_new_holdings(user_tables)
            new_account = round(
                previous_account + gross_pnl - expected_tax + additions_withdrawals
            )

            net_change = new_account - previous_account
            net_change_percentage = (
                (net_change / previous_account) * 100 if previous_account else 0
            )
            # Placeholder for drawdown calculation
            drawdown = user["Accounts"]["NetPnL"] - user["Accounts"]["PnLWithdrawals"]
            drawdown_percentage = drawdown / new_account * 100
            phone_number = user["Profile"]["PhoneNumber"]
            update_account_keys_fb(user['Tr_No'], today_fb_format, new_account, new_free_cash, new_holdings,previous_trading_day_fb_format)
        except Exception as e:
            logger.error(f"Error in calculating account values: {e}")
            continue

        # Format the message
        user_name = user["Profile"]["Name"]
        message = f"Hello {user_name}, We hope you're enjoying a wonderful day.\n\n"
        message += "Here are your PNLs for today:\n\n"
        message += "Today's Trades:\n"
        for trade in today_trades:
            message += f"{trade['trade_id']}: {format_currency(trade['pnl'],'INR', locale='en_IN')}\n"
        message += f"\nGross PnL: {format_currency(gross_pnl, 'INR', locale='en_IN')}\n"
        message += (
            f"Expected Tax: {format_currency(expected_tax,'INR',locale='en_IN')}\n"
        )
        message += f"{previous_trading_day_fb_format} Free Cash: {format_currency(previous_free_cash,'INR', locale='en_IN')}\n"
        message += f"{today_fb_format} Free Cash: {format_currency(new_free_cash,'INR', locale='en_IN')}\n\n"
        message += "Holdings:\n"
        message += f"{previous_trading_day_fb_format} Holdings: {format_currency(previous_holdings,'INR', locale='en_IN')}\n"
        message += f"{today_fb_format} Holdings: {format_currency(new_holdings,'INR', locale='en_IN')}\n\n"
        message += "Account:\n"
        message += f"{previous_trading_day_fb_format} Account: {format_currency(previous_account,'INR', locale='en_IN')}\n"
        message += f"{today_fb_format} Account: {format_currency(new_account,'INR', locale='en_IN')}\n"
        message += f"Additions/Withdrawals: {format_currency(additions_withdrawals,'INR', locale='en_IN')}\n"
        message += f"NetChange: {format_currency(net_change,'INR', locale='en_IN')} ({net_change_percentage:.2f}%)\n"
        message += f"Drawdown: {format_currency(drawdown,'INR', locale='en_IN')}({drawdown_percentage:.2f}%)\n\n"
        message += "Best Regards,\nTradeMan"

        # Send the report to Discord
        print(message)
        try:
            send_telegram_message(phone_number, message)
        except Exception as e:
            logger.error(f"Error in sending telegram message: {e}")


if __name__ == "__main__":
    main()
