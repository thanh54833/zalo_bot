from fastapi import APIRouter, Body, HTTPException
from typing import Dict, Any

from services.app_settings import config_manager, AppSettings

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
        updated_settings = await config_manager.update(updates)
        return updated_settings
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 