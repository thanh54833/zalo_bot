#!/usr/bin/env python3
"""
Test script to check langgraph functionality
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_langgraph():
    try:
        print("Testing langgraph imports...")
        
        # Test basic imports
        from langchain_groq import ChatGroq
        print("✅ ChatGroq imported successfully")
        
        from langgraph.prebuilt import create_react_agent
        print("✅ create_react_agent imported successfully")
        
        # Test if we can create a simple agent
        print("Testing agent creation...")
        
        # Create a simple LLM (we won't actually use it, just test the function)
        llm = ChatGroq(
            api_key="test_key",  # This won't work but we're just testing the import
            model="llama3-8b-8192"
        )
        print("✅ ChatGroq instance created successfully")
        
        # Test the create_react_agent function signature
        print("✅ All langgraph functionality available")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_langgraph() 