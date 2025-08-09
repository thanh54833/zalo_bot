from dataclasses import asdict
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator

from services.config_manager import config_manager

router = APIRouter(prefix="/config", tags=["Agent Config"])


class AgentConfigInput(BaseModel):
    prompt: str
    tools: List[str]
    metadata: dict

    @validator("prompt")
    def prompt_not_empty(cls, v: str):
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v


@router.get("/{agent_id}")
async def get_config(agent_id: str):
    cfg = config_manager.get_config(agent_id)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return asdict(cfg)


@router.post("/{agent_id}")
async def update_config(agent_id: str, payload: AgentConfigInput):
    await config_manager.update_config(agent_id, payload.dict())
    return {
        "status": "updated",
        "agent_id": agent_id,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.delete("/{agent_id}")
async def delete_config(agent_id: str):
    cfg = config_manager.get_config(agent_id)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    await config_manager.delete_config(agent_id)
    return {"status": "deleted", "agent_id": agent_id}


@router.get("/")
async def list_configs():
    agents = config_manager.list_agents()
    return {"count": len(agents), "agents": agents} 