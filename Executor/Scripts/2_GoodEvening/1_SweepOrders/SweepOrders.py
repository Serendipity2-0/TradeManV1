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
    download_json
)

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    CLIENTS_USER_FB_DB
)

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    get_today_orders_for_brokers,
    create_counter_order_details,
    create_hedge_counter_order_details,
    get_today_open_orders_for_brokers
)
import Executor.ExecutorUtils.OrderCenter.OrderCenterUtils as OrderCenterUtils


def sweep_sl_order():
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
                logger.debug(f"placing sweep order for  with details {counter_order_detail}")
                OrderCenterUtils.place_order_for_strategy([user], counter_order_detail, "Sweep")
        except Exception as e:
            logger.error(f"Error while sweeping SL orders for {user['Broker']['BrokerUsername']} with error: {e}")


def sweep_hedge_orders():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_active_users_from_firebase,
    )

    active_users = fetch_active_users_from_firebase()
    logger.debug(f"Sweeping hedge orders for {len(active_users)} users.")

    for user in active_users:
        try:
            tradebook = get_today_orders_for_brokers(user)
            open_orders = get_today_open_orders_for_brokers(user)
            hedge_counter_order_details = create_hedge_counter_order_details(tradebook, user,open_orders)
            if hedge_counter_order_details:
                logger.debug(f"placing hedge order for with details {hedge_counter_order_details}")
                OrderCenterUtils.place_order_for_strategy([user], hedge_counter_order_details, "Sweep")
        except Exception as e:
            logger.error(f"Error while sweeping hedge orders for {user['Broker']['BrokerUsername']} with error: {e}")


def main():
    download_json(CLIENTS_USER_FB_DB, "before_sweep_orders")
    sweep_sl_order()
    sweep_hedge_orders()
    

if __name__ == "__main__":
    main()