import logging

from pydantic import ValidationError

from app.errors import AppError
from app.services.ai_models import RiskResult
from app.services.ai_service import get_ai_provider
from app.utils.security import scrub

logger = logging.getLogger(__name__)


def evaluate_risk(payload: dict) -> RiskResult:
    provider = get_ai_provider()
    try:
        raw = provider.evaluate_risk(payload)
        return RiskResult.model_validate(raw)
    except AppError:
        raise
    except (ValidationError, TypeError, ValueError) as exc:
        logger.warning("risk_invalid error=%s", scrub(str(exc)))
        raise AppError("Unable to evaluate this reply right now. Please try again.") from None
