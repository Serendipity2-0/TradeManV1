import psycopg2
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_postgres_data():
    try:
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
        conn = psycopg2.connect(**postgres_params)
        cursor = conn.cursor()
        
        # Get row count
        cursor.execute('SELECT COUNT(*) FROM financials')
        count = cursor.fetchone()[0]
        logger.info(f"Total rows in PostgreSQL: {count}")
        
        # Sample some data
        cursor.execute('SELECT * FROM financials LIMIT 5')
        sample_rows = cursor.fetchall()
        logger.info("Sample data from PostgreSQL:")
        for row in sample_rows:
            logger.info(row)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}")
        raise

if __name__ == "__main__":
    verify_postgres_data()
