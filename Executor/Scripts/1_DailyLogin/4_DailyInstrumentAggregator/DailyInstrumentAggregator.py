import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, '.env')
load_dotenv(ENV_PATH)

import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils

zerodha_primary_account = broker_center_utils.fetch_primary_accounts_from_firebase(os.getenv('ZERODHA_PRIMARY_ACCOUNT'))
aliceblue_primary_account = broker_center_utils.fetch_primary_accounts_from_firebase(os.getenv('ALICEBLUE_PRIMARY_ACCOUNT'))

zerodha_ins_csv = broker_center_utils.download_csv_for_brokers(zerodha_primary_account)
aliceblue_ins_csv = broker_center_utils.download_csv_for_brokers(aliceblue_primary_account)

# a function merge_csv() on exchange_token is required to merge the csv files of aliceblue and zerodha
