import os, sys

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

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


from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    update_fields_firebase,
)


def update_maket_info_for_strategies():
    market_info = fetch_collection_data_firebase("market_info")
    strategies = fetch_collection_data_firebase("strategies")
    for strategy_key, strategy_data in strategies.items():
        strategy_data["MarketInfo"] = market_info
        update_fields_firebase("strategies", strategy_key, strategy_data)
    return "Market info updated for all strategies."


if __name__ == "__main__":
    logger.success(update_maket_info_for_strategies())
