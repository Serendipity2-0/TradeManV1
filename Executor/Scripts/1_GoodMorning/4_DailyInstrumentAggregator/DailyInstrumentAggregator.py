import os,sys

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from Executor.ExecutorUtils.InstrumentCenter.DailyInstrumentAggregator.DailyInstrumentAggregator import main as instrument_aggregator

instrument_aggregator()