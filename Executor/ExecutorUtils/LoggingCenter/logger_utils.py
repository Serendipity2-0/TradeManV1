from loguru import logger
import os, sys
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
        """
        Create a new instance of LoggerSetup if one does not already exist.

        This method configures the logger to write logs to the file specified in the
        environment variable "ERROR_LOG_PATH". The log level is set to "TRACE" and logs
        are rotated daily at midnight. The logger is also configured to handle exceptions
        with backtrace and diagnose options enabled.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            logger: Configured loguru logger instance.
        """
        if not cls._instance:
            cls._instance = super(LoggerSetup, cls).__new__(cls, *args, **kwargs)
            ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
            logger.add(
                ERROR_LOG_PATH,
                level="TRACE",
                rotation="00:00",
                enqueue=True,
                backtrace=True,
                diagnose=True,
            )
        return logger
