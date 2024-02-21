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

zerodha_primary_account = broker_center_utils.fetch_primary_accounts_from_firebase(
    os.getenv("ZERODHA_PRIMARY_ACCOUNT")
)
aliceblue_primary_account = broker_center_utils.fetch_primary_accounts_from_firebase(
    os.getenv("ALICEBLUE_PRIMARY_ACCOUNT")
)

zerodha_ins_df = broker_center_utils.download_csv_for_brokers(zerodha_primary_account)
aliceblue_ins_df = broker_center_utils.download_csv_for_brokers( aliceblue_primary_account)

def merge_ins_df(zerodha_ins_df, aliceblue_ins_df):
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

    # Filter the instruments DataFrame
    instruments_df_filtered = zerodha_ins_df[columns_to_keep_instruments]

    # Merge using 'Token' from merged_df and 'exchange_token' from instruments_df
    final_merged_df = pd.merge(
        aliceblue_ins_df,
        instruments_df_filtered,
        left_on="Token",
        right_on="exchange_token",
        how="left",
    )

    # Drop the 'Token' column
    final_merged_df.drop("Token", axis=1, inplace=True)
    return final_merged_df


def aggregate_ins():
    merged_ins_df = merge_ins_df(zerodha_ins_df, aliceblue_ins_df)
    conn = sql_utils.get_db_connection(os.getenv("SQLITE_INS_PATH"))
    # print number of rows in the table
    decimal_cols = []
    sql_utils.dump_df_to_sqlite(
        conn, merged_ins_df, "instrument_master", decimal_cols
    )  