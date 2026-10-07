"""Provider abstraction used by the email pipeline.

Future providers (Gemini, Anthropic, local models) can follow the same methods
as OpenAIProvider without changing the classifier, analyzer, or reply generator.
"""

from app.config import get_settings
from app.services.ai_models import AIProvider
from app.services.providers.demo_provider import DemoProvider
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.unconfigured_provider import UnconfiguredProvider


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.demo_mode:
        return DemoProvider()
    if not settings.openai_api_key.strip():
        return UnconfiguredProvider()
    return OpenAIProvider()
