import datetime as dt
import os, sys

print("Shree Ganeshaya Namaha")
print("Jai Hanuman")
print("Market is Supreme")
print("Today's date:", dt.datetime.today())

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# import Brokers.Aliceblue.alice_login as alice_login
# import Brokers.Zerodha.kite_login as kite_login
# import MarketUtils.general_calc as general_calc
# import MarketUtils.Calculations.qty_calc as qty_calc
# import Brokers.place_order_calc as place_order_calc
# import Brokers.Aliceblue.alice_utils as alice_utils
# import Brokers.Zerodha.kite_utils as kite_utils
# import MarketUtils.Firebase.firebase_utils as firebase_utils


import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils

# def clear_json_file(user_name):
#     order_json_folderpath = os.path.join(DIR_PATH, 'UserProfile','OrdersJson')
#     order_json_filepath = os.path.join(order_json_folderpath, f'{user_name}.json')
#     general_calc.write_json_file(order_json_filepath, {})

# active_users = all_broker_login(general_calc.get_active_users(broker_json_details))
active_users = broker_center_utils.all_broker_login(broker_center_utils.fetch_active_users_from_firebase())



# def calculate_qty(active_users):
#     for user in active_users:
#         lots = qty_calc.calculate_lots(user)
#         user['qty'] = lots
#         clear_json_file(user['account_name'])
#     return active_users

# active_users_json = calculate_qty(active_users)


