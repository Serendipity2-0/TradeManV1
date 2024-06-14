import os
import sys
import pytest
from unittest import mock
from dotenv import load_dotenv
import importlib

# Set up paths and environment
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Mock environment variables
os.environ["ERROR_LOG_PATH"] = "mock_error_log_path"
os.environ["FIREBASE_USER_COLLECTION"] = "trademan_clients"
os.environ["FIREBASE_STRATEGY_COLLECTION"] = "strategies"

# Mock data for testing based on the provided reference
mock_active_users = [
    {
        "Broker": {
            "BrokerName": "Zerodha",
            "BrokerUsername": "YY0333",
            "BrokerPassword": "K@nnada112",
            "ApiKey": "6b0dp5ussukmo77h",
            "ApiSecret": "eln2qrqob5neownuedmbv0f0hzq6lhby",
            "TotpAccess": "3GN2DNUD35FZQDIIWJUK6CSUIWBPXSBJ",
            "SessionId": "5h67lzOPT4dvVXAgovj3se7uaHi7HlGz",
        },
        "Active": True,
        "Tr_No": "Tr00",
        "Profile": {"Name": "John Doe"},
    }
]


@pytest.fixture
def mock_fetch_active_users():
    with mock.patch(
        "Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils.fetch_active_users_from_firebase",
        return_value=mock_active_users,
    ) as mock_fetch:
        yield mock_fetch


@pytest.fixture
def mock_firebase_update():
    with mock.patch(
        "Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils.firebase_utils.update_fields_firebase"
    ) as mock_update:
        yield mock_update


# Mock setup for Zerodha login
from kiteconnect import KiteConnect
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
import pyotp

# Mock `webdriver.Chrome` directly to avoid the InvalidSpecError
mock_driver = mock.Mock()
mock_driver.find_element.return_value = mock.Mock()
mock_driver.current_url = (
    "https://kite.trade?request_token=mock_request_token&status=success"
)

# Correct the mocking of `pyotp.TOTP`

mock_totp = mock.Mock()
mock_totp.now.return_value = "123456"

# Directly mock `KiteConnect` without creating a spec from an existing mock
mock_kite = mock.Mock()  # Use mock.Mock() without spec argument

mock_kite.generate_session.return_value = {"access_token": "mock_access_token"}


@pytest.fixture
def mock_login_in_zerodha():
    with mock.patch("kiteconnect.KiteConnect", return_value=mock_kite):
        with mock.patch("pyotp.TOTP", return_value=mock_totp):
            with mock.patch(
                "webdriver_manager.chrome.ChromeDriverManager.install",
                return_value="path_to_chromedriver",
            ):
                with mock.patch("selenium.webdriver.Chrome", return_value=mock_driver):
                    yield  # This is where your test can utilize the mocks


def test_daily_login_flow(
    mock_fetch_active_users, mock_firebase_update, mock_login_in_zerodha
):
    # Import the DailyLogin module and get the main function
    try:
        DailyLogin = importlib.import_module(
            "Executor.Scripts.1_GoodMorning.1_Login.DailyLogin"
        )
        main = getattr(DailyLogin, "main")
    except (ModuleNotFoundError, AttributeError) as e:
        pytest.fail(f"Failed to import DailyLogin or find the main function: {str(e)}")

    # Execute the main function to start the flow
    main()

    # Import BrokerCenterUtils directly
    import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils

    # Mock the kite_login module dynamically
    try:
        with mock.patch(
            "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.kite_login.login_in_zerodha",
            autospec=True,
        ) as mock_login_zerodha:
            # Verify that fetch_active_users function is called and users are fetched
            today_active_users = broker_center_utils.fetch_active_users_from_firebase()

            # Call the method that handles the login for all brokers
            broker_center_utils.all_broker_login(today_active_users)

            # Create the expected call structure based on reference data
            expected_call = {
                "BrokerName": "Zerodha",
                "BrokerUsername": "YY0333",
                "BrokerPassword": "K@nnada112",
                "ApiKey": "6b0dp5ussukmo77h",
                "ApiSecret": "eln2qrqob5neownuedmbv0f0hzq6lhby",
                "TotpAccess": "3GN2DNUD35FZQDIIWJUK6CSUIWBPXSBJ",
                "SessionId": "5h67lzOPT4dvVXAgovj3se7uaHi7HlGz",
            }

            # Verify that the login_in_zerodha function for Zerodha was called with the correct arguments
            mock_login_zerodha.assert_called_once_with(expected_call)

            # Verify the generate_session and TOTP methods were called in the mocked login
            mock_kite.generate_session.assert_called_once()
            mock_totp.now.assert_called_once()
    except ModuleNotFoundError as e:
        pytest.fail(f"Failed to import kite_login module: {str(e)}")


# Ensure this code is only executed if the script is run directly
if __name__ == "__main__":
    pytest.main([__file__])
