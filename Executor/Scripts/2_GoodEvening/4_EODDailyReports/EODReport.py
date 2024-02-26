import os, sys
from datetime import datetime, timedelta,date
from dotenv import load_dotenv
import pandas as pd
from babel.numbers import format_currency
from loguru import logger
from dotenv import load_dotenv
from fpdf import FPDF

# Define constants and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

CONSOLIDATED_REPORT_PATH = os.getenv("CONSOLIDATED_REPORT_PATH")
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
    send_file_via_telegram
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
    account_values
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
                f"{account_values['today_fb_format']}_AccountValue": account_values['new_account_value'],
                f"{account_values['today_fb_format']}_FreeCash": account_values['new_free_cash'],
                f"{account_values['today_fb_format']}_Holdings": account_values['new_holdings'],
            },
            "Accounts",
        )
    except Exception as e:
        logger.error(f"Error in update_account_keys_fb: {e}")

def fetch_user_tables(user_db_conn):
    user_tables = []
    try:
        for table in user_db_conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall():
            user_table = {table[0]: pd.read_sql_query(f"SELECT * FROM {table[0]}", user_db_conn)}
            user_tables.append(user_table)
    except Exception as e:
        logger.error(f"Error in fetching user tables: {e}")
    return user_tables

def calculate_account_values(user, today_trades):
    gross_pnl = sum(float(trade["pnl"]) for trade in today_trades)
    expected_tax = sum(float(trade["tax"]) for trade in today_trades)

    today_fb_format = datetime.now().strftime("%d%b%y")
    previous_trading_day_fb_format = get_previous_trading_day(datetime.now().date())

    previous_free_cash = user["Accounts"][f"{previous_trading_day_fb_format}_FreeCash"]
    previous_holdings = user["Accounts"][f"{previous_trading_day_fb_format}_Holdings"]
    previous_account_value = user["Accounts"][f"{previous_trading_day_fb_format}_AccountValue"]

    # Assuming no additions or withdrawals for simplicity
    additions_withdrawals = 0  # This would be calculated or fetched from somewhere

    new_free_cash = previous_free_cash + gross_pnl - expected_tax
    # Placeholder for new holdings calculation; you might need additional info for this
    new_holdings = previous_holdings  # This is a simplification

    new_account_value = previous_account_value + gross_pnl - expected_tax + additions_withdrawals
    net_change = new_account_value - previous_account_value
    net_change_percentage = (net_change / previous_account_value * 100) if previous_account_value else 0

    # Calculate drawdown, which is a placeholder here; you might need additional data for an accurate calculation
    drawdown = 0  # Simplification
    drawdown_percentage = (drawdown / new_account_value * 100) if new_account_value else 0

    account_values = {
        "today_fb_format": today_fb_format,
        "new_free_cash": new_free_cash,
        "new_holdings": new_holdings,
        "new_account_value": new_account_value,
        "net_change": net_change,
        "net_change_percentage": net_change_percentage,
        "drawdown": drawdown,
        "drawdown_percentage": drawdown_percentage
    }

    return account_values

def format_and_send_report(user, today_trades, account_values):
    # User details
    user_name = user["Profile"]["Name"]
    phone_number = user["Profile"]["PhoneNumber"]

    # Formatting today's date for the report
    today_fb_format = datetime.now().strftime("%d%b%y")

    # Constructing the message
    message = f"Hello {user_name}, We hope you're enjoying a wonderful day.\n\n"
    message += "Here are your PNLs for today:\n\n"
    message += "Today's Trades:\n"
    for trade in today_trades:
        trade_pnl_formatted = format_currency(trade['pnl'], 'INR', locale='en_IN')
        message += f"Trade ID {trade['trade_id']}: {trade_pnl_formatted}\n"
    message += f"\nGross PnL: {format_currency(account_values['new_free_cash'] - account_values['drawdown'], 'INR', locale='en_IN')}\n"
    message += f"Expected Tax: {format_currency(account_values['new_account_value'] - account_values['new_free_cash'], 'INR', locale='en_IN')}\n"
    message += f"{today_fb_format} Free Cash: {format_currency(account_values['new_free_cash'], 'INR', locale='en_IN')}\n\n"
    message += "Holdings:\n"
    message += f"{today_fb_format} Holdings: {format_currency(account_values['new_holdings'], 'INR', locale='en_IN')}\n\n"
    message += "Account:\n"
    message += f"{today_fb_format} Account: {format_currency(account_values['new_account_value'], 'INR', locale='en_IN')}\n"
    message += f"Net Change: {format_currency(account_values['net_change'], 'INR', locale='en_IN')} ({account_values['net_change_percentage']:.2f}%)\n"
    message += f"Drawdown: {format_currency(account_values['drawdown'], 'INR', locale='en_IN')} ({account_values['drawdown_percentage']:.2f}%)\n\n"
    message += "Best Regards,\nYour Trading Team"

    # Placeholder for sending the message
    print(message)
    send_telegram_message(phone_number, message)

def get_today_trades_for_all_users(active_users, active_strategies):
    all_today_trades = []
    for user in active_users:
        try:
            user_db_path = os.path.join(CLIENTS_TRADE_SQL_DB, f"{user['Tr_No']}.db")
            user_db_conn = get_db_connection(user_db_path)
            user_tables = fetch_user_tables(user_db_conn)

            today_trades = get_today_trades(user_tables, active_strategies)
            for trade in today_trades:
                trade['user_tr_no'] = user['Tr_No']  # Optionally tag each trade with the user's TR number for identification
            all_today_trades.extend(today_trades)

        except Exception as e:
            logger.error(f"Error processing trades for user {user['Tr_No']}: {e}")
    return all_today_trades

def generate_consolidated_report_data(active_users, today_trades):
    from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
        update_fields_firebase,
    )
    consolidated_data = []
    for user in active_users:
        strategy_pnl = {}
        user_name = user['Profile']['Name']
        tr_no = user['Tr_No']
        base_capital = user['Accounts']['CurrentBaseCapital']
        today_fb_format = datetime.now().strftime("%d%b%y")
        current_capital = user['Accounts'][f'{today_fb_format}_AccountValue']
        drawdown = min(current_capital-base_capital ,0)
        for trade in today_trades:
            if trade['user_tr_no'] == tr_no:
                strategy_pnl[trade['trade_id']] = trade['net_pnl']

        net_pnl = sum(float(trade['net_pnl']) for trade in today_trades)
        current_week_pnl = user['Accounts'].get('current_week_pnl', 0) + net_pnl
        
        # Update the user's current_week_pnl in Firebase (not shown, assume similar to update_account_keys_fb)
        update_fields_firebase(CLIENTS_USER_FB_DB, tr_no, {"CurrentWeekCapital": current_week_pnl}, "Accounts")

        consolidated_data.append([tr_no, user_name, base_capital, current_capital, drawdown, current_week_pnl, net_pnl, strategy_pnl])
    return consolidated_data

def convert_df_to_pdf(df, output_file):
    class PDF(FPDF):
        def __init__(self, orientation='L', unit='mm', format='A4'):
            super().__init__(orientation, unit, format)
        
        def header(self):
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, "Consolidated Report", 0, 1, "C")
            self.ln(10)
            # Adding headers
            headers = ["Tr_No", "Name", "Base Capital", "Current Capital", "Drawdown", "Current Week PnL", "Net PnL", "Strategy PnL"]
            self.set_font("Arial", "B", 10)  # Bold font for headers
            for header in headers:
                self.cell(30, 10, header, 1)  # Adjust cell width as needed
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

        def chapter_title(self, title):
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, title, 0, 1, "L")
            self.ln(10)

        def chapter_body(self, df):
            self.set_font("Arial", "", 10)
            for index, row in df.iterrows():
                self.cell(30, 10, str(row["Tr_No"]), 1, 0, "L")
                self.cell(30, 10, row["Name"], 1, 0, "L")
                self.cell(30, 10, f"{row['Base Capital']:.2f}", 1, 0, "R")
                self.cell(30, 10, f"{row['Current Capital']:.2f}", 1, 0, "R")
                
                # Change font color to red if Drawdown is less than 0
                if row["Drawdown"] < 0:
                    self.set_text_color(255, 0, 0)  # red
                else:
                    self.set_text_color(0, 0, 0)  # back to black
                self.cell(30, 10, f"{row['Drawdown']:.2f}", 1, 0, "R")
                
                self.set_text_color(0, 0, 0)  # Reset to black before moving to next cell
                self.cell(30, 10, f"{row['Current Week PnL']:.2f}", 1, 0, "R")
                
                # Change font color for Net PnL: green if > 0, else red
                if row["Net PnL"] > 0:
                    self.set_text_color(0, 128, 0)  # green
                else:
                    self.set_text_color(255, 0, 0)  # red
                self.cell(30, 10, f"{row['Net PnL']:.2f}", 1, 0, "R")
                
                # Reset text color to black for the next row
                self.set_text_color(0, 0, 0)
                
                # Assuming Strategy PnL is not a number and just displaying as is
                self.cell(60, 10, str(row["Strategy PnL"]), 1, 0, "R")
                self.ln(10)

    pdf = PDF()
    pdf.add_page()
    pdf.chapter_body(df)
    #save the file in the consolidated report path
    pdf.output(os.path.join(CONSOLIDATED_REPORT_PATH, output_file))

def send_consolidated_report_pdf_to_telegram():
    #create the file path of the pdf file
    pdf_file_path = os.path.join(CONSOLIDATED_REPORT_PATH, f"{today_string}_consolidated_report.pdf")
    #send the pdf to the telegram channel
    send_file_via_telegram(pdf_file_path, f"{today_string}_consolidated_report.pdf")

# Main function to generate and send the report
def main():
    download_json(CLIENTS_USER_FB_DB, "before_eod_report")
    active_users = fetch_active_users_from_firebase()
    active_strategies = fetch_active_strategies_all_users()

    for user in active_users:
        try:
            user_db_path = os.path.join(CLIENTS_TRADE_SQL_DB, f"{user['Tr_No']}.db")
            user_db_conn = get_db_connection(user_db_path)
            user_tables = fetch_user_tables(user_db_conn)
            # Placeholder values, replace with actual queries and Firebase fetches
            today_trades = get_today_trades(user_tables,active_strategies)
            account_values = calculate_account_values(user, today_trades)
            update_account_keys_fb(user['Tr_No'], account_values)
            format_and_send_report(user, today_trades, account_values)

        except Exception as e:
            logger.error(f"Error in sending User Report telegram message: {e}")

    try:
        today_trades = get_today_trades_for_all_users(active_users, active_strategies)
        consolidated_data = generate_consolidated_report_data(active_users, today_trades)
        #convert the consolidated_data to a dataframe and then into a pdf
        consolidated_df = pd.DataFrame(consolidated_data, columns=["Tr_No", "Name", "Base Capital", "Current Capital", "Drawdown", "Current Week PnL", "Net PnL", "Strategy PnL"])
        convert_df_to_pdf(consolidated_df, f"{today_string}_consolidated_report.pdf")
        send_consolidated_report_pdf_to_telegram()


        logger.info(f"consolidated_data: {consolidated_data}")
    except Exception as e:
        logger.error(f"Error in generating consolidated report data: {e}")

if __name__ == "__main__":
    main()
