import re

from app.config import get_settings


def scrub(text: str) -> str:
    """Remove secrets from log lines."""
    settings = get_settings()
    cleaned = text or ""
    for secret in (
        settings.openai_api_key,
        settings.groq_api_key,
        settings.gemini_api_key,
        settings.google_client_secret,
        settings.app_secret,
    ):
        if secret and len(secret) > 6:
            cleaned = cleaned.replace(secret, "[redacted]")
    cleaned = re.sub(r"ya29\.[0-9A-Za-z\-_]+", "[redacted-token]", cleaned)
    cleaned = re.sub(r"(?:sk|gsk)-[A-Za-z0-9_\-]{10,}", "[redacted-key]", cleaned)
    return cleaned
