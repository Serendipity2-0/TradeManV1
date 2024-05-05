import os
import sys
from dotenv import load_dotenv
import datetime

# Load holdings data
DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)



from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_users_for_strategies_from_firebase as fetch_active_users
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import fetch_sql_table_from_db as fetch_table_from_db
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import get_single_ltp

from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument
from Executor.Strategies.StrategiesUtil import StrategyBase,assign_trade_id,place_order_strategy_users
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

class PyStocks(StrategyBase):
    def get_general_params(self):
        return self.GeneralParams

    def get_entry_params(self):
        return self.EntryParams

    def get_exit_params(self):
        return self.ExitParams

    def get_raw_field(self, field_name: str):
        return super().get_raw_field(field_name)

pystocks_obj = PyStocks.load_from_db("PyStocks")

stoploss_multiplier = pystocks_obj.EntryParams.SLMultiplier
strategy_name = pystocks_obj.StrategyName
transaction_type = pystocks_obj.get_raw_field("GeneralParams").get("SlTransactionType")
product_type = pystocks_obj.GeneralParams.ProductType
order_type = pystocks_obj.get_raw_field("GeneralParams").get("SlOrderType")
trade_mode = os.getenv("TRADE_MODE")

users = fetch_active_users("PyStocks")

to_date = datetime.date.today()
# Calculate previous day's date
from_date = to_date - datetime.timedelta(days=1)

if True:
    for user in users:
        holdings = fetch_table_from_db(user['Tr_No'], "Holdings")
        py_holdings = holdings[holdings['trade_id'].str.startswith('PS')]  #TODO Remove hardcoded PS
        for index, row in py_holdings.iterrows():
            symbol = row['trading_symbol']
            exchange_token = Instrument().get_exchange_token_by_name(symbol,"NSE")
            ltp = get_single_ltp(exchange_token = exchange_token, segment = "NSE")
            buy_price = float(row['entry_price'])
            per_change = (ltp - buy_price) / buy_price * 100
            sl = buy_price - (buy_price * stoploss_multiplier/100)

            trade_id = row['trade_id']
            trade_id =  trade_id.split('_')
            trade_id = trade_id[0]

            if per_change // stoploss_multiplier > 0 and per_change//stoploss_multiplier != 1:
                for j in range(int(per_change // stoploss_multiplier)):
                    sl = sl + (buy_price * stoploss_multiplier/100)
                    
                    sl = round(sl, 1)
                    logger.debug('LTP', ltp, 'Buy Price', buy_price, 'SL', sl)
                order_details = [{
                    "strategy": strategy_name,
                    "signal": "Long",
                    "base_symbol": symbol,
                    "exchange_token": exchange_token,
                    "transaction_type": transaction_type,
                    "order_type": order_type,
                    "product_type": product_type,
                    "order_mode": "SL",
                    "trade_id": trade_id,
                    "trade_mode": trade_mode,
                    "limit_prc": sl,
                    "trigger_prc": sl+0.3,
                }]
                order_to_place = assign_trade_id(order_details)
                logger.debug(f"Orders to place: {order_to_place}")
                place_order_strategy_users(strategy_name, order_to_place)