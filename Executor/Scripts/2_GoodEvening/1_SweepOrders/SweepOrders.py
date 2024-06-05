import datetime as dt
import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_utils import (
    download_json,
)

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import CLIENTS_USER_FB_DB

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    get_today_orders_for_brokers,
    create_counter_order_details,
    create_hedge_counter_order_details,
    get_today_open_orders_for_brokers,
)
import Executor.ExecutorUtils.OrderCenter.OrderCenterUtils as OrderCenterUtils


def sweep_sl_order():
    """
    The function sweeps stop-loss (SL) orders for all active users by performing the following steps:
    1. Fetches active users from Firebase.
    2. For each user, retrieves today's orders from brokers.
    3. Creates counter order details based on the tradebook and user information.
    4. Places the sweep order if counter order details are available.

    Logs the progress and any errors encountered during the process.
    """
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_active_users_from_firebase,
    )

    active_users = fetch_active_users_from_firebase()
    logger.debug(f"Sweeping SL orders for {len(active_users)} users.")

    for user in active_users:
        try:
            tradebook = get_today_orders_for_brokers(user)
            counter_order_detail = create_counter_order_details(tradebook, user)
            if counter_order_detail:
                logger.debug(
                    f"placing sweep order for  with details {counter_order_detail}"
                )
                OrderCenterUtils.place_order_for_strategy(
                    [user], counter_order_detail, "Sweep"
                )
        except Exception as e:
            logger.error(
                f"Error while sweeping SL orders for {user['Broker']['BrokerUsername']} with error: {e}"
            )


def sweep_hedge_orders():
    """
    The function sweeps hedge orders for all active users by performing the following steps:
    1. Fetches active users from Firebase.
    2. For each user, retrieves today's orders and open orders from brokers.
    3. Creates hedge counter order details based on the tradebook, user information, and open orders.
    4. Places the hedge order if hedge counter order details are available.

    Logs the progress and any errors encountered during the process.
    """
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_active_users_from_firebase,
    )

    active_users = fetch_active_users_from_firebase()
    logger.debug(f"Sweeping hedge orders for {len(active_users)} users.")

    for user in active_users:
        try:
            tradebook = get_today_orders_for_brokers(user)
            open_orders = get_today_open_orders_for_brokers(user)
            hedge_counter_order_details = create_hedge_counter_order_details(
                tradebook, user, open_orders
            )
            if hedge_counter_order_details:
                logger.debug(
                    f"placing hedge order for with details {hedge_counter_order_details}"
                )
                OrderCenterUtils.place_order_for_strategy(
                    [user], hedge_counter_order_details, "Sweep"
                )
        except Exception as e:
            logger.error(
                f"Error while sweeping hedge orders for {user['Broker']['BrokerUsername']} with error: {e}"
            )


def main():
    """
    The main function orchestrates the order sweeping process by performing the following steps:
    1. Downloads the JSON data for the clients' user Firebase database before sweeping orders.
    2. Calls the function to sweep stop-loss orders for all active users.
    3. Calls the function to sweep hedge orders for all active users.
    """
    download_json(CLIENTS_USER_FB_DB, "before_sweep_orders")
    sweep_sl_order()
    sweep_hedge_orders()


if __name__ == "__main__":
    main()
