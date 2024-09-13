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
    send_messsage_via_discord,
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
from Executor.ExecutorUtils.ExeUtils import (
    EQUITY_STRATEGY_LIST,
    DERIVATIVES_STRATEGY_LIST,
)


def calculate_qty_for_equity(free_cash: float, ltp: float) -> int:
    """
    Calculate the quantity for equity based on free cash and last traded price.

    :param free_cash: Available free cash for the strategy
    :param ltp: Last traded price of the instrument
    :return: Calculated quantity as an integer
    """
    try:
        qty = int(free_cash / ltp)
        return max(qty, 0)  # Ensure non-negative quantity
    except Exception as e:
        logger.error(f"Error calculating quantity for equity: {e}")
        return 0


def calculate_qty_for_derivatives(
    capital: float,
    risk: float,
    avg_sl_points: float,
    lot_size: int,
    qty_amplifier: float = None,
    strategy_amplifier: float = None,
) -> int:
    """
    Calculate the quantity for a trading strategy based on various parameters.

    :param capital: The capital available for trading.
    :param risk: The percentage of capital to be risked.
    :param avg_sl_points: The average stop-loss points for the strategy.
    :param lot_size: The lot size of the instrument.
    :param qty_amplifier: The quantity amplifier percentage. Defaults to None.
    :param strategy_amplifier: The strategy amplifier percentage. Defaults to None.
    :return: The calculated quantity for the strategy.
    """
    logger.info(
        f"Calculating quantity for strategy with capital: {capital}, risk: {risk}, "
        f"avg_sl_points: {avg_sl_points}, lot_size: {lot_size}"
    )
    try:
        qty_multiplier = 1 + (qty_amplifier / 100) if qty_amplifier is not None else 1
        strategy_multiplier = (
            1 + (strategy_amplifier / 100) if strategy_amplifier is not None else 1
        )

        if avg_sl_points:
            raw_quantity = ((risk / 100) * capital) / avg_sl_points
            raw_quantity *= qty_multiplier * strategy_multiplier
            number_of_lots = math.ceil(raw_quantity / lot_size)
            quantity = int(number_of_lots * lot_size)
        else:
            adjusted_risk_percentage = risk / (qty_multiplier * strategy_multiplier)
            capital_at_risk = capital * (adjusted_risk_percentage / 100)
            effective_lots = capital_at_risk / lot_size
            quantity = math.ceil(effective_lots) * lot_size

        logger.debug(f"Final calculated quantity: {quantity}")
        return quantity
    except Exception as e:
        logger.error(f"Error calculating quantity for strategy: {e}")
        return 0


async def place_order_for_strategy(
    strategy_users, order_details, order_qty_mode: str = None
):
    all_order_statuses = []

    # Sort order_details to ensure hedge entry is first
    order_details.sort(key=lambda x: x.get("order_mode") != "HedgeEntry")

    for order in order_details:
        order_tasks = []
        for user in strategy_users:
            try:
                user_credentials = fetch_user_credentials_firebase(
                    user["Broker"]["BrokerUsername"]
                )

                # Create a new order dictionary for each user
                order_with_user_and_broker = order.copy()

                strategy_type = (
                    "Equity"
                    if order.get("strategy") in EQUITY_STRATEGY_LIST
                    else "Derivatives"
                    if order.get("strategy") in DERIVATIVES_STRATEGY_LIST
                    else None
                )

                if strategy_type:
                    qty = (
                        user["Strategies"][strategy_type][order.get("strategy")][
                            order.get("setup")
                        ]["Qty"]
                        if strategy_type == "Equity" and order_qty_mode != "Holdings"
                        else user["Strategies"][strategy_type][order.get("strategy")][
                            "Qty"
                        ]
                        if strategy_type == "Derivatives"
                        and order_qty_mode != "Holdings"
                        else fetch_qty_for_holdings_sqldb(
                            user["Tr_No"], order.get("trade_id"), strategy_type
                        )
                    )

                    order_with_user_and_broker.update(
                        {
                            "broker": user["Broker"]["BrokerName"],
                            "username": user["Broker"]["BrokerUsername"],
                            "qty": qty,
                        }
                    )

                else:
                    logger.error(f"Unknown strategy: {order.get('strategy')}")

                # Calculate tax for this specific order
                tax = get_orders_tax(order_with_user_and_broker, user_credentials)
                order_with_user_and_broker["tax"] = tax

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
                logger.error(traceback.format_exc())

        # Await all tasks for this particular order and collect statuses
        if order_tasks:
            order_statuses = await asyncio.gather(*order_tasks)
            all_order_statuses.extend(order_statuses)

        # Add a 1-second delay after placing hedge entry orders
        if order.get("order_mode") == "HedgeEntry":
            await asyncio.sleep(1)

    return all_order_statuses


# The place_order_with_tax function remains unchanged
async def place_order_with_tax(order, user_credentials, tr_no, strategy):
    try:
        # Place the order
        status = await place_order_for_brokers(order, user_credentials)

        if status is None:
            logger.error(f"Order placement returned None for user {order['username']}")
            status = {
                "tax": 0,
                "message": "Order placement failed",
                "error": "Received None status",
            }
        else:
            # Add the tax information to the status
            status["tax"] = order.get("tax")

        if strategy in EQUITY_STRATEGY_LIST:
            update_path = (
                f"Strategies/Equity/{strategy}/{order.get('setup')}/TradeState/orders"
            )
        elif strategy in DERIVATIVES_STRATEGY_LIST:
            update_path = f"Strategies/Derivatives/{strategy}/TradeState/orders"
        else:
            logger.error(f"Unknown strategy: {strategy}")

        push_orders_firebase(CLIENTS_USER_FB_DB, tr_no, status, update_path)

        if status.get("message", "") == "Order placement failed":
            send_messsage_via_discord(
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
