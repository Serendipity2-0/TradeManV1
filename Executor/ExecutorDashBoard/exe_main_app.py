# Required imports
import glob
import os,sys
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import error_logging_page
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

#######################
# Page configuration
st.set_page_config(
    page_title="TradeMan Executor Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded",
)

def main():
    from Executor.ExecutorDashBoard.live_trade_viewer import trade_state_viewer, calculate_trademan_stats
    from Executor.ExecutorDashBoard.signal_log_viewer import signal_log_viewer
    from Executor.ExecutorDashBoard.modify_trademan_params import modify_strategy_params, modify_market_info
    from Executor.ExecutorDashBoard.modify_user_strategy_risk import modify_user_strategy_params
    from Executor.ExecutorDashBoard.send_notice import send_notice
    tab1, tab2, tab3, tab4,tab5,tab6,tab7, tab8, tab9 = st.tabs(["Admin","Order Executor", "Trade State","Error Monitor", "Signal Log","Modify Strategy Params","Modify Market Info","Modify User Strategy Risks", "Send Notice"])
    
    st.balloons()

    # TODO: Add streamlit notifications for errors as well as trade state updates
    with tab1:
        st.header("TradeMan Admin")
        calculate_trademan_stats()

    with tab2:
        st.header("Order Executor")

    with tab3:
        st.header("Trade State")
        trade_state_viewer()
    
    with tab4:
        st.header("Error Monitor")
        #TODO: Add streamlit toast when error dataframe is updated to notify the user
        st.dataframe(error_logging_page.read_n_process_err_log(),use_container_width=True,hide_index=True)
        
    with tab5:
        st.header("Signal Log")
        signal_log_viewer()
        
    with tab6:
        st.header("Modify Strategy Params")
        modify_strategy_params()
        
    with tab7:
        st.header("Modify Market Info")
        modify_market_info()
    
    with tab8:
        st.header("Modify User Strategy Risks")
        modify_user_strategy_params()

    with tab9:
        st.header("Send Notice")
        send_notice()
        
# Run the app
if __name__ == "__main__":
    main()
