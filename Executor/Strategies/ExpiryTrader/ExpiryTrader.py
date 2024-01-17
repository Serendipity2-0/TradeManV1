import os
import sys
import datetime as dt
from time import sleep
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from Executor.Strategies.StrategiesUtil import StrategyBase
import Executor.ExecutorUtils.OrderCenter.OrderCenterUtils as OrderCenterUtils
import Executor.ExecutorUtils.ExeUtils as ExeUtils
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils



ENV_PATH = os.path.join(DIR_PATH, '.env')
load_dotenv(ENV_PATH)

class ExpiryTrader(StrategyBase.Strategy):
    def get_general_params(self):
        return self.general_params
    
    def get_entry_params(self):
        return self.entry_params
    
    def get_exit_params(self):
        return self.exit_params
    
# Testing the class with ExpiryTrader data
expiry_trader_obj = ExpiryTrader.load_strategy('ExpiryTrader')  
instrument_obj = InstrumentCenterUtils.Instrument()

hedge_transcation_type = expiry_trader_obj.get_general_params().get('HedgeTransactionType')
main_transcation_type = expiry_trader_obj.get_general_params().get('MainTransactionType')


# Extract strategy parameters
base_symbol, today_expiry_token = expiry_trader_obj.determine_expiry_index()
strategy_name = expiry_trader_obj.get_strategy_name()
prediction = expiry_trader_obj.get_general_params().get('TradeView')
order_type = expiry_trader_obj.get_general_params().get('OrderType')
segment_type = expiry_trader_obj.get_general_params().get('Segment')
product_type = expiry_trader_obj.get_general_params().get('ProductType')

strike_prc_multiplier = expiry_trader_obj.get_strike_multiplier(base_symbol)
hedge_multiplier = expiry_trader_obj.get_hedge_multiplier(base_symbol)
stoploss_mutiplier = expiry_trader_obj.get_stoploss_multiplier(base_symbol)
desired_start_time_str = expiry_trader_obj.get_entry_params().get('EntryTime')

start_hour, start_minute, start_second = map(int, desired_start_time_str.split(':'))

main_strikeprc = expiry_trader_obj.calculate_current_atm_strike_prc(base_symbol,today_expiry_token, prediction, strike_prc_multiplier)
hedge_strikeprc = expiry_trader_obj.get_hedge_strikeprc(base_symbol, today_expiry_token, prediction, hedge_multiplier)
main_option_type = expiry_trader_obj.get_option_type(prediction, "OS")
hedge_option_type = expiry_trader_obj.get_hedge_option_type(prediction)

today_expiry = instrument_obj.get_expiry_by_criteria(base_symbol,main_strikeprc,main_option_type, "current_week")
hedge_exchange_token = instrument_obj.get_exchange_token_by_criteria(base_symbol,hedge_strikeprc,hedge_option_type, today_expiry)
main_exchange_token = instrument_obj.get_exchange_token_for_option(base_symbol,main_strikeprc, main_option_type,today_expiry)
main_instrument_token = instrument_obj.get_instoken_by_exchange_token(main_exchange_token)

ltp = InstrumentCenterUtils.get_single_ltp(main_instrument_token)

OrderCenterUtils.calculate_quantity_based_on_ltp(ltp,expiry_trader_obj.get_strategy_name(),base_symbol)

trade_id = OrderCenterUtils.get_trade_id(strategy_name, "entry")

main_trade_symbol = instrument_obj.get_trading_symbol_by_exchange_token(main_exchange_token)
hedge_trade_symbol = instrument_obj.get_trading_symbol_by_exchange_token(hedge_exchange_token)

orders_to_place = [
    {  
        "strategy": strategy_name,
        "base_symbol": base_symbol,
        "exchange_token" : hedge_exchange_token,     
        "segment" : segment_type,
        "transaction_type": hedge_transcation_type,  
        "order_type" : order_type, 
        "product_type" : product_type,
        "order_mode" : ["Hedge"],
        "trade_id" : trade_id 
    },
    {
        "strategy": strategy_name,
        "base_symbol": base_symbol,
        "exchange_token" : main_exchange_token,     
        "segment" : segment_type,
        "transaction_type": main_transcation_type, 
        "order_type" : order_type, 
        "product_type" : product_type,
        "stoploss_mutiplier": stoploss_mutiplier,
        "order_mode" : ["Main","SL"],
        "trade_id" : trade_id
    }
    ]

def message_for_orders(trade_type,prediction,main_trade_symbol,hedge_trade_symbol):
    strategy_name = expiry_trader_obj.get_strategy_name()

    message = ( f"{trade_type} Trade for {expiry_trader_obj.get_strategy_name()}\n"
            f"Direction : {prediction}\n"
            f"Main Trade : {main_trade_symbol}\n"
            f"Hedge Trade {hedge_trade_symbol} \n")    
    print(message)
    

def main():
    now = dt.datetime.now()

    if now.date() in ExeUtils.holidays:
        print("Skipping execution as today is a holiday.")
        return

    if now.time() < dt.time(9, 0):
        print("Time is before 9:00 AM, Waiting to execute.")
    else:
        wait_time = dt.datetime(now.year, now.month, now.day, start_hour, start_minute) - now
        if wait_time.total_seconds() > 0:
            print(f"Waiting for {wait_time} before starting the bot")
            sleep(wait_time.total_seconds())
        
        message_for_orders("Live",prediction,main_trade_symbol,hedge_trade_symbol)
        OrderCenterUtils.place_order_for_strategy(strategy_name,orders_to_place)

if __name__ == "__main__":
    main()