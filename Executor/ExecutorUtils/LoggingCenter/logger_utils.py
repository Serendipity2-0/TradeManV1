from loguru import logger
import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)


class LoggerSetup:
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
            try:
                logger.add(
                    ERROR_LOG_PATH,
                    level="TRACE",
                    rotation="00:00",
                    enqueue=True,
                    backtrace=True,
                    diagnose=True,
                )
            except Exception as e:
                # Fallback to console logging if the file logging setup fails
                logger.add(sys.stderr, level="WARNING")
                logger.warning(
                    f"Failed to add file logger at {ERROR_LOG_PATH}: {str(e)}"
                )
                logger.warning("Logging will proceed with standard error output.")
        else:
            # Fallback to console logging if ERROR_LOG_PATH is not set
            logger.add(sys.stderr, level="WARNING")
            logger.warning(
                "ERROR_LOG_PATH is not set. Logging will proceed with standard error output."
            )
