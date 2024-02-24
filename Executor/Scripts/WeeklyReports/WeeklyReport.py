import os, sys
from datetime import datetime, timedelta,date
from dotenv import load_dotenv
import pandas as pd
from babel.numbers import format_currency

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


from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
        get_db_connection
    )
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_active_users_from_firebase,
        fetch_active_strategies_all_users,
        fetch_freecash_for_user,
        fetch_holdings_value_for_user

    )
from Executor.ExecutorUtils.ExeUtils import get_previous_trading_day
from Executor.ExecutorUtils.NotificationCenter.Telegram.telegram_adapter import send_telegram_message

# Function to find the start date of the current complete week
def get_current_week_range():
    """Finds and returns the start date of the current complete week."""
    today = datetime.now()
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=4)
    return start_date, end_date

def check_table_exists(conn, table_name):
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
    cur = conn.cursor()
    cur.execute(query, (table_name,))
    return cur.fetchone() is not None

def get_current_week_trades(user, active_strategies, start_date, end_date):
    trades = {}
    db_path = os.path.join(db_dir, f"{user['Tr_No']}.db")
    conn = get_db_connection(db_path)
    if conn is not None:
        for strategy in active_strategies:
            if not check_table_exists(conn, strategy):
                continue
            query = f"SELECT * FROM {strategy} WHERE exit_time BETWEEN '{start_date}' AND '{end_date}'"
            result = pd.read_sql_query(query, conn)
            net_pnl_sum = result['net_pnl'].sum()
            trades[strategy] = round(net_pnl_sum,2)
        logger.debug(f"Trades: {trades}")
        conn.close()
    else:
        logger.error("Failed to establish a database connection.")
    return trades

def get_current_week_fb_values(user):  
    fb_values = {}
    previous_trading_day_fb_format = get_previous_trading_day(date.today())
    fb_values['FreeCash'] = round(user['Accounts'][f"{previous_trading_day_fb_format}_FreeCash"],2)
    fb_values['Holdings'] = round(user['Accounts'][f"{previous_trading_day_fb_format}_Holdings"],2)
    fb_values['AccountValue'] = round(user['Accounts'][f"{previous_trading_day_fb_format}_AccountValue"],2)
    fb_values['Drawdown'] = user['Accounts']["Drawdown"]   
    # fb_values['Drawdown'] = 0.0 
    return fb_values

def send_telegram_message_to_user(user, user_details,start_date,end_date):
    start_date = start_date.strftime("%d-%m-%Y")
    end_date = end_date.strftime("%d-%m-%Y")
    user_name = user["Profile"]["Name"]
    message = f"Weekly Summary for {user_name} ({start_date} to {end_date})\n\n"
    for strategy, pnl in user_details['trades'].items():
        message += f"{strategy}: {format_currency(pnl,'INR', locale='en_IN')}\n"
    message += f"\nNet PnL: {format_currency(round((sum(user_details['trades'].values())),2),'INR', locale='en_IN')}\n\n"
    message += f"Free Cash: {format_currency(user_details['fb_values']['FreeCash'],'INR', locale='en_IN')}\n"
    message += f"TradeMan Holdings: {format_currency(user_details['fb_values']['Holdings'],'INR', locale='en_IN')}\n"
    message += f"TradeMan Account Value: {format_currency(user_details['fb_values']['AccountValue'],'INR', locale='en_IN')}\n"
    message += f"Broker Account Value: {format_currency(user_details['account_value'],'INR', locale='en_IN')}\n"
    message += f"Difference: {format_currency(user_details['difference'],'INR', locale='en_IN')}\n"
    message += f"Drawdown: {format_currency(user_details['drawdown'],'INR', locale='en_IN')}\n\n"
    message += "Best regards,\nTradeMan"

    logger.debug(f"Message: {message}")
    send_telegram_message(user["Profile"]["PhoneNumber"], message)

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


def calculate_ledger_values_and_update_fb():
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



# Main function to execute the script for generating weekly reports
def main():
    start_date, end_date = get_current_week_range()
    active_users = fetch_active_users_from_firebase()
    active_strategies = fetch_active_strategies_all_users()

    for user in active_users:
        try:
            logger.debug(f"broker_holdings: {fetch_holdings_value_for_user(user)}")
            user_details = {}
            user_details['trades'] = get_current_week_trades(user, active_strategies, start_date, end_date)
            user_details['fb_values'] = get_current_week_fb_values(user)
            user_details['broker_freecash'] = fetch_freecash_for_user(user)
            user_details['broker_holdings'] = fetch_holdings_value_for_user(user)
            user_details['account_value'] = round((user_details['broker_freecash'] + user_details['broker_holdings']),2)
            user_details['difference'] = round((user_details['account_value'] - user_details['fb_values']['AccountValue']),2)
            user_details['drawdown'] = user_details['fb_values']['Drawdown']
            logger.debug(f"User Details: {user_details}")
            send_telegram_message_to_user(user, user_details, start_date, end_date)

        except Exception as e:
            logger.error(f"Error fetching trades for {user['Tr_No']}: {e}")
            continue


    #TODO: Get the ledger and update the FB
    # calculate_ledger_values_and_update_fb()
    
    

if __name__ == "__main__":
    main()
