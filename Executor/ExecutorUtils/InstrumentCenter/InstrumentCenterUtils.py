import pandas as pd
import os, sys
from dotenv import load_dotenv
from datetime import datetime
from calendar import monthrange
from datetime import timedelta  # Importing the missing timedelta
from kiteconnect import KiteConnect

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as BrokerCenterUtils
import Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter as exesql_adapter

ins_db_path = os.getenv("SQLITE_INS_PATH")
logger = LoggerSetup()


def get_ins_df():
    """
    Retrieve the instrument data from the SQLite database and return it as a DataFrame.

    Returns:
        pd.DataFrame: The instrument data as a pandas DataFrame.
    """
    try:
        conn = exesql_adapter.get_db_connection(ins_db_path)
        data = pd.read_sql_query("select * from instrument_master", conn)
        # data to dataframe
        ins_df = pd.DataFrame(data)
        return ins_df
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None


class Instrument:
    _dataframe = get_ins_df()

    def __init__(self):
        self._dataframe = Instrument._dataframe
        self._instrument_token = None
        self._exchange_token = None

    def _filter_data(self, base_symbol, option_type, strike_price, expiry=None):
        """Filter the dataframe based on the given criteria.

        Args:
            base_symbol (str): The base symbol of the instrument.
            option_type (str): The type of the option (e.g., "CE" or "PE").
            strike_price (float): The strike price of the option.
            expiry (str, optional): The expiry date of the option. Defaults to None.

        Returns:
            pd.DataFrame: The filtered DataFrame.
        """
        criteria = (
            (self._dataframe["name"] == base_symbol)
            & (self._dataframe["instrument_type"] == option_type)
            & (self._dataframe["strike"] == strike_price)
        )
        if expiry:
            criteria &= self._dataframe["expiry"] == expiry
        return self._dataframe[criteria].sort_values(by="expiry")

    def _filter_data_by_exchange_token(self, exchange_token):
        """Filter the dataframe based on the given exchange token.

        Args:
            exchange_token (str): The exchange token of the instrument.

        Returns:
            pd.DataFrame: The filtered DataFrame.
        """
        return self._dataframe[self._dataframe["exchange_token"] == exchange_token]

    def _get_monthly_expiries(self, filtered_data, option_type):
        """Identify and return monthly expiry dates from the filtered data.

        Args:
            filtered_data (pd.DataFrame): The filtered DataFrame containing instrument data.
            option_type (str): The type of the option (e.g., "FUT", "CE", "PE").

        Returns:
            list: A list of monthly expiry dates.
        """
        monthly_expiries = []
        if option_type == "FUT":  # Only consider as monthly expiry for FUT type
            for expiry in filtered_data["expiry"].unique():
                expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
                if expiry_date.day > (
                    monthrange(expiry_date.year, expiry_date.month)[1] - 7
                ):
                    monthly_expiries.append(expiry)
        return monthly_expiries

    def _get_last_weekly_expiry(self, weekly_expiries, target_month):
        """Return the last weekly expiry of the target month.

        Args:
            weekly_expiries (list): A list of weekly expiry dates.
            target_month (int): The target month.

        Returns:
            str: The last weekly expiry date of the target month.
        """
        return max(
            [
                expiry
                for expiry in weekly_expiries
                if datetime.strptime(expiry, "%Y-%m-%d").date().month == target_month
            ]
        )

    def weekly_expiry_type(self):
        """
        Determine the weekly expiry type based on the current day of the week.

        Returns:
            str: "next_week" if today is Thursday, otherwise "current_week".
        """
        if datetime.today().weekday() == 3:
            weekly_expiry_type = "next_week"
        else:
            weekly_expiry_type = "current_week"
        return weekly_expiry_type

    def monthly_expiry_type(self):
        """
        Determine the monthly expiry type based on the current date.

        Returns:
            str: "next_month" if today is the last Thursday of the month, otherwise "current_month".
        """
        today = datetime.now().date()
        # Find the last day of the current month
        next_month = today.replace(day=28) + timedelta(days=4)
        last_day_of_current_month = next_month - timedelta(days=next_month.day)

        # Find the last Thursday of the current month
        last_thursday_of_current_month = last_day_of_current_month
        while last_thursday_of_current_month.weekday() != 3:
            last_thursday_of_current_month -= timedelta(days=1)

        # If today is the last Thursday of the current month
        if today == last_thursday_of_current_month:
            return "next_month"
        # If today is before the last Thursday of the current month
        elif today < last_thursday_of_current_month:
            return "current_month"
        # If today is after the last Thursday of the current month
        else:
            # If today is still within the current month
            if today <= last_day_of_current_month:
                return "current_month"
            # If we have moved into a new month
            else:
                return "next_month"

    def get_expiry_by_criteria(
        self, base_symbol, strike_price, option_type, expiry_type="current_week"
    ):
        """
        Get the expiry date based on the given criteria.

        Args:
            base_symbol (str): The base symbol of the instrument.
            strike_price (float): The strike price of the option.
            option_type (str): The type of the option (e.g., "FUT", "CE", "PE").
            expiry_type (str, optional): The type of expiry ("current_week", "next_week", "current_month", "next_month"). Defaults to "current_week".

        Returns:
            str: The expiry date matching the criteria.
        """
        filtered_data = self._filter_data(base_symbol, option_type, strike_price)
        today = datetime.now().date()
        future_expiries = filtered_data[
            filtered_data["expiry"].apply(
                lambda x: datetime.strptime(x, "%Y-%m-%d").date()
            )
            >= today
        ]["expiry"].tolist()
        monthly_expiries = self._get_monthly_expiries(filtered_data, option_type)
        # Exclude monthly expiries to get the list of weekly expiries
        weekly_expiries = [
            expiry for expiry in future_expiries if expiry not in monthly_expiries
        ]

        # Define strategy dictionary with safety checks for list indices
        expiry_strategies = {
            "current_week": lambda: weekly_expiries[0] if weekly_expiries else None,
            "next_week": lambda: (
                weekly_expiries[1] if len(weekly_expiries) > 1 else None
            ),
            "current_month": lambda: (
                monthly_expiries[0]
                if monthly_expiries
                else self._get_last_weekly_expiry(weekly_expiries, today.month)
            ),
            "next_month": lambda: (
                monthly_expiries[1]
                if len(monthly_expiries) > 1
                else self._get_last_weekly_expiry(
                    weekly_expiries, (today + timedelta(days=30)).month
                )
            ),
        }

        # If FUT with strike price 0, override to only consider monthly expiries
        if option_type == "FUT" and strike_price == 0:
            expiry_strategies = {
                "current_month": lambda: (
                    monthly_expiries[0] if monthly_expiries else None
                ),
                "next_month": lambda: (
                    monthly_expiries[1] if len(monthly_expiries) > 1 else None
                ),
            }
        return expiry_strategies[expiry_type]()

    def get_exchange_token_by_criteria(
        self, base_symbol, strike_price, option_type, expiry
    ):
        """
        Get the exchange token based on the given criteria.

        Args:
            base_symbol (str): The base symbol of the instrument.
            strike_price (float): The strike price of the option.
            option_type (str): The type of the option (e.g., "FUT", "CE", "PE").
            expiry (str): The expiry date of the option.

        Returns:
            str: The exchange token matching the criteria.
        """
        filtered_data = self._filter_data(
            base_symbol, option_type, strike_price, expiry
        )
        if not filtered_data.empty:
            return filtered_data.iloc[0]["exchange_token"]
        else:
            return None

    def get_kite_token_by_exchange_token(self, exchange_token, segment=None):
        """
        Get the kite token based on the exchange token.

        Args:
            exchange_token (str): The exchange token of the instrument.
            segment (str, optional): The market segment of the instrument. Defaults to None.

        Returns:
            int: The kite token matching the criteria.
        """
        filtered_data = self._filter_data_by_exchange_token(exchange_token)
        if not filtered_data.empty:
            if segment:
                filtered_data = filtered_data[filtered_data["segment"] == segment]
                return int(filtered_data.iloc[0]["instrument_token"])
            return int(filtered_data.iloc[0]["instrument_token"])
        else:
            return None

    def get_lot_size_by_exchange_token(self, exchange_token):
        """
        Get the lot size based on the exchange token.

        Args:
            exchange_token (str): The exchange token of the instrument.

        Returns:
            int: The lot size matching the criteria.
        """
        filtered_data = self._filter_data_by_exchange_token(exchange_token)
        if not filtered_data.empty:
            return filtered_data.iloc[0]["lot_size"]
        else:
            return None

    def get_trading_symbol_by_exchange_token(self, exchange_token: str, exchange=None):
        """
        Get the trading symbol based on the exchange token.

        Args:
            exchange_token (str): The exchange token of the instrument.
            exchange (str, optional): The exchange of the instrument. Defaults to None.

        Returns:
            str: The trading symbol matching the criteria.
        """
        if exchange:
            filtered_data = self._filter_data_by_exchange_token(exchange_token)
            filtered_data = filtered_data[filtered_data["exchange"] == exchange]
            filtered_data = filtered_data[filtered_data["exchange"] != "CDS"]
            return filtered_data.iloc[0]["Symbol"]
        filtered_data = self._filter_data_by_exchange_token(exchange_token)
        if not filtered_data.empty:
            return filtered_data.iloc[0]["Symbol"]
        else:
            return None

    def get_full_format_trading_symbol_by_exchange_token(
        self, exchange_token: str, segment=None
    ):
        """
        Get the full format trading symbol based on the exchange token.

        Args:
            exchange_token (str): The exchange token of the instrument.
            segment (str, optional): The market segment of the instrument. Defaults to None.

        Returns:
            str: The full format trading symbol matching the criteria.
        """
        if segment:
            filtered_data = self._filter_data_by_exchange_token(exchange_token)
            filtered_data = filtered_data[filtered_data["segment"] == segment]
            return filtered_data.iloc[0]["Trading Symbol"]
        filtered_data = self._filter_data_by_exchange_token(exchange_token)
        if not filtered_data.empty:
            return filtered_data.iloc[0]["Trading Symbol"]
        else:
            return None

    def get_base_symbol_by_exchange_token(self, exchange_token):
        """
        Get the base symbol based on the exchange token.

        Args:
            exchange_token (str): The exchange token of the instrument.

        Returns:
            str: The base symbol matching the criteria.
        """
        filtered_data = self._filter_data_by_exchange_token(exchange_token)
        if not filtered_data.empty:
            return filtered_data.iloc[0]["name"]
        else:
            return None

    def get_exchange_by_exchange_token(self, exchange_token):
        """
        Get the exchange based on the exchange token.

        Args:
            exchange_token (str): The exchange token of the instrument.

        Returns:
            str: The exchange matching the criteria.
        """
        filtered_data = self._filter_data_by_exchange_token(exchange_token)
        # Remove CDS from the list of segments
        filtered_data = filtered_data[filtered_data["exchange"] != "CDS"]
        if not filtered_data.empty:
            return filtered_data.iloc[0]["exchange"]
        else:
            return None

    def _filter_data_by_token(self, token):
        """Filter the dataframe based on the given instrument token.

        Args:
            token (str): The instrument token of the instrument.

        Returns:
            pd.DataFrame: The filtered DataFrame.
        """
        return self._dataframe[self._dataframe["instrument_token"] == token]

    def get_exchange_token_by_token(self, token):
        """
        Get the exchange token based on the instrument token.

        Args:
            token (str): The instrument token of the instrument.

        Returns:
            str: The exchange token matching the criteria.
        """
        filtered_data = self._filter_data_by_token(token)
        if not filtered_data.empty:
            return filtered_data.iloc[0]["exchange_token"]
        else:
            return None

    def _filter_data_by_name(self, name):
        """Filter the dataframe based on the given instrument name.

        Args:
            name (str): The name of the instrument.

        Returns:
            pd.DataFrame: The filtered DataFrame.
        """
        return self._dataframe[self._dataframe["Symbol"] == name]

    def get_exchange_token_by_name(self, name, segment=None):
        """
        Get the exchange token based on the instrument name.

        Args:
            name (str): The name of the instrument.
            segment (str, optional): The market segment of the instrument. Defaults to None.

        Returns:
            str: The exchange token matching the criteria.
        """
        if segment:
            filtered_data = self._filter_data_by_name(name)
            filtered_data = filtered_data[filtered_data["segment"] == segment]
            return filtered_data.iloc[0]["exchange_token"]
        elif segment is None:
            filtered_data = self._filter_data_by_name(name)
            return filtered_data.iloc[0]["exchange_token"]
        else:
            return None

    def get_instrument_type_by_exchange_token(self, exchange_token):
        """
        Get the instrument type based on the exchange token.

        Args:
            exchange_token (str): The exchange token of the instrument.

        Returns:
            str: The instrument type matching the criteria.
        """
        filtered_data = self._filter_data_by_exchange_token(exchange_token)
        if not filtered_data.empty:
            return filtered_data.iloc[0]["instrument_type"]
        else:
            return None

    def get_token_by_name(self, name):
        """
        Get the instrument token based on the instrument name.

        Args:
            name (str): The name of the instrument.

        Returns:
            str: The instrument token matching the criteria.
        """
        filtered_data = self._filter_data_by_name(name)
        if not filtered_data.empty:
            return filtered_data.iloc[0]["instrument_token"]
        else:
            return None

    def get_symbols_with_expiry_today(self, segment, symbols_list):
        """
        Filters symbols with expiry today for a given segment and symbols list.

        Parameters:
        segment (str): The market segment to filter.
        symbols_list (list): List of symbols to filter.

        Returns:
        list: A list of unique symbols with expiry today.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            # Filter the dataframe for the given segment, where expiry is today, and for the specified symbols
            specific_symbols_today_expiry = self._dataframe[
                (self._dataframe["segment"] == segment)
                & (self._dataframe["expiry"] == today)
                & (self._dataframe["name"].isin(symbols_list))
            ][
                "name"
            ]  # Get base symbols

            # Drop duplicate base symbols and return
            return specific_symbols_today_expiry.drop_duplicates().tolist()
        except KeyError as e:
            # Handle cases where columns might not exist in the dataframe
            logger.error(f"Column not found in the dataframe: {e}")
            return None
        except Exception as e:
            # Handle any other exceptions
            logger.error(f"An error occurred: {e}")
            return None

    def fetch_base_symbol_token(self, base_symbol):
        """
        Get the token for a given base symbol.

        Args:
            base_symbol (str): The base symbol of the instrument.

        Returns:
            str: The token matching the base symbol, or a default message if not found.
        """
        # Mapping of base symbols to their tokens
        symbol_to_token = {
            "MIDCPNIFTY": "288009",
            "FINNIFTY": "257801",
            "BANKNIFTY": "260105",
            "NIFTY": "256265",
            "SENSEX": "265",
        }
        # Return the token for the given base symbol, or a default message if not found
        return symbol_to_token.get(base_symbol, "No token found for given symbol")

    def get_margin_multiplier(self, trading_symbol):
        """
        Get the margin multiplier for a given trading symbol.

        Args:
            trading_symbol (str): The trading symbol of the instrument.

        Returns:
            int: The margin multiplier for the trading symbol.
        """
        # TODO: Remove this hardcoding and fetch from API
        return 546


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
    zerodha_primary = os.getenv("ZERODHA_PRIMARY_ACCOUNT")
    primary_account_session_id = BrokerCenterUtils.fetch_primary_accounts_from_firebase(
        zerodha_primary
    )
    kite = KiteConnect(api_key=primary_account_session_id["Broker"]["ApiKey"])
    kite.set_access_token(
        access_token=primary_account_session_id["Broker"]["SessionId"]
    )

    if exchange_token:
        if segment:
            kite_token = Instrument().get_kite_token_by_exchange_token(
                exchange_token, segment
            )
        else:
            kite_token = Instrument().get_kite_token_by_exchange_token(exchange_token)
        ltp = kite.ltp(kite_token)
        return ltp[str(kite_token)]["last_price"]
    else:
        ltp = kite.ltp(kite_token)
        return ltp[str(kite_token)]["last_price"]


def get_single_quote(kite_token=None, exchange_token=None, segment=None):
    """
    Get the last traded price (LTP) for a given kite token or exchange token using the quote method.

    Args:
        kite_token (str, optional): The kite token of the instrument. Defaults to None.
        exchange_token (str, optional): The exchange token of the instrument. Defaults to None.
        segment (str, optional): The market segment of the instrument. Defaults to None.

    Returns:
        float: The last traded price of the instrument from the quote method.
    """
    zerodha_primary = os.getenv("ZERODHA_PRIMARY_ACCOUNT")
    primary_account_session_id = BrokerCenterUtils.fetch_primary_accounts_from_firebase(
        zerodha_primary
    )
    kite = KiteConnect(api_key=primary_account_session_id["Broker"]["ApiKey"])
    kite.set_access_token(
        access_token=primary_account_session_id["Broker"]["SessionId"]
    )

    if exchange_token:
        if segment:
            kite_token = Instrument().get_kite_token_by_exchange_token(
                exchange_token, segment
            )
        else:
            kite_token = Instrument().get_kite_token_by_exchange_token(exchange_token)
        quote = kite.quote(kite_token)
        return quote[str(kite_token)]["last_price"]
    else:
        quote = kite.quote(kite_token)
        return quote[str(kite_token)]["last_price"]
