import os
import sys
import datetime as dt
from time import sleep
from dotenv import load_dotenv
import random

from pprint import pprint

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from Executor.Strategies.StrategiesUtil import StrategyBase
from Executor.Strategies.StrategiesUtil import update_qty_user_firebase, assign_trade_id, update_signal_firebase, place_order_strategy_users

import Executor.ExecutorUtils.ExeUtils as ExeUtils
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import discord_bot

ENV_PATH = os.path.join(DIR_PATH, 'trademan.env')
load_dotenv(ENV_PATH)

class Om(StrategyBase):
    def get_general_params(self):
        return self.GeneralParams
    
    def get_entry_params(self):
        return self.EntryParams
    
    def get_exit_params(self):
        return self.ExitParams
    
    def get_raw_field(self, field_name: str):
        return super().get_raw_field(field_name)
    
strategy_obj = Om.load_from_db('Om')
instrument_obj = InstrumentCenterUtils.Instrument()

def message_for_orders(trade_type,prediction,main_trade_symbol,strategy_name):
    #TODO: add noftication for the orders 
    message = ( f"{trade_type} Trade for {strategy_name}\n"
            f"Direction : {prediction}\n"
            f"Main Trade : {main_trade_symbol}") 
    print(message)
    discord_bot(message, strategy_name)


def om():
    next_trade_prefix = strategy_obj.NextTradeId
    result = random.choice(['Heads', 'Tails'])
    base_symbol,_ = strategy_obj.determine_expiry_index()
    option_type = 'CE' if result == 'Heads' else 'PE'
    prediction = 'Bullish' if option_type == 'CE' else 'Bearish'
    strike_price_multiplier = strategy_obj.get_raw_field("GeneralParams").get('StrikePriceMultiplier')
    strike_prc = strategy_obj.calculate_current_atm_strike_prc(base_symbol=base_symbol,prediction=prediction,strike_prc_multiplier=strike_price_multiplier)
    today_expiry = instrument_obj.get_expiry_by_criteria(base_symbol,strike_prc,option_type, "current_week")
    
    
    exchange_token = instrument_obj.get_exchange_token_by_criteria(base_symbol,strike_prc, option_type,today_expiry)
    trading_symbol = instrument_obj.get_trading_symbol_by_exchange_token(exchange_token)


    message_for_orders("Live",result,trading_symbol, strategy_obj.StrategyName)

    orders_to_place = [
        {  
        "strategy": strategy_obj.StrategyName,
        "signal":"Long",
        "base_symbol": base_symbol,
        "exchange_token" : exchange_token,     
        "transaction_type": strategy_obj.get_general_params().MainTransactionType,  
        "order_type" : strategy_obj.get_general_params().OrderType, 
        "product_type" : strategy_obj.get_general_params().ProductType,
        "order_mode" : "Main",
        "trade_id" : next_trade_prefix
        }]
    orders_to_place = assign_trade_id(orders_to_place)
    return orders_to_place


def main():
    desired_start_time_str = strategy_obj.get_entry_params().EntryTime
    start_hour, start_minute, start_second = map(int, desired_start_time_str.split(':'))
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
        
        signals_to_log = {
                        "TradeId" : strategy_obj.NextTradeId,
                        "Signal" : "Short",
                        "EntryTime" : dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "StrategyInfo" : {"Direction" : strategy_obj.get_general_params().TradeView,},
                        "Status" : "Open"}

        update_signal_firebase(strategy_obj.StrategyName,signals_to_log)
        orders_to_place = om()
        print(orders_to_place)
        # place_order_strategy_users(strategy_obj.StrategyName,orders_to_place)

if __name__ == "__main__":
    main()

