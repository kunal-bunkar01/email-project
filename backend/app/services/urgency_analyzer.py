import logging

from pydantic import ValidationError

from app.errors import AppError
from app.services.ai_models import UrgencyResult
from app.services.ai_service import get_ai_provider
from app.utils.security import scrub

logger = logging.getLogger(__name__)


def analyze_urgency(payload: dict) -> UrgencyResult:
    provider = get_ai_provider()
    try:
        raw = provider.analyze_urgency(payload)
        return UrgencyResult.model_validate(raw)
    except AppError:
        raise
    except (ValidationError, TypeError, ValueError) as exc:
        logger.warning("urgency_invalid error=%s", scrub(str(exc)))
        raise AppError("Unable to judge urgency right now. Please try again.") from None
