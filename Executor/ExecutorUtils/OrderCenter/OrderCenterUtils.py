import math
import os
import sys
import time
from dotenv import load_dotenv
import asyncio
import traceback

DIR = os.getcwd()
sys.path.append(DIR)

load_dotenv(os.path.join(DIR, "trademan.env"))

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    push_orders_firebase,
)
from Executor.ExecutorUtils.InstrumentCenter.FNOInfoBase import FNOInfo
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_user_credentials_firebase,
    place_order_for_brokers,
    modify_order_for_brokers,
    fetch_strategy_details_for_user,
    CLIENTS_USER_FB_DB,
    get_orders_tax,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    fetch_qty_for_holdings_sqldb,
)


def calculate_qty_for_strategies(
    capital, risk, avg_sl_points, lot_size, qty_amplifier=None, strategy_amplifier=None
):
    """
    Calculate the quantity for a trading strategy based on various parameters.

    Args:
        capital (float): The capital available for trading.
        risk (float): The percentage of capital to be risked.
        avg_sl_points (float): The average stop-loss points for the strategy.
        lot_size (int): The lot size of the instrument.
        qty_amplifier (float, optional): The quantity amplifier percentage. Defaults to None.
        strategy_amplifier (float, optional): The strategy amplifier percentage. Defaults to None.

    Returns:
        int: The calculated quantity for the strategy.
    """
    logger.info(
        f"Calculating quantity for strategy with capital: {capital}, risk: {risk}, avg_sl_points: {avg_sl_points}, lot_size: {lot_size}"
    )
    try:
        # Set default multipliers if amplifiers are not provided
        qty_multiplier = (
            1 + (qty_amplifier / 100) if qty_amplifier is not None else 1
        )  # qty_multiplier is fetched from the marketinfo
        strategy_multiplier = (
            1 + (strategy_amplifier / 100) if strategy_amplifier is not None else 1
        )  # strategy_multiplier is fetched from the strategy

        if avg_sl_points is not None:
            # Calculate the base raw quantity
            raw_quantity = ((risk / 100) * capital) / avg_sl_points

            # Adjust raw quantity with multipliers
            raw_quantity *= qty_multiplier * strategy_multiplier

            # Calculate the number of lots
            number_of_lots = raw_quantity / lot_size

            # Round up to the nearest whole number of lots
            number_of_lots = math.ceil(number_of_lots)

            # Calculate the final quantity as a multiple of lot size
            quantity = int(number_of_lots * lot_size)
            logger.debug(f"Final adjusted quantity: {quantity}")
        else:
            # For other strategies, adjust risk according to multipliers before calculating lots
            adjusted_risk = risk / (qty_multiplier * strategy_multiplier)
            lots = capital / (adjusted_risk / 100)
            quantity = math.ceil(lots) * lot_size
            logger.debug(
                f"Quantity calculated using default strategy without avg_sl_points: {quantity}"
            )

        return quantity
    except ZeroDivisionError as e:
        logger.error(
            f"Error calculating quantity for strategy due to division by zero: {e}"
        )
        return 0
    except Exception as e:
        logger.error(f"General error calculating quantity for strategy: {e}")
        return 0


async def place_order_for_strategy(
    strategy_users, order_details, order_qty_mode: str = None
):
    all_order_statuses = []
    order_tasks = []

    for order in order_details:
        for user in strategy_users:
            try:
                user_credentials = fetch_user_credentials_firebase(
                    user["Broker"]["BrokerUsername"]
                )

                # Create a new order dictionary for each user
                order_with_user_and_broker = order.copy()
                order_with_user_and_broker.update(
                    {
                        "broker": user["Broker"]["BrokerName"],
                        "username": user["Broker"]["BrokerUsername"],
                        "qty": user["Strategies"][order.get("strategy")]["Qty"]
                        if order_qty_mode != "Holdings"
                        else fetch_qty_for_holdings_sqldb(
                            user["Tr_No"], order.get("trade_id")
                        ),
                    }
                )

                # Calculate tax for this specific order
                tax = get_orders_tax(order_with_user_and_broker, user_credentials)
                order_with_user_and_broker["tax"] = tax

                if order_with_user_and_broker.get("order_type") == "Stoploss":
                    await asyncio.sleep(1)

                # Create a task for order placement
                order_task = asyncio.create_task(
                    place_order_with_tax(
                        order_with_user_and_broker.copy(),
                        user_credentials,
                        user["Tr_No"],
                        order.get("strategy"),
                    )
                )
                order_tasks.append(order_task)
            except Exception as e:
                logger.error(
                    f"Error preparing order for user {user['Broker']['BrokerUsername']}: {e}"
                )

    # Await all tasks and collect statuses
    if order_tasks:
        all_order_statuses = await asyncio.gather(*order_tasks)

    return all_order_statuses


async def place_order_with_tax(order, user_credentials, tr_no, strategy):
    try:
        # Place the order
        status = await place_order_for_brokers(order, user_credentials)

        if status is None:
            logger.error(f"Order placement returned None for user {order['username']}")
            # return {"message": "Order placement failed", "error": "Received None status"}
            status["tax"] = 0
        else:
            # Add the tax information to the status
            status["tax"] = order.get("tax")

        # Update Firebase with order status
        update_path = f"Strategies/{strategy}/TradeState/orders"
        push_orders_firebase(CLIENTS_USER_FB_DB, tr_no, status, update_path)

        if status.get("message", "") == "Order placement failed":
            discord_bot(
                f"Order failed for user {order['username']} in strategy {strategy}",
                strategy,
            )

        return status
    except Exception as e:
        logger.error(f"Error in place_order_with_tax: {e}")
        return {"message": "Order placement failed", "error": str(e)}


def modify_orders_for_strategy(strategy_users, order_details):
    """
    Modify orders for a trading strategy for multiple users.

    Args:
        strategy_users (list): A list of users involved in the strategy.
        order_details (list): A list of order details to be modified.
    """
    # Update the order details with the username and broker details for each order and pass it to modify_order_for_brokers
    for users in strategy_users:
        logger.debug(f"Modifying orders for user {users['Broker']['BrokerUsername']}")
        for order in order_details:
            user_credentials = fetch_user_credentials_firebase(
                users["Broker"]["BrokerUsername"]
            )
            order_with_user_and_broker = order.copy()
            order_with_user_and_broker.update(
                {
                    "broker": users["Broker"]["BrokerName"],
                    "username": users["Broker"]["BrokerUsername"],
                }
            )
            try:
                modify_order_for_brokers(order_with_user_and_broker, user_credentials)
            except Exception:
                logger.error(
                    f"Error modifying order for user: {users['Broker']['BrokerUsername']}"
                )
    pass


def retrieve_order_id(account_name, strategy, exchange_token: int):
    """
    Retrieve the order ID from Firebase for the given account name, strategy name, and exchange token.

    Args:
        account_name (str): The account name of the user.
        strategy (str): The name of the strategy.
        exchange_token (int): The exchange token of the instrument.

    Returns:
        dict: A dictionary with order IDs as keys and quantities as values.
    """
    # retrieve the order id from firebase for the given account name, strategy name and trade id
    order_ids = {}
    user_details = fetch_strategy_details_for_user(account_name)
    for strategy_name in user_details:
        if strategy_name == strategy:
            try:
                for trade in user_details[strategy_name]["TradeState"]["orders"]:
                    if (
                        trade is not None
                        and trade["exchange_token"] == exchange_token
                        and trade["trade_id"].endswith("EX")
                    ):
                        order_ids[trade["order_id"]] = trade["qty"]
            except Exception as e:
                logger.error(
                    f"Error retrieving order id for user: {account_name} and strategy: {strategy} : {e}"
                )
    return order_ids
