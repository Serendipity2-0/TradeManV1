import os, sys
from dotenv import load_dotenv
import datetime as dt

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

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


import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils

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
    return broker_free_cash


def fetch_freecash_all_db(active_users):  ####pass active_users['Accounts'] as argument
    previous_day_key = (dt.datetime.now() - dt.timedelta(days=1)).strftime(
        "%d%b%y"
    ) + "_FreeCash"
    for user in active_users:
        db_free_cash[user["Tr_No"]] = user["Accounts"][previous_day_key]
    return db_free_cash


def compare_freecash(broker_free_cash, db_free_cash):
    # TODO: add notification to this part of the code if the free cash is not matching
    for user in broker_free_cash:
        # check if the difference is more than 1%
        if abs(broker_free_cash[user] - db_free_cash[user]) > 0.01 * db_free_cash[user]:
            logger.info(
                f"Free cash for {user} is not matching"
            )  # TODO Integrate discord notification
            logger.info(f"Free cash from broker: {broker_free_cash[user]}")
            logger.info(f"Free cash from DB: {db_free_cash[user]}")
        else:
            logger.info(f"Free cash for {user} is matching")
            logger.info(f"Free cash from broker: {broker_free_cash[user]}")
            logger.info(f"Free cash from DB: {db_free_cash[user]}")


def main():
    broker_free_cash = fetch_freecash_all_brokers(active_users)
    db_free_cash = fetch_freecash_all_db(active_users)
    compare_freecash(broker_free_cash, db_free_cash)


if __name__ == "__main__":
    main()
