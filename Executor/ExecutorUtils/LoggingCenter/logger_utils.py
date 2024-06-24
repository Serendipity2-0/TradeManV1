from loguru import logger
import os, sys
from dotenv import load_dotenv

# Load environment variables
DIR_PATH = os.getcwd()
load_dotenv()


class LoggerSetup:
    """
    Singleton class for setting up a logger using the loguru library.

    This class ensures that only one instance of the logger is created and configured
    with the specified settings. The logger writes logs to the file specified in the
    environment variable "ERROR_LOG_PATH" or a relative path if not specified.

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
        ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")

        if ERROR_LOG_PATH:
            # Ensure the log directory exists
            os.makedirs(ERROR_LOG_PATH, exist_ok=True)
            log_file_path = os.path.join(ERROR_LOG_PATH, "error.log")
            try:
                logger.add(
                    log_file_path,
                    level="TRACE",
                    rotation="00:00",
                    enqueue=True,
                    backtrace=True,
                    diagnose=True,
                )
            except Exception as e:
                logger.add(sys.stderr, level="WARNING")
                logger.warning(
                    f"Failed to add file logger at {log_file_path}: {str(e)}"
                )
                logger.warning("Logging will proceed with standard error output.")
        else:
            logger.add(sys.stderr, level="WARNING")
            logger.warning("ERROR_LOG_PATH is not set. Logging to stderr.")
