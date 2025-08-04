import logging
from typing import List, Dict, Union

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

    def invoke(self, messages: Union[List[Dict[str, str]], Dict[str, List[Dict[str, str]]]]):
        """
        Invoke the agent with the given messages.

        Args:
            messages: Either a list of message dictionaries or a dictionary with a 'messages' key

        Returns:
            The agent's response
        """
        try:
            # Handle both direct message list and dictionary with 'messages' key
            if isinstance(messages, dict) and 'messages' in messages:
                return self.agent.invoke(messages)
            else:
                return self.agent.invoke({"messages": messages})
        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            raise

# Create a default instance of AgentAdvisor
agent_advisor = AgentAdvisor()
