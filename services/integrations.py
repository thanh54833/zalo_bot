"""
Integration manager for external services like LangSmith.
"""

import os
import logging
from langsmith import Client

# Configure logging
logger = logging.getLogger(__name__)

class IntegrationManager:
    """Manager for external service integrations"""
    
    def __init__(self):
        """Initialize integration manager and check for configured services"""
        # LangSmith integration
        self.is_langsmith_configured = all([
            os.environ.get("LANGCHAIN_API_KEY"),
            os.environ.get("LANGCHAIN_PROJECT"),
            os.environ.get("LANGCHAIN_ENDPOINT")
        ])
        
        if self.is_langsmith_configured:
            self.langsmith_client = Client()
            logger.info("LangSmith integration configured")
        else:
            self.langsmith_client = None
            logger.info("LangSmith integration not configured")
    
    def get_langsmith_project(self):
        """Get the configured LangSmith project name"""
        return os.environ.get("LANGCHAIN_PROJECT", "default")

# Singleton instance
integration_manager = IntegrationManager() 