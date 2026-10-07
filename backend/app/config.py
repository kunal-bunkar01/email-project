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
    llm_provider: str = "groq"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
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
    def active_llm(self) -> str:
        name = (self.llm_provider or "groq").strip().lower()
        if name not in {"groq", "gemini", "openai"}:
            return "groq"
        return name

    @property
    def llm_api_key(self) -> str:
        if self.active_llm == "gemini":
            return self.gemini_api_key.strip()
        if self.active_llm == "openai":
            return self.openai_api_key.strip()
        return self.groq_api_key.strip()

    @property
    def llm_model(self) -> str:
        if self.active_llm == "gemini":
            return self.gemini_model or "gemini-2.0-flash"
        if self.active_llm == "openai":
            return self.openai_model or "gpt-4o-mini"
        return self.groq_model or "llama-3.3-70b-versatile"

    @property
    def llm_base_url(self) -> str | None:
        if self.active_llm == "groq":
            return "https://api.groq.com/openai/v1"
        if self.active_llm == "gemini":
            return "https://generativelanguage.googleapis.com/v1beta/openai/"
        return None

    @property
    def ai_provider_name(self) -> str:
        if self.demo_mode:
            return "demo"
        return self.active_llm

    @property
    def ai_configured(self) -> bool:
        if self.demo_mode:
            return True
        return bool(self.llm_api_key)

    @property
    def ai_status_message(self) -> str:
        if self.demo_mode:
            return "Demo provider is simulating classification and replies on this machine."
        provider = self.active_llm
        if not self.llm_api_key:
            if provider == "groq":
                return "AI provider not configured. Add a free GROQ_API_KEY to backend/.env and set DEMO_MODE=false."
            if provider == "gemini":
                return "AI provider not configured. Add a free GEMINI_API_KEY to backend/.env and set DEMO_MODE=false."
            return "AI provider not configured. Add OPENAI_API_KEY to backend/.env and set DEMO_MODE=false."
        label = {"groq": "Groq free tier", "gemini": "Gemini free tier", "openai": "OpenAI"}[provider]
        return f"{label} is configured with model {self.llm_model}."


@lru_cache
def get_settings() -> Settings:
    return Settings()
