"""Prompt management for the advisor agent.

This module provides access to the system prompt from the global configuration.
"""

from services.app_settings import config_manager

def get_system_prompt():
    """Get the system prompt from the agent configuration.
    
    Returns:
        str: The system prompt
    """
    return config_manager.settings.agent_config.system_prompt

# For backward compatibility
SYSTEM_PROMPT = get_system_prompt()
