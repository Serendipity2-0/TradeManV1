import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from firebase_admin import db, credentials, storage
import firebase_admin
import pandas as pd
import requests
from io import BytesIO
import pprint
import sqlite3

# Define constants and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_users_from_firebase

# Load environment variables fromx the trademan.env file
ENV_PATH = os.path.join(DIR, 'trademan.env')
load_dotenv(ENV_PATH)

# Retrieve API details and contact number from the environment variables
api_id = os.getenv('telethon_api_id')
api_hash = os.getenv('telethon_api_hash')
# Retrieve your Discord webhook URL from the environment variables
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL') # TODO : Use this to send consolidated report along with inconsistencies
USR_TRADELOG_DB_FOLDER = os.getenv('USR_TRADELOG_DB_FOLDER')
ACTIVE_STRATEGIES = os.getenv('ACTIVE_STRATEGIES').split(',')

def get_today_trades(user_db):
    # go to all tables matching name with any str in ACTIVE_STRATEGIES and check if 'exit_time' is today and return list of all such trades
    today_trades = []
    for strategy in ACTIVE_STRATEGIES:
        trades = user_db.execute(f"SELECT * FROM {strategy} WHERE exit_time = date('now')").fetchall()
        today_trades.extend(trades)
    print("today_trades", today_trades)
    return today_trades
    

def get_additions_withdrawals(user_db):
    # go to "Transactions" table and check if 'transaction_date' is today and get sum of 'amount' column for all such transactions
    additions_withdrawals = user_db.execute("SELECT SUM(amount) FROM Transactions WHERE transaction_date = date('now')").fetchone()[0]
    print("additions_withdrawals", additions_withdrawals)
    return additions_withdrawals

def get_new_holdings(user_db):
    # go to "Holdings" table and get net sum of "MarginUtilized" column
    new_holdings = user_db.execute("SELECT SUM(MarginUtilized) FROM Holdings").fetchone()[0]
    print("new_holdings", new_holdings)
    return new_holdings
    

def update_account_keys_fb(tr_no, today_string, new_account, new_free_cash, new_holdings):
    pass

# Main function to generate and send the report
def main():
    from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import get_db_connection
    
    active_users = fetch_active_users_from_firebase()
    
    for user in active_users:
        user_db_path = f"USR_TRADELOG_DB_FOLDER/{user}.db"
        user_db = get_db_connection(user_db_path)
        

        # Placeholder values, replace with actual queries and Firebase fetches
        today_trades = get_today_trades(user_db)
        gross_pnl = sum(trade["pnl"] for trade in today_trades)
        expected_tax = sum(trade["tax"] for trade in today_trades)
        
        today_string = datetime.now().strftime('%Y-%m-%d')
        previous_trading_day_string = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        previous_free_cash = user['Accounts'][f"{previous_trading_day_string}_FreeCash"]
        previous_holdings = user['Accounts'][f"{previous_trading_day_string}_Holdings"]
        previous_account = user['Accounts'][f"{previous_trading_day_string}_Account_Value"]

        # Assuming no additions/withdrawals for simplicity, replace with actual logic to calculate
        additions_withdrawals = get_additions_withdrawals(user_db)

        new_free_cash = previous_free_cash + gross_pnl - expected_tax
        # Placeholder for calculating new holdings, assuming it's equal to previous for this example
        new_holdings = get_new_holdings(user_db)
        new_account = previous_account + gross_pnl - expected_tax + additions_withdrawals

        net_change = new_account - previous_account
        net_change_percentage = (net_change / previous_account) * 100 if previous_account else 0
        # Placeholder for drawdown calculation
        drawdown = user['Accounts']["NetPnL"] - user['Accounts']["PnLWithdrawals"]
        drawdown_percentage = drawdown / new_account * 100
        
        update_account_keys_fb(user['Tr_No'], today_string, new_account, new_free_cash, new_holdings)

        # Format the message
        message = f"Hello {user}, We hope you're enjoying a wonderful day.\n\n"
        message += "Here are your PNLs for today:\n\n"
        message += "Today's Trades:\n"
        for trade in today_trades:
            message += f"{trade['trade_id']}: ₹{trade['pnl']}\n"
        message += f"\nGross PnL: ₹{gross_pnl}\n"
        message += f"Expected Tax: ₹{expected_tax}\n"
        message += f"02FEB24 Free Cash: ₹{previous_free_cash}\n"
        message += f"03FEB24 Free Cash: ₹{new_free_cash}\n\n"
        message += "Holdings:\n"
        message += f"02FEB24 Holdings: ₹{previous_holdings}\n"
        message += f"03FEB24 Holdings: ₹{new_holdings}\n\n"
        message += "Account:\n"
        message += f"02FEB24 Account: ₹{previous_account}\n"
        message += f"Additions/Withdrawals: ₹{additions_withdrawals}\n"
        message += f"03FEB24 Account: ₹{new_account}\n"
        message += f"NetChange: ₹{net_change} ({net_change_percentage:.2f}%)\n"
        message += f"Drawdown: ₹{drawdown}({drawdown_percentage:.2f}%)\n\n"
        message += "Best Regards,\nTradeMan"

      # Send the report to Discord
    # send_discord_message(combined_report)

if __name__ == "__main__":
    main()
    
 