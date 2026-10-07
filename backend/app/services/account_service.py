import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Activity, User, UserSettings
from app.utils.helpers import utcnow

logger = logging.getLogger(__name__)


def get_or_create_user(db: Session) -> User:
    user = db.query(User).order_by(User.id.asc()).first()
    if user:
        return user
    user = User(email="morgan@demo.local", name="Morgan Ellis", google_connected=False)
    db.add(user)
    db.flush()
    logger.info("local_user_created")
    return user


def get_or_create_settings(db: Session, user: User | None = None) -> UserSettings:
    owner = user or get_or_create_user(db)
    existing = db.query(UserSettings).filter(UserSettings.user_id == owner.id).one_or_none()
    if existing:
        return existing
    env = get_settings()
    settings = UserSettings(
        user_id=owner.id,
        auto_send_enabled=True,
        auto_send_max_risk="LOW",
        auto_send_min_confidence=0.80,
        tone="Professional",
        custom_instructions=(
            "Keep replies short and direct.\n"
            "Do not use emojis.\n"
            "Use a professional but friendly tone.\n"
            "Do not invent facts, dates, prices, or commitments."
        ),
        signature="Best regards,\nMorgan Ellis",
        processing_enabled=True,
        polling_enabled=env.email_poll_enabled,
        poll_interval_seconds=max(15, env.email_poll_interval),
        review_high_urgency=True,
    )
    db.add(settings)
    db.flush()
    return settings


def log_activity(db: Session, activity_type: str, message: str, email_id: int | None = None, when=None) -> Activity:
    row = Activity(
        email_id=email_id,
        activity_type=activity_type,
        message=message[:500],
        created_at=when or utcnow(),
    )
    db.add(row)
    return row
