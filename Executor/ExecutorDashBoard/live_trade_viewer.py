import os, sys
import streamlit as st
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Initialize the Streamlit app
st.title('User Trade State Viewer')

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import fetch_collection_data_firebase

# Fetch data from Firebase
users_data = fetch_collection_data_firebase("new_clients")

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