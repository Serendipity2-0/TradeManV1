from loguru import logger
import os
import sys
import traceback
from dotenv import load_dotenv

# Load environment variables
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)


class LoggerSetup:
    """
    Singleton class for setting up a logger using the loguru library.

    This class ensures that only one instance of the logger is created and configured
    with the specified settings. The logger writes logs to the file specified in the
    environment variable "ERROR_LOG_PATH" or a default path if not specified.

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
        # Ensure log directory exists with proper permissions
        log_dir = os.path.join(DIR_PATH, "Data", "ErrorLogs")
        os.makedirs(log_dir, exist_ok=True)
        
        # Set default log path
        DEFAULT_LOG_PATH = os.path.join(log_dir, "trademan_error.log")
        
        # Try environment variable first, fallback to default
        ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH", DEFAULT_LOG_PATH)

        try:
            # Ensure the log file is writable
            logger.add(
                ERROR_LOG_PATH,
                level="TRACE",
                rotation="00:00",
                enqueue=True,
                backtrace=True,
                diagnose=True,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
            )
            
            # Set file permissions to be readable/writable by owner
            try:
                os.chmod(ERROR_LOG_PATH, 0o644)
            except Exception as perm_error:
                logger.warning(f"Could not set log file permissions: {perm_error}")

        except PermissionError:
            # Fallback to stderr if permission denied
            logger.add(
                sys.stderr, 
                level="WARNING",
                format="<red>PERMISSION ERROR:</red> {message}"
            )
            logger.warning(
                f"Permission denied writing to log file: {ERROR_LOG_PATH}. "
                "Logging to standard error output."
            )
        
        except Exception as e:
            # Catch-all for other potential logging setup errors
            logger.add(
                sys.stderr, 
                level="WARNING",
                format="<red>LOGGING SETUP ERROR:</red> {message}"
            )
            logger.warning(
                f"Failed to set up file logging: {e}. "
                "Logging to standard error output. "
                f"Error details: {traceback.format_exc()}"
            )
