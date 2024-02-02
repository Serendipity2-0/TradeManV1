# Import necessary libraries and modules
import os,sys
from dotenv import load_dotenv

import datetime as dt
from time import sleep

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, 'trademan.env')
load_dotenv(ENV_PATH)

from Executor.Strategies.StrategiesUtil import StrategyBase

import Executor.ExecutorUtils.ExeUtils as ExeUtils
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import discord_bot

import MPWizard_calc as MPWizard_calc
from MPWizard_monitor import OrderMonitor

class MPWizard(StrategyBase):
    def get_general_params(self):
        return self.GeneralParams
    
    def get_entry_params(self):
        return self.EntryParams
    
    def get_exit_params(self):
        return self.ExitParams
    
mpwizard_strategy_obj = MPWizard.load_from_db('MPWizard')
instrument_obj = InstrumentCenterUtils.Instrument()
next_trade_prefix = mpwizard_strategy_obj.NextTradeId


# Fetch the desired start time from the environment variables
desired_start_time_str = mpwizard_strategy_obj.get_entry_params().EntryTime
start_hour, start_minute, start_second = map(int, desired_start_time_str.split(':'))

# Fetch the list of users to trade with the strategy


def main():
    """
    Main function to execute the trading strategy.
    """
    now = dt.datetime.now()

    if now.date() in ExeUtils.holidays:
        print("Skipping execution as today is a holiday.")
        return
    
    # Update the JSON file with average range data
    MPWizard_calc.get_average_range_and_update_json(mpwizard_strategy_obj.GeneralParams.ATRPeriod)
    
    # Calculate the wait time before starting the bot
    desired_start_time = dt.datetime(now.year, now.month, now.day, start_hour, start_minute)
    wait_time = desired_start_time - now
    print(f"Waiting for {wait_time} before starting the bot")
    
    # Sleep for the calculated wait time if it's positive
    if wait_time.total_seconds() > 0:
        sleep(wait_time.total_seconds())
    
    # Update the JSON file with high-low range data
    MPWizard_calc.get_high_low_range_and_update_json()
    
    mood_data = mpwizard_strategy_obj.get_entry_params().InstrumentToday
    
    # Initialize the OrderMonitor with the users and instruments, then start monitoring
    order_monitor = OrderMonitor(mood_data, max_orders=2) 
    order_monitor.monitor_index()

if __name__ == "__main__":
    main()
