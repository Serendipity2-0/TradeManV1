#TODO: get all user/strategies/todaysorders from firebase and iterate over the order_id
# match tradebook and firebase data. Prepare the matching orders to be logged in usersql db
# unmatched orders should be also be prepared to be logged in as error trade but to be notified. 
# further unmatched orders to be logged in 'holdings' table with 'unidentified' source
# user/strategies/todaysorders format:
# "Strategies": {
#         "ExpiryTrader": {
#             "RiskPerTrade": 1,
#             "TradeState": [
#                 {
#                     "LastModified": "2020-03-22 11:23:22",
#                     "Status": "Active",
#                     "orders": [
#                         {
#                             "avg_prc": 0,
#                             "exchange_token": 48301,
#                             "order_id": "123456",
#                             "qty": 200,
#                             "timestamp": "2023-11-20 22:55:19.798995",
#                             "trade_id": "ET12_entry"
#                         },
#                         {
#                             "avg_prc": "1232",
#                             "order_id": "123456",
#                             "time": "12:23",
#                             "trade_id": "ET12_entry",
#                             "trading_symbol": "NIFTY"
#                         }
#                     ]
#                 }
#             ]
#         }
#     }

# alice orderhistory format:
# [
#     {
#         "Prc": "00.00",
#         "Action": "B",
#         "productcode": "MIS",
#         "reporttype": "NA",
#         "triggerprice": "0.0",
#         "filledShares": 0,
#         "disclosedqty": "0",
#         "exchangetimestamp": "--",
#         "symbolname": "ASHOKLEY",
#         "ExchTimeStamp": "01/06/2022 19:30:04",
#         "nestordernumber": "220601000204676",
#         "duration": "DAY",
#         "OrderUserMessage": "",
#         "averageprice": "0.0",
#         "Qty": 1,
#         "ordergenerationtype": "AMO",
#         "modifiedBy": "--",
#         "filldateandtime": "-- --",
#         "Status": "after market order req received",
#         "rejectionreason": "--",
#         "stat": "Ok",
#         "PriceDenomenator": "1",
#         "exchangeorderid": null,
#         "PriceNumerator": "1",
#         "legorderindicator": "",
#         "customerfirm": "C",
#         "ordersource": "NEST_REST_WEB",
#         "GeneralDenomenator": "1",
#         "nestreqid": "1",
#         "Ordtype": "L",
#         "unfilledSize": 1,
#         "scripname": "ASHOK LEYLAND LTD",
#         "exchange": "NSE",
#         "GeneralNumerator": "1",
#         "bqty": 1,
#         "Trsym": "ASHOKLEY-EQ"
#     }
# ]

# kite oderhistory format:
# {
#   "status": "success",
#   "data": [
#     {
#       "trade_id": "10000000",
#       "order_id": "200000000000000",
#       "exchange": "NSE",
#       "tradingsymbol": "SBIN",
#       "instrument_token": 779521,
#       "product": "CNC",
#       "average_price": 420.65,
#       "quantity": 1,
#       "exchange_order_id": "300000000000000",
#       "transaction_type": "BUY",
#       "fill_timestamp": "2021-05-31 09:16:39",
#       "order_timestamp": "09:16:39",
#       "exchange_timestamp": "2021-05-31 09:16:39"
#     },
#     {
#       "trade_id": "40000000",
#       "order_id": "500000000000000",
#       "exchange": "CDS",
#       "tradingsymbol": "USDINR21JUNFUT",
#       "instrument_token": 412675,
#       "product": "MIS",
#       "average_price": 72.755,
#       "quantity": 1,
#       "exchange_order_id": "600000000000000",
#       "transaction_type": "BUY",
#       "fill_timestamp": "2021-05-31 11:18:27",
#       "order_timestamp": "11:18:27",
#       "exchange_timestamp": "2021-05-31 11:18:27"
#     },
#     {
#       "trade_id": "70000000",
#       "order_id": "800000000000000",
#       "exchange": "MCX",
#       "tradingsymbol": "GOLDPETAL21JUNFUT",
#       "instrument_token": 58424839,
#       "product": "NRML",
#       "average_price": 4852,
#       "quantity": 1,
#       "exchange_order_id": "312115100078593",
#       "transaction_type": "BUY",
#       "fill_timestamp": "2021-05-31 16:00:36",
#       "order_timestamp": "16:00:36",
#       "exchange_timestamp": "2021-05-31 16:00:36"
#     },
#     {
#       "trade_id": "90000000",
#       "order_id": "1100000000000000",
#       "exchange": "MCX",
#       "tradingsymbol": "GOLDPETAL21JUNFUT",
#       "instrument_token": 58424839,
#       "product": "NRML",
#       "average_price": 4852,
#       "quantity": 1,
#       "exchange_order_id": "1200000000000000",
#       "transaction_type": "BUY",
#       "fill_timestamp": "2021-05-31 16:08:41",
#       "order_timestamp": "16:08:41",
#       "exchange_timestamp": "2021-05-31 16:08:41"
#     }
#   ]
# }

# Logging format columns:
# trade_id	trading_symbol	signal	entry_time	exit_time	entry_price	exit_price	hedge_entry_price	hedge_exit_price	trade_points	qty	pnl	tax	net_pnl
# calculation logic:
# trade_id:
# trading_symbol:
# signal:
# entry_time:
# exit_time:
# entry_price:
# exit_price:
# hedge_entry_price:
# hedge_exit_price:
# trade_points:
# qty:
# pnl:
# tax:
# net_pnl: