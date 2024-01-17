#get the trade_book for the broker
def get_trade_book(active_users):
    pass

#lld = list of list of dict
def fetch_tradebook_firebase_lld():
    # 1. Get the list of active users
    # 2. Get the list of orders for each strategy for each user
    pass

def fetch_tradebook_broker_lld():
    # 1. Get the list of active users
    # 2. Get the list of all the executed orders for each user
    pass

def compare_firebase_broker_lld(firebase_lld, broker_lld):
    # 1. Compare the firebase_lld and broker_lld
    # 2. The function should return 2 lld  one for matching and one for mismatching
    # 3. The reasons for mismatching can either be error trade or user trade
    # 4. The matched lld should be updated in the DB
    # 5. The mismatched lld should be manually validated and updated in the DB
    # 6. Notify for mismatching lld
    pass



