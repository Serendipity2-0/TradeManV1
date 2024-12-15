import os
import sys
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import pytest
from pathlib import Path

# Add project root to system path
DIR = os.getcwd()
sys.path.append(DIR)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.EquityCenter.data_fetcher import DataFetcher
from Executor.ExecutorUtils.EquityCenter.technical_indicators import TechnicalIndicators
from Executor.ExecutorUtils.EquityCenter.stock_analysis import StockAnalysis
from Executor.ExecutorUtils.EquityCenter.stock_validator import StockValidator

logger = LoggerSetup()

class TestEquityCenter:
    """Test class for EquityCenter functionality."""

    @classmethod
    def setup_class(cls):
        """Set up test environment and create necessary directories."""
        # Create required directories
        directories = [
            'Data/Equity',
            'Data/Derivatives',
            'Data/Signals',
            'Data/AsmGsmList'  # Added for ASM/GSM list testing
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

        # Initialize test data
        cls.test_symbols = ['TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM']
        cls.generate_test_data()

    @classmethod
    def generate_test_data(cls):
        """Generate test data for different databases."""
        cls.generate_financial_data()
        cls.generate_stock_data()
        cls.generate_today_stock_picks()
        cls.generate_asm_gsm_list()

    @classmethod
    def generate_asm_gsm_list(cls):
        """Generate test ASM/GSM list."""
        today = datetime.now().strftime("%Y-%m-%d")
        asm_gsm_data = pd.DataFrame({
            'SYMBOL': ['TESTSTOCK1', 'TESTSTOCK2', cls.test_symbols[0]],  # Include one test symbol
            'SERIES': ['EQ', 'EQ', 'EQ'],
            'DATE': [today, today, today]
        })
        Path('Data/AsmGsmList').mkdir(parents=True, exist_ok=True)
        asm_gsm_data.to_csv(f'Data/AsmGsmList/merged_asm_gsm_{today}.csv', index=False)
        logger.info(f"Generated ASM/GSM list with {len(asm_gsm_data)} symbols")

    @classmethod
    def generate_financial_data(cls):
        """Generate and store test financial data."""
        financial_data = []
        for symbol in cls.test_symbols:
            financial_data.append({
                'Symbol': symbol,
                'Market Cap': np.random.randint(100000, 1000000),
                'Total Revenue': np.random.randint(10000, 100000),
                'Net Income': np.random.randint(1000, 10000),
                'EPS': np.random.uniform(10, 100),
                'P/E Ratio': np.random.uniform(10, 30),
                'P/B Ratio': np.random.uniform(1, 5),
                'Dividend Yield': np.random.uniform(1, 5),
                'Operating Cashflow': np.random.randint(5000, 50000),
                'Total Debt': np.random.randint(1000, 10000),
                'Cash': np.random.randint(1000, 10000),
                'EBITDA': np.random.randint(5000, 50000),
                'Operating Profit Margin': np.random.uniform(10, 30),
                'Debt to Equity': np.random.uniform(0.1, 2),
                'Gross Profit Growth': np.random.uniform(5, 15),
                'Piotroski F-Score': np.random.randint(1, 9),
                'Return on Equity': np.random.uniform(10, 30)
            })

        df = pd.DataFrame(financial_data)
        conn = sqlite3.connect('Data/financial_data.db')
        df.to_sql('financials', conn, if_exists='replace', index=False)
        conn.close()
        logger.info(f"Generated financial data for {len(financial_data)} symbols")

    @classmethod
    def generate_stock_data(cls):
        """Generate and store test stock price data."""
        end_date = datetime.now()
        dates = [end_date - timedelta(days=x) for x in range(365)]
        dates.reverse()

        for symbol in cls.test_symbols:
            daily_data = []
            price = 1000  # Starting price
            
            for date in dates:
                change = np.random.uniform(-20, 20)
                price += change
                daily_data.append({
                    'Date': date.strftime('%Y-%m-%d'),
                    'DailyOpen': price * (1 + np.random.uniform(-0.01, 0.01)),
                    'DailyHigh': price * (1 + np.random.uniform(0, 0.02)),
                    'DailyLow': price * (1 - np.random.uniform(0, 0.02)),
                    'DailyClose': price,
                    'DailyVolume': np.random.randint(100000, 1000000),
                    'WeeklyOpen': price * (1 + np.random.uniform(-0.02, 0.02)),
                    'WeeklyHigh': price * (1 + np.random.uniform(0, 0.03)),
                    'WeeklyLow': price * (1 - np.random.uniform(0, 0.03)),
                    'WeeklyClose': price * (1 + np.random.uniform(-0.01, 0.01)),
                    'WeeklyVolume': np.random.randint(500000, 5000000)
                })

            df = pd.DataFrame(daily_data)
            conn = sqlite3.connect('Data/equity_stock_data.db')
            
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS "{symbol}" (
                    Date TEXT,
                    DailyOpen REAL,
                    DailyHigh REAL,
                    DailyLow REAL,
                    DailyClose REAL,
                    DailyVolume INTEGER,
                    WeeklyOpen REAL,
                    WeeklyHigh REAL,
                    WeeklyLow REAL,
                    WeeklyClose REAL,
                    WeeklyVolume INTEGER
                )
            """)
            
            df.to_sql(symbol, conn, if_exists='replace', index=False)
            conn.close()
        
        logger.info(f"Generated stock data for {len(cls.test_symbols)} symbols")

    @classmethod
    def generate_today_stock_picks(cls):
        """Generate and store test data for today's stock picks."""
        picks_data = []
        for symbol in cls.test_symbols:
            # Generate strategy-specific setup columns with some meaningful test data
            momentum_setups = {
                'Short_Momentum_Setup1': np.random.choice([0, 1], p=[0.7, 0.3]),  # 30% chance of being selected
                'Short_Momentum_Setup2': np.random.choice([0, 1], p=[0.8, 0.2]),  # 20% chance of being selected
                'Short_Momentum_Setup3': np.random.choice([0, 1], p=[0.9, 0.1]),  # 10% chance of being selected
            }
            
            # Add some technical indicators for more detailed logging
            technical_data = {
                'RSI': np.random.uniform(30, 70),
                'EMA_50': np.random.uniform(90, 110),
                'Volume_Ratio': np.random.uniform(0.8, 1.2),
                'Price_Change': np.random.uniform(-5, 5)
            }
            
            picks_data.append({
                'Symbol': symbol,
                **momentum_setups,  # Include strategy-specific setups
                **technical_data,   # Include technical indicators
                'Short_MeanReversion': np.random.randint(0, 2),
                'Short_EMABBConfluence': np.random.randint(0, 2),
                'Mid_tfMomentum': np.random.randint(0, 2),
                'Mid_tfEma': np.random.randint(0, 2),
                'Long_Ratio': np.random.randint(0, 2),
                'Long_Combo': np.random.randint(0, 2)
            })

        df = pd.DataFrame(picks_data)
        conn = sqlite3.connect('Data/stock_picks.db')
        df.to_sql('CombinedStocks', conn, if_exists='replace', index=False)
        conn.close()
        logger.info(f"Generated stock picks data with {len(picks_data)} records")

    def test_data_fetcher(self):
        """Test DataFetcher functionality."""
        fetcher = DataFetcher()
        
        # Test reading financial data
        financial_data = fetcher.read_stock_data_from_db('Data/financial_data.db')
        assert len(financial_data) > 0, "Financial data should not be empty"
        
        # Verify financial data structure
        first_symbol = list(financial_data.keys())[0]
        financial_record = financial_data[first_symbol]
        assert 'market_cap' in financial_record, "Financial data should contain market_cap"
        assert 'total_revenue' in financial_record, "Financial data should contain total_revenue"
        
        # Test reading stock data
        stock_data = fetcher.read_stock_data_from_db('Data/equity_stock_data.db')
        assert len(stock_data) > 0, "Stock data should not be empty"
        
        # Verify stock data structure
        first_symbol = list(stock_data.keys())[0]
        daily_data = stock_data[first_symbol]['daily_data']
        assert 'Open' in daily_data, "Daily data should contain Open prices"
        assert 'Close' in daily_data, "Daily data should contain Close prices"
        
        print("DataFetcher tests passed successfully!")

    def test_technical_indicators(self):
        """Test TechnicalIndicators functionality."""
        conn = sqlite3.connect('Data/equity_stock_data.db')
        test_data = pd.read_sql_query(
            f"""
            SELECT 
                Date,
                DailyOpen as Open,
                DailyHigh as High,
                DailyLow as Low,
                DailyClose as Close,
                DailyVolume as Volume
            FROM "{self.test_symbols[0]}"
            """, 
            conn
        )
        conn.close()

        # Set Date as index
        test_data['Date'] = pd.to_datetime(test_data['Date'])
        test_data.set_index('Date', inplace=True)

        # Test each indicator
        ema_5 = TechnicalIndicators.indicator_5ema(test_data)
        assert not ema_5.empty, "5 EMA calculation failed"

        rsi = TechnicalIndicators.indicator_rsi(test_data, 14, 'Close')
        assert not rsi.empty, "RSI calculation failed"

        bb_data = TechnicalIndicators.indicator_bollinger_bands(test_data, 20)
        assert 'Upper_band' in bb_data.columns, "Bollinger Bands calculation failed"

        macd, signal = TechnicalIndicators.indicator_macd(test_data)
        assert not macd.empty and not signal.empty, "MACD calculation failed"

        print("TechnicalIndicators tests passed successfully!")

    def test_stock_validator(self):
        """Test StockValidator functionality."""
        validator = StockValidator()
        
        # Test ASM/GSM list functionality
        asm_gsm_list = validator.get_asm_gsm_list()
        assert len(asm_gsm_list) > 0, "ASM/GSM list should not be empty"
        
        # Test symbol in list check
        assert validator.check_symbol_in_list(self.test_symbols, self.test_symbols[0]), \
            "Should find symbol in list"
        assert not validator.check_symbol_in_list(self.test_symbols, "NONEXISTENT"), \
            "Should not find nonexistent symbol"
        
        # Test holiday check
        is_holiday = validator.is_today_holiday()
        assert isinstance(is_holiday, bool), "Holiday check should return boolean"
        
        print("StockValidator tests passed successfully!")

    def test_stock_analysis(self):
        """Test StockAnalysis functionality."""
        analyzer = StockAnalysis()

        # Test merging dataframes
        conn = sqlite3.connect('Data/stock_picks.db')
        today_stocks_df = pd.read_sql("SELECT * FROM CombinedStocks", conn)
        conn.close()

        logger.info("\nFull test data:")
        logger.info(f"\n{today_stocks_df.to_string()}")

        # Test getting selected stocks
        symbol_list, strategy_setups = analyzer.get_selected_stocks(
            "Short_Momentum", 
            today_stocks_df
        )
        assert len(symbol_list) > 0, "Should return symbols"
        assert len(strategy_setups) > 0, "Should return strategy setups"

        # Verify strategy setup details are logged
        for setup in strategy_setups:
            selected_stocks = today_stocks_df[today_stocks_df[setup] == 1]["Symbol"].tolist()
            logger.info(f"Selected stocks for {setup}: {selected_stocks}")

        print("StockAnalysis tests passed successfully!")

def run_tests():
    """Run all tests."""
    test = TestEquityCenter()
    test.setup_class()
    test.test_data_fetcher()
    test.test_technical_indicators()
    test.test_stock_validator()
    test.test_stock_analysis()
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    run_tests()
