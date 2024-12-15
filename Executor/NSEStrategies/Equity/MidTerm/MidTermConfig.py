import os
from dotenv import load_dotenv
from Executor.NSEStrategies.NSEStrategiesUtil import StrategyBase

# Set up directory and load environment variables
DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

# Initialize strategy object
midterm_obj = StrategyBase.load_from_db("MidTerm")

# Strategy configuration
strategy_name = midterm_obj.StrategyName
order_type = midterm_obj.GeneralParams.OrderType
product_type = midterm_obj.GeneralParams.ProductType
strategy_type = midterm_obj.GeneralParams.StrategyType
desired_start_time_str = midterm_obj.EntryParams.EntryTime  # Fixed: Direct access to EntryParams
midterm_prefix = midterm_obj.StrategyPrefix
num_stocks = midterm_obj.ExtraInformation.StocksPerStrategy
transaction_type = midterm_obj.GeneralParams.TransactionType

# Strategy constants
MID_TFMOMENTUM = "Mid_tfMomentum"
MID_TFEMA = "Mid_tfEma"

# TFMomentum parameters
TFMOMENTUM_SMA_VALUE = midterm_obj.ExtraInformation.TFMomentumSMAValue
TFMOMENTUM_RSI_UPPER_THRESHOLD = midterm_obj.ExtraInformation.TFMomentumRSIUpperThreshold
TFMOMENTUM_RSI_LOWER_THRESHOLD = midterm_obj.ExtraInformation.TFMomentumRSILowerThreshold
TFMOMENTUM_GROSS_PROFIT_GROWTH = midterm_obj.ExtraInformation.TFMomentumGrossProfitGrowth
TFMOMENTUM_NET_INCOME = midterm_obj.ExtraInformation.TFMomentumNetIncome
TFMOMENTUM_TOTAL_REVENUE = midterm_obj.ExtraInformation.TFMomentumTotalRevenue
TFMOMENTUM_EMA_THRESHOLD = midterm_obj.ExtraInformation.TFMomentumEMAThreshold

# TFEMA parameters
TFEMA_SHORT_EMA_VALUE = midterm_obj.ExtraInformation.TFEMAShortValue
TFEMA_SMALL_EMA_VALUE = midterm_obj.ExtraInformation.TFEMASmallValue
TFEMA_MEDIUM_EMA_VALUE = midterm_obj.ExtraInformation.TFEMAMediumValue
TFEMA_LARGE_EMA_VALUE = midterm_obj.ExtraInformation.TFEMALargeValue
TFEMA_SMA_VALUE = midterm_obj.ExtraInformation.TFEMASMAValue
TFEMA_RSI_UPPER_THRESHOLD = midterm_obj.ExtraInformation.TFEMARSIUpperThreshold
TFEMA_MARKET_CAP_THRESHOLD = midterm_obj.ExtraInformation.TFEMAMarketCapThreshold
TFEMA_VOLUME_MULTIPLIER = midterm_obj.ExtraInformation.TFEMAVolumeMultiplier
TFEMA_ROE_THRESHOLD = midterm_obj.ExtraInformation.TFEMAROEThreshold

# Environment variables
TRADE_MODE = os.getenv("TRADE_MODE")
STRATEGIES_DB = os.getenv("MONGO_STRATEGY_COLLECTION", "strategies")
EQUITY_STOCK_DATA_DB_PATH = os.getenv("EQUITY_STOCK_DATA_DB_PATH")
FINANCIAL_DB_PATH = os.getenv("FINANCIAL_DB_PATH")
TODAY_STOCK_DATA_DB_PATH = os.getenv("TODAY_STOCK_DATA_DB_PATH")
