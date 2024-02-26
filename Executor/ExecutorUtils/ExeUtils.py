import datetime as dt
import os,sys
from loguru import logger
from dotenv import load_dotenv

# Define constants and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


#Expiry Dates Calculation
holidays = [dt.date(2024, i, j) for i, j in [
    (1, 26),
    (3, 8),
    (3, 25),
    (3, 29),
    (4, 11),
    (4, 17),
    (5, 1),
    (6, 17),
    (7, 17),
    (8, 15),
    (10, 2),
    (11, 1),
    (11, 15),
    (12, 25)
]]


def get_previous_trading_day(today: dt.date, prefix=None) -> dt.date:
    #check if today -1 is in holidays or its is a weekend(sat or sun) it should return me the previous trading day
    if today.weekday() == 0:
        previous_day = today - dt.timedelta(days=3)
        previous_day = previous_day.strftime("%d%b%y")
    elif today.weekday() == 6:
        previous_day = today - dt.timedelta(days=2)
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
    if today.weekday() == 0:
        previous_day = today - dt.timedelta(days=2)
        previous_day = previous_day.strftime("%d%b%y")
    elif today.weekday() == 6:
        previous_day = today - dt.timedelta(days=2)
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
    previous_day = get_previous_trading_day(today)
    previous_day = dt.datetime.strptime(previous_day, "%d%b%y").date()
    second_previous_day = get_previous_trading_day(previous_day)
    return second_previous_day
