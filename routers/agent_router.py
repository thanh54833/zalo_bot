import logging
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from pydantic import BaseModel
import datetime
import os

from services.app_settings import config_manager
# Remove the direct import - we'll get it dynamically
# from services.advisor import agent_advisor

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/agent",
    tags=["agent"],
    responses={404: {"description": "Not found"}},
)


def get_agent_advisor():
    """Get the agent_advisor instance dynamically"""
    try:
        from services.advisor import agent_advisor
        return agent_advisor
    except ImportError:
        logger.error("Failed to import agent_advisor")
        return None


@router.get("/status")
async def get_agent_status():
    """Get the current status of the AI agent"""
    try:
        agent_advisor = get_agent_advisor()
        if agent_advisor is None:
            raise HTTPException(status_code=500, detail="Agent advisor not available")
            
        status = agent_advisor.get_status()
        status["config_enabled"] = config_manager.settings.agent_config.enabled
        return status
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/initialize")
async def initialize_agent():
    """Initialize the agent if it's not already initialized"""
    try:
        if not config_manager.settings.agent_config.enabled:
            raise HTTPException(
                status_code=400,
                detail="Cannot initialize agent because it's disabled in configuration",
            )

        agent_advisor = get_agent_advisor()
        if agent_advisor is None:
            raise HTTPException(status_code=500, detail="Agent advisor not available")

        if agent_advisor.is_initialized:
            return {
                "status": "already_initialized",
                "message": "Agent is already initialized",
            }

        success = agent_advisor.initialize()
        if success:
            return {
                "status": "initialized",
                "message": "Agent initialized successfully",
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize agent")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shutdown")
async def shutdown_agent():
    """Shutdown the agent and clean up resources"""
    try:
        agent_advisor = get_agent_advisor()
        if agent_advisor is None:
            raise HTTPException(status_code=500, detail="Agent advisor not available")

        if not agent_advisor.is_initialized:
            return {"status": "not_initialized", "message": "Agent is not initialized"}

        agent_advisor.shutdown()
        return {"status": "shutdown", "message": "Agent shutdown successfully"}
    except Exception as e:
        logger.error(f"Error shutting down agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_agent():
    """Reload the agent with current configuration"""
    try:
        if not config_manager.settings.agent_config.enabled:
            raise HTTPException(
                status_code=400,
                detail="Cannot reload agent because it's disabled in configuration",
            )

        agent_advisor = get_agent_advisor()
        if agent_advisor is None:
            raise HTTPException(status_code=500, detail="Agent advisor not available")

        # Shutdown if initialized
        if agent_advisor.is_initialized:
            agent_advisor.shutdown()

        # Initialize
        success = agent_advisor.initialize()
        if success:
            return {"status": "reloaded", "message": "Agent reloaded successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reload agent")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reloading agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class Message(BaseModel):
    role: str
    content: str


class InvokeRequest(BaseModel):
    messages: List[Message]


@router.post("/invoke", summary="Invoke Agent")
async def invoke_agent(request: InvokeRequest = Body(...)):
    """
    Invoke the agent with a list of messages and get a response.
    """
    try:
        # Convert Pydantic models to dictionaries
        messages_as_dicts = [message.model_dump() for message in request.messages]

        agent_advisor = get_agent_advisor()
        if agent_advisor is None:
            raise HTTPException(status_code=500, detail="Agent advisor not available")

        # Call the agent's invoke method
        response = agent_advisor.invoke(messages_as_dicts)

        return response
    except Exception as e:
        logger.error(f"Error invoking agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred while invoking the agent.",
        )


class QueryRequest(BaseModel):
    query: str


@router.post("/query", summary="Send Single Query to Agent")
async def query_agent(request: QueryRequest = Body(...)):
    """
    Send a single query to the agent and get a response.
    """
    try:
        # Create a single user message from the query
        message = {"role": "user", "content": request.query}
        
        agent_advisor = get_agent_advisor()
        if agent_advisor is None:
            raise HTTPException(status_code=500, detail="Agent advisor not available")

        # Call the agent's invoke method with the single message
        response = agent_advisor.invoke([message])
        
        return response
    except Exception as e:
        logger.error(f"Error querying agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred while querying the agent.",
        )


@router.get("/health_check", summary="System Health Check")
async def agent_health_check():
    """
    Perform comprehensive system health check without input.
    Returns detailed health status for all tools and system.
    """
    try:
        agent_advisor = get_agent_advisor()
        if agent_advisor is None:
            raise HTTPException(status_code=500, detail="Agent advisor not available")

        # Resolve API key only from config file
        api_key = config_manager.settings.agent_config.model.api_key

        # If API key missing or obviously invalid, return actionable health info without invoking LLM
        if not api_key or not api_key.strip():
            health_response = {
                "timestamp": datetime.datetime.now().isoformat(),
                "agent_response": {
                    "output": "LLM authentication not configured. Skipping agent invocation.",
                    "error": {
                        "code": "invalid_api_key",
                        "message": "Missing GROQ API key. Update agent_config.model.api_key in data/app_config.json, then POST /api/agent/reload."
                    }
                },
                "available_tools": [
                    {
                        "name": "google_search",
                        "type": "web_search",
                        "enabled": True,
                        "description": "Web search functionality via Google"
                    },
                    {
                        "name": "scraper_content",
                        "type": "content_extraction",
                        "enabled": True,
                        "description": "Content extraction from URLs"
                    },
                    {
                        "name": "search_inventory",
                        "type": "api_tool",
                        "enabled": True,
                        "description": "Product inventory search API"
                    }
                ],
                "system_status": {
                    "agent_initialized": agent_advisor.is_initialized,
                    "config_enabled": config_manager.settings.agent_config.enabled,
                    "model_provider": config_manager.settings.agent_config.model.provider,
                    "model_name": config_manager.settings.agent_config.model.name
                }
            }
            return health_response

        # Create health check message for the agent
        health_message = {
            "role": "user",
            "content": "HEALTH_CHECK_REQUEST: Please perform a comprehensive system health check. Analyze all available tools and provide detailed status reports with clear indicators (✅ Healthy, ⚠️ Warning, ❌ Error)."
        }

        # Call the agent's invoke method with health check context
        response = agent_advisor.invoke([health_message])

        # Add metadata to response
        health_response = {
            "timestamp": datetime.datetime.now().isoformat(),
            "agent_response": response,
            "available_tools": [
                {
                    "name": "google_search",
                    "type": "web_search",
                    "enabled": True,
                    "description": "Web search functionality via Google"
                },
                {
                    "name": "scraper_content",
                    "type": "content_extraction",
                    "enabled": True,
                    "description": "Content extraction from URLs"
                },
                {
                    "name": "search_inventory",
                    "type": "api_tool",
                    "enabled": True,
                    "description": "Product inventory search API"
                }
            ],
            "system_status": {
                "agent_initialized": agent_advisor.is_initialized,
                "config_enabled": config_manager.settings.agent_config.enabled,
                "model_provider": config_manager.settings.agent_config.model.provider,
                "model_name": config_manager.settings.agent_config.model.name
            }
        }

        return health_response

    except Exception as e:
        logger.error(f"Error during health check: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred during health check"
        )


@router.get("/health_status", summary="Get System Health Status")
async def get_health_status():
    """
    Get current system health status without agent processing.
    """
    try:
        agent_advisor = get_agent_advisor()
        if agent_advisor is None:
            raise HTTPException(status_code=500, detail="Agent advisor not available")

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "system_status": {
                "agent_initialized": agent_advisor.is_initialized,
                "config_enabled": config_manager.settings.agent_config.enabled,
                "model_provider": config_manager.settings.agent_config.model.provider,
                "model_name": config_manager.settings.agent_config.model.name
            },
            "tools_overview": [
                {
                    "name": "google_search",
                    "status": "enabled" if config_manager.settings.agent_config.tools[0].enabled else "disabled",
                    "dependencies": ["googlesearch-python"]
                },
                {
                    "name": "scraper_content", 
                    "status": "enabled" if config_manager.settings.agent_config.tools[1].enabled else "disabled",
                    "dependencies": ["aiohttp", "trafilatura"]
                },
                {
                    "name": "search_inventory",
                    "status": "enabled" if config_manager.settings.agent_config.tools[2].enabled else "disabled",
                    "dependencies": ["api_connectivity"]
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
