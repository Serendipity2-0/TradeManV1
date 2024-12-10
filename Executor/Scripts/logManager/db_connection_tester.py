#!/usr/bin/env python3
"""
Database Connection Testing Script
This script tests connections to MongoDB and PostgreSQL databases.

Author: Cline
"""

import logging
import sys
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import time
import psycopg2
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from logManager.env
env_path = Path(__file__).parent / 'logManager.env'
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.getenv('LOG_FILE_PATH', 'logs/logmanager.log'))
    ]
)
logger = logging.getLogger(__name__)

class DatabaseConnectionTester:
    """
    Class to handle database connection testing
    """
    def __init__(self):
        """Initialize database connection parameters from environment"""
        # PostgreSQL configuration
        self.pg_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'trademan'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
        }

        # MongoDB configuration
        self.mongo_config = {
            'host': os.getenv('MONGO_HOST', 'localhost'),
            'port': int(os.getenv('MONGO_PORT', 27017)),
            'database': os.getenv('MONGO_DB', 'trademan'),
            'username': os.getenv('MONGO_USER', 'mongodb'),
            'password': os.getenv('MONGO_PASSWORD', 'mongodb')
        }

        # Test configuration
        self.retry_count = int(os.getenv('TEST_RETRY_COUNT', 3))
        self.retry_delay = int(os.getenv('TEST_RETRY_DELAY', 5))
        
        logger.info("Database Connection Tester initialized")

    def test_postgres_connection(self) -> Dict:
        """
        Test PostgreSQL database connection with retry mechanism

        Returns:
            Dictionary containing test results
        """
        for attempt in range(self.retry_count):
            start_time = time.time()
            try:
                conn = psycopg2.connect(
                    host=self.pg_config['host'],
                    port=self.pg_config['port'],
                    database=self.pg_config['database'],
                    user=self.pg_config['user'],
                    password=self.pg_config['password']
                )
                
                # Test the connection by executing a simple query
                with conn.cursor() as cur:
                    cur.execute('SELECT version();')
                    version = cur.fetchone()[0]
                
                conn.close()
                
                end_time = time.time()
                response_time = round((end_time - start_time) * 1000, 2)  # in milliseconds
                
                result = {
                    'database': 'PostgreSQL',
                    'success': True,
                    'version': version,
                    'response_time_ms': response_time,
                    'timestamp': datetime.now().isoformat(),
                    'attempt': attempt + 1
                }
                
                logger.info(f"PostgreSQL connection test successful: {result}")
                return result
                
            except Exception as e:
                logger.error(f"PostgreSQL connection error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.retry_count - 1:
                    logger.warning(f"Retrying PostgreSQL connection after {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    continue
                
                return {
                    'database': 'PostgreSQL',
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat(),
                    'attempts': attempt + 1
                }

    def test_mongo_connection(self) -> Dict:
        """
        Test MongoDB connection with retry mechanism

        Returns:
            Dictionary containing test results
        """
        for attempt in range(self.retry_count):
            start_time = time.time()
            try:
                # Construct MongoDB URI
                mongo_uri = f"mongodb://{self.mongo_config['username']}:{self.mongo_config['password']}@" \
                          f"{self.mongo_config['host']}:{self.mongo_config['port']}"
                
                client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
                
                # Test the connection by executing a command
                server_info = client.server_info()
                
                end_time = time.time()
                response_time = round((end_time - start_time) * 1000, 2)  # in milliseconds
                
                result = {
                    'database': 'MongoDB',
                    'success': True,
                    'version': server_info.get('version', 'Unknown'),
                    'response_time_ms': response_time,
                    'timestamp': datetime.now().isoformat(),
                    'attempt': attempt + 1
                }
                
                client.close()
                logger.info(f"MongoDB connection test successful: {result}")
                return result
                
            except Exception as e:
                logger.error(f"MongoDB connection error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.retry_count - 1:
                    logger.warning(f"Retrying MongoDB connection after {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    continue
                
                return {
                    'database': 'MongoDB',
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat(),
                    'attempts': attempt + 1
                }

    def generate_report(self, results: list) -> str:
        """
        Generate a formatted report from test results

        Args:
            results: List of test results

        Returns:
            Formatted report string
        """
        report = "\n=== Database Connection Test Report ===\n"
        report += f"Timestamp: {datetime.now().isoformat()}\n\n"
        
        successful_tests = len([r for r in results if r.get('success', False)])
        
        report += f"Total Tests: {len(results)}\n"
        report += f"Successful: {successful_tests}\n"
        report += f"Failed: {len(results) - successful_tests}\n\n"
        
        report += "Detailed Results:\n"
        for result in results:
            report += f"\nDatabase: {result['database']}\n"
            report += f"Success: {result.get('success', False)}\n"
            if result.get('success', False):
                report += f"Version: {result.get('version', 'Unknown')}\n"
                report += f"Response Time: {result.get('response_time_ms')}ms\n"
            else:
                report += f"Error: {result.get('error', 'Unknown error')}\n"
            report += f"Attempts: {result.get('attempt', result.get('attempts', 1))}\n"
            report += "-" * 50
        
        return report

def main():
    """Main function to run database connection tests"""
    try:
        tester = DatabaseConnectionTester()
        results = []
        
        # Test PostgreSQL connection
        logger.info("Testing PostgreSQL connection...")
        pg_result = tester.test_postgres_connection()
        results.append(pg_result)
        
        # Test MongoDB connection
        logger.info("Testing MongoDB connection...")
        mongo_result = tester.test_mongo_connection()
        results.append(mongo_result)
        
        # Generate and display report
        report = tester.generate_report(results)
        print(report)
        
        # Save report if configured
        if os.getenv('REPORT_SAVE_HISTORY', 'true').lower() == 'true':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.getenv('REPORT_PATH', 'reports')
            Path(report_path).mkdir(parents=True, exist_ok=True)
            report_file = Path(report_path) / f"db_test_report_{timestamp}.txt"
            report_file.write_text(report)
            logger.info(f"Test report saved to {report_file}")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
