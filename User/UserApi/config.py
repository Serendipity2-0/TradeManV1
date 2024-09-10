from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import os
import ast


class TrademanSettings(BaseSettings):
    # Main
    TRADE_MODE: str = Field(..., env="TRADE_MODE")
    ACC_DIFF_TOLERANCE: float = Field(..., env="ACC_DIFF_TOLERANCE")
    DERIVATIVES_STRATEGY_LIST: str = Field(..., env="DERIVATIVES_STRATEGY_LIST")
    EQUITY_STRATEGY_LIST: str = Field(..., env="EQUITY_STRATEGY_LIST")
    SUPPORTED_BROKERS: str = Field(..., env="SUPPORTED_BROKERS")

    # Firebase Cred
    FIREBASE_CRED_PATH: str = Field(..., env="FIREBASE_CRED_PATH")
    FIREBASE_DATABASE_URL: str = Field(..., env="FIREBASE_DATABASE_URL")
    FIREBASE_USER_COLLECTION: str = Field(..., env="FIREBASE_USER_COLLECTION")
    FIREBASE_STRATEGY_COLLECTION: str = Field(..., env="FIREBASE_STRATEGY_COLLECTION")
    MARKET_INFO_FB_COLLECTION: str = Field(..., env="MARKET_INFO_FB_COLLECTION")
    FIREBASE_ADMIN_COLLECTION: str = Field(..., env="FIREBASE_ADMIN_COLLECTION")

    # Conda Env
    CONDA_PATH: str = Field(..., env="CONDA_PATH")
    CONDA_ENV_NAME: str = Field(..., env="CONDA_ENV_NAME")
    PROJECT_PATH: str = Field(..., env="PROJECT_PATH")
    PYTHON_ENV_PATH: str = Field(..., env="PYTHON_ENV_PATH")

    # Broker
    ZERODHA_BROKER: str = Field(..., env="ZERODHA_BROKER")
    ALICEBLUE_BROKER: str = Field(..., env="ALICEBLUE_BROKER")
    FIRSTOCK_BROKER: str = Field(..., env="FIRSTOCK_BROKER")
    PRIMARY_BROKER: str = Field(..., env="PRIMARY_BROKER")

    # Trading Filepaths
    SQLITE_INS_PATH: str = Field(..., env="SQLITE_INS_PATH")
    FNO_INFO_PATH: str = Field(..., env="FNO_INFO_PATH")
    ASM_GSM_LIST_DIR: str = Field(..., env="ASM_GSM_LIST_DIR")

    # URL
    TICKERS_URL: str = Field(..., env="TICKERS_URL")

    # DB Related
    USR_TRADELOG_DB_FOLDER: str = Field(..., env="USR_TRADELOG_DB_FOLDER")
    USR_TRADELOG_EQUITY_DB_FOLDER: str = Field(..., env="USR_TRADELOG_EQUITY_DB_FOLDER")
    USR_TRADELOG_DERIVATIVES_DB_FOLDER: str = Field(
        ..., env="USR_TRADELOG_DERIVATIVES_DB_FOLDER"
    )
    EQUITY_SIGNAL_DB_PATH: str = Field(..., env="EQUITY_SIGNAL_DB_PATH")
    DERIVATIVES_SIGNAL_DB_PATH: str = Field(..., env="DERIVATIVES_SIGNAL_DB_PATH")
    FINANCIAL_DB_PATH: str = Field(..., env="FINANCIAL_DB_PATH")
    EQUITY_STOCK_DATA_DB_PATH: str = Field(..., env="EQUITY_STOCK_DATA_DB_PATH")
    TODAY_STOCK_DATA_DB_PATH: str = Field(..., env="TODAY_STOCK_DATA_DB_PATH")

    # Error and Log Paths
    ERROR_LOG_PATH: str = Field(..., env="ERROR_LOG_PATH")
    CONSOLIDATED_REPORT_PATH: str = Field(..., env="CONSOLIDATED_REPORT_PATH")
    ERROR_LOG_CSV_PATH: str = Field(..., env="ERROR_LOG_CSV_PATH")
    PARAMS_UPDATE_LOG_CSV_PATH: str = Field(..., env="PARAMS_UPDATE_LOG_CSV_PATH")
    CELERY_SCRIPTS_LOG_PATH: str = Field(..., env="CELERY_SCRIPTS_LOG_PATH")
    EOD_JSON_DIR: str = Field(..., env="EOD_JSON_DIR")

    # Discord Related
    DISCORD_BOT_TOKEN: str = Field(..., env="DISCORD_BOT_TOKEN")
    ADMIN_CHANNEL_ID: str = Field(..., env="ADMIN_CHANNEL_ID")
    AMIPY_CHANNEL_ID: str = Field(..., env="AMIPY_CHANNEL_ID")
    EXPIRYTRADER_CHANNEL_ID: str = Field(..., env="EXPIRYTRADER_CHANNEL_ID")
    MPWIZARD_CHANNEL_ID: str = Field(..., env="MPWIZARD_CHANNEL_ID")
    GOLDENCOIN_CHANNEL_ID: str = Field(..., env="GOLDENCOIN_CHANNEL_ID")
    NAMAHA_CHANNEL_ID: str = Field(..., env="NAMAHA_CHANNEL_ID")
    OM_CHANNEL_ID: str = Field(..., env="OM_CHANNEL_ID")
    OVERNIGHTFUTURES_CHANNEL_ID: str = Field(..., env="OVERNIGHTFUTURES_CHANNEL_ID")
    PYSTOCKS_CHANNEL_ID: str = Field(..., env="PYSTOCKS_CHANNEL_ID")
    DB_CHANNEL_ID: str = Field(..., env="DB_CHANNEL_ID")
    SHORTTERM_CHANNEL_ID: str = Field(..., env="SHORTTERM_CHANNEL_ID")
    MIDTERM_CHANNEL_ID: str = Field(..., env="MIDTERM_CHANNEL_ID")
    LONGTERM_CHANNEL_ID: str = Field(..., env="LONGTERM_CHANNEL_ID")

    # Telegram Related
    TELETHON_API_ID: str = Field(..., env="TELETHON_API_ID")
    TELETHON_API_HASH: str = Field(..., env="TELETHON_API_HASH")
    ERROR_TELEGRAM_BOT_TOKEN: str = Field(..., env="ERROR_TELEGRAM_BOT_TOKEN")
    ERROR_CHAT_ID: str = Field(..., env="ERROR_CHAT_ID")
    TELEGRAM_REPORT_GROUP_ID: str = Field(..., env="TELEGRAM_REPORT_GROUP_ID")

    # DB configs
    DB_USER: str = Field(..., env="DB_USER")
    DB_PASSWORD: str = Field(..., env="DB_PASSWORD")
    DB_HOST: str = Field(..., env="DB_HOST")
    DB_PORT: str = Field(..., env="DB_PORT")
    DB_NAME: str = Field(..., env="DB_NAME")

    class Config:
        # Construct the full path to trademan.env
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "trademan.env"
        )
        env_file_encoding = "utf-8"

    @field_validator(
        "DERIVATIVES_STRATEGY_LIST",
        "EQUITY_STRATEGY_LIST",
        "SUPPORTED_BROKERS",
        mode="after",
    )
    @classmethod
    def parse_list(cls, value: str) -> List[str]:
        try:
            return ast.literal_eval(value)
        except:
            return value.split(",") if value else []


@lru_cache()
def get_trademan_settings() -> TrademanSettings:
    return TrademanSettings()


settings = get_trademan_settings()
