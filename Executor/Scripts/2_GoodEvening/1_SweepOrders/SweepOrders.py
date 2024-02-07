import datetime as dt
import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
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

    for user in active_users:
        tradebook = get_today_orders_for_brokers(user)
        counter_order_detail = create_counter_order_details(tradebook, user)
        if counter_order_detail:
            OrderCenterUtils.place_order_for_strategy([user], counter_order_detail, True)


def sweep_hedge_orders():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_active_users_from_firebase,
    )

    active_users = fetch_active_users_from_firebase()

    for user in active_users:
        tradebook = get_today_orders_for_brokers(user)
        open_orders = get_today_open_orders_for_brokers(user)
        hedge_counter_order_details = create_hedge_counter_order_details(tradebook, user,open_orders)
        if hedge_counter_order_details:
            OrderCenterUtils.place_order_for_strategy([user], hedge_counter_order_details, True)


# TODO : Add a function to sweep the orders for the day including orders with no SL

# Execute the functions
sweep_sl_order()
sweep_hedge_orders()
