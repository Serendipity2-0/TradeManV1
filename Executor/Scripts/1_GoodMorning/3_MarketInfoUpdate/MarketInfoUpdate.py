#TODO: Read market info DB and update the "market_info" section of every strategy in firebase
# 1. Use exefirebaseutils to get market_info section from firebase for each strategy
# 2. Iterate over the strategies and update the "market_info" section
# 3. Commit the changes back to firebase using exefirebaseutils

import os,sys

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import fetch_collection_data_firebase, update_fields_firebase

def update_maket_info_for_strategies():
    market_info = fetch_collection_data_firebase('market_info')
    strategies = fetch_collection_data_firebase('strategies')
    for strategy_key, strategy_data in strategies.items():
        strategy_data['MarketInfo'] = market_info
        update_fields_firebase('strategies', strategy_key, strategy_data)
    return "Market info updated for all strategies."

if __name__ == "__main__":
    print(update_maket_info_for_strategies())