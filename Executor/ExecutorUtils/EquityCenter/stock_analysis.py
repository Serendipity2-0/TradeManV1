import os
import pandas as pd
import sqlite3
from typing import List, Dict, Optional, Union, Tuple
from dotenv import load_dotenv

# Load environment variables
DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    send_messsage_via_discord,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
    Instrument as instrument_obj,
    get_single_ltp,
)
from Executor.ExecutorUtils.EquityCenter.stock_validator import StockValidator

logger = LoggerSetup()

class StockAnalysis:
    """
    A class for analyzing stocks and generating trading signals.
    
    This class provides methods for analyzing stock data, generating trading signals,
    and managing stock-related operations.
    """

    # Strategy Constants
    SHORT_MOMENTUM = "Short_Momentum"
    SHORT_EMABBCONFLUENCE = "Short_EMABBConfluence"
    SHORT_MEANREVERSION = "Short_MeanReversion"
    MID_TFMOMENTUM = "Mid_tfMomentum"
    MID_TFEMA = "Mid_tfEma"
    LONG_RATIO = "Long_Ratio"
    LONG_COMBO = "Long_Combo"

    def __init__(self):
        """Initialize StockAnalysis with environment variables."""
        self.today_stock_data_db_path = os.getenv("TODAY_STOCK_DATA_DB_PATH")
        self.validator = StockValidator()

    @staticmethod
    def safe_merge(df1: Optional[pd.DataFrame], df2: Optional[pd.DataFrame], 
                  on: str, how: str) -> pd.DataFrame:
        """
        Safely merge two DataFrames handling None cases.

        Args:
            df1: First DataFrame
            df2: Second DataFrame
            on: Column to merge on
            how: Type of merge

        Returns:
            pd.DataFrame: Merged DataFrame
        """
        if df1 is None:
            return df2
        if df2 is None:
            return df1
        return pd.merge(df1, df2, on=on, how=how)

    def merge_dataframes(
        self,
        momentum_df: Optional[pd.DataFrame] = None,
        mean_reversion_df: Optional[pd.DataFrame] = None,
        ema_bb_df: Optional[pd.DataFrame] = None,
        ratio_df: Optional[pd.DataFrame] = None,
        combo_df: Optional[pd.DataFrame] = None,
        tfmomentum_df: Optional[pd.DataFrame] = None,
        tfema_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Merge DataFrames from different strategies into one comprehensive DataFrame.

        Args:
            momentum_df: DataFrame from momentum strategy
            mean_reversion_df: DataFrame from mean reversion strategy
            ema_bb_df: DataFrame from EMA/BB confluence strategy
            ratio_df: DataFrame from ratio strategy
            combo_df: DataFrame from combo strategy
            tfmomentum_df: DataFrame from timeframe momentum strategy
            tfema_df: DataFrame from timeframe EMA strategy

        Returns:
            pd.DataFrame: Combined DataFrame with all strategy results
        """
        try:
            combined_df = self.safe_merge(
                momentum_df, mean_reversion_df, on="Symbol", how="outer"
            )
            combined_df = self.safe_merge(combined_df, ema_bb_df, on="Symbol", how="outer")
            combined_df = self.safe_merge(combined_df, ratio_df, on="Symbol", how="outer")
            combined_df = self.safe_merge(combined_df, combo_df, on="Symbol", how="outer")
            combined_df = self.safe_merge(combined_df, tfmomentum_df, on="Symbol", how="outer")
            combined_df = self.safe_merge(combined_df, tfema_df, on="Symbol", how="outer")

            # Remove duplicate columns from merges
            combined_df = combined_df[
                [col for col in combined_df.columns if not col.endswith("_Drop")]
            ]

            # Fill NaN values with appropriate defaults
            combined_df = self._fill_default_values(combined_df)

            return combined_df
        except Exception as e:
            logger.error(f"Error merging DataFrames: {e}")
            return pd.DataFrame()

    def _fill_default_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fill NaN values in DataFrame with appropriate defaults.

        Args:
            df: DataFrame to fill

        Returns:
            pd.DataFrame: DataFrame with NaN values filled
        """
        defaults = {
            "DailyOpen": 0, "DailyHigh": 0, "DailyLow": 0, "DailyClose": 0,
            "WeeklyOpen": 0, "WeeklyHigh": 0, "WeeklyLow": 0, "WeeklyClose": 0,
            "DailyRSI": 0, "DailyUpper_band": 0, "DailyAbove_50_EMA": 0,
            "DailyMACD": 0, "DailySignal_Line": 0, "DailyEMA_50": 0,
            "DailyMA": 0, "DailyLower_band": 0, "WeeklyMA": 0,
            "AthLtpRatio": 0, "WeeklyLower_band": 0, "Market Cap": 0,
            "P/E Ratio": 0, "P/B Ratio": 0, "Dividend Yield": 0,
            "Piotroski F-Score": 0, "Operating Profit Margin": 0,
            "Debt to Equity": 0, "Gross Profit Growth": 0,
            self.SHORT_MOMENTUM: 0, self.SHORT_MEANREVERSION: 0,
            self.SHORT_EMABBCONFLUENCE: 0, self.LONG_RATIO: 0,
            self.LONG_COMBO: 0, self.MID_TFMOMENTUM: 0, self.MID_TFEMA: 0,
        }
        return df.fillna(defaults)

    def update_todaystocks_db(
        self,
        momentum_stocks_df: Optional[pd.DataFrame] = None,
        mean_reversion_stocks_df: Optional[pd.DataFrame] = None,
        ema_bb_confluence_stocks_df: Optional[pd.DataFrame] = None,
        ratio_stocks_df: Optional[pd.DataFrame] = None,
        combo_stocks_df: Optional[pd.DataFrame] = None,
        tfmomentum_stocks_df: Optional[pd.DataFrame] = None,
        tfema_stocks_df: Optional[pd.DataFrame] = None,
    ) -> None:
        """
        Update the database with today's stock analysis results.

        Args:
            momentum_stocks_df: DataFrame from momentum strategy
            mean_reversion_stocks_df: DataFrame from mean reversion strategy
            ema_bb_confluence_stocks_df: DataFrame from EMA/BB confluence strategy
            ratio_stocks_df: DataFrame from ratio strategy
            combo_stocks_df: DataFrame from combo strategy
            tfmomentum_stocks_df: DataFrame from timeframe momentum strategy
            tfema_stocks_df: DataFrame from timeframe EMA strategy
        """
        try:
            merged_df = self.merge_dataframes(
                momentum_df=momentum_stocks_df,
                mean_reversion_df=mean_reversion_stocks_df,
                ema_bb_df=ema_bb_confluence_stocks_df,
                ratio_df=ratio_stocks_df,
                combo_df=combo_stocks_df,
                tfmomentum_df=tfmomentum_stocks_df,
                tfema_df=tfema_stocks_df,
            )

            conn = sqlite3.connect(self.today_stock_data_db_path)
            merged_df.to_sql("CombinedStocks", conn, if_exists="replace", index=False)
            conn.close()

            logger.info("Stock data successfully stored in TodayStocks database.")
        except Exception as e:
            logger.error(f"Error updating TodayStocks DB: {e}")

    @staticmethod
    def get_selected_stocks(
        strategy_name: str, 
        today_stocks_df: pd.DataFrame
    ) -> Tuple[List[str], List[str]]:
        """
        Get selected stocks for a strategy.

        Args:
            strategy_name: Name of the strategy
            today_stocks_df: DataFrame of today's stocks

        Returns:
            tuple: (List of symbols, List of strategy setups)
        """
        symbol_list = today_stocks_df["Symbol"].tolist()
        
        # Handle both direct strategy columns and setup-specific columns
        strategy_setups = [
            col for col in today_stocks_df.columns 
            if col.startswith(f"{strategy_name}") or  # Direct strategy columns
               col.startswith(f"{strategy_name}_Setup")  # Setup-specific columns
        ]
        
        logger.warning(f"Selected stocks for {strategy_name}: {strategy_setups}")
        
        # Log detailed information for each setup
        for setup in strategy_setups:
            # Get stocks that have a value of 1 for this setup
            selected_stocks = today_stocks_df[today_stocks_df[setup] == 1]["Symbol"].tolist()
            logger.info(f"{setup} selected stocks: {selected_stocks}")
            
            # Log additional details for selected stocks
            if selected_stocks:
                for stock in selected_stocks:
                    stock_data = today_stocks_df[today_stocks_df["Symbol"] == stock].iloc[0]
                    details = {
                        "Symbol": stock,
                        "Setup": setup
                    }
                    # Add any numerical columns as additional details
                    for col in today_stocks_df.columns:
                        if col != "Symbol" and isinstance(stock_data[col], (int, float)):
                            details[col] = stock_data[col]
                    
                    logger.info(f"Stock details for {stock} in {setup}: {details}")
            else:
                logger.info(f"No stocks selected for {setup}")
        
        return symbol_list, strategy_setups

    @staticmethod
    def send_signals_via_discord(
        setup_symbol_list: List[str],
        setup_name: str,
        strategy_name: str,
        trade_mode: str
    ) -> None:
        """
        Send trading signals via Discord.

        Args:
            setup_symbol_list: List of symbols for the setup
            setup_name: Name of the setup
            strategy_name: Name of the strategy
            trade_mode: Trading mode
        """
        valid_count = 0
        for symbol in setup_symbol_list:
            exchange_token = instrument_obj().get_exchange_token_by_name(symbol, "NSE")
            if not StockValidator.check_symbol_for_errors(symbol, exchange_token):
                continue

            ltp = get_single_ltp(exchange_token=exchange_token, segment="NSE")
            ltp = round(ltp * 20) / 20  # Round to nearest 0.05
            
            message = (
                f"{trade_mode} Trade for {strategy_name}\n"
                f"Setup : {setup_name}\n"
                f"Symbol : {symbol}\n"
                f"Ltp : {ltp} \n"
            )
            send_messsage_via_discord(message, strategy_name)
            valid_count += 1
            if valid_count >= 3:
                break

        if valid_count < 3:
            additional_message = f"{valid_count} stocks were selected for {setup_name}."
            send_messsage_via_discord(additional_message, strategy_name)
