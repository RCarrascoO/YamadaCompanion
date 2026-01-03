import os
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
