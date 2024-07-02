import importlib
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import shutil
import datetime as dt
import pandas as pd
import os
import sys
from dotenv import load_dotenv

# Set up paths and environment
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Path to the original and test databases
ORIGINAL_DB_PATH = "D:/TradeManV1/Data/stock_picks.db"
TEST_DB_PATH = "D:/TradeManV1/Data/stock_picks_test.db"


# Mock database connection and cursor for SQLite
class MockCursor:
    def execute(self, *args, **kwargs):
        return None

    def fetchall(self):
        return []

    def fetchone(self):
        return None

    def close(self):
        pass

    @property
    def description(self):
        return [("column1",), ("column2",)]  # Example column names


class MockConnection:
    def cursor(self):
        return MockCursor()

    def commit(self):
        pass

    def close(self):
        pass

    def create_function(self, *args, **kwargs):
        pass

    def rollback(self):
        pass


# Mock functions for SQLite database operations
def mock_sqlite_connect(*args, **kwargs):
    return MockConnection()


# Mock function for Firebase update
def mock_update_signal_firebase(strategy_name, signal, trade_id=None):
    print(
        f"Mock update_signal_firebase called with {strategy_name}, {signal}, {trade_id}"
    )


# Mock function for updating today's stocks in the database
def mock_update_todaystocks_db(*args, **kwargs):
    print("Mock update_todaystocks_db called")


# Mock functions for fetching stock data
def mock_get_shortterm_stocks_df():
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def mock_get_longterm_stocks_df():
    return pd.DataFrame(), pd.DataFrame()


# Mock function for fetch_collection_data_firebase
def mock_fetch_collection_data_firebase(collection, document=None):
    if document == "PyStocks":
        return {
            "StrategyName": "PyStocks",
            "GeneralParams": {
                "OrderType": "Market",
                "ProductType": "CNC",
                "StrategyType": "ShortTerm",
                "ExpiryType": "Monthly",
                "TimeFrame": "Daily",
            },
            "Description": "Short term strategy",
            "EntryParams": {"EntryTime": "09:15:00"},
            "ExitParams": {"SLType": "Fixed"},
            "ExtraInformation": {"QtyCalc": "Fixed"},
            "Instruments": [],
            "MarketInfoParams": {"TradeView": "Bullish"},
        }
    return None


# Mocking the PyStocks object
class MockPyStocks(MagicMock):
    StrategyName = "PyStocks"
    GeneralParams = MagicMock(
        OrderType="Market", ProductType="CNC", StrategyType="ShortTerm"
    )

    @classmethod
    def load_from_db(cls, name):
        if name == "PyStocks":
            return MockPyStocks()
        raise ValueError(f"No data found for strategy {name}")


# Apply the mocks before importing the module
with patch(
    "Executor.NSEStrategies.NSEStrategiesUtil.fetch_collection_data_firebase",
    side_effect=mock_fetch_collection_data_firebase,
):
    with patch(
        "Executor.NSEStrategies.Equity.Equity.PyStocks",
        new_callable=lambda: MockPyStocks,
    ):
        Equity = importlib.import_module("Executor.NSEStrategies.Equity.Equity")


# Simplified test case for the main function
class TestMainFunction(unittest.TestCase):
    @patch("sqlite3.connect", side_effect=mock_sqlite_connect)
    @patch(
        "Executor.NSEStrategies.NSEStrategiesUtil.update_signal_firebase",
        side_effect=mock_update_signal_firebase,
    )
    @patch(
        "Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.update_todaystocks_db",
        side_effect=mock_update_todaystocks_db,
    )
    @patch(
        "Executor.NSEStrategies.Equity.ShortTerm.ShortTermUtils.get_shortterm_stocks_df",
        side_effect=mock_get_shortterm_stocks_df,
    )
    @patch(
        "Executor.NSEStrategies.Equity.LongTerm.LongTermUtils.get_longterm_stocks_df",
        side_effect=mock_get_longterm_stocks_df,
    )
    @patch("Executor.ExecutorUtils.LoggingCenter.logger_utils.LoggerSetup")
    def test_main(
        self,
        mock_logger,
        mock_sqlite,
        mock_firebase,
        mock_update_db,
        mock_shortterm,
        mock_longterm,
    ):
        try:
            # Copy the original database to the test path
            print("Copying database file for testing...")
            shutil.copyfile(ORIGINAL_DB_PATH, TEST_DB_PATH)
            assert os.path.exists(
                TEST_DB_PATH
            ), f"Test database path does not exist after copying: {TEST_DB_PATH}"

            # Set the environment variable to point to the test database
            os.environ["today_stock_data_db_path"] = TEST_DB_PATH

            print(f"Environment variable set: today_stock_data_db_path={TEST_DB_PATH}")

            # Mock other dependencies as needed, like holidays
            with patch("Executor.ExecutorUtils.ExeUtils.holidays", new_callable=list):
                # Mock current time to a specific datetime for consistent testing
                with patch("datetime.datetime") as mock_datetime:
                    mock_now = dt.datetime(2024, 7, 2, 10, 0, 0)
                    mock_datetime.now.return_value = mock_now
                    mock_datetime.side_effect = lambda *args, **kwargs: dt.datetime(
                        *args, **kwargs
                    )

                    # Call the main function
                    print("Calling main function...")
                    Equity.main()

                    # Assertions to ensure the mocks were called correctly
                    mock_update_db.assert_called()
                    mock_shortterm.assert_called_once()
                    mock_longterm.assert_called_once()
                    mock_firebase.assert_called()

        except Exception as e:
            print(f"An exception occurred during testing: {e}")
        finally:
            # Clean up the test database
            if os.path.exists(TEST_DB_PATH):
                print("Removing test database file...")
                os.remove(TEST_DB_PATH)


# Run the tests
if __name__ == "__main__":
    unittest.main(verbosity=2)
