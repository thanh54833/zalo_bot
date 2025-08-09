import logging
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any

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
                detail="Cannot initialize agent because it's disabled in configuration"
            )
            
        if agent_advisor.is_initialized:
            return {"status": "already_initialized", "message": "Agent is already initialized"}
            
        success = agent_advisor.initialize()
        if success:
            return {"status": "initialized", "message": "Agent initialized successfully"}
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
                detail="Cannot reload agent because it's disabled in configuration"
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

@router.post("/update")
async def update_agent_config(updates: Dict[str, Any] = Body(...)):
    """Update the agent configuration"""
    try:
        await agent_advisor.update_config(updates)
        return {"status": "updated", "message": "Agent configuration updated successfully"}
    except Exception as e:
        logger.error(f"Error updating agent configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 