# Import necessary libraries and modules
import os, sys
from dotenv import load_dotenv

import datetime as dt
from time import sleep

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.Strategies.StrategiesUtil import StrategyBase

import Executor.ExecutorUtils.ExeUtils as ExeUtils
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

# The `MPWizard` class extends `StrategyBase` and includes a method `get_general_params` to retrieve
# general parameters.
import MPWizard_calc as MPWizard_calc


class MPWizard(StrategyBase):
    def get_general_params(self):
        """
        The function `get_general_params` returns the `GeneralParams` attribute of the object.
        :return: The method `get_general_params` is returning the attribute `GeneralParams` of the object.
        """
        return self.GeneralParams

    def get_entry_params(self):
        """
        The `get_entry_params` function returns the `EntryParams` attribute of the object.
        :return: The `EntryParams` attribute of the `self` object is being returned.
        """
        return self.EntryParams

    def get_exit_params(self):
        """
        The function `get_exit_params` returns the `ExitParams` attribute of the object.
        :return: The `ExitParams` attribute of the `self` object is being returned.
        """
        return self.ExitParams


mpwizard_strategy_obj = MPWizard.load_from_db("MPWizard")
instrument_obj = InstrumentCenterUtils.Instrument()

# Fetch the desired start time from the environment variables
desired_start_time_str = mpwizard_strategy_obj.get_entry_params().EntryTime
start_hour, start_minute, start_second = map(int, desired_start_time_str.split(":"))


# Fetch the list of users to trade with the strategy
def main():
    """
    Main function to execute the trading strategy.

    This function performs the following steps:
    1. Checks if today is a holiday and skips execution if it is.
    2. Updates the JSON file with average range data using the `get_average_range_and_update_json` function from `MPWizard_calc`.
    3. Calculates the wait time before starting the bot based on the desired start time and the current time.
    4. Sleeps for the calculated wait time if it is positive.
    5. Updates the JSON file with high-low range data using the `get_high_low_range_and_update_json` function from `MPWizard_calc`.
    6. Loads the updated strategy data from the database.
    7. Initializes the `OrderMonitor` with the mood data and starts monitoring for index triggers.
    """
    now = dt.datetime.now()

    if now.date() in ExeUtils.holidays:
        logger.info("Skipping execution as today is a holiday.")
        return

    # Update the JSON file with average range data
    MPWizard_calc.get_average_range_and_update_json(
        mpwizard_strategy_obj.GeneralParams.ATRPeriod
    )

    # Calculate the wait time before starting the bot
    desired_start_time = dt.datetime(
        now.year, now.month, now.day, start_hour, start_minute
    )
    wait_time = desired_start_time - now
    logger.info(f"Waiting for {wait_time} before starting the bot")

    # Sleep for the calculated wait time if it's positive
    if wait_time.total_seconds() > 0:
        sleep(wait_time.total_seconds())

    # Update the JSON file with high-low range data
    MPWizard_calc.get_high_low_range_and_update_json()

    strat = MPWizard.load_from_db("MPWizard")
    mood_data = strat.get_entry_params().InstrumentToday

    from MPWizard_monitor import OrderMonitor

    # Initialize the OrderMonitor with the users and instruments, then start monitoring
    order_monitor = OrderMonitor(mood_data, max_orders=2)
    order_monitor.monitor_index()


if __name__ == "__main__":
    main()
