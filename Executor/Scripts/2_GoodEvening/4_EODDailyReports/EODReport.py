import os, sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
from babel.numbers import format_currency

# Define constants and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

from loguru import logger
ERROR_LOG_PATH = os.getenv('ERROR_LOG_PATH')
logger.add(ERROR_LOG_PATH,level="TRACE", rotation="00:00",enqueue=True,backtrace=True, diagnose=True)


from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_users_from_firebase
from Executor.ExecutorUtils.NotificationCenter.Telegram.telegram_adapter import send_telegram_message
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import get_db_connection

# Load environment variables fromx the trademan.env file
ENV_PATH = os.path.join(DIR, 'trademan.env')
load_dotenv(ENV_PATH)

db_dir = os.getenv('DB_DIR')
# ACTIVE_STRATEGIES = os.getenv('ACTIVE_STRATEGIES')
active_stratgies = ['ExpiryTrader','GoldenCoin']####WARNING: This is a placeholder, replace with actual logic to get active strategies

def get_today_trades(user_tables):
    # got to user db and find table names matching Active Strategies and get trades for today
    today_string = datetime.now().strftime('%Y-%m-%d')
    today_trades = []
    # print("user_tables", user_tables)
    for strategy in active_stratgies:
        #user_tables is a list of dict with table name as key and table df as value, match the strategy name with the key and get the trades for today
        for table in user_tables:
            # print("strategy_name", list(table.keys())[0])
            if strategy in list(table.keys())[0]:
                trades = table[strategy]
                #in the table the exit_time column is in this format '2021-08-25 15:30:00'. so i want convert it to '2021-08-25' and then compare it with today_string if matched append it to today_trades
                trades['exit_time'] = trades['exit_time'].apply(lambda x: x.split(' ')[0])
                if today_string in trades['exit_time'].values:
                    today_trades.extend(trades[trades['exit_time'] == today_string].to_dict('records'))      
    return today_trades

def get_additions_withdrawals(user_tables):
    #key = Transactions and get the sum of the "amount" column for today under transaction_date which is in this format '2021-08-25 15:30:00'
    today_string = datetime.now().strftime('%Y-%m-%d')
    additions_withdrawals = 0
    for table in user_tables: 
        if list(table.keys())[0] == 'Transactions':
            transactions = table['Transactions']
            transactions['transaction_date'] = transactions['transaction_date'].apply(lambda x: x.split(' ')[0])
            if today_string in transactions['transaction_date'].values:
                additions_withdrawals = transactions[transactions['transaction_date'] == today_string]['amount'].sum()
    logger.debug("additions_withdrawals", additions_withdrawals)
    return round(additions_withdrawals)

def get_new_holdings(user_tables):
    # go to "Holdings" table and get net sum of "MarginUtilized" column
    new_holdings = 0
    for table in user_tables:
        if list(table.keys())[0] == 'Holdings':
            holdings = table['Holdings']
            new_holdings = holdings['margin_utilized'].sum()
    logger.info("new_holdings", new_holdings)
    return round(new_holdings)
    

def update_account_keys_fb(tr_no, today_fb_format, new_account, new_free_cash, new_holdings,previous_trading_day_fb_format):
    from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import update_fields_firebase,delete_fields_firebase
    #use this method to update the account keys in the firebase update_fields_firebase(collection, document, data, field_key=None)
    update_fields_firebase('new_clients', tr_no, {f"{today_fb_format}_AccountValue": new_account, f"{today_fb_format}_FreeCash": new_free_cash, f"{today_fb_format}_Holdings": new_holdings}, 'Accounts')

    #i want to delete all the keys which have previous_trading_day_string in them
    delete_fields_firebase('new_clients', tr_no, f"Accounts/{previous_trading_day_fb_format}_AccountValue")
    delete_fields_firebase('new_clients', tr_no, f"Accounts/{previous_trading_day_fb_format}_FreeCash")
    delete_fields_firebase('new_clients', tr_no, f"Accounts/{previous_trading_day_fb_format}_Holdings")

    

# Main function to generate and send the report
def main():
    #TODO: Logic to handle user transactions
    
    
    active_users = fetch_active_users_from_firebase()
    
    for user in active_users:
        user_db_path = os.path.join(db_dir, f"{user['Tr_No']}.db")
        user_db_conn = get_db_connection(user_db_path)

        user_tables = []
        #get all the tables in the user db with table name as key and table df as value
        for table in user_db_conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall():
            user_table = {}
            #create user table_df without the index column from sql table and append it to user_tables as a dict with table name as key and table df as value
            user_table[table[0]] = pd.read_sql_query(f"SELECT * FROM {table[0]}", user_db_conn)
            user_tables.append(user_table)
            
        phone_number = user['Profile']['PhoneNumber']
        
        # Placeholder values, replace with actual queries and Firebase fetches
        today_trades = get_today_trades(user_tables)
        #TODO: add DTD function to append to the DTD table in the user's db
        gross_pnl = sum(trade["pnl"] for trade in today_trades)
        expected_tax = sum(trade["tax"] for trade in today_trades)
        
        today_string = datetime.now().strftime('%Y-%m-%d')
        today_fb_format = datetime.now().strftime('%d%b%y')
        previous_trading_day_string = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d') #TODO: Replace with actual logic to get previous trading day
        previous_trading_day_fb_format = (datetime.now() - timedelta(days=1)).strftime('%d%b%y')
        #02Feb24_Account_Value
        

        previous_free_cash = user['Accounts'][f"{previous_trading_day_fb_format}_FreeCash"]
        previous_holdings = user['Accounts'][f"{previous_trading_day_fb_format}_Holdings"]
        previous_account = user['Accounts'][f"{previous_trading_day_fb_format}_AccountValue"]

        # Assuming no additions/withdrawals for simplicity, replace with actual logic to calculate
        additions_withdrawals = get_additions_withdrawals(user_tables)

        new_free_cash = round(previous_free_cash + gross_pnl - expected_tax)
        # Placeholder for calculating new holdings, assuming it's equal to previous for this example
        new_holdings = get_new_holdings(user_tables)
        new_account = round(previous_account + gross_pnl - expected_tax + additions_withdrawals)

        net_change = new_account - previous_account
        net_change_percentage = (net_change / previous_account) * 100 if previous_account else 0
        # Placeholder for drawdown calculation
        drawdown = user['Accounts']["NetPnL"] - user['Accounts']["PnLWithdrawals"]
        drawdown_percentage = drawdown / new_account * 100
        
        # update_account_keys_fb(user['Tr_No'], today_fb_format, new_account, new_free_cash, new_holdings,previous_trading_day_fb_format)
        
        # Format the message
        user_name = user['Profile']['Name']
        message = f"Hello {user_name}, We hope you're enjoying a wonderful day.\n\n"
        message += "Here are your PNLs for today:\n\n"
        message += "Today's Trades:\n"
        for trade in today_trades:
            message += f"{trade['trade_id']}: {format_currency(trade['pnl'],'INR', locale='en_IN')}\n"
        message += f"\nGross PnL: {format_currency(gross_pnl, 'INR', locale='en_IN')}\n"
        message += f"Expected Tax: {format_currency(expected_tax,'INR',locale='en_IN')}\n"
        message += f"{previous_trading_day_fb_format} Free Cash: {format_currency(previous_free_cash,'INR', locale='en_IN')}\n"
        message += f"{today_fb_format} Free Cash: {format_currency(new_free_cash,'INR', locale='en_IN')}\n\n"
        message += "Holdings:\n"
        message += f"{previous_trading_day_fb_format} Holdings: {format_currency(previous_holdings,'INR', locale='en_IN')}\n"
        message += f"{today_fb_format} Holdings: {format_currency(new_holdings,'INR', locale='en_IN')}\n\n"
        message += "Account:\n"
        message += f"{previous_trading_day_fb_format} Account: {format_currency(previous_account,'INR', locale='en_IN')}\n"
        message += f"Additions/Withdrawals: {format_currency(additions_withdrawals,'INR', locale='en_IN')}\n"
        message += f"{today_fb_format} Account: {format_currency(new_account,'INR', locale='en_IN')}\n"
        message += f"NetChange: {format_currency(net_change,'INR', locale='en_IN')} ({net_change_percentage:.2f}%)\n"
        message += f"Drawdown: {format_currency(drawdown,'INR', locale='en_IN')}({drawdown_percentage:.2f}%)\n\n"
        message += "Best Regards,\nTradeMan"

      # Send the report to Discord
    send_telegram_message(phone_number, message)

if __name__ == "__main__":
    main()