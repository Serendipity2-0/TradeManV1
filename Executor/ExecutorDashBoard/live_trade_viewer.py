import os, sys
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

user_db_collection = os.getenv("FIREBASE_USER_COLLECTION")

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

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import fetch_collection_data_firebase
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_users_from_firebase

user_db_collection = os.getenv("FIREBASE_USER_COLLECTION")

def trade_state_viewer():
    # Initialize the Streamlit app
    st.title('User Trade State Viewer')
    # Fetch data from Firebase
    # users_data = fetch_active_users_from_firebase()
    
    # Fetch data from Firebase
    users_data = fetch_collection_data_firebase(user_db_collection)

    # User selection dropdown
    user_ids = list(users_data.keys())
    selected_user_id = st.selectbox('Select a User', user_ids)

    # Once a user is selected, display strategy dropdown based on available strategies for that user
    if selected_user_id:
        strategies = users_data[selected_user_id].get('Strategies', {})
        strategy_names = list(strategies.keys())
        selected_strategy_name = st.selectbox('Select a Strategy', strategy_names)

        # Display TradeState for the selected user and strategy
        if selected_strategy_name:
            trade_state = strategies[selected_strategy_name].get('TradeState', {})
            orders = trade_state.get('orders', [])
            if orders:
                for order in orders:
                    st.write(f"Order ID: {order.get('order_id')}, Qty: {order.get('qty')}, Time Stamp: {order.get('time_stamp')}")
            else:
                st.write("No orders found for the selected strategy.")
                
def format_in_indian_lakhs_crores(number):
    if number < 1e5:
        return f"₹{number:,.2f}"
    elif number < 1e7:
        return f"₹{number/1e5:.2f} Lacs"
    else:
        return f"₹{number/1e7:.2f} Crores"
# Example usage with your metrics
                
def calculate_trademan_stats():
    from Executor.ExecutorUtils.ExeUtils import get_previous_trading_day

    users_data = fetch_active_users_from_firebase()
    today_fb_format = datetime.now().strftime("%d%b%y")
    today_acc_key = f"{today_fb_format}_AccountValue"
    logger.debug(f"type users_data: {type(users_data)}")
    
    previous_trading_day_fb_format = get_previous_trading_day(datetime.today())
    previous_day_key = previous_trading_day_fb_format+"_"+'AccountValue'
    
    # users_data is a list. iterate and get sum of users_data["Accounts"][today_acc_key]
    aum = 0
    net_pnl = 0
    
    no_of_users = len(users_data)
    
    
    for user in users_data:
        aum += user['Accounts'][previous_day_key]
        net_pnl += user['Accounts']['NetPnL']
        
    # Assuming AUM, no_of_users, and net_pnl have been calculated as in your function

    col1, col2, col3 = st.columns(3)
    # col1.metric("Total AUM", f"${aum:,.2f}", delta=None)
    # col2.metric("Active Users", f"{no_of_users}", delta=None)
    # col3.metric("Net PnL", f"${net_pnl:,.2f}", delta=None)
    
    col1.metric("Total AUM", format_in_indian_lakhs_crores(aum), delta=None)
    col2.metric("Active Users", f"{no_of_users}", delta=None)
    col3.metric("Net PnL", format_in_indian_lakhs_crores(net_pnl), delta=None)

    
        
    logger.debug(f"Total AUM for today: {aum}")
    
    users_data_list = fetch_active_users_from_firebase()  # Assuming this returns the list of user data
    users_df = pd.DataFrame([{
        'Tr_No': user['Tr_No'],
        'Name': user['Profile']['Name'],
        'CurrentCapital': user['Accounts'][previous_day_key],
        "NetAdditions": user['Accounts']['NetAdditions'],
        "NetCharges": user['Accounts']['NetCharges'],
        "NetCommission": user['Accounts']['NetCommission'],
        "NetPnL": user['Accounts']['NetPnL'],
        "NetWithdrawals": user['Accounts']['NetWithdrawals'],
        "PnLWithdrawals": user['Accounts']['PnLWithdrawals'],
    } for user in users_data_list])
    
    

    # Display the DataFrame
    st.write("Detailed Users Data")
    st.dataframe(users_df,hide_index=True,use_container_width=True)