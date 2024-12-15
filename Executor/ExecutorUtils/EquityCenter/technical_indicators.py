import pandas as pd
import numpy as np
from typing import Tuple, Optional
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

class TechnicalIndicators:
    """
    A class containing methods for calculating various technical indicators.
    
    This class provides a comprehensive set of technical analysis tools for
    analyzing stock market data.
    """

    @staticmethod
    def calculate_sma(data: pd.Series, window: int = 20) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA).

        Args:
            data (pd.Series): Price data
            window (int): Window size for calculation

        Returns:
            pd.Series: SMA values
        """
        return data.rolling(window=window).mean()

    @staticmethod
    def calculate_ema(data: pd.Series, window: int) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA).

        Args:
            data (pd.Series): Price data
            window (int): Window size for calculation

        Returns:
            pd.Series: EMA values
        """
        return data.ewm(span=window, adjust=False).mean()

    @staticmethod
    def indicator_5ema(stock_data: pd.DataFrame) -> pd.Series:
        """
        Calculate the 5-period Exponential Moving Average (EMA).

        Args:
            stock_data (DataFrame): The stock data

        Returns:
            Series: 5-period EMA values
        """
        try:
            return stock_data["Close"].ewm(span=5, min_periods=0, adjust=False).mean()
        except Exception as e:
            logger.error(f"Error calculating 5 EMA: {e}")
            return pd.Series()

    @staticmethod
    def indicator_13ema(stock_data: pd.DataFrame) -> pd.Series:
        """
        Calculate the 13-period Exponential Moving Average (EMA).

        Args:
            stock_data (DataFrame): The stock data

        Returns:
            Series: 13-period EMA values
        """
        try:
            return stock_data["Close"].ewm(span=13, min_periods=0, adjust=False).mean()
        except Exception as e:
            logger.error(f"Error calculating 13 EMA: {e}")
            return pd.Series()

    @staticmethod
    def indicator_26ema(stock_data: pd.DataFrame) -> pd.Series:
        """
        Calculate the 26-period Exponential Moving Average (EMA).

        Args:
            stock_data (DataFrame): The stock data

        Returns:
            Series: 26-period EMA values
        """
        try:
            return stock_data["Close"].ewm(span=26, min_periods=0, adjust=False).mean()
        except Exception as e:
            logger.error(f"Error calculating 26 EMA: {e}")
            return pd.Series()

    @staticmethod
    def indicator_50ema(stock_data: pd.DataFrame) -> pd.Series:
        """
        Calculate the 50-period Exponential Moving Average (EMA).

        Args:
            stock_data (DataFrame): The stock data

        Returns:
            Series: 50-period EMA values
        """
        try:
            return stock_data["Close"].ewm(span=50, min_periods=0, adjust=False).mean()
        except Exception as e:
            logger.error(f"Error calculating 50 EMA: {e}")
            return pd.Series()

    @staticmethod
    def indicator_rsi(data: pd.DataFrame, rsi_length: int, rsi_source: str) -> pd.Series:
        """
        Calculate the Relative Strength Index (RSI).

        Args:
            data (DataFrame): The stock data
            rsi_length (int): The period for calculating RSI
            rsi_source (str): The source column for RSI calculation

        Returns:
            Series: RSI values
        """
        try:
            delta = data[rsi_source].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            avg_gain = gain.rolling(window=rsi_length).mean()
            avg_loss = loss.rolling(window=rsi_length).mean()

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return pd.Series()

    @staticmethod
    def indicator_bollinger_bands(data: pd.DataFrame, window: int) -> pd.DataFrame:
        """
        Calculate the Bollinger Bands.

        Args:
            data (DataFrame): The stock data
            window (int): The period for calculation

        Returns:
            DataFrame: DataFrame with Bollinger Bands columns added
        """
        try:
            data = data.copy()
            data["MA"] = data["Close"].rolling(window=window).mean()
            data["Std_dev"] = data["Close"].rolling(window=window).std()
            data["Upper_band"] = data["MA"] + (data["Std_dev"] * 2)
            data["Lower_band"] = data["MA"] - (data["Std_dev"] * 2)
            return data
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return data

    @staticmethod
    def indicator_macd(
        data: pd.DataFrame, 
        fast_length: int = 12, 
        slow_length: int = 26, 
        signal_length: int = 9
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate the Moving Average Convergence Divergence (MACD).

        Args:
            data (DataFrame): The stock data
            fast_length (int): The period for the fast EMA
            slow_length (int): The period for the slow EMA
            signal_length (int): The period for the signal line

        Returns:
            tuple: (MACD line, Signal line)
        """
        try:
            data = data.copy()
            data["EMA_fast"] = data["Close"].ewm(span=fast_length, adjust=False).mean()
            data["EMA_slow"] = data["Close"].ewm(span=slow_length, adjust=False).mean()
            data["MACD"] = data["EMA_fast"] - data["EMA_slow"]
            data["Signal_line"] = data["MACD"].ewm(span=signal_length, adjust=False).mean()
            return data["MACD"], data["Signal_line"]
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return pd.Series(), pd.Series()

    @staticmethod
    def indicator_atr(stock_data: pd.DataFrame, window: int) -> pd.Series:
        """
        Calculate the Average True Range (ATR).

        Args:
            stock_data (DataFrame): The stock data
            window (int): The period for calculation

        Returns:
            Series: ATR values
        """
        try:
            stock_data = stock_data.copy()
            stock_data["HL"] = stock_data["High"] - stock_data["Low"]
            stock_data["HC"] = abs(stock_data["High"] - stock_data["Close"].shift())
            stock_data["LC"] = abs(stock_data["Low"] - stock_data["Close"].shift())
            stock_data["TR"] = stock_data[["HL", "HC", "LC"]].max(axis=1)
            stock_data["ATR"] = stock_data["TR"].rolling(window=window).mean()
            return stock_data["ATR"]
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return pd.Series()

    @staticmethod
    def check_if_above_50ema(stock_data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Check if stock is trading above its 50-period EMA.

        Args:
            stock_data (DataFrame): The stock data

        Returns:
            DataFrame: Original DataFrame with Above_50_EMA column added
        """
        try:
            if stock_data is not None and not stock_data.empty:
                stock_data = stock_data.copy()
                stock_data["EMA_50"] = TechnicalIndicators.indicator_50ema(stock_data)
                stock_data["Above_50_EMA"] = stock_data["Close"] > stock_data["EMA_50"]
                return stock_data
            return None
        except Exception as e:
            logger.error(f"Error checking if above 50 EMA: {e}")
            return stock_data
