import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from MarketInfo.DataCenter.DailyEODDB import main as daily_eod_db


def main():
    """
    The main function calls the daily end-of-day (EOD) database update function.

    This function is intended to perform daily EOD database operations for the MarketInfo DataCenter.
    """
    daily_eod_db()


if __name__ == "__main__":
    main()
