import os
import sys

DIR = os.getcwd()
sys.path.append(DIR)

import Executor.NSEStrategies.Equity.EquityStopLoss.EquityStopLoss as StopLoss


def main():
    StopLoss.main()


if __name__ == "__main__":
    main()
