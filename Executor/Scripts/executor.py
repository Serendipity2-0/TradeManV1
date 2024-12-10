#!/usr/bin/env python3
"""
Script execution module for TradeMan V1
This module handles the execution of trading scripts.

Author: Cline
"""

import os
import sys
import logging
import subprocess
from datetime import datetime
from typing import Dict

# Get script directory for relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, f'executor_{datetime.now().strftime("%Y%m%d")}.log'))
    ]
)
logger = logging.getLogger(__name__)

class ScriptExecutor:
    """
    Handles the execution of trading scripts
    """
    def __init__(self):
        """Initialize the ScriptExecutor with base path"""
        self.base_path = SCRIPT_DIR
        logger.info("ScriptExecutor initialized successfully")

    def get_scripts_in_category(self, category_path: str) -> Dict[int, str]:
        """
        Get all executable scripts in a category directory
        
        Args:
            category_path: Path to the category directory
            
        Returns:
            Dictionary mapping menu numbers to script paths
        """
        scripts = {}
        count = 1
        full_path = os.path.join(self.base_path, category_path)
        
        if not os.path.exists(full_path):
            logger.error(f"Category path does not exist: {full_path}")
            return scripts

        for root, _, files in os.walk(full_path):
            for file in files:
                if file.endswith(('.sh', '.py')) and not file.startswith('__'):
                    script_path = os.path.join(root, file)
                    scripts[count] = os.path.relpath(script_path, self.base_path)
                    count += 1
        
        return scripts

    def execute_script(self, script_path: str) -> None:
        """
        Execute the selected script
        
        Args:
            script_path: Path to the script to execute
        """
        try:
            full_path = os.path.join(self.base_path, script_path)
            logger.info(f"Executing script: {script_path}")
            
            if script_path.endswith('.py'):
                subprocess.run([sys.executable, full_path], check=True)
            elif script_path.endswith('.sh'):
                subprocess.run(['bash', full_path], check=True)
            
            logger.info(f"Script execution completed: {script_path}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing script {script_path}: {str(e)}")
            print(f"Error executing script: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error executing script {script_path}: {str(e)}")
            print(f"Unexpected error: {str(e)}")
