from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
CREDENTIALS_DIR = BACKEND_DIR / "credentials"
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    demo_mode: bool = True
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    email_poll_enabled: bool = False
    email_poll_interval: int = 60
    gmail_sync_limit: int = 25
    frontend_url: str = "http://localhost:5173"
    log_level: str = "INFO"
    database_url: str = ""
    app_secret: str = "local-dev-secret"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url.strip():
            return self.database_url.strip()
        return "sqlite:///" + (DATA_DIR / "email_assistant.db").as_posix()

    @property
    def ai_provider_name(self) -> str:
        if self.demo_mode:
            return "demo"
        return "openai"

    @property
    def ai_configured(self) -> bool:
        if self.demo_mode:
            return True
        return bool(self.openai_api_key.strip())

    @property
    def ai_status_message(self) -> str:
        if self.demo_mode:
            return "Demo provider is simulating classification and replies on this machine."
        if not self.openai_api_key.strip():
            return "AI provider not configured. Add OPENAI_API_KEY to backend/.env."
        return f"OpenAI is configured with model {self.openai_model}."


@lru_cache
def get_settings() -> Settings:
    return Settings()
