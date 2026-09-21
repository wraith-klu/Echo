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
    DATABASE_URL: str | None = None
    SQLALCHEMY_DATABASE_URL: str | None = None

    @property
    def async_database_url(self) -> str:
        raw_url = self.DATABASE_URL or self.SQLALCHEMY_DATABASE_URL
        if raw_url:
            url = raw_url
            # SQLite — pass through as-is (uses aiosqlite driver)
            if url.startswith("sqlite"):
                return url
            # Convert postgres:// or postgresql:// to postgresql+asyncpg://
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif not url.startswith("postgresql+asyncpg://"):
                url = "postgresql+asyncpg://" + url
            # Remove unsupported query parameters for asyncpg like sslmode
            if "?" in url:
                base, query = url.split("?", 1)
                params = [p for p in query.split("&") if not p.startswith("sslmode=")]
                url = f"{base}?{'&'.join(params)}" if params else base
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # AI model configuration
    # Use 'tiny' on free-tier hosts (512 MB RAM); upgrade to 'base' or 'small' on paid plans
    WHISPER_MODEL_NAME: str = "tiny"
    # Gemini Flash API key for cloud-based translation (no local model weights required)
    GEMINI_API_KEY: str = ""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
