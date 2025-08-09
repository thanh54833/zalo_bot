"""Test script for system prompt configuration.

This script demonstrates how the system prompt is loaded from configuration.
"""

import asyncio
import logging
from services.config import config_manager
from services.advisor.prompts import get_system_prompt
from services.advisor.update_prompt import update_system_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_prompt_config():
    """Test the system prompt configuration."""
    print("Starting system prompt test...")
    
    # Start the config system
    await config_manager.start()
    
    # Get the current prompt
    current_prompt = get_system_prompt()
    print(f"Current system prompt (first 50 chars): {current_prompt[:50]}...")
    
    # Update the prompt
    new_prompt = "This is a test prompt for the agent."
    await config_manager.patch_global({
        "default_system_prompt": new_prompt
    })
    
    # Verify the update by getting it again
    updated_prompt = get_system_prompt()
    print(f"Updated system prompt: {updated_prompt}")
    
    # Reset to default
    await update_system_prompt()
    reset_prompt = get_system_prompt()
    print(f"Reset system prompt (first 50 chars): {reset_prompt[:50]}...")
    
    # Stop the config system
    await config_manager.stop()
    print("System prompt test completed!")


if __name__ == "__main__":
    asyncio.run(test_prompt_config()) 