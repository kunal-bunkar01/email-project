from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, selectinload

from app.constants import CATEGORIES, EMAIL_STATUSES, URGENCIES
from app.db.database import get_db
from app.db.models import Email, User
from app.db.schemas import EmailDetail, EmailPage, SyncResult
from app.errors import AppError
from app.services.account_service import get_or_create_user
from app.services.email_processor import process_email, regenerate_reply, sync_inbox
from app.services.presenters import email_detail, email_summary, load_email
from datetime import datetime, timedelta, timezone

from app.utils.helpers import escape_like, paginate

router = APIRouter(prefix="/api/emails", tags=["emails"])


def _user(db: Session = Depends(get_db)) -> User:
    user = get_or_create_user(db)
    db.commit()
    return user


@router.post("/sync", response_model=SyncResult)
def sync_gmail(db: Session = Depends(get_db), user: User = Depends(_user)) -> SyncResult:
    result = sync_inbox(db, user)
    return SyncResult(**result)


@router.get("", response_model=EmailPage)
def list_emails(
    q: str | None = None,
    category: str | None = None,
    urgency: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_user),
) -> EmailPage:
    if category and category not in CATEGORIES:
        raise AppError("Unknown category.", status_code=400)
    if urgency and urgency not in URGENCIES:
        raise AppError("Unknown urgency.", status_code=400)
    statuses = [item.strip() for item in status.split(",")] if status else []
    for item in statuses:
        if item not in EMAIL_STATUSES:
            raise AppError("Unknown status.", status_code=400)

    query = (
        db.query(Email)
        .options(selectinload(Email.ai_runs), selectinload(Email.drafts))
        .filter(Email.user_id == user.id)
    )
    if q and q.strip():
        like = f"%{escape_like(q.strip())}%"
        query = query.filter(
            Email.subject.ilike(like, escape="\\")
            | Email.sender_name.ilike(like, escape="\\")
            | Email.sender_email.ilike(like, escape="\\")
            | Email.clean_body.ilike(like, escape="\\")
        )
    if category:
        query = query.filter(Email.category == category)
    if urgency:
        query = query.filter(Email.urgency == urgency)
    if statuses:
        query = query.filter(Email.status.in_(statuses))
    if date_from:
        query = query.filter(Email.received_at >= _parse_day(date_from))
    if date_to:
        query = query.filter(Email.received_at < _parse_day(date_to) + timedelta(days=1))

    query = query.order_by(Email.received_at.desc())
    items, total, safe_page, safe_size = paginate(query, page, page_size)
    return EmailPage(
        items=[email_summary(item) for item in items],
        total=total,
        page=safe_page,
        page_size=safe_size,
    )


@router.get("/{email_id}", response_model=EmailDetail)
def get_email(email_id: int, db: Session = Depends(get_db), user: User = Depends(_user)) -> EmailDetail:
    email = load_email(db, email_id)
    if email is None or email.user_id != user.id:
        raise AppError("Email not found.", status_code=404)
    return email_detail(db, email)


@router.post("/{email_id}/process", response_model=EmailDetail)
def process_one(email_id: int, db: Session = Depends(get_db), user: User = Depends(_user)) -> EmailDetail:
    email = db.get(Email, email_id)
    if email is None or email.user_id != user.id:
        raise AppError("Email not found.", status_code=404)
    process_email(db, email_id, force=email.status in {"failed", "unprocessed"})
    refreshed = load_email(db, email_id)
    if refreshed is None:
        raise AppError("Email not found.", status_code=404)
    return email_detail(db, refreshed)


@router.post("/{email_id}/regenerate", response_model=EmailDetail)
def regenerate(email_id: int, db: Session = Depends(get_db), user: User = Depends(_user)) -> EmailDetail:
    email = db.get(Email, email_id)
    if email is None or email.user_id != user.id:
        raise AppError("Email not found.", status_code=404)
    regenerate_reply(db, email_id)
    refreshed = load_email(db, email_id)
    if refreshed is None:
        raise AppError("Email not found.", status_code=404)
    return email_detail(db, refreshed)


def _parse_day(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise AppError("Use dates in YYYY-MM-DD format.", status_code=400) from exc
