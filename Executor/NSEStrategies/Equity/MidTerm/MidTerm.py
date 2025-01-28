"""
MidTerm strategy module for equity trading.
This module implements mid-term trading strategy by:
1. Getting active users from MongoDB
2. Selecting top 3 stocks based on EMA signals
3. Placing orders through FirstStock broker
"""


import os
import sys


DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)


import logging
from datetime import datetime
from typing import List, Dict, Optional


from Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock import firstock_adapter
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument


from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    update_fields_firebase,
)

from Executor.ExecutorUtils.EquityCenter.EQBase import EQBaseFilter
from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import place_order_for_brokers
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_adapter import (
   firstock_place_equity_orders,
)

user_db_collection = os.getenv("FIREBASE_USER_COLLECTION")


class MidTermStrategy:
   """
   MidTerm trading strategy implementation.


   This class handles:
   - User configuration from MongoDB
   - Stock selection using EMA-based signals
   - Order placement through FirstStock broker
   """


   def __init__(self):
       """Initialize MidTerm strategy with necessary components."""
       self.logger = LoggerSetup()
       self.eq_filter = EQBaseFilter()


       # Add strategy-specific log file
       log_file = f"Data/Logs/midterm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
       self.logger.add(
           log_file,
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
           level="DEBUG",
       )


       self.logger.info("Initialized MidTerm Strategy")


   def get_active_users(self) -> List[Dict]:
       """
       Get active users from MongoDB who have enabled MidTerm strategy.


       Returns:
           List[Dict]: List of active user configurations
       """
       try:
           self.logger.info("Fetching active users from Firebase")
           users_data = fetch_collection_data_firebase(user_db_collection)


           if not users_data:
               self.logger.warning("No users found in firebase")
               return []


           # Filter active users with MidTerm strategy enabled
           active_users = []
           for user in users_data.values():
               midterm_config = (
                   user.get("Strategies", {}).get("Equity", {}).get("MidTerm", {})
               )
               if user.get("Active", False) and midterm_config:
                   self.logger.info(
                       f"Found active user {user.get('Tr_No')} with MidTerm strategy"
                   )
                   active_users.append(user)


           self.logger.info(
               f"Found {len(active_users)} active users with MidTerm strategy"
           )
           return active_users


       except Exception as e:
           self.logger.error(f"Error fetching active users: {e}")
           return []


   def get_top_stocks(self, sector: str) -> List[Dict]:
       """
       Get top 3 stocks based on EMA signals for given sector.


       Args:
           sector (str): Sector to analyze


       Returns:
           List[Dict]: List of top 3 stocks with their details
       """
       try:
           self.logger.info(f"Getting top stocks for sector: {sector}")
           stocks_df = self.eq_filter.get_ema_filtered_stocks(sector, limit=3)


           if stocks_df.empty:
               self.logger.warning(f"No stocks found for sector {sector}")
               return []


           # Convert DataFrame to list of dicts
           stocks = stocks_df.to_dict("records")
           self.logger.info(
               f"Selected top {len(stocks)} stocks: {[s['Symbol'] for s in stocks]}"
           )
           return stocks


       except Exception as e:
           self.logger.error(f"Error getting top stocks: {e}")
           return []


   async def place_orders(self, user: Dict, stocks: List[Dict]) -> bool:
       """
       Place orders for given stocks through the user's configured broker.


       Args:
           user (Dict): User configuration and credentials
           stocks (List[Dict]): List of stocks to place orders for


       Returns:
           bool: True if all orders placed successfully, False otherwise
       """
       try:
           self.logger.info(f"Placing orders for user {user.get('Tr_No')}")


           # Get MidTerm strategy configuration
           midterm_config = user["Strategies"]["Equity"]["MidTerm"]
           user_id = user["Broker"]["BrokerUsername"]
           quantity = midterm_config.get("Qty", 1)
           self.logger.info(f"Placing {quantity} orders for user {user.get('Tr_No')}")


           for stock in stocks:
               try:
                   eq_symbol = stock["Symbol"]


                   exchange_token, trading_symbol = firstock_adapter.search_instrument(
                       eq_symbol, user_id
                   )


                   ltp = firstock_adapter.get_eq_quote(trading_symbol, user_id)
                   price = float(ltp["data"]["lastTradedPrice"])


                   print("price:", price)


                   self.logger.info(
                       f"Found exchange token {exchange_token} and trading symbol {trading_symbol} for {eq_symbol}"
                   )


                   order_details = {
                       "broker": user["Broker"]["BrokerName"],
                       "remarks": "MidTerm",
                       "username": user.get("Tr_No"),
                       "setup": "MidTerm_" + stock["Symbol"],
                       "trading_symbol": trading_symbol,
                       "exchange_token": str(exchange_token),
                       "quantity": str(quantity),
                       "price": str(price),
                       "price_type": "LMT",
                       "transaction_type": "B",
                       "product": "C",
                       "retention": "DAY",
                       "trigger_price": str(price + 1),
                       "trade_id": f"MT_{stock['Symbol']}_5",
                   }


                   # Place order using broker_orders module
                   response = await firstock_place_equity_orders(
                       order_details, user_id
                   )


                   if response:
                       self.logger.info(
                           f"Order placed successfully for {stock['Symbol']} - "
                           f"User: {user.get('Tr_No')} - Quantity: {quantity}"
                       )
                   else:
                       self.logger.error(
                           f"Failed to place order for {stock['Symbol']} - "
                           f"User: {user.get('Tr_No')}"
                       )
                       return False


               except Exception as e:
                   self.logger.error(
                       f"Error processing order for {stock['Symbol']}: {e}"
                   )
                   continue


           return True


       except Exception as e:
           self.logger.error(f"Error placing orders: {e}")
           return False


   async def execute_strategy(self):
       """Execute the complete MidTerm strategy workflow."""
       try:
           self.logger.info("Starting MidTerm strategy execution")


           # 1. Get active users
           active_users = self.get_active_users()
           if not active_users:
               self.logger.warning("No active users found, stopping execution")
               return


           # 2. Get top stocks and place orders for each user
           for user in active_users:
               # Get user's configured sector and normalize it
               configured_sector = user["Strategies"]["Equity"]["MidTerm"].get(
                   "Sector", "NIFTY 50"
               )
               normalized_sector = configured_sector.strip()
               if normalized_sector.lower() == "Consumer Cyclical":
                   normalized_sector = "Consumer Cyclical"


               # Get available sectors
               available_sectors = self.eq_filter.get_available_sectors()
               self.logger.info(f"Available sectors: {available_sectors}")


               # Use configured sector if available, otherwise fallback to NIFTY 50
               sector = (
                   normalized_sector
                   if normalized_sector in available_sectors
                   else "NIFTY 50"
               )
               if sector != normalized_sector:
                   self.logger.warning(
                       f"Configured sector '{configured_sector}' not found, using '{sector}' instead"
                   )


               self.logger.info(f"Using sector: {sector}")


               # Get top stocks for sector
               top_stocks = self.get_top_stocks(sector)
               if not top_stocks:
                   self.logger.warning(
                       f"No suitable stocks found for sector {sector}, skipping user {user.get('Tr_No')}"
                   )
                   continue


               # Place orders for user
               success = await self.place_orders(user, top_stocks)
               if success:
                   self.logger.info(
                       f"Successfully executed strategy for user {user.get('Tr_No')}"
                   )
               else:
                   self.logger.error(
                       f"Strategy execution failed for user {user.get('Tr_No')}"
                   )


           self.logger.info("Completed MidTerm strategy execution")


       except Exception as e:
           self.logger.error(f"Error executing strategy: {e}")




if __name__ == "__main__":
   # Initialize and run strategy
   strategy = MidTermStrategy()
   import asyncio


   asyncio.run(strategy.execute_strategy())



