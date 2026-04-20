import os
import logging
from typing import Set, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Application settings with Pydantic validation and ENV override support.
    """
    model_config = SettingsConfigDict(
        env_prefix="TG_", 
        json_file="config.json",
        env_file=".env",
        extra="ignore"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        from pydantic_settings import JsonConfigSettingsSource
        return (
            init_settings,
            JsonConfigSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    api_id: int
    api_hash: str
    session_name: str = "tg_msg_manager"
    
    # Storage
    db_path: str = "messages.db"
    
    account_name: str = "Default Account"
    
    # Whitelist of chat IDs or usernames that should NEVER be cleaned
    whitelist_chats: Set[str] = Field(default_factory=set)
    
    # Chats to search for user messages by default if --chat-id is missing
    chats_to_search_user_msgs: Set[str] = Field(default_factory=set)
    
    # Throttling
    max_rps: float = 3.0
    
    # Observability
    log_level: str = "INFO"

    @validator("api_id", pre=True)
    def validate_api_id(cls, v):
        if v is None:
            raise ValueError("api_id is required")
        return int(v)

    @validator("whitelist_chats", "chats_to_search_user_msgs", pre=True)
    def split_str(cls, v):
        if isinstance(v, str):
            return {s.strip() for s in v.split(",") if s.strip()}
        return v

def load_settings(config_path: Optional[str] = None) -> Settings:
    """
    Loads settings from config.json (if exists) and overrides with ENV.
    """
    # Pydantic Settings handles the loading logic
    # To support config.json explicitly if needed:
    try:
        if config_path and os.path.exists(config_path):
            import json
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return Settings(**config_data)
        return Settings()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        raise

# Global settings instance
settings = load_settings("config.json")
