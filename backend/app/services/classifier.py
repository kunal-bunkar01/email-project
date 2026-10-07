import logging

from pydantic import ValidationError

from app.errors import AppError
from app.services.ai_models import ClassificationResult
from app.services.ai_service import get_ai_provider
from app.utils.security import scrub

logger = logging.getLogger(__name__)


def classify_email(payload: dict) -> ClassificationResult:
    provider = get_ai_provider()
    try:
        raw = provider.classify_email(payload)
        return ClassificationResult.model_validate(raw)
    except AppError:
        raise
    except (ValidationError, TypeError, ValueError) as exc:
        logger.warning("classification_invalid error=%s", scrub(str(exc)))
        raise AppError("Unable to classify this email right now. Please try again.") from None
