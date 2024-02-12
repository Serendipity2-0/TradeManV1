import os, sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

db_dir = os.getenv("DB_DIR")
user_collection_firebase = os.getenv("FIREBASE_USER_COLLECTION")

from loguru import logger

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


# Function to find the start date of the current complete week
def get_current_week_range():
    """Finds and returns the start date of the current complete week."""
    today = datetime.now()
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=4)
    return start_date, end_date


# Function to read base capital from basecapital.txt
def read_base_capital(file_path):
    base_capital = {}
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
            for line in lines:
                parts = line.strip().split(":")
                if len(parts) == 2:
                    user = parts[0].strip()
                    balance_str = parts[1].strip()  # Directly strip whitespace
                    base_capital[user] = float(
                        balance_str
                    )  # Convert the balance string to a float
    except FileNotFoundError:
        print("basecapital.txt not found.")
    except ValueError as e:
        print(f"Error parsing base capital: {e}")
    return base_capital


# Function to calculate commission and drawdown
def calculate_commission_and_drawdown(user, actual_account_value, base_capital):
    user_name = user["account_name"]
    commission = 0.0
    drawdown = 0.0

    if user_name in base_capital:
        user_base_capital = base_capital[user_name]

        if actual_account_value > user_base_capital:
            # Commission is positive when there's a profit
            commission = actual_account_value - user_base_capital
        elif actual_account_value < user_base_capital:
            # Drawdown is negative when there's a loss
            drawdown = actual_account_value - user_base_capital
        # print(f"Account: {user_name}, Commission: {commission}, Drawdown: {drawdown}")
    else:
        print(f"Base capital not found for {user_name}.")

    return commission, drawdown


def update_user_net_values_firebase(user, net_values):
    from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
        update_fields_firebase,
    )
    logger.debug(net_values)
    fields_to_update = {
        "NetAdditions": round(net_values['Deposits'],2),
        "NetWithdrawals": round(net_values['Withdrawals'],2),
        "NetCharges": round(net_values['Charges'],2),
        "NetPnL": round(net_values['Trades'],2),
    }
    logger.debug(f"fields_to_update: {fields_to_update}")
    update_fields_firebase(user_collection_firebase,user['Tr_No'],fields_to_update,"Accounts")
    # update_fields_firebase(user_collection_firebase,user,fields_to_update,"Accounts")


def update_user_db(user, categorized_df):
    from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
        get_db_connection,
        append_df_to_sqlite
    )
    # db_path = os.path.join(db_dir, f"{user}.db")
    db_path = os.path.join(db_dir, f"{user['Tr_No']}.db")
    conn = get_db_connection(db_path)

    for key,value in categorized_df.items():
        decimal_columns = [
            'debit',
            'credit',
            'net_balance'
        ]
        append_df_to_sqlite(conn,value,key,decimal_columns)


# Main function to execute the script for generating weekly reports
def main():
    # Get ledger for all activer users
    # Call broker center utils to process broker ledgers
    # Update the processed dfs to the respective users.db under the transactions_charges, transactions_deposits, transactions_withdrawals, transactions_other, transactions_trades
    # Call the calculate_net_values function to calculate the net values for all users and update the values in thr firebase['Tr_no']['Accounts']

    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_active_users_from_firebase,
        get_ledger_for_user,
        process_user_ledger,
        calculate_user_net_values,
    )
    from Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter import process_kite_ledger, calculate_kite_net_values
    from Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter import process_alice_ledger,calculate_alice_net_values

    # Get the active users from the firebase
    # active_users = fetch_active_users_from_firebase()

    # for user in active_users:
    #     user_ledger = get_ledger_for_user(user)
    #     categorized_df = process_user_ledger(user, user_ledger)
        # net_values = calculate_user_net_values(user, categorized_df)

        # update_user_net_values_firebase(user, net_values)

        # update_user_db(user["Tr_No"], categorized_df)

    csv_file_path = r'/Users/amolkittur/Downloads/ledger-YY0222.csv'
    # Example usage
    kite_categorized_dfs = process_kite_ledger(csv_file_path)
    kite_net_values = calculate_kite_net_values(kite_categorized_dfs)
    update_user_net_values_firebase("Tr00", kite_net_values) 
    # update_user_db("Tr00", kite_categorized_dfs)

    # # Print the net values
    print(kite_net_values)

    # # Example usage
    # excel_file_path = r'/Users/amolkittur/Downloads/924446_LedgerStatementofEquityDerivativeCurrency_12022024_013508.xlsx'  # Replace with your Excel file path
    # alice_cat_dfs= process_alice_ledger(excel_file_path)
    # alice_net_values = calculate_alice_net_values(alice_cat_dfs)

    # update_user_net_values_firebase("Tr03", alice_net_values) 
    # update_user_db("Tr03", alice_cat_dfs)

    # # Print the net values
    # print(alice_net_values)



if __name__ == "__main__":
    main()
