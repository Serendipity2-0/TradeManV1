#!/usr/bin/env python3
"""
Menu handling module for TradeMan V1 Script Execution
This module provides menu display and interaction functionality.

Author: Cline
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class MenuManager:
    """
    Handles menu display and user interaction for the script executor
    """
    def __init__(self):
        """Initialize the MenuManager with script categories"""
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
        logger.info("MenuManager initialized successfully")

    def display_main_menu(self) -> None:
        """Display the main menu with all script categories"""
        print("\n" + "="*50)
        print("TradeMan V1 Script Executor".center(50))
        print("="*50)
        
        for key, (name, _) in self.categories.items():
            print(f"{key}. {name}")
            # Add AI Agent option for each category
            print(f"{key}.9. {name} AI Agent")
        print("0. Exit")
        print("="*50)

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

    def get_user_choice(self, max_choice: int) -> Optional[int]:
        """
        Get and validate user input
        
        Args:
            max_choice: Maximum allowed choice number
            
        Returns:
            Validated user choice or None if invalid
        """
        try:
            choice = input(f"\nEnter your choice (0-{max_choice}): ").strip()
            
            if not choice.isdigit():
                print("Please enter a valid number")
                return None
            
            choice = int(choice)
            
            if 0 <= choice <= max_choice:
                return choice
            
            print("Invalid choice. Please try again.")
            return None
            
        except Exception as e:
            logger.error(f"Error getting user choice: {str(e)}")
            return None

    def get_category_info(self, choice: int) -> Optional[Tuple[str, str]]:
        """
        Get category name and path for a given choice
        
        Args:
            choice: User's menu choice
            
        Returns:
            Tuple of category name and path, or None if invalid choice
        """
        return self.categories.get(choice)
