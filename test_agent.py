#!/usr/bin/env python3
"""
Test script to debug agent initialization
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_agent():
    try:
        print("Testing agent initialization...")
        
        # Test config loading
        from services.app_settings import config_manager
        print("✅ Config manager imported successfully")
        
        await config_manager.load()
        print("✅ Config loaded successfully")
        
        # Test agent creation
        from services.advisor.agent import AgentAdvisor
        print("✅ AgentAdvisor imported successfully")
        
        agent = AgentAdvisor()
        print("✅ Agent created successfully")
        
        # Test agent initialization
        if agent.initialize():
            print("✅ Agent initialized successfully")
            print(f"Agent status: {agent.get_status()}")
        else:
            print("❌ Agent initialization failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent()) 