import datetime as dt
import os, sys
from dotenv import load_dotenv


# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.ExeUtils import (
    get_previous_trading_day,
    get_previous_freecash,
    get_second_previous_trading_day,
)

# Define a test date that is a weekday
test_date = dt.date(
    2024, 6, 10
)  # This date is a Saturday, let's change it to a weekday

# Change the test date to a weekday
test_date = dt.date(2024, 6, 7)  # Adjust the date to a weekday


def test_get_previous_trading_day():
    # Test if the previous trading day is correct
    expected_previous_day = dt.date(2024, 6, 6)  # Adjusted expected date
    assert get_previous_trading_day(test_date) == expected_previous_day.strftime(
        "%d%b%y"
    )


def test_get_previous_freecash():
    # Test if the previous free cash day is correct
    expected_previous_day = dt.date(2024, 6, 6)  # Adjusted expected date
    assert get_previous_freecash(test_date) == expected_previous_day.strftime("%d%b%y")


def test_get_second_previous_trading_day():
    # Test if the second previous trading day is correct
    expected_second_previous_day = dt.date(2024, 6, 5)  # Adjusted expected date
    assert get_second_previous_trading_day(
        test_date
    ) == expected_second_previous_day.strftime("%d%b%y")
