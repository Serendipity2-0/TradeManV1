# Required imports
import glob
import os,sys
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import stats as stats
import streamlit as st
from portfoliostats_view import PortfolioStats
from profile_page import show_profile
from dotenv import load_dotenv


DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)


ACTIVE_STRATEGIES = os.getenv("ACTIVE_STRATEGIES")
USR_TRADELOG_DB_FOLDER = os.getenv("USR_TRADELOG_DB_FOLDER")
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

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    
if 'client_data' not in st.session_state:
    st.session_state.client_data = None


def display_formatted_statistics(formatted_stats):
    # Convert the statistics to a DataFrame for better display
    stats_df = pd.DataFrame(list(formatted_stats.items()), columns=["Metric", "Value"])

    # Apply conditional formatting
    def color_value(val):
        color = "black"  # default
        try:
            num = float(val)
            if num < 0:
                color = "red"  # bad
            elif num > 0:
                color = "green"  # good
            # Add more conditions for 'okay' or other statuses
        except ValueError:
            pass  # Keep default color for non-numeric values
        return f"color: {color};"

    st.write(stats_df.style.map(color_value))


##################################################################


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

    # print(aggregated_data)
    return aggregated_data


def process_tables(db_path, table_name):
    # Attempt to load the specific table from the SQLite database
    print("db_path", db_path)
    try:
        # Check if the table_name exists in the database
        if table_name in ACTIVE_STRATEGIES:
            conn = sqlite3.connect(db_path)
            data = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            data["exit_time"] = pd.to_datetime(data["exit_time"])
            return data
        elif table_name == "DTD":
            return create_dtd_df(db_path)
        elif table_name == "Transactions" or table_name == "Holdings":
            conn = sqlite3.connect(db_path)
            return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    except Exception as e:
        st.error(f"Error: {e}")


def determine_file_type(file_name):
    # Implement your logic here. For example, you might check the file name pattern
    if "signals" in file_name.lower():
        return "signals"
    else:
        return "user"


# Streamlit app
def main():
    from user_login_page import  user_login_page
    st.title("Trading Strategy Analyzer")

    if not st.session_state.logged_in:
        logger.debug("User not logged in")
        user_login_page()

    if st.session_state.logged_in:

        # Extract username or another unique identifier from the session state
        username = st.session_state.client_data[
            "Username"
        ]  # Adjust based on actual data
        
        print("username", username)

        # Modify the logic to select only the file associated with the logged-in user
        db_files = [f for f in get_db_files(USR_TRADELOG_DB_FOLDER) if username in f]

        # Get list of SQLite database file names
        db_file_names = [os.path.basename(file) for file in db_files]

        selected_file = db_file_names[0]

        # Get table names (strategies) from the selected file
        table_names = get_table_names(os.path.join(USR_TRADELOG_DB_FOLDER, selected_file))

        user_strategy_table_names = [
            table for table in table_names if table in ACTIVE_STRATEGIES
        ]

        # Sidebar for strategy selection
        selected_strategy = st.sidebar.radio(
            "Choose a strategy", user_strategy_table_names
        )

        # Determine whether the selected file is 'Signals' or a user file
        is_signals = "Signals" in selected_file

        # Process the selected sheet and get data, stats, and charts
        data = process_tables(
            os.path.join(USR_TRADELOG_DB_FOLDER, selected_file), selected_strategy
        )

        dtd_data = process_tables(os.path.join(USR_TRADELOG_DB_FOLDER, selected_file), "DTD")

        transactions_data = process_tables(
            os.path.join(USR_TRADELOG_DB_FOLDER, selected_file), "Transactions"
        )

        holdings_data = process_tables(
            os.path.join(USR_TRADELOG_DB_FOLDER, selected_file), "Holdings"
        )

        account_value = 2500000 # TODO: This should be fetched from the database
        port_stats = PortfolioStats(dtd_data, account_value)

        # Create tabs for 'Data', 'Stats', and 'Charts'
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
            [
                "Profile",
                "PortfolioView",
                "Strategy Data",
                "Holdings",
                "DailyTrades",
                "Transactions",
                "UserTrades",
            ]
        )

        with tab1:
            show_profile(st.session_state.client_data)

        with tab2:
            st.header("Portfolio View")

            equity_curve_fig = port_stats.show_equity_curve()
            st.pyplot(equity_curve_fig)

            monthly_returns_table = port_stats.calculate_monthly_returns()
            weekly_returns_table = port_stats.calculate_weekly_returns
            st.write("Monthly Returns:", monthly_returns_table)
            st.write("Weekly Returns:", weekly_returns_table)

            max_impact_df = port_stats.max_impact_day()

            st.write("Max Impact Day:")
            st.table(max_impact_df)

            portfolio_statistics = port_stats.portfolio_stats()
            with st.expander("Portfolio Statistics"):
                # st.write("Portfolio Statistics:")
                st.write(portfolio_statistics)

        with tab3:
            st.header("Strategy View")

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

                # Display the plot in Streamlit

        with tab4:
            st.header("Holdings")
            st.write(holdings_data)

        with tab5:
            st.header("Daily Trades")

        with tab6:
            st.header("Transactions")
            st.write(transactions_data)

        with tab7:
            st.header("User Trades")


# Run the app
if __name__ == "__main__":
    main()
