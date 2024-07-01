import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    update_fields_firebase,
)

STRATEGY_FB_DB = os.getenv("FIREBASE_STRATEGY_COLLECTION")
MARKET_INFO_FB_COLLECTION = os.getenv("MARKET_INFO_FB_COLLECTION")


def update_market_info_for_strategies():
    """
    The function updates market information for various strategies stored in a Firebase database.
    It fetches the latest market information and strategies data from the Firebase collections,
    updates the 'MarketInfoParams' for each strategy based on its type, and then saves the updated
    strategy data back to the Firebase database.

    The function performs the following steps:
    1. Fetches market information from the Firebase collection specified by the environment variable
       'MARKET_INFO_FB_COLLECTION'.
    2. Validates that the fetched market information is in dictionary format.
    3. Fetches strategies data from the Firebase collection specified by the environment variable
       'FIREBASE_STRATEGY_COLLECTION'.
    4. Validates that the fetched strategies data is in dictionary format.
    5. Iterates over each strategy, validates its format, and updates its 'MarketInfoParams' based on
       the strategy type ('OB', 'OS', 'Equity') with appropriate market info parameters.
    6. Adds a common 'TradeView' parameter from the market information to each strategy.
    7. Updates the strategy data in the Firebase collection.

    :raises ValueError: If the fetched market information or strategies data are not dictionaries.
    :raises Exception: If there is an error during the update process, an error message is logged.
    """
    try:
        market_info = fetch_collection_data_firebase(MARKET_INFO_FB_COLLECTION)
        if not isinstance(market_info, dict):
            raise ValueError("market_info should be a dictionary")

        strategies = fetch_collection_data_firebase(STRATEGY_FB_DB)
        if not isinstance(strategies, dict):
            raise ValueError("strategies should be a dictionary")

        for strategy_key, strategy_data in strategies.items():
            if (
                "GeneralParams" not in strategy_data
                or "StrategyType" not in strategy_data["GeneralParams"]
            ):
                logger.error(f"Strategy data format error for key {strategy_key}")
                continue  # Skip to next strategy if the current one has invalid format

            strategy_type = strategy_data["GeneralParams"]["StrategyType"]
            if "MarketInfoParams" not in strategy_data or not isinstance(
                strategy_data["MarketInfoParams"], dict
            ):
                strategy_data[
                    "MarketInfoParams"
                ] = {}  # Initialize if not present or not a dictionary

            # Clear and update market info parameters
            strategy_data["MarketInfoParams"].clear()

            if strategy_type == "OB":
                strategy_data["MarketInfoParams"]["OBQtyAmplifier"] = market_info.get(
                    "OBQtyAmplifier", 1
                )  # Default to 1 if not found
            elif strategy_type == "OS":
                strategy_data["MarketInfoParams"]["OSQtyAmplifier"] = market_info.get(
                    "OSQtyAmplifier", 1
                )
            elif strategy_type == "Equity":
                strategy_data["MarketInfoParams"][
                    "EquityQtyAmplifier"
                ] = market_info.get("EquityQtyAmplifier", 1)

            # Add common TradeView parameter
            strategy_data["MarketInfoParams"]["TradeView"] = market_info.get(
                "TradeView"
            )  # Default to "Neutral" if not found

            # Update the strategy data in Firebase (uncomment this line when ready to update)
            update_fields_firebase(STRATEGY_FB_DB, strategy_key, strategy_data)

        logger.success("Market info updated for all strategies.")
    except Exception as e:
        logger.error(f"Error in updating market info for strategies: {e}")


if __name__ == "__main__":
    update_market_info_for_strategies()
