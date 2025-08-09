"""Unified configuration store for the entire application.

This module replaces the old PersistentConfigManager and now supports
multiple sections: agents, zalo, models, and global options.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiofiles

# -----------------------------------------
# Dataclasses for various config sections
# -----------------------------------------


@dataclass
class AgentConfig:
    prompt: str = ""
    tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: Optional[str] = None

    def touch(self):
        self.updated_at = datetime.utcnow().isoformat()


@dataclass
class ZaloConfig:
    phone: str = ""
    password: str = ""
    imei: str = ""
    cookies: Dict[str, str] | None = None
    active: bool = True


@dataclass
class ModelConfig:
    name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2048
    provider: str = "openai"


try:
    from services.advisor.prompts import SYSTEM_PROMPT
except Exception:
    SYSTEM_PROMPT = ""


@dataclass
class GlobalConfig:
    rate_limit: int = 50  # msgs/min
    default_system_prompt: str = SYSTEM_PROMPT


# Mapping helpers for load/save
SECTION_AGENTS = "agents"
SECTION_ZALO = "zalo"
SECTION_MODELS = "models"
SECTION_GLOBAL = "__global__"


class AppConfigStore:
    """In-memory config store with JSON persistence and pub/sub."""

    def __init__(self, storage_file: str = "data/app_configs.json") -> None:
        self._file = Path(storage_file)
        self._file.parent.mkdir(parents=True, exist_ok=True)

        # Actual config data
        self.global_cfg: GlobalConfig = GlobalConfig()
        self.zalo_cfg: ZaloConfig = ZaloConfig()
        self.agents: Dict[str, AgentConfig] = {}
        self.models: Dict[str, ModelConfig] = {}

        # Pub/Sub
        self._subscribers: Dict[str, List[Callable[[str, Any], Any]]] = {}
        self._event_q: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._save_lock = asyncio.Lock()

    # ------------- lifecycle ------------------
    async def start(self):
        await self._load()
        self._running = True
        asyncio.create_task(self._worker())

    async def stop(self):
        self._running = False
        await self._save()

    # ------------- CRUD helpers ---------------
    # Agents
    def list_agents(self) -> List[str]:
        return list(self.agents.keys())

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        return self.agents.get(agent_id)

    async def update_agent(self, agent_id: str, data: Dict[str, Any]):
        cfg = AgentConfig(**data)
        cfg.touch()
        self.agents[agent_id] = cfg
        await self._publish(f"{SECTION_AGENTS}.{agent_id}", cfg)

    async def delete_agent(self, agent_id: str):
        if agent_id in self.agents:
            del self.agents[agent_id]
            await self._publish(f"{SECTION_AGENTS}.{agent_id}", None)

    # Zalo
    def get_zalo(self) -> ZaloConfig:
        return self.zalo_cfg

    async def update_zalo(self, data: Dict[str, Any]):
        for k, v in data.items():
            if hasattr(self.zalo_cfg, k):
                setattr(self.zalo_cfg, k, v)
        await self._publish(SECTION_ZALO, self.zalo_cfg)

    # Models
    def get_model(self, name: str) -> Optional[ModelConfig]:
        return self.models.get(name)

    async def update_model(self, name: str, data: Dict[str, Any]):
        self.models[name] = ModelConfig(**data)
        await self._publish(f"{SECTION_MODELS}.{name}", self.models[name])

    async def delete_model(self, name: str):
        if name in self.models:
            del self.models[name]
            await self._publish(f"{SECTION_MODELS}.{name}", None)

    # Global
    def get_global(self) -> GlobalConfig:
        return self.global_cfg

    async def patch_global(self, data: Dict[str, Any]):
        for k, v in data.items():
            if hasattr(self.global_cfg, k):
                setattr(self.global_cfg, k, v)
        await self._publish(SECTION_GLOBAL, self.global_cfg)

    # ------------- Pub/Sub --------------------
    def subscribe(self, scope: str, cb: Callable[[str, Any], Any]):
        self._subscribers.setdefault(scope, []).append(cb)

    async def _publish(self, scope: str, payload: Any):
        await self._event_q.put((scope, payload))

    async def _worker(self):
        while self._running:
            try:
                scope, payload = await asyncio.wait_for(self._event_q.get(), timeout=1.0)
                # fan-out
                for key in (scope, "*"):
                    for cb in self._subscribers.get(key, []):
                        await _maybe_await(cb(scope, payload))
                await self._save()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print("[ConfigStore] worker error:", e)

    # ------------- Persistence ----------------
    async def _load(self):
        if not self._file.exists():
            return
        try:
            async with aiofiles.open(self._file, "r") as f:
                data = json.loads(await f.read())

            # Global
            if SECTION_GLOBAL in data:
                self.global_cfg = GlobalConfig(**data[SECTION_GLOBAL])

            # Zalo
            if SECTION_ZALO in data:
                self.zalo_cfg = ZaloConfig(**data[SECTION_ZALO])

            # Agents
            for k, v in data.get(SECTION_AGENTS, {}).items():
                self.agents[k] = AgentConfig(**v)

            # Models
            for k, v in data.get(SECTION_MODELS, {}).items():
                self.models[k] = ModelConfig(**v)

            print(f"[ConfigStore] Loaded agents={len(self.agents)}, models={len(self.models)}")
        except Exception as e:
            print("[ConfigStore] load error:", e)

    async def _save(self):
        async with self._save_lock:
            try:
                tmp = self._file.with_suffix(".tmp")
                async with aiofiles.open(tmp, "w") as f:
                    payload = {
                        SECTION_GLOBAL: asdict(self.global_cfg),
                        SECTION_ZALO: asdict(self.zalo_cfg),
                        SECTION_AGENTS: {k: asdict(v) for k, v in self.agents.items()},
                        SECTION_MODELS: {k: asdict(v) for k, v in self.models.items()},
                    }
                    await f.write(json.dumps(payload, indent=2))
                tmp.replace(self._file)
            except Exception as e:
                print("[ConfigStore] save error:", e)


# Helper to await callbacks that may be sync/async

async def _maybe_await(result):
    if asyncio.iscoroutine(result):
        await result


# Singleton instance
config_store = AppConfigStore()

# Backward-compat alias
config_manager = config_store  # keep old name for existing imports 