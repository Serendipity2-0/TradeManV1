import sys
import os
import pandas as pd
import pytest
import json
import runpy
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Set up paths and environment
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.Strategies.StrategiesUtil import StrategyBase


# Function to load mock data based on the script path
def load_mock_data(script_path):
    script_name = os.path.basename(script_path)
    mock_data_filename = f"{script_name.replace('.py', '')}_mock.json"
    # Change to the directory where mock data is stored relative to the script
    base_dir = os.path.dirname(__file__)  # Directory of the script
    mock_data_path = os.path.join(
        base_dir, "IntegrationTest", "TestData", mock_data_filename
    )
    with open(mock_data_path, "r") as file:
        return json.load(file)


# Paths to the strategy scripts
strategy_scripts = [
    os.path.join(DIR_PATH, "Executor", "Strategies", "AmiPy", "amipy_place_orders.py"),
    # os.path.join(DIR_PATH, "Executor", "Strategies", "ExpiryTrader", "ExpiryTrader.py"),
    # Add other script paths here
]


# Mock function to replace pandas.read_sql_query
def mock_read_sql_query(sql_query, conn, mock_data):
    if "instrument_master" in sql_query:
        return pd.DataFrame(mock_data.get("InstrumentData", []))
    return pd.DataFrame()  # Empty DataFrame for other queries


# Mock the get_db_connection to return a mock object
def mock_get_db_connection(db_path):
    conn = MagicMock()
    conn.cursor.return_value = MagicMock()  # Mock cursor
    return conn


# Mock the fetch_collection_data_firebase function to return mock data
def mock_fetch_collection_data_firebase(db, document, mock_data):
    return mock_data.get(document, {})


@pytest.mark.parametrize("script_path", strategy_scripts)
def test_strategy_script(script_path):
    # Load the appropriate mock data for the script
    mock_data = load_mock_data(script_path)

    with patch(
        "Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter.fetch_collection_data_firebase",
        side_effect=lambda db, document: mock_fetch_collection_data_firebase(
            db, document, mock_data
        ),
    ), patch(
        "Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter.get_db_connection",
        mock_get_db_connection,
    ), patch(
        "pandas.read_sql_query",
        side_effect=lambda sql_query, conn: mock_read_sql_query(
            sql_query, conn, mock_data
        ),
    ), patch(
        "Executor.Strategies.StrategiesUtil.StrategyBase.load_from_db",
        side_effect=lambda strategy_name: StrategyBase(
            **mock_data.get(strategy_name, {})
        ),
    ):
        try:
            # Run the script
            runpy.run_path(script_path, run_name="__main__")
        except Exception as e:
            pytest.fail(f"Error running {script_path}: {str(e)}")
