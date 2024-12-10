#!/usr/bin/env python3
"""
Docker Container Health Check Script
This script monitors the health of Docker containers and their logs.

Author: Cline
"""

import docker
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
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

class DockerHealthChecker:
    """
    Class to handle Docker container health checks and log monitoring
    """
    def __init__(self):
        """Initialize Docker client and configuration from environment"""
        try:
            self.client = docker.from_env()
            self.containers_to_monitor = os.getenv('DOCKER_CONTAINERS_TO_MONITOR', 'mongodb,postgres').split(',')
            self.log_lines = int(os.getenv('DOCKER_LOG_LINES', 100))
            self.health_check_interval = int(os.getenv('DOCKER_HEALTH_CHECK_INTERVAL', 300))
            self.report_path = os.getenv('REPORT_PATH', 'reports')
            
            # Create reports directory if it doesn't exist
            Path(self.report_path).mkdir(parents=True, exist_ok=True)
            
            logger.info("Docker client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {str(e)}")
            raise

    def check_container_health(self, container_name: Optional[str] = None) -> Dict:
        """
        Check the health status of specified container or all containers

        Args:
            container_name: Optional name of specific container to check

        Returns:
            Dictionary containing health status of container(s)
        """
        try:
            containers = []
            if container_name:
                containers = [self.client.containers.get(container_name)]
            else:
                containers = [
                    container for container in self.client.containers.list()
                    if container.name in self.containers_to_monitor
                ]

            health_status = {}
            for container in containers:
                status = {
                    'name': container.name,
                    'status': container.status,
                    'health': container.attrs.get('State', {}).get('Health', {}).get('Status', 'N/A'),
                    'started_at': container.attrs.get('State', {}).get('StartedAt', 'N/A'),
                    'memory_usage': container.stats(stream=False).get('memory_stats', {}).get('usage', 'N/A'),
                    'timestamp': datetime.now().isoformat()
                }
                health_status[container.name] = status
                logger.info(f"Container {container.name} health status: {status}")

            return health_status

        except docker.errors.NotFound:
            logger.error(f"Container {container_name} not found")
            return {'error': f'Container {container_name} not found'}
        except Exception as e:
            logger.error(f"Error checking container health: {str(e)}")
            return {'error': str(e)}

    def get_container_logs(self, container_name: str, tail: Optional[int] = None) -> List[str]:
        """
        Get logs from a specific container

        Args:
            container_name: Name of the container
            tail: Number of log lines to retrieve

        Returns:
            List of log lines
        """
        try:
            container = self.client.containers.get(container_name)
            tail = tail or self.log_lines
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8').splitlines()
            logger.info(f"Retrieved {len(logs)} log lines from container {container_name}")
            return logs
        except docker.errors.NotFound:
            logger.error(f"Container {container_name} not found")
            return [f"Error: Container {container_name} not found"]
        except Exception as e:
            logger.error(f"Error retrieving logs: {str(e)}")
            return [f"Error: {str(e)}"]

    def monitor_container_resources(self, container_name: str) -> Dict:
        """
        Monitor resource usage of a specific container

        Args:
            container_name: Name of the container to monitor

        Returns:
            Dictionary containing resource usage statistics
        """
        try:
            container = self.client.containers.get(container_name)
            stats = container.stats(stream=False)
            
            # Calculate CPU usage percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_percent = 0.0
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * 100.0

            resources = {
                'container': container_name,
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': round(cpu_percent, 2),
                'memory_usage': stats['memory_stats'].get('usage', 0),
                'memory_limit': stats['memory_stats'].get('limit', 0),
                'network_rx': stats['networks']['eth0']['rx_bytes'] if 'networks' in stats else 0,
                'network_tx': stats['networks']['eth0']['tx_bytes'] if 'networks' in stats else 0
            }
            
            logger.info(f"Resource usage for {container_name}: {resources}")
            return resources

        except Exception as e:
            logger.error(f"Error monitoring container resources: {str(e)}")
            return {'error': str(e)}

    def generate_report(self, health_data: Dict, resource_data: List[Dict]) -> str:
        """
        Generate a formatted report from health and resource data

        Args:
            health_data: Dictionary containing health status
            resource_data: List of resource usage data

        Returns:
            Formatted report string
        """
        report = "\n=== Docker Container Health Report ===\n"
        report += f"Timestamp: {datetime.now().isoformat()}\n\n"
        
        report += "Health Status:\n"
        report += "=" * 50 + "\n"
        for container, status in health_data.items():
            report += f"\nContainer: {container}\n"
            for key, value in status.items():
                if key != 'name':  # Skip name as it's already shown
                    report += f"{key}: {value}\n"
            report += "-" * 50
        
        report += "\n\nResource Usage:\n"
        report += "=" * 50 + "\n"
        for data in resource_data:
            if 'error' in data:
                report += f"\nError monitoring {data.get('container', 'unknown')}: {data['error']}\n"
                continue
                
            report += f"\nContainer: {data['container']}\n"
            report += f"CPU Usage: {data['cpu_percent']}%\n"
            report += f"Memory Usage: {data['memory_usage']} bytes\n"
            report += f"Memory Limit: {data['memory_limit']} bytes\n"
            report += f"Network RX: {data['network_rx']} bytes\n"
            report += f"Network TX: {data['network_tx']} bytes\n"
            report += "-" * 50
        
        return report

def main():
    """Main function to run container health checks"""
    try:
        checker = DockerHealthChecker()
        
        # Check health status of all monitored containers
        health_status = checker.check_container_health()
        
        # Monitor resources for each container
        resource_data = []
        for container in checker.containers_to_monitor:
            # Get container resources
            resources = checker.monitor_container_resources(container)
            resource_data.append(resources)
            
            # Get container logs
            logs = checker.get_container_logs(container)
            if logs and not any(log.startswith('Error:') for log in logs):
                logger.info(f"Latest log from {container}: {logs[-1]}")
        
        # Generate and display report
        report = checker.generate_report(health_status, resource_data)
        print(report)
        
        # Save report if configured
        if os.getenv('REPORT_SAVE_HISTORY', 'true').lower() == 'true':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = Path(checker.report_path) / f"docker_health_report_{timestamp}.txt"
            report_file.write_text(report)
            logger.info(f"Health report saved to {report_file}")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
