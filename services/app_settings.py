import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

import aiofiles
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Nested Config Models ---

class ToolConfig(BaseSettings):
    name: str
    type: str
    enabled: bool = True
    description: str
    curl: Optional[str] = None  # Optional for web tools, required for API tools
    input: Dict[str, Any]
    header: Optional[Dict[str, str]] = None  # Optional for web tools, required for API tools
    output: Dict[str, Any]
    dependencies: Optional[List[str]] = None  # For web tools
    category: Optional[str] = None  # For web tools
    max_concurrent: Optional[int] = None  # For web tools that support concurrent processing
    headers: Optional[Dict[str, str]] = None  # For web tools that need custom headers

class ModelConfig(BaseSettings):
    provider: str = "groq"
    name: str = "llama3-8b-8192"
    api_key: str = ""  # Should be set via env var GROQ_API_KEY or in app_config.json
    temperature: float = 0.7
    max_tokens: int = 2048

class AgentConfig(BaseSettings):
    enabled: bool = True
    system_prompt: str = "You are a helpful Zalo assistant."
    tools: List[ToolConfig] = Field(default_factory=list)
    model: ModelConfig = Field(default_factory=ModelConfig)


class ZaloOAConfig(BaseSettings):
    enabled: bool = True
    secret_key: str = ""  # Should be set in app_config.json

class ZaloPersonalConfig(BaseSettings):
    enabled: bool = False
    phone: str = ""  # Set in app_config.json
    password: str = ""  # Set in app_config.json
    imei: str = ""  # Set in app_config.json
    cookies: Optional[Dict[str, str]] = None

class ZaloConfig(BaseSettings):
    oa: ZaloOAConfig = Field(default_factory=ZaloOAConfig)
    personal: ZaloPersonalConfig = Field(default_factory=ZaloPersonalConfig)


# --- Root Settings Model ---

class AppSettings(BaseSettings):
    """ The main settings object, nesting all configurations """
    model_config = SettingsConfigDict(
        env_nested_delimiter='__', # e.g., AGENT_CONFIG__MODEL__API_KEY
        env_file=None
    )
    agent_config: AgentConfig = Field(default_factory=AgentConfig)
    zalo_config: ZaloConfig = Field(default_factory=ZaloConfig)


# --- Config Manager to handle persistence ---

class ConfigManager:
    def __init__(self, storage_file: str = "data/app_config.json"):
        self._file = Path(storage_file)
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self.settings: AppSettings = AppSettings()
        self._save_lock = asyncio.Lock()

    async def load(self):
        config_from_file = {}
        if self._file.exists():
            try:
                async with aiofiles.open(self._file, "r") as f:
                    content = await f.read()
                    if content:
                        config_from_file = json.loads(content)
            except Exception as e:
                print(f"[ConfigManager] Error loading config file: {e}")

        # This validates and merges data from file with defaults and env vars
        self.settings = AppSettings.model_validate(config_from_file)

    async def save(self):
        async with self._save_lock:
            try:
                tmp = self._file.with_suffix(".tmp.json")
                async with aiofiles.open(tmp, "w") as f:
                    # model_dump will convert Pydantic models to dicts
                    await f.write(self.settings.model_dump_json(indent=2))
                tmp.replace(self._file)
            except Exception as e:
                print(f"[ConfigManager] Error saving config file: {e}")

    async def update(self, data: Dict[str, Any]) -> AppSettings:
        # Get current settings as a dict
        updated_settings_data = self.settings.model_dump()

        # Recursive merge function
        def merge(a, b):
            for key, value in b.items():
                if isinstance(value, dict) and key in a and isinstance(a[key], dict):
                    a[key] = merge(a[key], value)
                else:
                    a[key] = value
            return a

        # Merge new data into existing data
        merged_data = merge(updated_settings_data, data)
        
        # Re-validate the entire structure
        self.settings = AppSettings.model_validate(merged_data)
        
        # Persist the changes
        await self.save()
        return self.settings

config_manager = ConfigManager() 