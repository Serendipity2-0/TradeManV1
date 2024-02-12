import datetime as dt
import os, sys
import pendulum
from dotenv import load_dotenv


DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from loguru import logger

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


logger.info("Shree Ganeshaya Namaha")
logger.info("Jai Hanuman")
logger.info("Market is Supreme")
today = pendulum.today().format("DD-MM-YYYY")
logger.info(f"Today's date: {today}")

def main():
    import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils

    broker_center_utils.all_broker_login(
        broker_center_utils.fetch_active_users_from_firebase()
    )

if __name__ == "__main__":
    main()
