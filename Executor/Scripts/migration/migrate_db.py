import sqlite3
import psycopg2
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_to_postgres():
    try:
        # SQLite connection
        logger.info("Connecting to SQLite database...")
        sqlite_conn = sqlite3.connect('Data/financial_data.db')
        sqlite_cursor = sqlite_conn.cursor()
        
        # Read data from SQLite
        logger.info("Reading data from SQLite...")
        sqlite_cursor.execute("SELECT * FROM financials")
        rows = sqlite_cursor.fetchall()
        logger.info(f"Read {len(rows)} rows from SQLite")
        
        # PostgreSQL connection parameters
        postgres_params = {
            'dbname': 'trademan',
            'user': 'admin',
            'password': 'admin',
            'host': 'localhost',
            'port': '5432'
        }
        
        # Connect to PostgreSQL
        logger.info("Connecting to PostgreSQL...")
        pg_conn = psycopg2.connect(**postgres_params)
        pg_cursor = pg_conn.cursor()
        
        # Create table in PostgreSQL
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS financials (
            "Symbol" TEXT,
            "Market Cap" REAL,
            "Total Revenue" REAL,
            "Net Income" REAL,
            "EPS" REAL,
            "P/E Ratio" REAL,
            "P/B Ratio" REAL,
            "Dividend Yield" REAL,
            "Operating Cashflow" REAL,
            "Total Debt" REAL,
            "Cash" REAL,
            "EBITDA" REAL,
            "Operating Profit Margin" REAL,
            "Debt to Equity" REAL,
            "Gross Profit Growth" REAL,
            "Piotroski F-Score" INTEGER
        );
        """
        logger.info("Creating table in PostgreSQL...")
        pg_cursor.execute(create_table_sql)
        
        # Insert data into PostgreSQL
        logger.info("Inserting data into PostgreSQL...")
        insert_sql = """
        INSERT INTO financials (
            "Symbol", "Market Cap", "Total Revenue", "Net Income", "EPS", 
            "P/E Ratio", "P/B Ratio", "Dividend Yield", "Operating Cashflow", 
            "Total Debt", "Cash", "EBITDA", "Operating Profit Margin", 
            "Debt to Equity", "Gross Profit Growth", "Piotroski F-Score"
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Execute batch insert
        pg_cursor.executemany(insert_sql, rows)
        
        # Commit the transaction
        pg_conn.commit()
        logger.info("Data migration completed successfully!")
        
        # Close connections
        pg_cursor.close()
        pg_conn.close()
        sqlite_cursor.close()
        sqlite_conn.close()
        
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

if __name__ == "__main__":
    migrate_to_postgres()
