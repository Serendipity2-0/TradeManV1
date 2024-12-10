#!/usr/bin/env python3
"""
Master CLI Client for TradeMan V1 Script Execution
This module provides an interactive CLI interface to manage and execute various trading scripts.

Author: Cline
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from typing import Optional

from menu import MenuManager
from executor import ScriptExecutor
from agents import get_agent_for_category

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

class MasterCLI:
    """
    Main class to handle CLI operations and coordinate between menu, executor, and agents
    """
    def __init__(self):
        """Initialize the MasterCLI with required components"""
        self.menu = MenuManager()
        self.executor = ScriptExecutor()
        logger.info("MasterCLI initialized successfully")

    async def handle_agent_query(self, category: int, query: str) -> None:
        """
        Handle AI agent interaction for a specific category
        
        Args:
            category: Category number from menu
            query: User's query for the agent
        """
        try:
            agent = get_agent_for_category(category)
            if agent:
                response = await agent.process_query(query)
                print("\nAI Agent Response:")
                print(f"\nExplanation: {response.explanation}")
                print(f"\nRecommendation: {response.recommendation}")
                print(f"\nConfidence: {response.confidence:.2%}")
            else:
                print("\nError: No agent available for this category")
                
        except Exception as e:
            logger.error(f"Error processing agent query: {str(e)}")
            print(f"\nError processing query: {str(e)}")

    def run(self) -> None:
        """Main loop to run the CLI interface"""
        while True:
            try:
                self.menu.display_main_menu()
                choice = self.menu.get_user_choice(8)
                
                if choice is None:
                    continue
                    
                if choice == 0:
                    logger.info("Exiting script executor")
                    print("\nThank you for using TradeMan V1 Script Executor!")
                    break
                
                category_info = self.menu.get_category_info(choice)
                if not category_info:
                    print("Invalid choice. Please try again.")
                    continue
                
                category_name, category_path = category_info
                scripts = self.executor.get_scripts_in_category(category_path)
                
                if not scripts:
                    print(f"No executable scripts found in {category_name}")
                    continue
                
                while True:
                    self.menu.display_category_menu(category_name, scripts)
                    script_choice = self.menu.get_user_choice(len(scripts))
                    
                    if script_choice is None:
                        continue
                    
                    if script_choice == 0:
                        break
                    
                    # Check if this is an AI agent request (x.9 format)
                    if str(script_choice).endswith('9'):
                        query = input("\nEnter your question for the AI agent: ")
                        asyncio.run(self.handle_agent_query(choice, query))
                    else:
                        if script_choice not in scripts:
                            print("Invalid script number. Please try again.")
                            continue
                        
                        self.executor.execute_script(scripts[script_choice])
                    
                    input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, exiting...")
                print("\nExiting...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {str(e)}")
                print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    cli = MasterCLI()
    cli.run()
