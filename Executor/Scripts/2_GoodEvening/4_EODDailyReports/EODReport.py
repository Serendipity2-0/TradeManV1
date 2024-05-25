import os, sys
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
from babel.numbers import format_currency
from dotenv import load_dotenv
from time import sleep


# Define constants and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

CONSOLIDATED_REPORT_PATH = os.getenv("CONSOLIDATED_REPORT_PATH")
ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_utils import (
    download_json
)
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_active_users_from_firebase,
    fetch_active_strategies_all_users,
    )
from Executor.ExecutorUtils.NotificationCenter.Telegram.telegram_adapter import (
    send_telegram_message,
    send_file_via_telegram,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import get_db_connection
from Executor.ExecutorUtils.ExeUtils import get_previous_trading_day
from Executor.ExecutorUtils.ReportUtils.MarketMovementData import main as fetch_market_movement_data
from Executor.ExecutorUtils.ReportUtils.SignalMovementData import main as fetch_signal_movement_data
from Executor.ExecutorUtils.ReportUtils.UserPnLMovementData import main as user_pnl_movement_data
from Executor.ExecutorUtils.ReportUtils.ErrorLogData import main as fetch_errorlog_data
from Executor.ExecutorUtils.ReportUtils.MarketInfoData import create_market_info_df
from Executor.ExecutorUtils.ReportUtils.EodReportUtils import (
    get_today_trades_for_all_users,
    today_trades_data,
    format_df_data,
    convert_dfs_to_pdf,
    fetch_user_tables,
    calculate_account_values,
    get_today_trades,
    update_account_keys_fb
)

CLIENTS_TRADE_SQL_DB = os.getenv("DB_DIR")
CLIENTS_USER_FB_DB = os.getenv("FIREBASE_USER_COLLECTION")
today_string = datetime.now().strftime("%Y-%m-%d")

def format_and_send_report(user, today_trades, account_values):
    # User details
    user_name = user["Profile"]["Name"]
    phone_number = user["Profile"]["PhoneNumber"]

    # Formatting today's date for the report
    today_fb_format = datetime.now().strftime("%d%b%y")
    previous_trading_day_fb_format = get_previous_trading_day(datetime.now().date())
    gross_pnl = sum(float(trade["pnl"]) for trade in today_trades)
    expected_tax = sum(float(trade["tax"]) for trade in today_trades)

    # Constructing the message
    message = f"Hello {user_name}, We hope you're enjoying a wonderful day.\n\n"
    message += "Here are your PNLs for today:\n\n"
    message += "Today's Trades:\n"
    for trade in today_trades:
        trade_pnl_formatted = format_currency(trade['pnl'], 'INR', locale='en_IN')
        message += f"Trade ID {trade['trade_id']}: {trade_pnl_formatted}\n"
    message += f"\nGross PnL: {format_currency(gross_pnl, 'INR', locale='en_IN')}\n"
    message += f"Expected Tax: {format_currency(expected_tax, 'INR', locale='en_IN')}\n"
    if "additions" in account_values:
        additions = account_values["additions"]
        message += f"\nAdditions: {format_currency(additions, 'INR', locale='en_IN')}\n"
    message += "\nFree Cash:\n"
    message += f"{previous_trading_day_fb_format} Free Cash: {format_currency(account_values['previous_free_cash'], 'INR', locale='en_IN')}\n"
    message += f"{today_fb_format} Free Cash: {format_currency(account_values['new_free_cash'], 'INR', locale='en_IN')}\n\n"
    message += "Holdings:\n"
    message += f"{previous_trading_day_fb_format} Holdings: {format_currency(account_values['previous_holdings'], 'INR', locale='en_IN')}\n"
    message += f"{today_fb_format} Holdings: {format_currency(account_values['new_holdings'], 'INR', locale='en_IN')}\n\n"
    message += "Account:\n"
    message += f"{previous_trading_day_fb_format} Account: {format_currency(user['Accounts'][f'{previous_trading_day_fb_format}_AccountValue'], 'INR', locale='en_IN')}\n"
    message += f"{today_fb_format} Account: {format_currency(account_values['new_account_value'], 'INR', locale='en_IN')}\n"
    message += f"\nNet Change: {format_currency(account_values['net_change'], 'INR', locale='en_IN')} ({account_values['net_change_percentage']:.2f}%)\n"
    message += f"Drawdown: {format_currency(account_values['drawdown'], 'INR', locale='en_IN')} ({account_values['drawdown_percentage']:.2f}%)\n\n"
    message += "Best Regards,\nYour Trading Team"

    # Placeholder for sending the message
    logger.debug(message)
    send_telegram_message(phone_number, message)

def send_consolidated_report_pdf_to_telegram():
    #create the file path of the pdf file
    pdf_file_path = os.path.join(CONSOLIDATED_REPORT_PATH, f"{today_string}_consolidated_report.pdf")
    group_id = os.getenv("TELEGRAM_REPORT_GROUP_ID")
    #send the pdf to the telegram channel
    send_file_via_telegram(int(group_id), pdf_file_path, f"{today_string}_consolidated_report.pdf", is_group=True)

def create_eod_report(active_users, active_strategies):
    for user in active_users:
        try:
            user_db_path = os.path.join(CLIENTS_TRADE_SQL_DB, f"{user['Tr_No']}.db")
            user_db_conn = get_db_connection(user_db_path)
            user_tables = fetch_user_tables(user_db_conn)
            # Placeholder values, replace with actual queries and Firebase fetches
            today_trades = get_today_trades(user_tables,active_strategies)
            account_values = calculate_account_values(user, today_trades, user_tables)
            update_account_keys_fb(user['Tr_No'], account_values)
            format_and_send_report(user, today_trades, account_values)

        except Exception as e:
            logger.error(f"Error in sending User Report telegram message: {e}")

def create_consolidated_report(active_users, active_strategies):
    try:
        #Page 1 data
        df_movements = fetch_market_movement_data()

        #Page 2 data
        df_signals = fetch_signal_movement_data()

        #Page 3 data
        df_market_info = create_market_info_df()

        #Page 4 data
        df_user_pnl = user_pnl_movement_data()

        #Page 5 data
        today_trades = get_today_trades_for_all_users(active_users, active_strategies)
        consolidated_data = today_trades_data(active_users, today_trades)

        consolidated_df = pd.DataFrame(consolidated_data, columns=["Tr_No", "Name", "Base Capital", "Current Capital", "Drawdown", "Current Week PnL", "Net PnL", "Strategy PnL"])
        consolidated_df = format_df_data(consolidated_df)
        output_path = os.path.join(CONSOLIDATED_REPORT_PATH, f"{today_string}_consolidated_report.pdf")

        #Page 6 data
        errorlog_df = fetch_errorlog_data()
        formatted_errorlog_df = format_df_data(errorlog_df)

        convert_dfs_to_pdf(consolidated_df,df_movements, df_signals, df_market_info, df_user_pnl, formatted_errorlog_df,output_path)
        send_consolidated_report_pdf_to_telegram()

        logger.info(f"consolidated_data: {consolidated_data}")
    except Exception as e:
        logger.error(f"Error in generating consolidated report data: {e}")

# Main function to generate and send the report
def main():
    download_json(CLIENTS_USER_FB_DB, "before_eod_report")
    active_users = fetch_active_users_from_firebase()
    active_strategies = fetch_active_strategies_all_users()

    create_eod_report(active_users, active_strategies)
    logger.debug("Sleeping for 10 seconds before creating consolidated report")
    sleep(10)
    latest_active_users = fetch_active_users_from_firebase()
    latest_active_strategies = fetch_active_strategies_all_users()
    create_consolidated_report(latest_active_users, latest_active_strategies)
    
if __name__ == "__main__":
    main()
