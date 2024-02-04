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



from Executor.ExecutorUtils.InstrumentCenter.DailyInstrumentAggregator.DailyInstrumentAggregator import (
    main as instrument_aggregator,
)

instrument_aggregator()
