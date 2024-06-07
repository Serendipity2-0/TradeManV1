import os
import sys
from unittest import TestCase, mock
from unittest.mock import patch
from loguru import logger
import tempfile

from dotenv import load_dotenv

# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Import the functions to test
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup


class TestLoggerSetup(TestCase):
    @patch.dict(
        os.environ, {"ERROR_LOG_PATH": "D:/TradeManV1/Data/ErrorLogs/TradeManError.log"}
    )
    def test_logger_file_logging(self):
        # Test when ERROR_LOG_PATH is correctly set and file logging is successful
        with mock.patch("loguru.logger.add") as mock_add:
            _ = LoggerSetup()
            mock_add.assert_called_with(
                "D:/TradeManV1/Data/ErrorLogs/TradeManError.log",
                level="TRACE",
                rotation="00:00",
                enqueue=True,
                backtrace=True,
                diagnose=True,
            )

    @patch.dict(os.environ, {}, clear=True)
    def test_logger_initialization_without_error_log_path(self):
        # Test if LoggerSetup initializes without any error when ERROR_LOG_PATH is not set
        try:
            _ = LoggerSetup()
            self.assertTrue(True)  # If no exception, test passes
        except Exception as e:
            self.fail(f"LoggerSetup raised an exception unexpectedly: {e}")

    @patch.dict(
        os.environ, {"ERROR_LOG_PATH": "D:/TradeManV1/Data/TradeManInvalidError.log"}
    )
    def test_logger_initialization_with_invalid_error_log_path(self):
        # Test if LoggerSetup initializes without any error when ERROR_LOG_PATH is invalid
        try:
            _ = LoggerSetup()
            self.assertTrue(True)  # If no exception, test passes
        except Exception as e:
            self.fail(f"LoggerSetup raised an exception unexpectedly: {e}")

    def test_singleton_behavior(self):
        # Test to ensure that only one instance of LoggerSetup is created
        logger1 = LoggerSetup()
        logger2 = LoggerSetup()
        self.assertIs(logger1, logger2)


if __name__ == "__main__":
    import unittest

    unittest.main()
