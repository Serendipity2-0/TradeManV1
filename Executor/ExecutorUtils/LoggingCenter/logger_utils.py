from loguru import logger
import os,sys
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
