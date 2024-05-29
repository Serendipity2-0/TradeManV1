import datetime as dt
import os, sys
from dotenv import load_dotenv

# Define constants and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
logger = LoggerSetup()

# Expiry Dates Calculation
holidays = [dt.date(2024, i, j) for i, j in [
    (1, 26),
    (3, 8),
    (3, 25),
    (3, 29),
    (4, 11),
    (4, 17),
    (5, 1),
    (5, 20),
    (6, 17),
    (7, 17),
    (8, 15),
    (10, 2),
    (11, 1),
    (11, 15),
    (12, 25)
]]

def get_previous_trading_day(today: dt.date, prefix=None) -> dt.date:
# check if today -1 is in holidays or its is a weekend(sat or sun) it should return me the previous trading day    
    """
    Get the previous trading day, accounting for holidays and weekends.

    Args:
        today (dt.date): The current date.
        prefix (str, optional): A prefix to append to the date string.

    Returns:
        dt.date: The previous trading day.
    """
    # Check if today -1 is in holidays or its is a weekend(sat or sun) it should return me the previous trading day
    if today.weekday() == 0:
        previous_day = today - dt.timedelta(days=2)
        previous_day = previous_day.strftime("%d%b%y")
    elif today.weekday() == 6:
        previous_day = today - dt.timedelta(days=1)
        previous_day = previous_day.strftime("%d%b%y")
    else:
        previous_day = today - dt.timedelta(days=1)
        previous_day = previous_day.strftime("%d%b%y")
    while previous_day in holidays:
        logger.debug(f"previous_day: {previous_day} is a holiday")
        previous_day = previous_day - dt.timedelta(days=1)
        if prefix:
            previous_day = dt.date.strftime(previous_day, "%d%b%y")
            previous_day = f"{previous_day}{prefix}"

    return previous_day

def get_previous_freecash(today: dt.date, prefix=None) -> dt.date:
    """
    Get the previous free cash day, accounting for holidays and weekends.

    Args:
        today (dt.date): The current date.
        prefix (str, optional): A prefix to append to the date string.

    Returns:
        dt.date: The previous free cash day.
    """
    if today.weekday() == 0:
        previous_day = today - dt.timedelta(days=2)
        previous_day = previous_day.strftime("%d%b%y")
    elif today.weekday() == 6:
        previous_day = today - dt.timedelta(days=1)
        previous_day = previous_day.strftime("%d%b%y")
    else:
        previous_day = today - dt.timedelta(days=1)
        previous_day = previous_day.strftime("%d%b%y")
    while previous_day in holidays:
        logger.debug(f"previous_day: {previous_day} is a holiday")
        previous_day = previous_day - dt.timedelta(days=1)
        if prefix:
            previous_day = dt.date.strftime(previous_day, "%d%b%y")
            previous_day = f"{previous_day}{prefix}"

    return previous_day

def get_second_previous_trading_day(today: dt.date):
    """
    Get the second previous trading day, accounting for holidays and weekends.

    Args:
        today (dt.date): The current date.

    Returns:
        dt.date: The second previous trading day.
    """
    previous_day = get_previous_trading_day(today)
    previous_day = dt.datetime.strptime(previous_day, "%d%b%y").date()
    second_previous_day = get_previous_trading_day(previous_day)
    return second_previous_day
