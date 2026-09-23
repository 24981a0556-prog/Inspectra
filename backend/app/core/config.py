"""
INSPECTRA — Application Configuration
Reads all settings from environment variables / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "INSPECTRA"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Storage
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    LOCAL_UPLOAD_DIR: str = "uploads"

    # CORS — comma-separated string in env, parsed into a list
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # AI / OCR
    # OCR_PROVIDER: "demo" (default) | "gemini" | "openai"
    # The demo provider produces realistic deterministic output without any API call.
    # Set to "gemini" or "openai" and provide the key to use a real provider.
    OCR_PROVIDER: str = "demo"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Demo mode — when True, clearly labels demo data in UI and logs
    DEMO_MODE: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def effective_ocr_provider(self) -> str:
        """Determine the actual OCR provider based on config + available keys."""
        if self.OCR_PROVIDER == "gemini" and self.GEMINI_API_KEY:
            return "gemini"
        if self.OCR_PROVIDER == "openai" and self.OPENAI_API_KEY:
            return "openai"
        return "demo"


settings = Settings()

