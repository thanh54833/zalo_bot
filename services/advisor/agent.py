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

# Define a proper MockLLM that is compatible with langgraph
class MockLLM(BaseChatModel):
    """Mock LLM for testing when API key is not available"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kwargs = kwargs
        
    def invoke(self, messages, **kwargs):
        return AIMessage(content="This is a mock response for testing")
    
    def bind_tools(self, tools, **kwargs):
        """Required for compatibility with langgraph's create_react_agent"""
        return self
        
    @property
    def _llm_type(self):
        return "mock"

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
        
        # Load configuration
        self.load_config()
        
        # Only initialize if enabled
        if self.is_enabled:
            self.initialize()

    def load_config(self):
        """Load configuration from the config manager"""
        # Get agent config from new structure
        agent_config = config_manager.settings.agent_config
        
        # Check if agent is enabled
        self.is_enabled = agent_config.enabled
        
        # Initialize with values from config or defaults
        self.model_name = agent_config.model.name
        self.temperature = agent_config.model.temperature
        self.max_tokens = agent_config.model.max_tokens
        self.prompt = agent_config.system_prompt
        self.enabled_tools = agent_config.tools or ["google_search", "scraper_content"]
        
        logger.info(f"Loaded configuration for agent {self.agent_id}. Enabled: {self.is_enabled}")
        
    def initialize(self):
        """Initialize the agent with the current configuration"""
        if not self.is_enabled:
            logger.info("Agent is disabled. Not initializing.")
            return False
            
        if self.is_initialized:
            logger.info("Agent is already initialized.")
            return True
            
        try:
            # Initialize the LLM
            self._initialize_llm()
            
            # Initialize tools
            self._initialize_tools()
            
            # Build the agent
            self.agent = self.build()
            
            self.is_initialized = True
            logger.info(f"Agent {self.agent_id} initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing agent: {e}")
            self.is_initialized = False
            return False
    
    def _initialize_llm(self):
        """Initialize the LLM with current configuration"""
        try:
            # Check for API key - try environment first, then config
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                # If not in environment, use from config
                api_key = config_manager.settings.agent_config.model.api_key
                
                # Set it in environment for libraries that expect it there
                if api_key:
                    os.environ["GROQ_API_KEY"] = api_key
            
            if not api_key:
                logger.warning("GROQ_API_KEY not found in environment or config, using mock LLM for testing")
                # For testing without API key, use our custom mock
                self.llm = MockLLM(
                    model=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
            else:
                self.llm = ChatGroq(
                    api_key=api_key,  # Explicitly pass the API key
                    model=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    callbacks=self.callbacks
                )
                logger.info(f"Initialized ChatGroq with model {self.model_name}")
            
            return True
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            # Use our custom mock for testing
            self.llm = MockLLM(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return False
    
    def _initialize_tools(self):
        """Initialize tools based on configuration"""
        self.tools = []
        if "google_search" in self.enabled_tools:
            self.tools.append(GoogleSearchTool())
        if "scraper_content" in self.enabled_tools:
            self.tools.append(ScraperContentTool())
            
        logger.info(f"Initialized tools: {[tool.name for tool in self.tools]}")
        return True

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
                "enabled": self.is_enabled,
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
        if not self.is_enabled:
            logger.info("Agent is disabled. Not building.")
            return None
            
        if not self.llm:
            logger.error("LLM not initialized. Cannot build agent.")
            return None
            
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
                return {"output": "This is a mock response for testing. Agent could not be built properly."}
            return mock_agent
    
    def shutdown(self):
        """Shutdown the agent and clean up resources"""
        if not self.is_initialized:
            return
            
        try:
            # Clean up LLM resources if any
            if self.llm and hasattr(self.llm, 'client'):
                try:
                    # Try to close client connections
                    if hasattr(self.llm.client, 'close'):
                        self.llm.client.close()
                    elif hasattr(self.llm.client, 'aclose'):
                        # Create a task to close async client
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self.llm.client.aclose())
                    
                    logger.info("Closed LLM client connections")
                except Exception as e:
                    logger.error(f"Error closing LLM client: {e}")
            
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

    def run_evaluation(self, eval_config=None):
        """
        Run evaluation on recent agent runs
        
        Args:
            eval_config: Optional evaluation configuration
        """
        if not self.is_enabled:
            logger.warning("Agent is disabled. Cannot run evaluation.")
            return
            
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

    async def handle_enabled_state_change(self, new_state: bool):
        """
        Handle changes to the enabled state
        
        Args:
            new_state: The new enabled state
        """
        if new_state == self.is_enabled:
            # No change
            return
            
        old_state = self.is_enabled
        self.is_enabled = new_state
        logger.info(f"Agent enabled state changed: {old_state} -> {new_state}")
        
        if new_state:
            # Agent was enabled
            logger.info("Agent was enabled. Initializing...")
            self.initialize()
        else:
            # Agent was disabled
            logger.info("Agent was disabled. Cleaning up...")
            self.shutdown()
            
        # Save the new state to config
        await self._save_config()

    async def update_config(self, config_data):
        """
        Update the agent's configuration
        
        Args:
            config_data: Dictionary with configuration values to update
        """
        # Check if enabled status is changing
        if "enabled" in config_data:
            new_enabled = config_data["enabled"]
            if new_enabled != self.is_enabled:
                await self.handle_enabled_state_change(new_enabled)
            
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
        
        # Save to config manager
        await self._save_config()
        
        # Rebuild the agent if enabled
        if self.is_enabled and self.is_initialized:
            # Shutdown first
            self.shutdown()
            # Then reinitialize
            self.initialize()
            logger.info(f"Updated configuration for agent {self.agent_id}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent"""
        return {
            "enabled": self.is_enabled,
            "initialized": self.is_initialized,
            "has_agent": self.agent is not None,
            "model": self.model_name,
            "tools": self.enabled_tools
        }


# Create a default instance of AgentAdvisor
agent_advisor = AgentAdvisor()
