from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import SettingsOut, SettingsUpdate
from app.errors import AppError
from app.services.account_service import get_or_create_settings, get_or_create_user
from app.services.gmail_service import google_credentials_configured
from app.utils.helpers import utcnow

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _user(db: Session = Depends(get_db)) -> User:
    user = get_or_create_user(db)
    db.commit()
    return user


def _to_out(db: Session, user: User) -> SettingsOut:
    row = get_or_create_settings(db, user)
    db.commit()
    env = get_settings()
    return SettingsOut(
        auto_send_enabled=row.auto_send_enabled,
        auto_send_max_risk=row.auto_send_max_risk,
        auto_send_min_confidence=row.auto_send_min_confidence,
        tone=row.tone,
        custom_instructions=row.custom_instructions or "",
        signature=row.signature or "",
        processing_enabled=row.processing_enabled,
        polling_enabled=row.polling_enabled,
        poll_interval_seconds=row.poll_interval_seconds,
        review_high_urgency=row.review_high_urgency,
        demo_mode=env.demo_mode,
        ai_provider=env.ai_provider_name,
        ai_configured=env.ai_configured,
        ai_message=env.ai_status_message,
        google_connected=bool(user.google_connected),
        account_email=user.email or "",
        account_name=user.name or "",
        google_configured=google_credentials_configured(),
    )


@router.get("", response_model=SettingsOut)
def get_settings_route(db: Session = Depends(get_db), user: User = Depends(_user)) -> SettingsOut:
    return _to_out(db, user)


@router.put("", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db), user: User = Depends(_user)) -> SettingsOut:
    try:
        payload.validate_choices()
    except ValueError as exc:
        raise AppError(str(exc), status_code=422) from exc
    row = get_or_create_settings(db, user)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = utcnow()
    db.commit()
    return _to_out(db, user)
