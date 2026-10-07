import logging

from pydantic import ValidationError

from app.errors import AppError
from app.services.ai_models import AnalysisResult
from app.services.ai_service import get_ai_provider
from app.utils.security import scrub

logger = logging.getLogger(__name__)


def analyze_email(payload: dict) -> AnalysisResult:
    provider = get_ai_provider()
    try:
        raw = provider.analyze_email(payload)
        return AnalysisResult.model_validate(raw)
    except AppError:
        raise
    except (ValidationError, TypeError, ValueError) as exc:
        logger.warning("analysis_invalid error=%s", scrub(str(exc)))
        raise AppError("Unable to analyze this email right now. Please try again.") from None
