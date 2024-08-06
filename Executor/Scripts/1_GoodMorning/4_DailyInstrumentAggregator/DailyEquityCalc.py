import os
import sys

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.NSEStrategies.Equity.EquityCalculation import main as equity_calc_main

logger = LoggerSetup()


def main():
    """
    This is the main function for the DailyEquityCalc script.
    """
    equity_calc_main()
    logger.success("Instruments aggregated successfully.")


if __name__ == "__main__":
    main()
