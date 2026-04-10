from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    APP_NAME: str = "AlocacoesUEPA"
    ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    APP_TIMEZONE: str = "America/Belem"

    DATABASE_URL: str = "postgresql://user:password@localhost:5432/alocacoes"

    JWT_SECRET: str = "change_me_super_secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 120

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/google/callback"
    GOOGLE_CALENDAR_ID: str = "primary"
    GOOGLE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"

    # Cache TTL Settings
    CACHE_TTL_STRICT: int = 300
    CACHE_TTL_DASHBOARD: int = 600
    CACHE_TTL_USER: int = 3600
    CACHE_TTL_CATALOG: int = 86400

    # Lista de tipos de sala configuráveis
    ROOM_TYPES: list[str] = ["laboratorio", "auditorio"]


@lru_cache
def get_settings() -> Settings:
	return Settings()


