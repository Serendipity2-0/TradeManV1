"""
This module provides utility functions for order management.
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.BrokerCenter.broker_orders import place_order_for_brokers
import asyncio

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

logger = LoggerSetup()

async def place_order_single_user(users: List[Dict[str, Any]], order_details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Place orders for a single user.

    Args:
        users (List[Dict[str, Any]]): List of user details
        order_details (List[Dict[str, Any]]): List of order details

    Returns:
        List[Dict[str, Any]]: List of order statuses
    """
    order_statuses = []
    try:
        for user in users:
            for order in order_details:
                # Add broker information to the order
                order["broker"] = user["Broker"]["BrokerName"]
                
                # Place the order
                status = await place_order_for_brokers(order, user["Broker"])
                
                # Format the response
                order_status = {
                    "user": user["Tr_No"],
                    "symbol": order["base_symbol"],
                    "order_status": "PASS" if status and status.get("status") == "success" else "FAIL",
                    "message": status.get("message", "Unknown error") if status else "Order placement failed",
                    "trade_id": order["trade_id"]
                }
                
                # Check for ASM/GSM
                if status and "ASM/GSM" in status.get("message", ""):
                    order_status["order_status"] = "ASM/GSM"
                
                order_statuses.append(order_status)
                
                # Log the order status
                logger.info(f"Order status for {user['Tr_No']}: {order_status}")
                
    except Exception as e:
        logger.error(f"Error placing orders: {str(e)}")
        # Add error status for all orders
        for order in order_details:
            order_statuses.append({
                "user": users[0]["Tr_No"] if users else "Unknown",
                "symbol": order["base_symbol"],
                "order_status": "FAIL",
                "message": f"Error: {str(e)}",
                "trade_id": order["trade_id"]
            })
    
    return order_statuses

def place_order_single_user_sync(users: List[Dict[str, Any]], order_details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for place_order_single_user.

    Args:
        users (List[Dict[str, Any]]): List of user details
        order_details (List[Dict[str, Any]]): List of order details

    Returns:
        List[Dict[str, Any]]: List of order statuses
    """
    return asyncio.run(place_order_single_user(users, order_details))
