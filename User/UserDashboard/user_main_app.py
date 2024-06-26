# Required imports
import glob
import os,sys
import sqlite3
from babel.numbers import format_currency
import pandas as pd
import plotly.graph_objects as go
import stats as stats
import streamlit as st
from portfoliostats_view import PortfolioStats
from profile_page import show_profile
from dotenv import load_dotenv
from datetime import datetime

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.ExeUtils import get_previous_trading_day
from User.UserDashboard.user_dashboard_utils import ACTIVE_STRATEGIES

USR_TRADELOG_DB_FOLDER = os.getenv("USR_TRADELOG_DB_FOLDER")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    
if 'client_data' not in st.session_state:
    st.session_state.client_data = None


def display_formatted_statistics(formatted_stats):
    # Convert the statistics dictionary to a DataFrame
    stats_df = pd.DataFrame(list(formatted_stats.items()), columns=["Metric", "Value"])

    # Define the metrics to format as currency
    currency_metrics = {
        "Avg. Profit/Loss (Expectancy Rs)", 
        "Max. Trade Drawdown", 
        "Max. System Drawdown"
    }

    # Define a function to format values as currency and apply color based on the value
    def format_and_color(row):
        metric, val = row['Metric'], row['Value']
        try:
            # Convert to float and format as currency if the metric matches
            num = float(val)
            if metric in currency_metrics:
                val = format_currency(num, 'INR', locale='en_IN')
            color = "red" if num < 0 else "green" if num > 0 else "black"
            return f'<span style="color: {color};">{val}</span>'
        except ValueError:
            return val  # Return the value unchanged if it's not a number

    # Apply the formatting and coloring function
    stats_df['Value'] = stats_df.apply(format_and_color, axis=1)

    # Display the DataFrame using Streamlit's HTML rendering to support styling
    st.write(stats_df.to_html(escape=False, index=False), unsafe_allow_html=True)

# Function to get all SQLite database files in the specified folder
def get_db_files(folder_path):
    pattern = f"{folder_path}/*.db"
    return glob.glob(pattern)


# Function to get all table names from a SQLite database file
def get_table_names(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [table[0] for table in cursor.fetchall()]


def create_charts(df, column_for_calc):
    # Equity Chart
    df["Cumulative_PnL"] = df[column_for_calc].cumsum()
    equity_chart = go.Figure()
    equity_chart.add_trace(
        go.Scatter(
            x=df.index, y=df["Cumulative_PnL"], mode="lines", name="Equity Curve"
        )
    )

    # Drawdown Chart
    roll_max = df["Cumulative_PnL"].cummax()
    drawdown = roll_max - df["Cumulative_PnL"]
    drawdown_chart = go.Figure()
    drawdown_chart.add_trace(
        go.Scatter(x=df.index, y=drawdown, mode="lines", name="Drawdown")
    )

    return equity_chart, drawdown_chart


def create_dtd_df(file_path):
    # Read the 'DTD' table with sql lite
    conn = sqlite3.connect(file_path)
    dtd_table_name = "DTD"
    dtd_data = pd.read_sql_query(f"SELECT * FROM '{dtd_table_name}'", conn)

    # Convert 'Amount' to a numeric value (if needed)
    # This assumes 'Amount' is stored as a string with currency symbols.
    dtd_data["Amount"] = (
        dtd_data["Amount"].replace("[₹,]", "", regex=True).astype(float)
    )

    # Specify the date format for your 'Date' column if known, or leave as None for automatic parsing
    date_format = (
        None  # Update this with your date format, e.g., '%Y-%m-%d' or leave as None
    )

    # Aggregate 'Amount' by 'Date' to calculate 'NetPnL'
    aggregated_data = (
        dtd_data.groupby("Date").agg(NetPnL=("Amount", "sum")).reset_index()
    )
    aggregated_data["Date"] = pd.to_datetime(
        aggregated_data["Date"], format=date_format, errors="coerce"
    )
    aggregated_data["Day"] = aggregated_data["Date"].dt.day_name()

    return aggregated_data


def process_tables(db_path, table_name):
    strategies = ACTIVE_STRATEGIES + ["Holdings"]
    # Attempt to load the specific table from the SQLite database
    try:
        # Check if the table_name exists in the database
        conn = sqlite3.connect(db_path)
        if table_name in strategies:
            data = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            if table_name == "Holdings":
                return data
            data["exit_time"] = pd.to_datetime(data["exit_time"])
            return data
        elif table_name == "Deposits" or table_name == "Withdrawals" or table_name == "Charges":
            table_df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            return table_df
    except Exception as e:
        st.error(f"Error: {e}")

def determine_file_type(file_name):
    # Implement your logic here. For example, you might check the file name pattern
    if "signals" in file_name.lower():
        return "signals"
    else:
        return "user"
    
def create_dtd_data(file_path, table_names):
    dtd_data_list = []  # Use a list to collect DataFrame fragments
    
    conn = sqlite3.connect(file_path)
    for table in table_names:
        data = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        
        # Check if required columns exist in the table
        required_columns = ['exit_time', 'trade_id', 'net_pnl']
        if all(item in data.columns for item in required_columns):
            dtd_data_list.append(data[required_columns])
        else:
            missing_cols = set(required_columns) - set(data.columns)
            logger.error(f"Missing columns {missing_cols} in table {table}")
    
    if dtd_data_list:  # Only concatenate if there are data frames in the list
        dtd_data = pd.concat(dtd_data_list, ignore_index=True)  # Concatenate all DataFrame fragments
        return dtd_data
    else:
        logger.error("No data frames to concatenate. Check table column consistency.")
        return None


# Streamlit app
def main():
    from user_login_page import  user_login_page
    st.title("Trading Strategy Analyzer")

    if not st.session_state.logged_in:
        user_login_page()

    if st.session_state.logged_in and st.session_state.login_type == "client":

        # Logout Button in the sidebar
        if st.sidebar.button('Logout'):
            st.session_state.client_data = None
            st.session_state.logged_in = False 
            st.sidebar.success("You have been logged out.")
            st.experimental_rerun()

        # Extract username or another unique identifier from the session state
        username = st.session_state.client_data[
            "Tr_No"
        ]  # Adjust based on actual data
        
        # Modify the logic to select only the file associated with the logged-in user
        db_files = [f for f in get_db_files(USR_TRADELOG_DB_FOLDER) if username in f]

        # Get list of SQLite database file names
        db_file_names = [os.path.basename(file) for file in db_files]

        selected_file = db_file_names[0]
        
        selected_file_path = os.path.join(USR_TRADELOG_DB_FOLDER, selected_file)

        # Get table names (strategies) from the selected file
        table_names = get_table_names(os.path.join(USR_TRADELOG_DB_FOLDER, selected_file))
        
        user_strategy_table_names = [
            table for table in table_names if table in ACTIVE_STRATEGIES
        ]
        


        # Create tabs for 'Data', 'Stats', and 'Charts'
        tab1, tab2, tab3, tab4, tab5= st.tabs(
            [
                "Profile",
                "PortfolioView",
                "Strategy Data",
                "Holdings",
                "Transactions",
            ]
        )

        with tab1:
            show_profile(st.session_state.client_data)

        with tab2:
            st.header("Portfolio View")
            dtd_data = create_dtd_data(os.path.join(USR_TRADELOG_DB_FOLDER, selected_file),user_strategy_table_names)
            previous_trading_day_fb_format = get_previous_trading_day(datetime.today())
            previous_day_key = previous_trading_day_fb_format+"_"+'AccountValue'
            account_value = st.session_state.client_data.get("Accounts").get(previous_day_key)
            port_stats = PortfolioStats(dtd_data, account_value)
            equity_curve_fig = port_stats.show_equity_curve()
            st.pyplot(equity_curve_fig)

            monthly_returns_table = port_stats.calculate_monthly_returns()
            weekly_returns_table = port_stats.calculate_weekly_returns()
            
            st.dataframe(monthly_returns_table,use_container_width=True)
            st.dataframe(weekly_returns_table,use_container_width=True)

            max_impact_df = port_stats.max_impact_day()

            st.write("Max Impact Day:")
            st.table(max_impact_df)

            portfolio_statistics = port_stats.portfolio_stats()
            with st.expander("Portfolio Statistics"):
                # st.write("Portfolio Statistics:")
                st.dataframe(portfolio_statistics,use_container_width=True)

        with tab3:
            st.header("Strategy View")
            st.session_state.active_tab = "Strategy Data"

            if st.session_state.active_tab == "Strategy Data":
            
                # Conditionally render the sidebar within this tab
                selected_strategy = st.sidebar.radio(
                    "Choose a strategy", user_strategy_table_names
                )
            
                # Process the selected sheet and get data, stats, and charts
                data = process_tables(
                    os.path.join(USR_TRADELOG_DB_FOLDER, selected_file), selected_strategy
                )
                
                # Determine whether the selected file is 'Signals' or a user file
                is_signals = "Signals" in selected_file

                if selected_strategy in ACTIVE_STRATEGIES:
                    column_for_calc = "trade_points" if is_signals else "net_pnl"
                    equity_chart, drawdown_chart = create_charts(
                        data, column_for_calc
                    )  # This should return a plotly.graph_objs.Figure
                    # Use the figure directly in st.plotly_chart
                    formatted_stats = stats.return_statistics(data, is_signals)
                    display_formatted_statistics(formatted_stats)
                    st.header("Strategy Equity Curve")
                    st.divider()
                    st.plotly_chart(equity_chart, use_container_width=True)
                    st.divider()
                    st.header("Strategy Drawdown Curve")
                    st.plotly_chart(drawdown_chart, use_container_width=True)
                    st.divider()
                    st.write(f"Data for {selected_strategy}", data)
                    st.divider()

        with tab4:
            st.header("Holdings")
            holdings_data = process_tables(os.path.join(USR_TRADELOG_DB_FOLDER, selected_file), "Holdings")
            st.write(holdings_data)

       
        with tab5:
            st.header("Transactions")
            deposits =  process_tables(selected_file_path, 'Deposits')
            withdrawals = process_tables(selected_file_path, 'Withdrawals')
            charges = process_tables(selected_file_path, 'Charges')
            
            # if deposits column contains 'credit' use deposit['credit'] else if it contains 'Credit' use deposit['Credit']
            if 'credit' in deposits.columns:
                net_deposit = deposits['credit'].astype(float).sum()
                net_withdrawal = withdrawals['debit'].astype(float).sum()
                net_charges = charges['debit'].astype(float).sum()
            elif 'Credit' in deposits.columns:
                net_deposit = deposits['Credit'].astype(float).sum()
                net_withdrawal = withdrawals['Debit'].astype(float).sum()
                net_charges = charges['Debit'].astype(float).sum()
            
            with st.expander("Deposits"):
                st.write(f"Net Deposit: {net_deposit}")
                st.write(deposits)
            with st.expander("Withdrawals"):
                st.write(f"Net Withdrawal: {net_withdrawal}")
                st.write(withdrawals)
            with st.expander("Charges"):    
                st.write(f"Net Charges: {net_charges}")
                st.write(charges)


# Run the app
if __name__ == "__main__":
    main()
