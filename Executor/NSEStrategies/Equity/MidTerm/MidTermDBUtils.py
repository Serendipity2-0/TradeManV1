import sqlite3
import pandas as pd
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.NSEStrategies.Equity.MidTerm.MidTermConfig import TODAY_STOCK_DATA_DB_PATH

logger = LoggerSetup()

def initialize_db():
    """
    Initialize the database with required tables and columns if they don't exist.

    Returns:
        None
    """
    try:
        conn = sqlite3.connect(TODAY_STOCK_DATA_DB_PATH)
        cursor = conn.cursor()

        # Create CombinedStocks table with required columns if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS CombinedStocks (
                Symbol TEXT PRIMARY KEY,
                AthLtpRatio REAL DEFAULT 0,
                Mid_tfMomentum INTEGER DEFAULT 0,
                Mid_tfEma INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")


def get_today_stocks():
    """
    Get today's stocks from the database.

    Returns:
        pandas.DataFrame: DataFrame containing today's stocks.
    """
    try:
        # Initialize database if needed
        initialize_db()
        
        conn = sqlite3.connect(TODAY_STOCK_DATA_DB_PATH)
        cursor = conn.cursor()

        # Check if CombinedStocks table exists and has data
        cursor.execute("SELECT COUNT(*) FROM CombinedStocks")
        count = cursor.fetchone()[0]

        if count == 0:
            logger.warning("No stocks found in database")
            return pd.DataFrame(columns=['Symbol', 'AthLtpRatio', 'Mid_tfMomentum', 'Mid_tfEma'])

        # Load the data from the CombinedStocks table
        df = pd.read_sql_query("SELECT * FROM CombinedStocks", conn)
        conn.close()

        # Filter the rows where any column name starting with "Mid_" is equal to 1
        midterm_stocks_df = df[df.filter(regex="Mid_").eq(1).any(axis=1)]

        if midterm_stocks_df.empty:
            logger.warning("No mid-term stocks found")
            return pd.DataFrame(columns=['Symbol', 'AthLtpRatio', 'Mid_tfMomentum', 'Mid_tfEma'])

        # Sort by AthLtpRatio in descending order
        midterm_stocks = midterm_stocks_df.sort_values(
            by="AthLtpRatio", ascending=False
        )
        return midterm_stocks
    except Exception as e:
        logger.error(f"Error getting today's stocks: {e}")
        return pd.DataFrame(columns=['Symbol', 'AthLtpRatio', 'Mid_tfMomentum', 'Mid_tfEma'])


def update_stock_data(symbol, data):
    """
    Update stock data in the database.

    Args:
        symbol (str): Stock symbol
        data (dict): Data to update

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(TODAY_STOCK_DATA_DB_PATH)
        cursor = conn.cursor()

        # Create SET clause dynamically from data dictionary
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [symbol]  # Add symbol for WHERE clause

        # Update the record
        cursor.execute(
            f"UPDATE CombinedStocks SET {set_clause} WHERE Symbol = ?",
            values
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating stock data: {e}")
        return False
