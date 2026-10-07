import logging
import time

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Email, User
from app.errors import AppError
from app.services import gmail_service

logger = logging.getLogger(__name__)


def deliver_reply(db: Session, user: User, email: Email, body_text: str) -> str:
    if get_settings().demo_mode:
        logger.info("demo_send email_id=%s", email.id)
        return f"demo-{email.id}-{int(time.time())}"
    if not user.google_connected:
        raise AppError("Connect Gmail before sending a reply.", status_code=400)
    return gmail_service.send_reply(db, user, email, body_text)
