from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Echo Speech Translation Backend"
    API_V1_STR: str = "/api/v1"
    
    # CORS Origins: List of URLs allowed to call endpoints (e.g. ESP32, React Frontend)
    # Accepts JSON-formatted list or comma-separated string
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database Configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "speech_translation"
    SQLALCHEMY_DATABASE_URL: str | None = None

    @property
    def async_database_url(self) -> str:
        if self.SQLALCHEMY_DATABASE_URL:
            url = self.SQLALCHEMY_DATABASE_URL
            # SQLite — pass through as-is (uses aiosqlite driver)
            if url.startswith("sqlite"):
                return url
            # PostgreSQL — ensure asyncpg driver is specified
            if not url.startswith("postgresql+asyncpg://"):
                return url.replace("postgresql://", "postgresql+asyncpg://")
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Placeholders for future AI model paths/keys
    WHISPER_MODEL_NAME: str = "base"
    TRANSLATION_MODEL_NAME: str = "facebook/nllb-200-distilled-600M"
    TTS_MODEL_NAME: str = "suno/bark-small"

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
