import os, sys

from dotenv import load_dotenv
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)


# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from loguru import logger

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


def main():
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentAggregator.InstrumentAggregator import (
        aggregate_ins as instrument_aggregator,
    )

    instrument_aggregator()

if __name__ == "__main__":
    main()