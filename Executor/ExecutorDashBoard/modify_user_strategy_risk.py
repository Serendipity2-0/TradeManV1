import os, sys
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
import csv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

signal_db_path = os.getenv("SIGNAL_DB_PATH")
ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
PARAMS_UPDATE_LOG_CSV_PATH = os.getenv("PARAMS_UPDATE_LOG_CSV_PATH")

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import fetch_collection_data_firebase, update_fields_firebase, update_collection
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_users_from_firebase, fetch_active_strategies_all_users

logger = LoggerSetup()

user_fb_collection = os.getenv("FIREBASE_USER_COLLECTION")
strategy_fb_collection = os.getenv("FIREBASE_STRATEGY_COLLECTION")

def modify_user_strategy_params():
    try:
        if 'active_users' not in st.session_state:
            st.session_state.active_users = fetch_active_users_from_firebase()

        if 'active_strategies' not in st.session_state:
            st.session_state.active_strategies = fetch_active_strategies_all_users()

        active_users = fetch_active_users_from_firebase()
        # Create a list of the Tr_no of the active users
        traders_list = ["Select All"] + [user['Tr_No'] for user in active_users]

        active_strategies = fetch_active_strategies_all_users()

        # Trader number dropdown
        trader_number_selection = st.selectbox("Select Trader Number", traders_list)

        # Convert selection to a list
        if trader_number_selection == "Select All":
            trader_numbers = [user['Tr_No'] for user in active_users]
        else:
            trader_numbers = [trader_number_selection]

        # Strategies dropdown
        strategy = st.selectbox("Select Trading Strategy", active_strategies)

        #risk percentage
        risk_percentage = st.slider("Enter Risk Percentage", min_value=0.0, max_value=5.0, step=0.1)

        st.write(f"Trader Number: {trader_numbers}")
        st.write(f"Selected Strategy: {strategy}")
        st.write(f"Risk Percentage: {risk_percentage}%")

        if st.button("Submit"):
             st.write("Form submitted!")
             #update the risk percentage in the firebase for the selected user and selected strategy
             for trader_number in trader_numbers:
                update_path = f"Strategies/{strategy}/"
                update_fields_firebase(user_fb_collection, trader_number, {"RiskPerTrade": risk_percentage}, update_path)
    
    except Exception as e:
        logger.error(f"Error in modifying user strategy params: {e}")