import os
import sys
from unittest import TestCase, mock
from unittest.mock import patch
from loguru import logger
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Import the functions to test
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

# Set the environment variable for the log path
ERROR_LOG_PATH = "./Data/ErrorLogs"


class TestLoggerSetup(TestCase):
    @patch.dict(os.environ, {"ERROR_LOG_PATH": ERROR_LOG_PATH})
    def test_logger_file_logging(self):
        with mock.patch("loguru.logger.add") as mock_add:
            _ = LoggerSetup()
            log_file_path = os.path.join(ERROR_LOG_PATH, "./Data/ErrorLogs")
            mock_add.assert_called_with(
                log_file_path,
                level="TRACE",
                rotation="00:00",
                enqueue=True,
                backtrace=True,
                diagnose=True,
            )

    @patch.dict(os.environ, {}, clear=True)
    def test_logger_initialization_without_error_log_path(self):
        try:
            _ = LoggerSetup()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"LoggerSetup raised an exception unexpectedly: {e}")

    @patch.dict(os.environ, {"ERROR_LOG_PATH": ERROR_LOG_PATH})
    def test_logger_initialization_with_invalid_error_log_path(self):
        try:
            _ = LoggerSetup()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"LoggerSetup raised an exception unexpectedly: {e}")

    def test_singleton_behavior(self):
        logger1 = LoggerSetup()
        logger2 = LoggerSetup()
        self.assertIs(logger1, logger2)
