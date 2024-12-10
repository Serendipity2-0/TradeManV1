#!/usr/bin/env python3
"""
AI Agents module for TradeMan V1
This module provides AI assistance for various trading script categories.

Author: Cline
"""

import os
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent

# Configure logging
logger = logging.getLogger(__name__)

# Get script directory for relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPERTS_DIR = os.path.join(SCRIPT_DIR, 'Experts')

# Create Experts directory if it doesn't exist
os.makedirs(EXPERTS_DIR, exist_ok=True)

class BaseExpertResponse(BaseModel):
    """Base model for expert responses"""
    explanation: str = Field(..., description="Detailed explanation of the response")
    recommendation: str = Field(..., description="Specific recommendation or action to take")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level in the response")

class BaseTrademanAgent:
    """Base class for all TradeMan AI agents"""
    def __init__(self, model_name: str = "ollama:llama2"):
        """
        Initialize the base agent
        
        Args:
            model_name: Name of the LLM model to use
        """
        self.model_name = model_name
        self.agent = Agent(model_name, result_type=BaseExpertResponse)
        logger.info(f"Initialized {self.__class__.__name__} with model {model_name}")

    def get_expertise_path(self) -> str:
        """Get the path to the expertise markdown file"""
        raise NotImplementedError("Subclasses must implement get_expertise_path")

    async def process_query(self, query: str) -> BaseExpertResponse:
        """
        Process a user query using the agent
        
        Args:
            query: User's question or request
            
        Returns:
            Processed response from the agent
        """
        try:
            # Load expertise context
            with open(self.get_expertise_path(), 'r') as f:
                expertise = f.read()
                
            # Combine expertise with query
            full_prompt = f"""
            Expert Context:
            {expertise}
            
            User Query:
            {query}
            
            Please provide a detailed response based on the expert context above.
            """
            
            response = await self.agent.run(full_prompt)
            logger.info(f"Successfully processed query with {self.__class__.__name__}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing query with {self.__class__.__name__}: {str(e)}")
            raise

class MorningScriptsAgent(BaseTrademanAgent):
    """Agent specialized in morning trading scripts and procedures"""
    def get_expertise_path(self) -> str:
        return os.path.join(EXPERTS_DIR, 'MorningScripts.md')

class EveningScriptsAgent(BaseTrademanAgent):
    """Agent specialized in evening trading scripts and procedures"""
    def get_expertise_path(self) -> str:
        return os.path.join(EXPERTS_DIR, 'EveningScripts.md')

class StrategyScriptsAgent(BaseTrademanAgent):
    """Agent specialized in trading strategy scripts"""
    def get_expertise_path(self) -> str:
        return os.path.join(EXPERTS_DIR, 'StrategyScripts.md')

class WeeklyReportsAgent(BaseTrademanAgent):
    """Agent specialized in weekly trading reports"""
    def get_expertise_path(self) -> str:
        return os.path.join(EXPERTS_DIR, 'WeeklyReports.md')

class CeleryScriptsAgent(BaseTrademanAgent):
    """Agent specialized in Celery task management"""
    def get_expertise_path(self) -> str:
        return os.path.join(EXPERTS_DIR, 'CeleryScripts.md')

class RestartScriptsAgent(BaseTrademanAgent):
    """Agent specialized in system restart procedures"""
    def get_expertise_path(self) -> str:
        return os.path.join(EXPERTS_DIR, 'RestartScripts.md')

class MigrationScriptsAgent(BaseTrademanAgent):
    """Agent specialized in database migration procedures"""
    def get_expertise_path(self) -> str:
        return os.path.join(EXPERTS_DIR, 'MigrationScripts.md')

class APITestingAgent(BaseTrademanAgent):
    """Agent specialized in API testing procedures"""
    def get_expertise_path(self) -> str:
        return os.path.join(EXPERTS_DIR, 'APITesting.md')

def get_agent_for_category(category: int) -> Optional[BaseTrademanAgent]:
    """
    Factory function to get the appropriate agent for a category
    
    Args:
        category: Category number from the menu
        
    Returns:
        Appropriate agent instance or None if category is invalid
    """
    agents = {
        1: MorningScriptsAgent,
        2: EveningScriptsAgent,
        3: StrategyScriptsAgent,
        4: WeeklyReportsAgent,
        5: CeleryScriptsAgent,
        6: RestartScriptsAgent,
        7: MigrationScriptsAgent,
        8: APITestingAgent
    }
    
    agent_class = agents.get(category)
    if agent_class:
        return agent_class()
    return None
