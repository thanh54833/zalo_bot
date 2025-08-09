import logging
from typing import List, Dict, Union
import os
import asyncio

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain.callbacks.tracers import LangChainTracer
from langchain.smith import RunEvalConfig
from langsmith import Client

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
        
        # Load agent configuration or use defaults
        self.load_config()
        
        # Build the agent
        self.agent = self.build()
        logger.info(f"Initialized AgentAdvisor with configuration for agent: {agent_id}")

    def load_config(self):
        """Load configuration from the config manager"""
        # Get agent config from new structure
        agent_config = config_manager.settings.agent_config
        
        # Initialize with values from config or defaults
        self.model_name = agent_config.model.name
        self.temperature = agent_config.model.temperature
        self.max_tokens = agent_config.model.max_tokens
        self.prompt = agent_config.system_prompt
        self.enabled_tools = agent_config.tools or ["google_search", "scraper_content"]
        
        # Initialize the LLM with config values
        try:
            # Check for API key
            api_key = os.environ.get("GROQ_API_KEY") or agent_config.model.api_key
            if not api_key:
                logger.warning("GROQ_API_KEY not found in environment, using mock LLM for testing")
                # For testing without API key, use a simple mock
                from langchain.schema import AIMessage
                class MockLLM:
                    def __init__(self, **kwargs):
                        self.kwargs = kwargs
                    def invoke(self, messages, **kwargs):
                        return AIMessage(content="This is a mock response for testing")
                self.llm = MockLLM(
                    model=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
            else:
                self.llm = ChatGroq(
                    model=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    callbacks=self.callbacks
                )
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            # Use a simple mock for testing
            from langchain.schema import AIMessage
            class MockLLM:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs
                def invoke(self, messages, **kwargs):
                    return AIMessage(content="This is a mock response for testing")
            self.llm = MockLLM(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
        
        # Initialize tools based on configuration
        self.tools = []
        if "google_search" in self.enabled_tools:
            self.tools.append(GoogleSearchTool())
        if "scraper_content" in self.enabled_tools:
            self.tools.append(ScraperContentTool())
            
        logger.info(f"Loaded configuration: model={self.model_name}, tools={[tool.name for tool in self.tools]}")

    def _save_config_sync(self):
        """Save the current configuration to the config manager (synchronous version)"""
        # Create a task in the event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule the task for later execution
            asyncio.create_task(self._save_config())
        else:
            # Run the coroutine in a new event loop
            asyncio.run(self._save_config())

    async def _save_config(self):
        """Save the current configuration to the config manager"""
        # Update the config with current values
        await config_manager.update({
            "agent_config": {
                "system_prompt": self.prompt,
                "tools": self.enabled_tools,
                "model": {
                    "name": self.model_name,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "provider": "groq"
                }
            }
        })

    def build(self):
        """Build the ReAct agent with current configuration"""
        try:
            agent = create_react_agent(
                model=self.llm,
                tools=self.tools,
                prompt=self.prompt
            )
            logger.info(f"Built agent {self.agent_id} with configuration")
            return agent
        except Exception as e:
            logger.error(f"Error building agent: {e}")
            # Return a simple function that returns a mock response
            def mock_agent(input_data):
                return {"output": "This is a mock response for testing"}
            return mock_agent

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

    def run_evaluation(self, eval_config=None):
        """
        Run evaluation on recent agent runs
        
        Args:
            eval_config: Optional evaluation configuration
        """
        if not integration_manager.is_langsmith_configured:
            logger.warning("LangSmith not configured. Cannot run evaluation.")
            return
            
        try:
            if eval_config is None:
                eval_config = RunEvalConfig(
                    evaluators=["qa"]  # Default QA evaluator
                )
                
            project_name = integration_manager.get_langsmith_project()
            self.client.run_evaluation(
                project_name=project_name,
                eval_config=eval_config
            )
            logger.info(f"Evaluation started for project {project_name}")
        except Exception as e:
            logger.error(f"Error running evaluation: {e}")

    async def update_config(self, config_data):
        """
        Update the agent's configuration
        
        Args:
            config_data: Dictionary with configuration values to update
        """
        # Update local values
        if "prompt" in config_data:
            self.prompt = config_data["prompt"]
        
        if "tools" in config_data:
            self.enabled_tools = config_data["tools"]
            
        if "model" in config_data:
            model_data = config_data["model"]
            if "name" in model_data:
                self.model_name = model_data["name"]
            if "temperature" in model_data:
                self.temperature = model_data["temperature"]
            if "max_tokens" in model_data:
                self.max_tokens = model_data["max_tokens"]
                
            # Update the LLM
            try:
                api_key = os.environ.get("GROQ_API_KEY")
                if api_key:
                    self.llm = ChatGroq(
                        model=self.model_name,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        callbacks=self.callbacks
                    )
            except Exception as e:
                logger.error(f"Error updating LLM: {e}")
        
        # Reload tools
        self.tools = []
        if "google_search" in self.enabled_tools:
            self.tools.append(GoogleSearchTool())
        if "scraper_content" in self.enabled_tools:
            self.tools.append(ScraperContentTool())
        
        # Save to config manager
        await self._save_config()
        
        # Rebuild the agent
        self.agent = self.build()
        logger.info(f"Updated configuration for agent {self.agent_id}")


# Create a default instance of AgentAdvisor
agent_advisor = AgentAdvisor()
