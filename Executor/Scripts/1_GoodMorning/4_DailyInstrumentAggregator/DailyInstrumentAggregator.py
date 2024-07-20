import os, sys

from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)


# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


def main():
    """
    The main function is responsible for importing and executing the instrument aggregation process.
    It performs the following steps:
    1. Dynamically imports the `instrument_aggregator` function from the `InstrumentAggregator` module.
    2. Executes the `instrument_aggregator` function to perform the aggregation of instruments.
    3. Logs a success message upon successful aggregation of instruments.
    """
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentAggregator.InstrumentAggregator import (
        aggregate_ins as instrument_aggregator,
    )

    instrument_aggregator()
    logger.success("Instruments aggregated successfully.")


if __name__ == "__main__":
    main()
