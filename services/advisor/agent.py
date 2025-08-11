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
from services.advisor.tools.api_tool import create_auto_api_tools

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
        
        #  Tool management từ config
        self.tool_instances = {}  # Cache cho tool instances
        self.tool_configs = {}    # Cache cho tool configs
        self.last_config_check = 0
        self.config_check_interval = 30  # Check config mỗi 30 giây

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

    def _load_tool_configs_from_file(self) -> Dict[str, Dict[str, Any]]:
        """Load tool configurations từ app_config.json"""
        try:
            agent_config = config_manager.settings.agent_config
            tools_config = {}
            
            for tool_config in agent_config.tools:
                tool_name = tool_config.get("name")
                if tool_name:
                    tools_config[tool_name] = tool_config
                    logger.debug(f"Loaded tool config: {tool_name} (type: {tool_config.get('type')})")
            
            logger.info(f"Loaded {len(tools_config)} tool configurations from file")
            return tools_config
            
        except Exception as e:
            logger.error(f"Failed to load tool configs: {e}")
            return {}

    def _create_tool_instance(self, tool_name: str, tool_config: Dict[str, Any]):
        """Tạo tool instance dựa trên config"""
        try:
            tool_type = tool_config.get("type")
            
            if tool_type == "web_search":
                # ✅ TẠO TOOLS VỚI CONFIG
                if tool_name == "google_search":
                    return GoogleSearchTool(tool_config)  # ✅ TRUYỀN CONFIG
                elif tool_name == "scraper_content":
                    return ScraperContentTool(tool_config)  # ✅ TRUYỀN CONFIG
                else:
                    logger.warning(f"Unknown web_search tool: {tool_name}")
                    return None
                    
            elif tool_type == "api_tool":
                # API tools từ auto-scanner
                try:
                    from services.advisor.tools.api_tool import create_auto_api_tool
                    return create_auto_api_tool(tool_name)
                except Exception as e:
                    logger.error(f"Failed to create API tool {tool_name}: {e}")
                    return None
                    
            else:
                logger.warning(f"Unknown tool type: {tool_type} for {tool_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create tool instance for {tool_name}: {e}")
            return None

    def _load_tools_from_config(self) -> List:
        """Load tất cả tools từ config file"""
        tools = []
        
        # 🆕 Load tool configs từ file
        self.tool_configs = self._load_tool_configs_from_file()
        
        for tool_name, tool_config in self.tool_configs.items():
            # Kiểm tra tool có được enable không
            if not tool_config.get("enabled", True):
                logger.debug(f"Tool {tool_name} is disabled, skipping")
                continue
            
            # Tạo tool instance
            tool_instance = self._create_tool_instance(tool_name, tool_config)
            if tool_instance:
                self.tool_instances[tool_name] = tool_instance
                tools.append(tool_instance)
                logger.info(f"✅ Loaded tool: {tool_name} (type: {tool_config.get('type')})")
            else:
                logger.error(f"❌ Failed to load tool: {tool_name}")
        
        logger.info(f"Total tools loaded: {len(tools)}")
        return tools

    def _should_refresh_tools(self) -> bool:
        """Kiểm tra xem có cần refresh tools không"""
        import time
        current_time = time.time()
        return (current_time - self.last_config_check) > self.config_check_interval

    def _refresh_tools_if_needed(self):
        """Refresh tools nếu cần thiết"""
        if self._should_refresh_tools():
            logger.debug("Checking for tool config updates...")
            self._load_tools_from_config()
            self.last_config_check = time.time()

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
            
            # 🆕 KHÔNG hard-code tools nữa - lấy từ config
            logger.info(f"Loading tools from configuration file...")

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

            # 🆕 Load tools từ config file
            self.tools = self._load_tools_from_config()
            
            if not self.tools:
                logger.warning("No tools loaded from configuration. Agent may not function properly.")

            # Build the agent
            if not self.llm:
                logger.error("LLM not initialized. Cannot build agent.")
                return False

            self.agent = create_react_agent(
                model=self.llm,
                tools=self.tools,
                prompt=self.prompt
            )
            logger.info(f"Built agent {self.agent_id} with {len(self.tools)} tools")

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
            for tool_name, tool in self.tool_instances.items():
                if hasattr(tool, 'close') and callable(tool.close):
                    try:
                        tool.close()
                    except Exception as e:
                        logger.error(f"Error closing tool {tool_name}: {e}")

            self.tool_instances.clear()
            self.tools.clear()
            self.agent = None
            self.is_initialized = False
            logger.info(f"Agent {self.agent_id} shutdown complete")
        except Exception as e:
            logger.error(f"Error during agent shutdown: {e}")

    def invoke(self, messages: Union[List[Dict[str, str]], Dict[str, List[Dict[str, str]]]]):
        """
        Invoke the agent with the given messages.
        """
        # Check if agent is enabled and initialized
        if not self.is_enabled:
            logger.warning("Agent is disabled. Cannot process message.")
            return {"output": "Agent is currently disabled."}

        if not self.is_initialized or self.agent is None:
            logger.warning("Agent is not initialized. Attempting to initialize...")
            if not self.initialize():
                return {"output": "Agent could not be initialized. Please check the logs."}

        #  Auto-refresh tools nếu cần
        self._refresh_tools_if_needed()

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
            "total_tools": len(self.tools),
            "tool_details": self._get_tool_details()
        }

    def _get_tool_details(self) -> Dict[str, Any]:
        """Get detailed information về tools"""
        tool_details = {}
        
        for tool_name, tool_config in self.tool_configs.items():
            tool_details[tool_name] = {
                "type": tool_config.get("type"),
                "enabled": tool_config.get("enabled", True),
                "description": tool_config.get("description", ""),
                "category": tool_config.get("category", "unknown"),
                "loaded": tool_name in self.tool_instances,
                "dependencies": tool_config.get("dependencies", [])
            }
        
        return tool_details

    def refresh_tools(self) -> bool:
        """Manually refresh tools từ config file"""
        try:
            logger.info("Manually refreshing tools from configuration...")
            old_tools_count = len(self.tools)
            
            # Reload tools
            self.tools = self._load_tools_from_config()
            
            # Rebuild agent với tools mới
            if self.llm:
                self.agent = create_react_agent(
                    model=self.llm,
                    tools=self.tools,
                    prompt=self.prompt
                )
                logger.info(f"Tools refreshed: {old_tools_count} -> {len(self.tools)}")
                return True
        except Exception as e:
            logger.error(f"Failed to refresh tools: {e}")
            return False

    def get_tool_info(self, tool_name: str = None) -> Dict[str, Any]:
        """Get detailed information về tool cụ thể hoặc tất cả tools"""
        if tool_name:
            if tool_name in self.tool_configs:
                return {
                    "config": self.tool_configs[tool_name],
                    "instance": tool_name in self.tool_instances,
                    "status": "loaded" if tool_name in self.tool_instances else "not_loaded"
                }
            else:
                return {"error": f"Tool {tool_name} not found in configuration"}
        
        return {
            "total_tools": len(self.tools),
            "loaded_tools": list(self.tool_instances.keys()),
            "config_tools": list(self.tool_configs.keys()),
            "tool_details": self._get_tool_details()
        }



