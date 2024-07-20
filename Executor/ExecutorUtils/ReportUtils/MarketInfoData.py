import os, sys
from dotenv import load_dotenv
import pandas as pd

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

STRATEGIES_DB = os.getenv("FIREBASE_STRATEGY_COLLECTION")

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
)


def create_market_info_df():
    """
    Create a DataFrame containing market information for various strategies.

    Returns:
        DataFrame: DataFrame containing extracted market information for each strategy.
    """
    # Fetch data from Firebase collection
    strategy_fb_data = fetch_collection_data_firebase(STRATEGIES_DB)

    # Initialize an empty list to store the extracted data
    extracted_data = []

    # Iterate over each strategy in the JSON data
    for strategy_name, strategy_info in strategy_fb_data.items():
        # Extract necessary data
        strategy_type = strategy_info.get("GeneralParams", {}).get(
            "StrategyType", "N/A"
        )
        trade_view = strategy_info.get("MarketInfoParams", {}).get("TradeView", "N/A")

        # Extract Qty Amplifier, which can be in different sub-dictionaries
        qty_amplifier = strategy_info.get("MarketInfoParams", {}).get(
            "EquityQtyAmplifier",
            strategy_info.get("MarketInfoParams", {}).get(
                "OBQtyAmplifier",
                strategy_info.get("MarketInfoParams", {}).get("OSQtyAmplifier", "N/A"),
            ),
        )

        strategy_amplifier = strategy_info.get("MarketInfoParams", {}).get(
            "StrategyQtyAmplifier", "N/A"
        )

        # Append the extracted data as a dictionary to the list
        extracted_data.append(
            {
                "Strategy Name": strategy_name,
                "Strategy Type": strategy_type,
                "Qty Amplifier": qty_amplifier,
                "Trade View": trade_view,
                "Strategy Amplifier": strategy_amplifier,
            }
        )

    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(extracted_data)
    return df
