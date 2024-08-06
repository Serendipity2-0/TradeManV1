import os
import sys

import pandas as pd
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils
import Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter as sql_utils


ZERODHA = os.getenv("ZERODHA_BROKER")
ALICEBLUE = os.getenv("ALICEBLUE_BROKER")


def download_instruments():
    """
    Downloads instrument data for primary brokers concurrently.

    Returns:
        dict: A dictionary with broker names as keys and their respective DataFrames as values.
    """
    primary_brokers = broker_center_utils.fetch_primary_broker_list()
    broker_dfs = {}

    for broker in primary_brokers:
        broker_dfs[broker] = broker_center_utils.download_csv_for_brokers(broker)

    return broker_dfs


def merge_ins_df(broker_dfs):
    """
    Merge instrument dataframes from multiple brokers on the 'Token' column.

    Args:
        broker_dfs (dict): A dictionary with broker names as keys and their respective DataFrames as values.

    Returns:
        pd.DataFrame: Merged DataFrame with combined instrument data.
    """
    # Columns to keep from instruments.csv
    columns_to_keep_instruments = [
        "instrument_token",
        "exchange_token",
        "tradingsymbol",
        "name",
        "expiry",
        "strike",
        "tick_size",
        "lot_size",
        "instrument_type",
        "segment",
        "exchange",
    ]

    # Filter the instruments DataFrame from Zerodha
    zerodha_ins_df = broker_dfs.get(ZERODHA)
    if zerodha_ins_df is not None:
        instruments_df_filtered = zerodha_ins_df[columns_to_keep_instruments]

    # Merge with other brokers
    merged_df = instruments_df_filtered
    for broker, df in broker_dfs.items():
        if broker != ZERODHA:
            merged_df = pd.merge(
                df,
                merged_df,
                left_on="Token",
                right_on="exchange_token",
                how="left",
            )
            merged_df.drop("Token", axis=1, inplace=True)

    return merged_df


def aggregate_ins():
    """
    Aggregate instrument data from Zerodha and AliceBlue, merge it, and dump it to an SQLite database.

    Returns:
        None
    """
    try:
        broker_dfs = download_instruments()
        merged_ins_df = merge_ins_df(broker_dfs)
        conn = sql_utils.get_db_connection(os.getenv("SQLITE_INS_PATH"))
        decimal_cols = []
        sql_utils.dump_df_to_sqlite(
            conn, merged_ins_df, "instrument_master", decimal_cols
        )
    except Exception as e:
        print(f"Error in aggregating instruments: {e}")
