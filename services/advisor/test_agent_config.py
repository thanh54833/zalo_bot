"""Test script for agent configuration integration.

This script demonstrates how to use the agent with the configuration system.
"""

import asyncio
import logging
from services.config import config_manager
from services.advisor.agent import AgentAdvisor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_agent_config():
    """Test the agent configuration integration."""
    print("Starting agent configuration test...")
    
    # Start the config system
    await config_manager.start()
    
    # Create an agent with a custom ID
    custom_agent = AgentAdvisor(agent_id="test_agent")
    
    # Update the agent configuration
    await custom_agent.update_config({
        "prompt": "Bạn là trợ lý AI chuyên về tài chính. Hãy trả lời ngắn gọn và chính xác.",
        "tools": ["google_search"],
        "model": {
            "temperature": 0.3,
            "max_tokens": 2048
        }
    })
    
    # Verify the configuration was saved
    agent_config = config_manager.get_agent("test_agent")
    model_config = config_manager.get_model("test_agent")
    
    print(f"Agent config: prompt={agent_config.prompt[:30]}..., tools={agent_config.tools}")
    print(f"Model config: temperature={model_config.temperature}, max_tokens={model_config.max_tokens}")
    
    # Create another instance with the same ID to test loading from config
    print("\nCreating a new instance with the same ID to test loading from config...")
    loaded_agent = AgentAdvisor(agent_id="test_agent")
    
    # Test invoking the agent
    print("\nTesting agent invocation...")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, who are you?"}
    ]
    
    try:
        # We're not actually going to run this since it would make API calls
        # Just showing how it would be used
        print("(Skipping actual API call for testing purposes)")
        # response = loaded_agent.invoke(messages)
        # print(f"Agent response: {response}")
    except Exception as e:
        print(f"Error invoking agent: {e}")
    
    # Stop the config system
    await config_manager.stop()
    print("Agent configuration test completed!")


if __name__ == "__main__":
    asyncio.run(test_agent_config()) 