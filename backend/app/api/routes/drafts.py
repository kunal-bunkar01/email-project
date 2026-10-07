from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.db.database import get_db
from app.db.models import Draft, User
from app.db.schemas import DraftAction, DraftOut, DraftUpdate, EmailDetail
from app.errors import AppError
from app.services.account_service import get_or_create_user
from app.services.email_processor import approve_draft, reject_draft, send_draft, update_draft_text
from app.services.presenters import draft_out, email_detail, load_email

router = APIRouter(prefix="/api/drafts", tags=["drafts"])


def _user(db: Session = Depends(get_db)) -> User:
    user = get_or_create_user(db)
    db.commit()
    return user


def _get_draft(db: Session, draft_id: int, user: User) -> Draft:
    draft = db.query(Draft).options(selectinload(Draft.email)).filter(Draft.id == draft_id).first()
    if draft is None or draft.email is None or draft.email.user_id != user.id:
        raise AppError("Draft not found.", status_code=404)
    return draft


@router.put("/{draft_id}", response_model=DraftOut)
def update_draft(draft_id: int, body: DraftUpdate, db: Session = Depends(get_db), user: User = Depends(_user)) -> DraftOut:
    draft = _get_draft(db, draft_id, user)
    update_draft_text(db, draft, body.current_draft)
    return draft_out(draft)


@router.post("/{draft_id}/approve", response_model=DraftOut)
def approve(draft_id: int, body: DraftAction, db: Session = Depends(get_db), user: User = Depends(_user)) -> DraftOut:
    draft = _get_draft(db, draft_id, user)
    approve_draft(db, draft, body.current_draft)
    return draft_out(draft)


@router.post("/{draft_id}/reject", response_model=EmailDetail)
def reject(draft_id: int, body: DraftAction, db: Session = Depends(get_db), user: User = Depends(_user)) -> EmailDetail:
    draft = _get_draft(db, draft_id, user)
    reject_draft(db, draft, body.current_draft)
    refreshed = load_email(db, draft.email_id)
    if refreshed is None:
        raise AppError("Email not found.", status_code=404)
    return email_detail(db, refreshed)


@router.post("/{draft_id}/send", response_model=EmailDetail)
def send(draft_id: int, body: DraftAction, db: Session = Depends(get_db), user: User = Depends(_user)) -> EmailDetail:
    draft = _get_draft(db, draft_id, user)
    send_draft(db, user, draft, body.current_draft)
    refreshed = load_email(db, draft.email_id)
    if refreshed is None:
        raise AppError("Email not found.", status_code=404)
    return email_detail(db, refreshed)
