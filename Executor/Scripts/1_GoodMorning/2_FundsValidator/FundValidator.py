import os, sys
from dotenv import load_dotenv
import datetime as dt

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.ExeUtils import get_previous_trading_day,get_second_previous_trading_day,get_previous_freecash
import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    update_fields_firebase,
    delete_fields_firebase)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

CLIENTS_USER_FB_DB = os.getenv("FIREBASE_USER_COLLECTION")

active_users = broker_center_utils.fetch_active_users_from_firebase()

broker_free_cash = {}
db_free_cash = {}


def fetch_freecash_all_brokers(active_users):
    logger.debug(f"Fetching free cash no of users for brokers: {len(active_users)}")
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
    return broker_free_cash


def fetch_freecash_all_db(active_users):  ####pass active_users['Accounts'] as argument
    logger.debug(f"Fetching free cash no of users from Firebase DB: {len(active_users)}") 
    previous_trading_day_fb_format = get_previous_freecash(dt.date.today())
    previous_day_key = previous_trading_day_fb_format+"_"+'FreeCash'
    for user in active_users:
        try:
            db_free_cash[user["Tr_No"]] = user["Accounts"][previous_day_key]
        except KeyError:
            logger.error(f"Free cash for {user['Tr_No']} not found in Firebase DB")
            db_free_cash[user["Tr_No"]] = 0
        logger.info(f"Free cash for {user['Tr_No']} from Firebase DB: {db_free_cash[user['Tr_No']]}")
    return db_free_cash

def delete_old_free_cash(active_users):
    #delete all the keys which have _FreeCash , _Holdings and _AccountValue and are older than 2 days
    for user in active_users:
        for key in user['Accounts']:
            if '_FreeCash' in key or '_Holdings' in key or '_AccountValue' in key:
                second = get_second_previous_trading_day(dt.date.today())
                second = dt.datetime.strptime(second, "%d%b%y")
                if dt.datetime.strptime(key.split('_')[0], "%d%b%y") <= second:
                    logger.info(f"Deleting old key {key} for user {user['Tr_No']}")
                    delete_fields_firebase(CLIENTS_USER_FB_DB, user['Tr_No'], f"Accounts/{key}")

def compare_freecash(broker_free_cash, db_free_cash):
    from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import discord_admin_bot
    
    tolerable_difference = os.getenv("ACC_DIFF_TOLERANCE")

    discord_admin_bot(f"Today's number of users = {len(broker_free_cash)}")

    for user in broker_free_cash:
        logger.info(f"Comparing free cash for {user}")
        # check if the difference is more than 1%
        try:
            message = f"Trader Number - {user} : Broker Freecash - {broker_free_cash[user]} : Difference - {broker_free_cash[user] - db_free_cash[user]}"
            discord_admin_bot(message)

            if abs(broker_free_cash[user] - db_free_cash[user]) > float(tolerable_difference) * db_free_cash[user]:
                logger.error(f"Free cash for {user} is not matching")
                discord_admin_bot(f"Free cash for {user} is not matching, BrokerFreeCash - {broker_free_cash[user]}, DBFreeCash - {db_free_cash[user]}")            
            else:
                logger.info(f"Free cash for {user} is matching")
            update_fields_firebase(CLIENTS_USER_FB_DB, user, {dt.datetime.now().strftime("%d%b%y") + "_FreeCash": broker_free_cash[user]},"Accounts")
        except Exception as e:
            logger.error(f"Error while comparing free cash for {user} with error: {e}")
            discord_admin_bot(f"Error while comparing free cash for {user} with error: {e}")

def main():
    broker_free_cash = fetch_freecash_all_brokers(active_users)
    db_free_cash = fetch_freecash_all_db(active_users)
    compare_freecash(broker_free_cash, db_free_cash)
    delete_old_free_cash(active_users)


if __name__ == "__main__":
    main()
