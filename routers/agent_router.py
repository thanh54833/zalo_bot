import logging
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from pydantic import BaseModel

from services.app_settings import config_manager
from services.advisor import agent_advisor

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/agent",
    tags=["agent"],
    responses={404: {"description": "Not found"}},
)


@router.get("/status")
async def get_agent_status():
    """Get the current status of the AI agent"""
    try:
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
        
        # Call the agent's invoke method with the single message
        response = agent_advisor.invoke([message])
        
        return response
    except Exception as e:
        logger.error(f"Error querying agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred while querying the agent.",
        )
