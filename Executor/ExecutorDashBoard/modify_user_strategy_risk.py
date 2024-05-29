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

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import  update_fields_firebase
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_strategies_all_users, fetch_users_for_strategies_from_firebase
from Executor.ExecutorDashBoard.exe_main_app_utils import log_changes
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import discord_admin_bot

logger = LoggerSetup()

user_fb_collection = os.getenv("FIREBASE_USER_COLLECTION")
strategy_fb_collection = os.getenv("FIREBASE_STRATEGY_COLLECTION")

def modify_user_strategy_params():
    """
    The function `modify_user_strategy_params` allows users to select a trader number, trading strategy,
    and risk percentage, and submit the form to update the risk percentage in Firebase for the selected
    user and strategy.
    """
    try:
        with st.form("modify_user_strategy_params"):
            # Strategies dropdown
            active_strategies = fetch_active_strategies_all_users()
            strategy = st.selectbox("Select Trading Strategy", active_strategies)
            strategy_active_users = fetch_users_for_strategies_from_firebase(strategy)
            traders_list = ["Select All"] + [user['Tr_No'] for user in strategy_active_users]

            # Trader number dropdown
            trader_number_selection = st.selectbox("Select Trader Number", traders_list)
            trader_numbers = [user['Tr_No'] for user in strategy_active_users] if trader_number_selection == "Select All" else [trader_number_selection]

            # Risk percentage
            risk_percentage = round(st.number_input("Enter Risk Percentage", min_value=0.0, max_value=10.0, step=0.1), 2)

            if strategy =="PyStocks":
                #SECTOR is hardcoded for now need to change once the csv is ready
                sector = st.selectbox("Select the Sector", ["GAS", "AUTOMOBILE", "ELECTRIC", "FINANCE", "HOUSEHOLD", "INDUSTRY", "REALTY", "RETAIL", "TRANSPORT", "OTHER"])
                cap = st.selectbox("Select the Cap", ["SMALL", "MID", "LARGE"])
            submit_button = st.form_submit_button("Submit")

        # Form submission
        if submit_button:
            st.write("Form submitted!")
            st.write(f"Trader Number: {trader_numbers}")
            st.write(f"Selected Strategy: {strategy}")
            update_fields = {"RiskPerTrade": risk_percentage}
            if strategy == "PyStocks":
                update_fields.update({"Sector": sector, "Cap": cap})
            for trader_number in trader_numbers:
                update_path = f"Strategies/{strategy}/"
                update_fields_firebase(user_fb_collection, trader_number, update_fields, update_path)
            message = f"Params {update_fields.keys()} changed for {strategy} for {trader_numbers}"
            log_changes(update_fields, section_info=message)
            discord_admin_bot(message)
            st.success("Form submitted successfully!")
    
    except Exception as e:
        logger.error(f"Error in modifying user strategy params: {e}")