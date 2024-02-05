import os, sys
from dotenv import load_dotenv
import datetime as dt
from loguru import logger

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    update_fields_firebase)

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)

user_db_collection = os.getenv("FIREBASE_USER_COLLECTION")

active_users = broker_center_utils.fetch_active_users_from_firebase()

broker_free_cash = {}
db_free_cash = {}


def fetch_freecash_all_brokers(
    active_users,
):  ####pass active_users['Brokers'] as argument
    for user in active_users:
        if user["Broker"]["BrokerName"] == broker_center_utils.ZERODHA:
            cash_margin = broker_center_utils.zerodha_adapter.zerodha_fetch_free_cash(
                user["Broker"]
            )
            broker_free_cash[user["Tr_No"]] = cash_margin
        elif user["Broker"]["BrokerName"] == broker_center_utils.ALICEBLUE:
            cash_margin = broker_center_utils.alice_adapter.alice_fetch_free_cash(
                user["Broker"]
            )
            broker_free_cash[user["Tr_No"]] = cash_margin
    return broker_free_cash, user["Tr_No"]


def fetch_freecash_all_db(active_users):  ####pass active_users['Accounts'] as argument
    previous_day_key = (dt.datetime.now() - dt.timedelta(days=1)).strftime(
        "%d%b%y"
    ) + "_FreeCash"
    for user in active_users:
        db_free_cash[user["Tr_No"]] = user["Accounts"][previous_day_key]
    return db_free_cash


def compare_freecash(broker_free_cash, db_free_cash, trader_no):
    from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import discord_admin_bot
    
    tolerable_difference = 0.03
    
    for user in broker_free_cash:
        # check if the difference is more than 1%
        if abs(broker_free_cash[user] - db_free_cash[user]) > tolerable_difference * db_free_cash[user]:
            logger.info(
                f"Free cash for {user} is not matching"
            )  
            logger.info(f"Free cash from broker: {broker_free_cash[user]}")
            logger.info(f"Free cash from DB: {db_free_cash[user]}")
            discord_admin_bot(f"Free cash for {user} is not matching, Broker: {broker_free_cash[user]}, DB: {db_free_cash[user]}")
            update_fields_firebase(user_db_collection, trader_no, {dt.datetime.now().strftime("%d%b%y") + "_FreeCash": broker_free_cash[user]},"Accounts")
            # TODO: Update holdings and account value in the FirebaseDB using sqlite DB
            # TODO: Add logic to get legder from broker and update the sqlite DB transactions table
            
        else:
            logger.info(f"Free cash for {user} is matching")
            logger.info(f"Free cash from broker: {broker_free_cash[user]}")
            logger.info(f"Free cash from DB: {db_free_cash[user]}")


def main():
    broker_free_cash, trader_no = fetch_freecash_all_brokers(active_users)
    db_free_cash = fetch_freecash_all_db(active_users)
    compare_freecash(broker_free_cash, db_free_cash, trader_no)


if __name__ == "__main__":
    main()
