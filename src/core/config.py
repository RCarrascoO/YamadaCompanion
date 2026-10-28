import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DISCORD_TOKEN: str
    DISCORD_PREFIX: str = "!"
    
    GOOGLE_API_KEY: str
    
    LAVALINK_HOST: str = "localhost"
    LAVALINK_PORT: int = 2333
    LAVALINK_PASSWORD: str = "youshallnotpass"
    
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    DB_PATH: str = "/shared/yamada.db"

    ADMIN_USER_IDS: List[int] = []

    @field_validator("ADMIN_USER_IDS", mode="before")
    @classmethod
    def parse_admin_user_ids(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return [int(x) for x in json.loads(v)]
                except Exception:
                    pass
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        elif isinstance(v, (list, tuple, set)):
            return [int(x) for x in v]
        return v or []

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
