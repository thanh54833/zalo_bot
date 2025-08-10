import logging
from typing import List, Dict, Union, Any
import os
import asyncio

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain.callbacks.tracers import LangChainTracer
from langchain.smith import RunEvalConfig
from langsmith import Client
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from services.app_settings import config_manager
from services.integrations import integration_manager
from services.advisor.tools.google_search_tool import GoogleSearchTool
from services.advisor.tools.scraper_content_tool import ScraperContentTool

# Configure logging
logger = logging.getLogger(__name__)


class AgentAdvisor:
    """Agent manager that uses the configuration system for settings"""

    def __init__(self, agent_id="default"):
        """
        Initialize the model with configuration values and build the agent.
        
        Args:
            agent_id: The ID of the agent configuration to use
        """
        self.agent_id = agent_id
        self.is_enabled = False
        self.is_initialized = False
        self.llm = None
        self.tools = []
        self.agent = None
        self.model_name = None
        self.enabled_tools = []

        # Initialize LangSmith tracer if configured
        self.callbacks = []
        if integration_manager.is_langsmith_configured:
            try:
                project_name = integration_manager.get_langsmith_project()
                self.tracer = LangChainTracer(project_name=project_name)
                self.callbacks.append(self.tracer)
                logger.info(f"LangSmith tracer initialized for project: {project_name}")

                # Initialize LangSmith client
                self.client = integration_manager.langsmith_client
            except Exception as e:
                logger.error(f"Error initializing LangSmith: {e}")

        # Initialize based on config
        if config_manager.settings.agent_config.enabled:
            self.initialize()
            
    async def handle_enabled_state_change(self, is_enabled: bool):
        """Handle changes to the enabled state"""
        if is_enabled and not self.is_initialized:
            self.initialize()
        elif not is_enabled and self.is_initialized:
            self.shutdown()

    def initialize(self):
        """Initialize the agent with the current configuration"""
        if self.is_initialized:
            logger.info("Agent is already initialized.")
            return True

        try:
            # Load configuration
            agent_config = config_manager.settings.agent_config
            self.is_enabled = agent_config.enabled

            if not self.is_enabled:
                logger.info("Agent is disabled. Not initializing.")
                return False

            self.model_name = agent_config.model.name
            self.temperature = agent_config.model.temperature
            self.max_tokens = agent_config.model.max_tokens
            self.prompt = agent_config.system_prompt
            self.enabled_tools = agent_config.tools or ["google_search", "scraper_content"]
            logger.info(f"Loaded configuration for agent {self.agent_id}. Enabled: {self.is_enabled}")

            # Initialize the LLM
            api_key = config_manager.settings.agent_config.model.api_key

            if not api_key:
                logger.error("GROQ_API_KEY not found in config. Agent cannot be initialized.")
                return False

            self.llm = ChatGroq(
                api_key=api_key,
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                callbacks=self.callbacks
            )
            logger.info(f"Initialized ChatGroq with model {self.model_name}")

            # Initialize tools
            self.tools = []
            if "google_search" in self.enabled_tools:
                self.tools.append(GoogleSearchTool())
            if "scraper_content" in self.enabled_tools:
                self.tools.append(ScraperContentTool())
            logger.info(f"Initialized tools: {[tool.name for tool in self.tools]}")

            # Build the agent
            if not self.llm:
                logger.error("LLM not initialized. Cannot build agent.")
                return False

            self.agent = create_react_agent(
                model=self.llm,
                tools=self.tools,
                prompt=self.prompt
            )
            logger.info(f"Built agent {self.agent_id} with configuration")

            self.is_initialized = True
            logger.info(f"Agent {self.agent_id} initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing agent: {e}")
            self.is_initialized = False
            return False

    def shutdown(self):
        """Shutdown the agent and clean up resources"""
        if not self.is_initialized:
            return

        try:
            # Clean up tools
            for tool in self.tools:
                if hasattr(tool, 'close') and callable(tool.close):
                    try:
                        tool.close()
                    except Exception as e:
                        logger.error(f"Error closing tool {tool.name}: {e}")

            self.agent = None
            self.is_initialized = False
            logger.info(f"Agent {self.agent_id} shutdown complete")
        except Exception as e:
            logger.error(f"Error during agent shutdown: {e}")

    def invoke(self, messages: Union[List[Dict[str, str]], Dict[str, List[Dict[str, str]]]]):
        """
        Invoke the agent with the given messages.

        Args:
            messages: Either a list of message dictionaries or a dictionary with a 'messages' key

        Returns:
            The agent's response
        """
        # Check if agent is enabled and initialized
        if not self.is_enabled:
            logger.warning("Agent is disabled. Cannot process message.")
            return {"output": "Agent is currently disabled."}

        if not self.is_initialized or self.agent is None:
            logger.warning("Agent is not initialized. Attempting to initialize...")
            if not self.initialize():
                return {"output": "Agent could not be initialized. Please check the logs."}

        try:
            # Prepare input
            if isinstance(messages, dict) and 'messages' in messages:
                input_data = messages
            else:
                input_data = {"messages": messages}

            # Add run metadata if LangSmith is configured
            if integration_manager.is_langsmith_configured:
                metadata = {
                    "source": "zalo_bot",
                    "conversation_id": str(hash(str(messages))),
                    "user_id": "zalo_user",
                    "agent_id": self.agent_id
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
            return {"output": f"Error: {str(e)}"}

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent"""
        return {
            "enabled": self.is_enabled,
            "initialized": self.is_initialized,
            "has_agent": self.agent is not None,
            "model": self.model_name,
            "tools": self.enabled_tools
        }



