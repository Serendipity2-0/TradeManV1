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

def update_maket_info_for_strategies():
    try:
        market_info = fetch_collection_data_firebase("market_info")
        strategies = fetch_collection_data_firebase("strategies")
        for strategy_key, strategy_data in strategies.items():
            strategy_data["MarketInfoParams"] = market_info
            update_fields_firebase("strategies", strategy_key, strategy_data)
        logger.success("Market info updated for all strategies.")
    except Exception as e:
        logger.error(f"Error in updating market info for strategies: {e}")

if __name__ == "__main__":
    update_maket_info_for_strategies()
