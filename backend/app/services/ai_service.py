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
    if not settings.llm_api_key:
        return UnconfiguredProvider(settings.ai_status_message, settings.active_llm)
    return OpenAIProvider(
        name=settings.active_llm,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
    )
