import datetime as dt
import os, sys

print("Shree Ganeshaya Namaha")
print("Jai Hanuman")
print("Market is Supreme")
print("Today's date:", dt.datetime.today())

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils

active_users = broker_center_utils.all_broker_login(broker_center_utils.fetch_active_users_from_firebase())
