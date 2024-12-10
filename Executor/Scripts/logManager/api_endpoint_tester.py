#!/usr/bin/env python3
"""
FastAPI Endpoint Testing Script
This script performs comprehensive testing of FastAPI endpoints in the TradeMan V1 project.

Author: Cline
"""

import requests
import logging
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
import sys
import os
from pathlib import Path
import ast
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

class APIEndpointTester:
    """
    Class to handle FastAPI endpoint testing with configuration from environment
    """
    def __init__(self):
        """Initialize API tester with configuration from environment"""
        self.base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        self.timeout = int(os.getenv('API_TIMEOUT', 30))
        self.retry_count = int(os.getenv('TEST_RETRY_COUNT', 3))
        self.retry_delay = int(os.getenv('TEST_RETRY_DELAY', 5))
        self.report_path = os.getenv('REPORT_PATH', 'reports')
        self.report_format = os.getenv('REPORT_FORMAT', 'detailed')
        
        # Create reports directory if it doesn't exist
        Path(self.report_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize session with timeout
        self.session = requests.Session()
        self.session.timeout = self.timeout
        
        logger.info(f"API Endpoint Tester initialized with base URL: {self.base_url}")

    def test_endpoint(self, endpoint: str, method: str = "GET", 
                     data: Optional[Dict] = None, 
                     expected_status: int = 200) -> Dict:
        """
        Test a specific API endpoint with retry mechanism

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, PUT, DELETE)
            data: Request payload data
            expected_status: Expected HTTP status code

        Returns:
            Dictionary containing test results
        """
        for attempt in range(self.retry_count):
            try:
                url = f"{self.base_url}{endpoint}"
                start_time = time.time()
                
                response = None
                if method.upper() == "GET":
                    response = self.session.get(url)
                elif method.upper() == "POST":
                    response = self.session.post(url, json=data)
                elif method.upper() == "PUT":
                    response = self.session.put(url, json=data)
                elif method.upper() == "DELETE":
                    response = self.session.delete(url)
                
                end_time = time.time()
                response_time = round((end_time - start_time) * 1000, 2)  # in milliseconds
                
                result = {
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': response.status_code,
                    'response_time_ms': response_time,
                    'success': response.status_code == expected_status,
                    'response_data': response.json() if response.text else None,
                    'timestamp': datetime.now().isoformat(),
                    'attempt': attempt + 1
                }
                
                log_level = logging.INFO if result['success'] else logging.ERROR
                logger.log(log_level, f"Endpoint test result: {json.dumps(result, indent=2)}")
                
                if result['success']:
                    return result
                
                if attempt < self.retry_count - 1:
                    logger.warning(f"Retrying endpoint {endpoint} after {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                
            except requests.exceptions.ConnectionError:
                logger.error(f"Connection error for endpoint {endpoint} on attempt {attempt + 1}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
                continue
            except Exception as e:
                logger.error(f"Error testing endpoint {endpoint} on attempt {attempt + 1}: {str(e)}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
                continue
        
        return {
            'endpoint': endpoint,
            'method': method,
            'error': f'Failed after {self.retry_count} attempts',
            'success': False,
            'timestamp': datetime.now().isoformat()
        }

    def run_health_check(self) -> Dict:
        """
        Test the API health check endpoint

        Returns:
            Dictionary containing health check results
        """
        return self.test_endpoint("/health")

    def test_all_endpoints(self) -> List[Dict]:
        """
        Test all endpoints defined in configuration

        Returns:
            List of dictionaries containing test results for each endpoint
        """
        try:
            endpoints_str = os.getenv('ENDPOINTS_TO_TEST', '[]')
            endpoints = ast.literal_eval(endpoints_str)
            
            results = []
            for endpoint in endpoints:
                result = self.test_endpoint(
                    endpoint["path"],
                    method=endpoint["method"]
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error parsing endpoints configuration: {str(e)}")
            return []

    def generate_report(self, results: List[Dict]) -> str:
        """
        Generate a formatted report from test results

        Args:
            results: List of test results

        Returns:
            Formatted report string
        """
        report = "\n=== API Endpoint Test Report ===\n"
        report += f"Timestamp: {datetime.now().isoformat()}\n"
        report += f"Base URL: {self.base_url}\n"
        report += f"Timeout: {self.timeout}s\n"
        report += f"Retry Count: {self.retry_count}\n\n"
        
        total_tests = len(results)
        successful_tests = len([r for r in results if r.get('success', False)])
        
        report += f"Total Tests: {total_tests}\n"
        report += f"Successful: {successful_tests}\n"
        report += f"Failed: {total_tests - successful_tests}\n\n"
        
        if self.report_format == 'detailed':
            report += "Detailed Results:\n"
            for result in results:
                report += f"\nEndpoint: {result['endpoint']}\n"
                report += f"Method: {result['method']}\n"
                report += f"Success: {result.get('success', False)}\n"
                if 'response_time_ms' in result:
                    report += f"Response Time: {result['response_time_ms']}ms\n"
                if 'attempt' in result:
                    report += f"Attempts: {result['attempt']}\n"
                if 'error' in result:
                    report += f"Error: {result['error']}\n"
                report += "-" * 50
        
        return report

def main():
    """Main function to run API endpoint tests"""
    try:
        tester = APIEndpointTester()
        
        # Run health check first
        logger.info("Running API health check...")
        health_result = tester.run_health_check()
        
        if health_result.get('success', False):
            logger.info("Health check passed, proceeding with endpoint tests...")
            
            # Run all endpoint tests
            results = tester.test_all_endpoints()
            
            # Generate and display report
            report = tester.generate_report(results)
            print(report)
            
            # Save report to file
            if os.getenv('REPORT_SAVE_HISTORY', 'true').lower() == 'true':
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_file = Path(tester.report_path) / f"api_test_report_{timestamp}.txt"
                report_file.write_text(report)
                logger.info(f"Test report saved to {report_file}")
            
        else:
            logger.error("Health check failed, skipping further tests")
            print("API health check failed. Please ensure the API is running and accessible.")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
