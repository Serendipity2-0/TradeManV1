import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.MongoUtils.exemongo_adapter import (
    update_fields_mongodb,
    fetch_collection_data_mongodb,
)

logger = LoggerSetup()

STRATEGY_MONGO_DB = os.getenv("MONGO_STRATEGY_COLLECTION", "strategies")
MARKET_INFO_MONGO_COLLECTION = os.getenv("MONGO_MARKET_INFO_COLLECTION", "market_info")


def update_market_info_for_strategies():
    """
    The function updates market information for various strategies stored in a MongoDB database.
    It fetches the latest market information and strategies data from the MongoDB collections,
    updates the 'MarketInfoParams' for each strategy based on its type, and then saves the updated
    strategy data back to the MongoDB database.

    The function performs the following steps:
    1. Fetches market information from the MongoDB collection specified by the environment variable
       'MONGO_MARKET_INFO_COLLECTION'.
    2. Validates that the fetched market information is in dictionary format.
    3. Fetches strategies data from the MongoDB collection specified by the environment variable
       'MONGO_STRATEGY_COLLECTION'.
    4. Validates that the fetched strategies data is in dictionary format.
    5. Iterates over each strategy, validates its format, and updates its 'MarketInfoParams' based on
       the strategy type ('OB', 'OS', 'Equity') with appropriate market info parameters.
    6. Adds a common 'TradeView' parameter from the market information to each strategy.
    7. Updates the strategy data in the MongoDB collection.

    :raises ValueError: If the fetched market information or strategies data are not dictionaries.
    :raises Exception: If there is an error during the update process, an error message is logged.
    """
    try:
        # First update market info collection with the data from screenshot
        market_info_data = {
            "OBQtyAmplifier": 1,
            "OSQtyAmplifier": 1,
            "EquityQtyAmplifier": 1,
            "TradeView": "Bullish"  # From the screenshot
        }
        
        # Update market info collection
        update_fields_mongodb(
            MARKET_INFO_MONGO_COLLECTION,
            "market_info",  # Document ID
            market_info_data
        )
        logger.info("Market info collection updated successfully")

        # Fetch market info and strategies
        market_info = fetch_collection_data_mongodb(MARKET_INFO_MONGO_COLLECTION)
        if not isinstance(market_info, dict):
            raise ValueError("market_info should be a dictionary")

        strategies = fetch_collection_data_mongodb(STRATEGY_MONGO_DB)
        if not isinstance(strategies, dict):
            raise ValueError("strategies should be a dictionary")

        for strategy_key, strategy_data in strategies.items():
            if (
                "GeneralParams" not in strategy_data
                or "StrategyType" not in strategy_data["GeneralParams"]
            ):
                logger.error(f"Strategy data format error for key {strategy_key}")
                continue

            strategy_type = strategy_data["GeneralParams"]["StrategyType"]
            if "MarketInfoParams" not in strategy_data or not isinstance(
                strategy_data["MarketInfoParams"], dict
            ):
                strategy_data["MarketInfoParams"] = {}

            # Clear and update market info parameters
            strategy_data["MarketInfoParams"].clear()

            if strategy_type == "OB":
                strategy_data["MarketInfoParams"]["OBQtyAmplifier"] = market_info.get(
                    "OBQtyAmplifier", 1
                )
            elif strategy_type == "OS":
                strategy_data["MarketInfoParams"]["OSQtyAmplifier"] = market_info.get(
                    "OSQtyAmplifier", 1
                )
            elif strategy_type == "Equity":
                strategy_data["MarketInfoParams"]["EquityQtyAmplifier"] = market_info.get(
                    "EquityQtyAmplifier", 1
                )

            # Add common TradeView parameter
            strategy_data["MarketInfoParams"]["TradeView"] = market_info.get("TradeView")

            # Update the strategy in MongoDB
            update_fields_mongodb(
                STRATEGY_MONGO_DB,
                strategy_key,
                strategy_data
            )

        logger.success("Market info updated for all strategies.")

    except Exception as e:
        logger.error(f"Error in updating market info for strategies: {e}")


if __name__ == "__main__":
    update_market_info_for_strategies()
