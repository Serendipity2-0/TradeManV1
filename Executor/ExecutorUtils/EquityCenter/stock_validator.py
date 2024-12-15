import os
import datetime as dt
import pandas as pd
from time import sleep
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeUtils import holidays
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
    Instrument as instrument_obj,
)

logger = LoggerSetup()

class StockValidator:
    """
    A class for validating stock-related operations.
    
    This class provides methods for validating stocks, checking market conditions,
    and ensuring trading rules are followed.
    """

    def __init__(self):
        """Initialize StockValidator."""
        self.asm_gsm_list_dir = os.getenv("ASM_GSM_LIST_DIR", "Data/AsmGsmList")

    @staticmethod
    def get_asm_gsm_list() -> List[str]:
        """
        Get the ASM/GSM list from the database.

        Returns:
            list: The ASM/GSM list
        """
        try:
            today = dt.datetime.now().strftime("%Y-%m-%d")
            asm_gsm_list_path = os.path.join("Data/AsmGsmList", f"merged_asm_gsm_{today}.csv")
            if not os.path.exists(asm_gsm_list_path):
                logger.warning(f"ASM/GSM list file not found: {asm_gsm_list_path}")
                return []
                
            asm_gsm_list = pd.read_csv(asm_gsm_list_path)
            return asm_gsm_list["SYMBOL"].tolist()
        except Exception as e:
            logger.error(f"Error while getting ASM/GSM list: {e}")
            return []

    @staticmethod
    def check_symbol_in_list(symbol_list: List[str], symbol: str) -> bool:
        """
        Check if a symbol is in a list (case-insensitive).

        Args:
            symbol_list: List of symbols
            symbol: Symbol to check

        Returns:
            bool: True if symbol is in list
        """
        symbol_list = [s.upper() for s in symbol_list]
        symbol = symbol.upper()
        return symbol in symbol_list or symbol.split("-")[0] in symbol_list

    @staticmethod
    def check_symbol_for_errors(
        symbol: str, 
        exchange_token: str, 
        holdings_symbol_list: Optional[List[str]] = None
    ) -> bool:
        """
        Check if a symbol has any errors that would prevent trading.

        Args:
            symbol: Symbol to check
            exchange_token: Exchange token for the symbol
            holdings_symbol_list: List of symbols in holdings

        Returns:
            bool: True if symbol passes all checks
        """
        try:
            if holdings_symbol_list is not None:
                if StockValidator.check_symbol_in_list(holdings_symbol_list, symbol):
                    logger.debug(f"{symbol} is already in holdings, skipping")
                    return False

            if StockValidator.check_symbol_in_list(StockValidator.get_asm_gsm_list(), symbol):
                logger.debug(f"{symbol} is in ASM/GSM list, skipping")
                return False

            if exchange_token is None:
                logger.debug(f"Exchange token not found for {symbol}, skipping")
                return False

            return True
        except Exception as e:
            logger.error(f"Error while checking symbol for errors: {e}")
            return False

    @staticmethod
    def is_today_holiday() -> bool:
        """
        Check if today is a market holiday.

        Returns:
            bool: True if today is a holiday
        """
        return dt.datetime.now().date() in holidays

    @staticmethod
    def should_wait_for_start_time(desired_start_time_str: str) -> bool:
        """
        Check if we should wait for market start time.

        Args:
            desired_start_time_str: Desired start time in "HH:MM:SS" format

        Returns:
            bool: True if we should wait
        """
        now = dt.datetime.now()
        start_hour, start_minute, _ = map(int, desired_start_time_str.split(":"))
        
        if now.time() < dt.time(9, 0):
            logger.info("Time is before 9:00 AM, Waiting to execute.")
            return True
            
        wait_time = (
            dt.datetime(now.year, now.month, now.day, start_hour, start_minute) - now
        )
        if wait_time.total_seconds() > 0:
            logger.info(f"Waiting for {wait_time} before starting the bot")
            sleep(wait_time.total_seconds())
            return True
            
        return False
