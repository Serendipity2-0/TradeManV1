import os, sys
from dotenv import load_dotenv
import pandas as pd

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, '.env')
load_dotenv(ENV_PATH)

import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils
import Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter as sql_utils

zerodha_primary_account = broker_center_utils.fetch_primary_accounts_from_firebase(os.getenv('ZERODHA_PRIMARY_ACCOUNT'))
aliceblue_primary_account = broker_center_utils.fetch_primary_accounts_from_firebase(os.getenv('ALICEBLUE_PRIMARY_ACCOUNT'))

zerodha_ins_df = broker_center_utils.download_csv_for_brokers(zerodha_primary_account)
print(zerodha_ins_df.shape)
aliceblue_ins_df = broker_center_utils.download_csv_for_brokers(aliceblue_primary_account)
print(aliceblue_ins_df.shape)

#function to merge zerodha_ins_df and aliceblue_ins_df based on exchannge_token in zerodha_ins_df and token in aliceblue_ins_df
def merge_ins_df(zerodha_ins_df, aliceblue_ins_df):
    #convert exchange_token and token columns type to str 
    zerodha_ins_df['exchange_token'] = zerodha_ins_df['exchange_token'].astype(str)
    aliceblue_ins_df['Token'] = aliceblue_ins_df['Token'].astype(str)
    # Merge the two DataFrames on the 'Token' column
    merged_df = pd.merge(zerodha_ins_df, aliceblue_ins_df, left_on='exchange_token', right_on='Token', how='right', suffixes=('_zerodha', '_aliceblue'))
    # Remove duplicate columns generated from merging
    merged_df = merged_df.loc[:,~merged_df.columns.str.endswith('_dup')]
    return merged_df

def main():
    merged_ins_df = merge_ins_df(zerodha_ins_df, aliceblue_ins_df)
    conn = sql_utils.get_db_connection(os.getenv('SQLITE_INS_PATH'))
    #print number of rows in the table
    print(merged_ins_df.shape)
    sql_utils.dump_df_to_sqlite(merged_ins_df, 'instrument_master', conn)

if __name__ == '__main__':
    main()