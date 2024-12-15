#!/usr/bin/env python3
"""
Master CLI Client for TradeMan V1 Script Execution
This module provides an interactive CLI interface to manage and execute various trading scripts.

Author: Cline
"""

import os
import sys
import logging
from typing import Dict, List, Optional
import subprocess
from datetime import datetime

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
        logging.FileHandler(os.path.join(LOG_DIR, f'master_cli_{datetime.now().strftime("%Y%m%d")}.log'))
    ]
)
logger = logging.getLogger(__name__)

class ScriptExecutor:
    """
    Main class to handle script execution and menu management
    """
    def __init__(self):
        """Initialize the ScriptExecutor with script categories and paths"""
        self.base_path = SCRIPT_DIR
        self.categories = {
            1: ("Morning Scripts", "1_GoodMorning"),
            2: ("Evening Scripts", "2_GoodEvening"),
            3: ("Strategy Scripts", "StrategyScripts"),
            4: ("Weekly Reports", "WeeklyReports"),
            5: ("Celery Scripts", "CeleryScripts"),
            6: ("Restart Scripts", "RestartScripts"),
            7: ("Migration Scripts", "migration"),
            8: ("API Testing Scripts", "logManager")
        }
        
        logger.info("ScriptExecutor initialized successfully")

    def display_main_menu(self) -> None:
        """Display the main menu with all script categories"""
        print("\n" + "="*50)
        print("TradeMan V1 Script Executor".center(50))
        print("="*50)
        
        for key, (name, _) in self.categories.items():
            print(f"{key}. {name}")
        print("0. Exit")
        print("="*50)

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

    def display_category_menu(self, category_name: str, scripts: Dict[int, str]) -> None:
        """
        Display the menu for a specific category
        
        Args:
            category_name: Name of the category
            scripts: Dictionary of available scripts
        """
        print("\n" + "="*50)
        print(f"{category_name} Menu".center(50))
        print("="*50)
        
        for num, script in scripts.items():
            print(f"{num}. {os.path.basename(script)}")
        print("0. Back to Main Menu")
        print("="*50)

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

    def run(self) -> None:
        """Main loop to run the CLI interface"""
        while True:
            try:
                self.display_main_menu()
                choice = input("\nEnter your choice (0-8): ").strip()
                
                if not choice.isdigit():
                    print("Please enter a valid number")
                    continue
                
                choice = int(choice)
                
                if choice == 0:
                    logger.info("Exiting script executor")
                    print("\nThank you for using TradeMan V1 Script Executor!")
                    break
                
                if choice not in self.categories:
                    print("Invalid choice. Please try again.")
                    continue
                
                category_name, category_path = self.categories[choice]
                scripts = self.get_scripts_in_category(category_path)
                
                if not scripts:
                    print(f"No executable scripts found in {category_name}")
                    continue
                
                while True:
                    self.display_category_menu(category_name, scripts)
                    script_choice = input("\nEnter script number (0 to go back): ").strip()
                    
                    if not script_choice.isdigit():
                        print("Please enter a valid number")
                        continue
                    
                    script_choice = int(script_choice)
                    
                    if script_choice == 0:
                        break
                    
                    if script_choice not in scripts:
                        print("Invalid script number. Please try again.")
                        continue
                    
                    self.execute_script(scripts[script_choice])
                    input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, exiting...")
                print("\nExiting...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {str(e)}")
                print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    executor = ScriptExecutor()
    executor.run()

