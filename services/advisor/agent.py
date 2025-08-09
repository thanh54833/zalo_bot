import logging
from typing import List, Dict, Union
import os

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain.callbacks.tracers import LangChainTracer
from langchain.smith import RunEvalConfig
from langsmith import Client

from services.advisor.prompts import SYSTEM_PROMPT
from services.config import is_langsmith_configured, LANGCHAIN_PROJECT
from services.advisor.tools.google_search_tool import GoogleSearchTool
from services.advisor.tools.scraper_content_tool import ScraperContentTool

# Configure logging
logger = logging.getLogger(__name__)

class AgentAdvisor:
    """Simple class to manage a ReAct agent with LangSmith integration"""

    def __init__(self):
        """
        Initialize the model with default values and build the agent.
        Integrates with LangSmith if configured.
        """
        # Initialize LangSmith tracer if configured
        self.callbacks = []
        if is_langsmith_configured:
            try:
                self.tracer = LangChainTracer(project_name=LANGCHAIN_PROJECT)
                self.callbacks.append(self.tracer)
                logger.info(f"LangSmith tracer initialized for project: {LANGCHAIN_PROJECT}")
                
                # Initialize LangSmith client
                self.client = Client()
            except Exception as e:
                logger.error(f"Error initializing LangSmith: {e}")
        
        # Initialize the LLM
        self.llm = ChatGroq(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=0.0,
            max_tokens=1024,
            callbacks=self.callbacks
        )

        # Initialize tools
        self.tools = [
            GoogleSearchTool(),
            ScraperContentTool()
        ]
        logger.info(f"Initialized tools: {[tool.name for tool in self.tools]}")

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
            # Prepare input
            if isinstance(messages, dict) and 'messages' in messages:
                input_data = messages
            else:
                input_data = {"messages": messages}
            
            # Add run metadata if LangSmith is configured
            if is_langsmith_configured:
                metadata = {
                    "source": "zalo_bot",
                    "conversation_id": str(hash(str(messages))),
                    "user_id": "zalo_user"
                }
                
                # Try to extract user message for better tracing
                if isinstance(messages, dict) and 'messages' in messages and messages['messages']:
                    user_msg = next((m for m in messages['messages'] if m.get('role') == 'user'), None)
                    if user_msg and 'content' in user_msg:
                        metadata["user_query"] = user_msg['content'][:100]  # First 100 chars
            
                # Invoke with metadata
                return self.agent.invoke(input_data, config={"metadata": metadata})
            
            # Regular invoke without metadata
            return self.agent.invoke(input_data)
            
        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            raise

    def run_evaluation(self, eval_config=None):
        """
        Run evaluation on recent agent runs
        
        Args:
            eval_config: Optional evaluation configuration
        """
        if not is_langsmith_configured:
            logger.warning("LangSmith not configured. Cannot run evaluation.")
            return
            
        try:
            if eval_config is None:
                eval_config = RunEvalConfig(
                    evaluators=["qa"]  # Default QA evaluator
                )
                
            self.client.run_evaluation(
                project_name=LANGCHAIN_PROJECT,
                eval_config=eval_config
            )
            logger.info(f"Evaluation started for project {LANGCHAIN_PROJECT}")
        except Exception as e:
            logger.error(f"Error running evaluation: {e}")

# Create a default instance of AgentAdvisor
agent_advisor = AgentAdvisor()
