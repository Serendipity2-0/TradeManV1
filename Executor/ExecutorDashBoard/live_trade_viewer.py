import os, sys
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime

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
                
def calculate_trademan_stats():
    users_data = fetch_active_users_from_firebase()
    today_fb_format = datetime.now().strftime("%d%b%y")
    today_acc_key = f"{today_fb_format}_AccountValue"
    logger.debug(f"type users_data: {type(users_data)}")
    
    # users_data is a list. iterate and get sum of users_data["Accounts"][today_acc_key]
    aum = 0
    net_pnl = 0
    
    no_of_users = len(users_data)
    
    
    for user in users_data:
        aum += user['Accounts'][today_acc_key]
        net_pnl += user['Accounts']['NetPnL']
    
        
    logger.debug(f"Total AUM for today: {aum}")
        
    st.write(f"Total AUM for today: {aum}")
    st.write(f"Total number of users: {no_of_users}")
    st.write(f"Total Net PnL for all clients: {net_pnl}")
    