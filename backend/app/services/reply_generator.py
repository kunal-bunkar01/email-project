import logging

from pydantic import ValidationError

from app.errors import AppError
from app.services.ai_models import ReplyResult
from app.services.ai_service import get_ai_provider
from app.utils.security import scrub

logger = logging.getLogger(__name__)


def generate_reply(payload: dict) -> ReplyResult:
    provider = get_ai_provider()
    try:
        raw = provider.generate_reply(payload)
        return ReplyResult.model_validate(raw)
    except AppError as exc:
        if exc.status_code == 503 and "not configured" in exc.message.lower():
            raise
        raise AppError("Unable to generate a reply right now. Please try again.", status_code=exc.status_code) from None
    except (ValidationError, TypeError, ValueError) as exc:
        logger.warning("reply_invalid error=%s", scrub(str(exc)))
        raise AppError("Unable to generate a reply right now. Please try again.") from None
