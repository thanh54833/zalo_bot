"""Prompt management for the advisor agent.

This module provides access to the system prompt from the global configuration.
"""

from services.config import config_manager

def get_system_prompt():
    """Get the system prompt from the global configuration.
    
    Returns:
        str: The default system prompt
    """
    return config_manager.get_global().default_system_prompt

# For backward compatibility
SYSTEM_PROMPT = get_system_prompt()
