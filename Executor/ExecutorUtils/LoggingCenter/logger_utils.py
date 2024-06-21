import os
import sys
from loguru import logger
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)


class LoggerSetup:
    """
    Singleton class for setting up a logger using the loguru library.

    This class ensures that only one instance of the logger is created and configured
    with the specified settings. The logger writes logs to the file specified in the
    environment variable "ERROR_LOG_PATH".

    Attributes:
        _instance (LoggerSetup): Singleton instance of LoggerSetup.

    Methods:
        __new__(cls, *args, **kwargs): Creates a new instance of LoggerSetup if one does not already exist.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LoggerSetup, cls).__new__(cls, *args, **kwargs)
            cls._setup_logger()
        return logger

    @staticmethod
    def _setup_logger():
        # Fetch the ERROR_LOG_PATH from environment variables
        ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
        print(f"DEBUG: ERROR_LOG_PATH is set to {ERROR_LOG_PATH}")  # Debugging line

        if ERROR_LOG_PATH:
            # Resolve to an absolute path
            ERROR_LOG_PATH = os.path.abspath(ERROR_LOG_PATH)
            try:
                # Setup the logger with the specified path and configurations
                logger.add(
                    ERROR_LOG_PATH,
                    level="TRACE",
                    rotation="00:00",
                    enqueue=True,
                    backtrace=True,
                    diagnose=True,
                )
                logger.info(f"Logger initialized with file: {ERROR_LOG_PATH}")
            except Exception as e:
                # Fallback to console logging if file logging setup fails
                logger.add(sys.stderr, level="WARNING")
                logger.warning(
                    f"Failed to add file logger at {ERROR_LOG_PATH}: {str(e)}"
                )
        else:
            # Fallback to console logging if ERROR_LOG_PATH is not set
            logger.add(sys.stderr, level="WARNING")
            logger.warning(
                "ERROR_LOG_PATH is not set. Logging will proceed with standard error output."
            )
