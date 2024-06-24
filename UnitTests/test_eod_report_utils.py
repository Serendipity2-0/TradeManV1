from reportlab.platypus import Table
import pytest
import pandas as pd
from unittest.mock import patch, Mock
from datetime import datetime
import os
import sys
from dotenv import load_dotenv

# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Import the functions to test
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ReportUtils.EodReportUtils import (
    update_account_keys_fb,
    get_today_trades,
    get_additions_withdrawals,
    get_new_holdings,
    today_trades_data,
    df_to_table,
    convert_dfs_to_pdf,
    format_df_data,
    calculate_account_values,
    get_today_trades_for_all_users,
)


# Set up the logger
logger = LoggerSetup()

# Constants and Environment Setup
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Use relative paths to reference files and directories within the repository
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
os.environ["CONSOLIDATED_REPORT_PATH"] = os.path.join(
    DIR_PATH, "Data/ConsolidatedReports"
)
os.environ["ERROR_LOG_PATH"] = os.path.join(DIR_PATH, "Data/ErrorLogs")
os.environ["DB_DIR"] = os.path.join(DIR_PATH, "Data/UserSQLDB")
os.environ["FIREBASE_TEST_COLLECTION"] = "test"

today_string = datetime.now().strftime("%Y-%m-%d")


@pytest.fixture
def sample_user_tables():
    return [
        {
            "StrategyA": pd.DataFrame(
                {
                    "exit_time": ["2024-06-07 15:30:00", "2024-06-06 14:00:00"],
                    "other_data": [100, 200],
                }
            )
        },
        {
            "StrategyB": pd.DataFrame(
                {
                    "exit_time": ["2024-06-07 14:00:00", "2024-06-06 14:00:00"],
                    "other_data": [300, 400],
                }
            )
        },
    ]


@pytest.fixture
def sample_user():
    return {
        "Profile": {"Name": "Sample User"},  # Adding the missing "Profile" key
        "Tr_No": "001",  # Adding the missing "Tr_No" key
        "Accounts": {
            "07Jun24_FreeCash": 1000,
            "06Jun24_Holdings": 5000,
            "06Jun24_AccountValue": 6000,
            "CurrentBaseCapital": 7000,
        },
        "Broker": {"BrokerUsername": "test_user"},
    }


@pytest.fixture
def sample_trades():
    return [
        {"trade_id": "T1", "net_pnl": 100},
        {"trade_id": "T2", "net_pnl": 200},
    ]


@pytest.fixture
def sample_dataframe():
    return pd.DataFrame(
        {
            "Tr_No": ["001"],
            "Current Week PnL": ["500.00 (5.00%)"],
            "Net PnL": ["100.00 (1.00%)"],
            "Strategy PnL": ["200.00 (2.00%)"],
        }
    )


@pytest.fixture
def empty_dataframe():
    return pd.DataFrame()


@pytest.fixture
def mock_connection():
    mock_conn = Mock()
    mock_conn.execute.return_value.fetchall.return_value = [("Table1",)]
    return mock_conn


@pytest.fixture
def mock_env():
    patch.dict(
        "os.environ",
        {
            "CONSOLIDATED_REPORT_PATH": "mock_path",
            "ERROR_LOG_PATH": "mock_error_log_path",
            "DB_DIR": "mock_db_dir",
            "FIREBASE_USER_COLLECTION": "mock_fb_collection",
        },
    ).start()


def test_get_new_holdings(sample_user_tables):
    sample_user_tables[0] = {
        "Holdings": pd.DataFrame({"margin_utilized": ["1000", "2000"]})
    }
    result = get_new_holdings(sample_user_tables)
    assert result == 3000


@patch(
    "Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter.update_fields_firebase"
)
def test_update_account_keys_fb(mock_update_fields_firebase, sample_user):
    account_values = {
        "today_fb_format": "07Jun24",
        "new_account_value": 15000,
        "new_free_cash": 5000,
        "new_holdings": 10000,
    }
    update_account_keys_fb("test_tr_no", account_values)
    mock_update_fields_firebase.assert_called_once()


@patch(
    "Executor.ExecutorUtils.ReportUtils.EodReportUtils.get_db_connection",
    return_value=Mock(),
)
@patch(
    "Executor.ExecutorUtils.ReportUtils.EodReportUtils.fetch_user_tables",
    return_value=[{"StrategyA": pd.DataFrame()}],
)
@patch(
    "Executor.ExecutorUtils.ReportUtils.EodReportUtils.get_today_trades",
    return_value=[{"trade_id": "T1", "net_pnl": "100"}],
)
def test_df_to_table():
    # Test case for a normal DataFrame with the expected columns
    df = pd.DataFrame(
        {
            "Tr_No": [1, 2, 3],
            "Current Week PnL": [10.0, -20.0, 0.0],
            "Strategy PnL": [100.0, -200.0, 0.0],
            "Today": [1.0, 2.0, 3.0],
            "Week": [10.0, 20.0, 30.0],
            "Month": [100.0, 200.0, 300.0],
            "Year": [1000.0, 2000.0, 3000.0],
            "Drawdown": [0.5, 0.3, 0.2],
        }
    )
    table = df_to_table(df)
    assert isinstance(table, Table)
    assert len(table._argW) == len(df.columns), f"Column widths mismatch: {table._argW}"

    # Test case for DataFrame missing 'Tr_No' and 'Strategy PnL'
    df = pd.DataFrame(
        {
            "Col1": [1, 2, 3],
            "Current Week PnL": [10.0, -20.0, 0.0],
            "Net PnL": [100.0, -200.0, 0.0],
            "Today": [1.0, 2.0, 3.0],
            "Week": [10.0, 20.0, 30.0],
            "Month": [100.0, 200.0, 300.0],
            "Year": [1000.0, 2000.0, 3000.0],
            "Drawdown": [0.5, 0.3, 0.2],
        }
    )
    table = df_to_table(df)
    assert isinstance(table, Table)
    assert len(table._argW) == len(df.columns), f"Column widths mismatch: {table._argW}"

    # Test case for an empty DataFrame
    df = pd.DataFrame(columns=["Col1", "Col2"])
    table = df_to_table(df)
    assert isinstance(table, Table)
    assert len(table._argW) == len(df.columns), f"Column widths mismatch: {table._argW}"

    # Test case for a DataFrame with a single column
    df = pd.DataFrame({"Col1": [1, 2, 3]})
    table = df_to_table(df)
    assert isinstance(table, Table)
    assert len(table._argW) == len(df.columns), f"Column widths mismatch: {table._argW}"

    # Test case for a DataFrame with more columns than specified
    df = pd.DataFrame(
        {
            "Col1": [1, 2, 3],
            "Col2": [10.0, 20.0, 30.0],
            "Col3": [5.0, 15.0, 25.0],
            "Col4": [50, 100, 150],
            "Col5": [0, 0, 0],
            "Col6": [-10, -20, -30],
            "Col7": [1000, 2000, 3000],
            "Col8": [3000, 2000, 1000],
        }
    )
    table = df_to_table(df)
    assert isinstance(table, Table)
    assert len(table._argW) == len(df.columns), f"Column widths mismatch: {table._argW}"


# Capture exceptions for debugging
def run_test():
    try:
        test_df_to_table()
    except Exception as e:
        print(f"Exception: {e}")
        raise


def test_convert_dfs_to_pdf(tmp_path):
    output_path = tmp_path / "test_output.pdf"

    # Test with normal DataFrames
    trade_df = pd.DataFrame(
        {"Trade ID": [1, 2, 3], "Trade Value": [100.0, 200.0, 300.0]}
    )
    movement_df = pd.DataFrame({"Movement ID": [1, 2], "Movement Value": [50.0, 60.0]})
    signal_with_market_info_df = pd.DataFrame(
        {"Signal": ["Buy", "Sell"], "Market Info": [110.0, 120.0]}
    )
    user_pnl = pd.DataFrame({"User": ["A", "B"], "PnL": [500.0, -100.0]})
    errorlog_df = pd.DataFrame({"Error": ["None", "Minor"], "Count": [0, 1]})

    convert_dfs_to_pdf(
        trade_df,
        movement_df,
        signal_with_market_info_df,
        user_pnl,
        errorlog_df,
        str(output_path),
    )

    assert output_path.exists()

    # Test with empty DataFrames
    trade_df = pd.DataFrame(columns=["Trade ID", "Trade Value"])
    movement_df = pd.DataFrame(columns=["Movement ID", "Movement Value"])
    signal_with_market_info_df = pd.DataFrame(columns=["Signal", "Market Info"])
    user_pnl = pd.DataFrame(columns=["User", "PnL"])
    errorlog_df = pd.DataFrame(columns=["Error", "Count"])

    convert_dfs_to_pdf(
        trade_df,
        movement_df,
        signal_with_market_info_df,
        user_pnl,
        errorlog_df,
        str(output_path),
    )

    assert output_path.exists()

    # Test with missing expected columns
    trade_df = pd.DataFrame({"Col1": [1, 2, 3], "Col2": [100.0, 200.0, 300.0]})

    convert_dfs_to_pdf(
        trade_df,
        movement_df,
        signal_with_market_info_df,
        user_pnl,
        errorlog_df,
        str(output_path),
    )

    assert output_path.exists()


def test_format_df_data(sample_dataframe):
    formatted_df = format_df_data(sample_dataframe)
    assert not formatted_df["Strategy PnL"].empty
