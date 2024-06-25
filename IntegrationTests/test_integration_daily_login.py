import unittest
from unittest.mock import patch, MagicMock
import importlib
import os
from dotenv import load_dotenv
import sys


# Set up paths and environment
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Import the module to be tested
DailyLogin = importlib.import_module(
    "Executor.Scripts.1_GoodMorning.1_Login.DailyLogin"
)

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import all_broker_login

# Mock data for testing
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
        "Active": False,
        "Tr_No": "Tr00",
        "Profile": {"Name": "John Doe"},
    },
    {
        "Broker": {
            "BrokerName": "AliceBlue",
            "BrokerUsername": "XX0444",
            "BrokerPassword": "SecurePass123",
            "ApiKey": "7a1ep6vssvnmo78i",
            "ApiSecret": "fmv3rsuod6peownuedcbv0g1hzr7lmcy",
            "TotpAccess": "4HN3ENVF36GZREFJJWLR7DTUJXCPYTCJ",
            "SessionId": "6j78lzQRT5fwWYBhqvk4tf8vbIj8ImHk",
        },
        "Active": False,
        "Tr_No": "Tr01",
        "Profile": {"Name": "Jane Smith"},
    },
    {
        "Broker": {
            "BrokerName": "Firstock",
            "BrokerUsername": "ZZ0555",
            "BrokerPassword": "TopSecret456",
            "ApiKey": "8b2fq7wttvoop89j",
            "TotpAccess": "5IO4FOEG47HZSGGKMXMS8EVVKYDQZUDK",
            "BrokerVendorCode": "VENDOR123",
            "SessionId": "7k89mzSRU6gxXZCiraw5ug9wcJj9JmJl",
        },
        "Active": True,
        "Tr_No": "Tr02",
        "Profile": {"Name": "Alice Johnson"},
    },
]


class TestIntegration(unittest.TestCase):
    @patch(
        "Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils.fetch_active_users_from_firebase"
    )
    @patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_login.login_in_aliceblue"
    )
    @patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.kite_login.login_in_zerodha"
    )
    @patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_login.login_in_firstock"
    )
    @patch(
        "Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter.discord_admin_bot"
    )
    @patch("Executor.ExecutorUtils.LoggingCenter.logger_utils.LoggerSetup")
    @patch.dict(
        "os.environ",
        {
            "CLIENTS_USER_FB_DB": "mock_trademan_clients",
            "STRATEGY_FB_DB": "mock_strategy",
            "ERROR_LOG_PATH": "D:/TradeManV1Data/ErrorLogs.log",
        },
    )
    def test_main_function_flow(
        self,
        mock_logger,
        mock_discord,
        mock_firstock_login,
        mock_kite_login,
        mock_alice_login,
        mock_fetch_users,
    ):
        # Set up mock return values
        mock_fetch_users.return_value = mock_active_users
        mock_kite_login.return_value = "mock_kite_session_id"
        mock_alice_login.return_value = "mock_alice_session_id"
        mock_firstock_login.return_value = "mock_firstock_session_id"

        # Mock logger method
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance

        # Run the main function
        DailyLogin.main()

        # Assertions to check that each function was called correctly
        mock_fetch_users.assert_called_once()
        mock_kite_login.assert_called_once_with(mock_active_users[0]["Broker"])
        mock_alice_login.assert_called_once_with(mock_active_users[1]["Broker"])
        mock_firstock_login.assert_called_once_with(mock_active_users[2]["Broker"])
        mock_discord.assert_not_called()  # No discord notification in this flow

        # Verify logging was done correctly

        print(f"Today's date: {len(mock_active_users)}")
        print(
            f"Fetching users from {os.getenv('CLIENTS_USER_FB_DB')} and {os.getenv('STRATEGY_FB_DB')} collections."
        )
        print(f"Total active users today: {len(mock_active_users)}")
        print(
            f"Active user: {mock_active_users[0]['Broker']['BrokerName']}: {mock_active_users[0]['Profile']['Name']}"
        )

    @patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_login.login_in_aliceblue"
    )
    @patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.kite_login.login_in_zerodha"
    )
    @patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_login.login_in_firstock"
    )
    @patch("Executor.ExecutorUtils.LoggingCenter.logger_utils.LoggerSetup")
    @patch(
        "Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter.update_fields_firebase"
    )
    def test_all_broker_login(
        self,
        mock_update_firebase,
        mock_logger,
        mock_firstock_login,
        mock_kite_login,
        mock_alice_login,
    ):
        # Set up mock return values
        mock_kite_login.return_value = "mock_kite_session_id"
        mock_alice_login.return_value = "mock_alice_session_id"
        mock_firstock_login.return_value = "mock_firstock_session_id"

        # Mock logger methods
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance

        # Test all_broker_login function
        updated_users = all_broker_login(mock_active_users)

        # Update expected session IDs for active users
        expected_users = mock_active_users[:]
        expected_users[0]["Broker"]["SessionId"] = "mock_kite_session_id"
        expected_users[1]["Broker"]["SessionId"] = "mock_alice_session_id"
        expected_users[2]["Broker"]["SessionId"] = "mock_firstock_session_id"

        # Assertions
        mock_kite_login.assert_called_once_with(mock_active_users[0]["Broker"])
        mock_alice_login.assert_called_once_with(mock_active_users[1]["Broker"])
        mock_firstock_login.assert_called_once_with(mock_active_users[2]["Broker"])

        # Check that firebase_utils.update_fields_firebase was called with correct parameters
        mock_update_firebase.assert_any_call(
            "mock_trademan_clients",
            "Tr00",
            {"SessionId": "mock_kite_session_id"},
            "Broker",
        )
        mock_update_firebase.assert_any_call(
            "mock_trademan_clients",
            "Tr01",
            {"SessionId": "mock_alice_session_id"},
            "Broker",
        )
        mock_update_firebase.assert_any_call(
            "mock_trademan_clients",
            "Tr02",
            {"SessionId": "mock_firstock_session_id"},
            "Broker",
        )

        # Verify that session IDs are updated
        self.assertEqual(updated_users, expected_users)

        # Verify logging was done correctly
        print(f"Total active users today: {len(mock_active_users)}")
        print(
            f"Active user: {mock_active_users[0]['Broker']['BrokerName']}: {mock_active_users[0]['Profile']['Name']}"
        )


if __name__ == "__main__":
    unittest.main()
