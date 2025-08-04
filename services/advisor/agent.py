import logging

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from services.advisor.prompts import SYSTEM_PROMPT

# Configure logging
logger = logging.getLogger(__name__)

class AgentAdvisor:
    """Simple class to manage a ReAct agent"""
    
    def __init__(self):
        """
        Initialize the model with default values and build the agent.
        No input parameters required.
        """
        # Initialize the LLM
        self.llm = ChatGroq(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=1.0,
            max_tokens=1024,
        )
        
        # Initialize empty tools list
        self.tools = []
        
        # Get the default prompt
        self.prompt = SYSTEM_PROMPT
        
        # Build the agent
        self.agent = self.build()
        
        logger.info("Initialized AgentAdvisor with default configuration")
        
    def build(self):
        """Build the ReAct agent with current configuration"""
        agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        logger.info("Built agent with default configuration")
        return agent

# Create a default instance of AgentAdvisor
agent_advisor = AgentAdvisor()
