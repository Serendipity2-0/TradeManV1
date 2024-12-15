"""
Utility module for Last Traded Price (LTP) related functions.
This module is separated to avoid circular imports in the codebase.
"""

import os
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

def get_single_ltp(kite_token=None, exchange_token=None, segment=None):
    """
    Get the last traded price (LTP) for a given kite token or exchange token.

    Args:
        kite_token (str, optional): The kite token of the instrument. Defaults to None.
        exchange_token (str, optional): The exchange token of the instrument. Defaults to None.
        segment (str, optional): The market segment of the instrument. Defaults to None.

    Returns:
        float: The last traded price of the instrument.
    """
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import get_primary_account_obj
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument

    primary_broker = os.getenv("PRIMARY_BROKER")
    kite = get_primary_account_obj(primary_broker)
    try:
        if exchange_token:
            if segment:
                kite_token = Instrument().get_kite_token_by_exchange_token(
                    exchange_token, segment
                )
            else:
                kite_token = Instrument().get_kite_token_by_exchange_token(
                    exchange_token
                )
            ltp = kite.ltp(kite_token)
            return ltp[str(kite_token)]["last_price"]
        else:
            ltp = kite.ltp(kite_token)
            return ltp[str(kite_token)]["last_price"]
    except Exception as e:
        logger.error(f"An error occurred while fetching LTP: {e}")
        return 10.0
