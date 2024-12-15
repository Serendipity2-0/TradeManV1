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

from Executor.ExecutorUtils.EquityCenter.data_fetcher import DataFetcher
from Executor.ExecutorUtils.EquityCenter.technical_indicators import TechnicalIndicators
from Executor.ExecutorUtils.EquityCenter.stock_analysis import StockAnalysis

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
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

        # Initialize test data
        cls.test_symbols = ['TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM']
        cls.generate_test_data()

    @classmethod
    def generate_test_data(cls):
        """Generate test data for different databases."""
        # Generate financial data
        cls.generate_financial_data()
        
        # Generate stock data
        cls.generate_stock_data()
        
        # Generate today's stock picks
        cls.generate_today_stock_picks()

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
            
            # Create table with proper schema
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

    @classmethod
    def generate_today_stock_picks(cls):
        """Generate and store test data for today's stock picks."""
        picks_data = []
        for symbol in cls.test_symbols:
            # Generate strategy-specific setup columns
            short_momentum_setups = {
                'Short_Momentum_Setup1': np.random.randint(0, 2),
                'Short_Momentum_Setup2': np.random.randint(0, 2),
                'Short_Momentum_Setup3': np.random.randint(0, 2)
            }
            
            picks_data.append({
                'Symbol': symbol,
                **short_momentum_setups,  # Include strategy-specific setups
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
        # Get test data
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

    def test_stock_analysis(self):
        """Test StockAnalysis functionality."""
        analyzer = StockAnalysis()

        # Test merging dataframes
        conn = sqlite3.connect('Data/stock_picks.db')
        today_stocks_df = pd.read_sql("SELECT * FROM CombinedStocks", conn)
        conn.close()

        # Test getting selected stocks
        symbol_list, strategy_setups = analyzer.get_selected_stocks(
            "Short_Momentum", 
            today_stocks_df
        )
        assert len(symbol_list) > 0, "Should return symbols"
        assert len(strategy_setups) > 0, "Should return strategy setups"

        # Test holiday check
        is_holiday = analyzer.is_today_holiday()
        assert isinstance(is_holiday, bool), "Holiday check should return boolean"

        print("StockAnalysis tests passed successfully!")

def run_tests():
    """Run all tests."""
    test = TestEquityCenter()
    test.setup_class()
    test.test_data_fetcher()
    test.test_technical_indicators()
    test.test_stock_analysis()
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    run_tests()
