import datetime as dt
import os, sys
import pendulum
from dotenv import load_dotenv
from loguru import logger


DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import discord_admin_bot

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
CLIENTS_USER_FB_DB = os.getenv("FIREBASE_USER_COLLECTION")
STRATEGY_FB_DB = os.getenv("FIREBASE_STRATEGY_COLLECTION")

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

    logger.debug(f"Fetching users from {CLIENTS_USER_FB_DB} and {STRATEGY_FB_DB} collections.")

    if CLIENTS_USER_FB_DB != "trademan_clients" or STRATEGY_FB_DB != "strategies":
        logger.warning(f"Using Non Production Environment Using {CLIENTS_USER_FB_DB} and {STRATEGY_FB_DB} collections.")
        discord_admin_bot(f"Using Non Production Environment Using {CLIENTS_USER_FB_DB} and {STRATEGY_FB_DB} collections.")


    today_active_users = broker_center_utils.fetch_active_users_from_firebase()

    logger.info(f"Total active users today: {len(today_active_users)}")

    for user in today_active_users:
        logger.debug(f"Active user: {user['Broker']['BrokerName']}: {user['Profile']['Name']}")
    
    broker_center_utils.all_broker_login(today_active_users)

if __name__ == "__main__":
    main()
