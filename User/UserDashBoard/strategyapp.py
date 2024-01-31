# Required imports
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import User.UserDashBoard.stats as stats
import os
import glob
import calendarview
from portfoliostats_view import PortfolioStats

strategy_sheet_names  = ['AmiPy', 'MPWizard', 'OvernightFutures', 'ExpiryTrader','PyStocks', 'ExtraTrades', 'ErrorTrade']

#######################
# Page configuration
st.set_page_config(
    page_title="TradeMan Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded")

def display_formatted_statistics(formatted_stats):
    # Convert the statistics to a DataFrame for better display
    stats_df = pd.DataFrame(list(formatted_stats.items()), columns=['Metric', 'Value'])

    # Apply conditional formatting
    def color_value(val):
        color = 'black'  # default
        try:
            num = float(val)
            if num < 0:
                color = 'red'  # bad
            elif num > 0:
                color = 'green'  # good
            # Add more conditions for 'okay' or other statuses
        except ValueError:
            pass  # Keep default color for non-numeric values
        return f'color: {color};'
    st.write(stats_df.style.applymap(color_value))
    
##################################################################
    
# Function to get all excel files in the specified folder
def get_excel_files(folder_path):
   pattern = f"{folder_path}/*.xlsx"
   return glob.glob(pattern)

# Function to get all sheet names (strategies) from an Excel file
def get_sheet_names(file_path):
    xl = pd.ExcelFile(file_path)
    return xl.sheet_names

def create_charts(df, column_for_calc):
    
    # Equity Chart
    df['Cumulative_PnL'] = df[column_for_calc].cumsum()
    equity_chart = go.Figure()
    equity_chart.add_trace(go.Scatter(x=df.index, y=df['Cumulative_PnL'], mode='lines', name='Equity Curve'))

    # Drawdown Chart
    roll_max = df['Cumulative_PnL'].cummax()
    drawdown = roll_max - df['Cumulative_PnL']
    drawdown_chart = go.Figure()
    drawdown_chart.add_trace(go.Scatter(x=df.index, y=drawdown, mode='lines', name='Drawdown'))

    return equity_chart, drawdown_chart

def create_dtd_df (file_path):
    # Read the 'DTD' sheet
    dtd_data = pd.read_excel(file_path, sheet_name='DTD', engine='openpyxl')

    # Convert 'Amount' to a numeric value (if needed)
    # This assumes 'Amount' is stored as a string with currency symbols.
    dtd_data['Amount'] = dtd_data['Amount'].replace('[₹,]', '', regex=True).astype(float)

    # Specify the date format for your 'Date' column if known, or leave as None for automatic parsing
    date_format = None  # Update this with your date format, e.g., '%Y-%m-%d' or leave as None

    # Aggregate 'Amount' by 'Date' to calculate 'NetPnL'
    aggregated_data = dtd_data.groupby('Date').agg(NetPnL=('Amount', 'sum')).reset_index()
    aggregated_data['Date'] = pd.to_datetime(aggregated_data['Date'], format=date_format, errors='coerce')
    aggregated_data['Day'] = aggregated_data['Date'].dt.day_name()

    # print(aggregated_data)
    return aggregated_data

# Function to process the selected sheet and return data, stats, and charts
def process_sheet(file_path, sheet_name):
    # Attempt to load the specific sheet from the excel file
    try:
        # Check if the sheet_name exists in the file
        if sheet_name in strategy_sheet_names:
            data = pd.read_excel(file_path, sheet_name=sheet_name)
            data['exit_time'] = pd.to_datetime(data['exit_time'])
            return data
        elif sheet_name == 'DTD':
            return create_dtd_df(file_path)
        elif sheet_name == 'Transactions'or sheet_name == 'Holdings':
            return pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            print(f"Sheet '{sheet_name}' does not exist in the file.")
            return None  # or handle it as you see fit

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None  # or handle as needed
    except Exception as e:
        # Handle any other exceptions
        print(f"An error occurred: {e}")
        return None  # or handle as needed

def determine_file_type(file_name):
    # Implement your logic here. For example, you might check the file name pattern
    if "signals" in file_name.lower():
        return "signals"
    else:
        return "user"
    
    

# Streamlit app
def main():
    st.title("Trading Strategy Analyzer")

    # Define path of folder containing excel files
    folder_path = r'C:\Users\user\Desktop\Kaas\StrategyAdmin\userexcel'  # Update this with the actual folder path

    # Get all excel files in the folder
    excel_files = get_excel_files(folder_path)
    
    #Get list of Excel file names
    excel_file_names = [os.path.basename(file) for file in excel_files]

    # Sidebar for file selection
    selected_file = st.sidebar.radio("Choose a file", excel_file_names)

    # Get sheet names (strategies) from the selected file
    sheet_names = get_sheet_names(os.path.join(folder_path, selected_file))
    
    user_strategy_sheet_names = [sheet for sheet in sheet_names if sheet in strategy_sheet_names]

    # Sidebar for strategy selection
    selected_strategy = st.sidebar.radio("Choose a strategy", user_strategy_sheet_names)

    # Determine whether the selected file is 'Signals' or a user file
    is_signals = 'Signals' in selected_file

    # Process the selected sheet and get data, stats, and charts
    strategy_data = process_sheet(os.path.join(folder_path, selected_file), selected_strategy)
    
    dtd_data = process_sheet(os.path.join(folder_path, selected_file), 'DTD')
    
    transactions_data = process_sheet(os.path.join(folder_path, selected_file), 'Transactions')
    
    holdings_data = process_sheet(os.path.join(folder_path, selected_file), 'Holdings')
        
    account_value = 2500000 #TODO: Make account value dynamic
    
    port_stats = PortfolioStats(dtd_data, account_value)

    # Create tabs for 'Data', 'Stats', and 'Charts'
    tab1, tab2, tab3, tab4 = st.tabs(["Strategy Data", "PortfolioView","Holdings","Transactions"])

    with tab1:
        if selected_strategy in strategy_sheet_names:
            column_for_calc = 'trade_points' if is_signals else 'net_pnl'
            equity_chart, drawdown_chart = create_charts(strategy_data,column_for_calc)  # This should return a plotly.graph_objs.Figure
            # Use the figure directly in st.plotly_chart
            formatted_stats = stats.return_statistics(strategy_data,is_signals)
            display_formatted_statistics(formatted_stats)
            st.header('Strategy Equity Curve')
            st.divider()
            st.plotly_chart(equity_chart, use_container_width=True)
            st.divider()
            st.header('Strategy Drawdown Curve')
            st.plotly_chart(drawdown_chart, use_container_width=True)
            st.divider()
            st.write(f"Data for {selected_strategy}", strategy_data)
            st.divider()
            st.header('Strategy Calendar View')
            column_for_calc = 'trade_points' if is_signals else 'net_pnl'

            fig1 =calendarview.generate_interactive_calendar_heatmap(strategy_data, 'exit_time', column_for_calc)
            # Display the plot in Streamlit
            # st.plotly_chart(fig1)
        
    with tab2:
        st.header('Portfolio View')

        equity_curve_fig = port_stats.show_equity_curve()
        st.pyplot(equity_curve_fig)

        monthly_returns_table = port_stats.calculate_monthly_returns()
        weekly_returns_table = port_stats.calculate_weekly_returns()
        mod_weekly_returns_table = port_stats.add_financial_metrics(weekly_returns_table,transactions_data)
        
        # st.write("Monthly Returns:", monthly_returns_table)
        st.write("Weekly Returns:", mod_weekly_returns_table)

        max_impact_df = port_stats.max_impact_day()

        st.write("Max Impact Day:")
        st.table(max_impact_df)

        portfolio_statistics = port_stats.portfolio_stats()
        st.write("Portfolio Statistics:")
        st.write(portfolio_statistics)
        st.divider()
        st.header('Portfolio DTD Data')
        st.write(dtd_data)
        
    with tab3:
        st.header('Trade Validator')
        st.write(transactions_data)
        
    with tab4:
        st.header('Holdings')
        st.write(holdings_data)
        

# Run the app
if __name__ == '__main__':
    main()
