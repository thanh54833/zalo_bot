from fastapi import APIRouter, Body, HTTPException
from typing import Dict, Any

from services.app_settings import config_manager, AppSettings
from services.advisor import agent_advisor

router = APIRouter(
    prefix="/api/config",
    tags=["config"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=AppSettings)
async def get_current_config():
    """
    Retrieve the current application configuration.
    Values may be from the config file or overridden by environment variables.
    """
    return config_manager.settings


@router.patch("/", response_model=AppSettings)
async def update_config(updates: Dict[str, Any] = Body(...)):
    """
    Update and persist configuration settings.
    Provide a JSON object with the keys and values to update.
    Example: 
    {
        "agent_config": {
            "system_prompt": "New prompt here",
            "model": {"temperature": 0.8}
        },
        "zalo_config": {
            "oa": {"secret_key": "new_key"}
        }
    }
    """
    try:
        # First, save the current state
        old_agent_enabled = config_manager.settings.agent_config.enabled
        
        # Update settings in config manager
        updated_settings = await config_manager.update(updates)
        
        # Check if agent enabled state changed
        if "agent_config" in updates and "enabled" in updates["agent_config"]:
            new_agent_enabled = updates["agent_config"]["enabled"]
            if new_agent_enabled != old_agent_enabled:
                # Handle agent enabled state change
                await agent_advisor.handle_enabled_state_change(new_agent_enabled)
        
        return updated_settings
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 