from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Draft, Email, User
from app.db.schemas import EmailDetail, ReviewItem
from app.errors import AppError
from app.services.account_service import get_or_create_user
from app.services.presenters import draft_out, email_detail, email_summary, load_email

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


def _user(db: Session = Depends(get_db)) -> User:
    user = get_or_create_user(db)
    db.commit()
    return user


@router.get("", response_model=list[ReviewItem])
def list_reviews(db: Session = Depends(get_db), user: User = Depends(_user)) -> list[ReviewItem]:
    drafts = (
        db.query(Draft)
        .join(Email, Draft.email_id == Email.id)
        .filter(Draft.status == "pending", Email.user_id == user.id)
        .order_by(Draft.updated_at.desc())
        .all()
    )
    items = []
    for draft in drafts:
        email = draft.email
        if email is None:
            continue
        items.append(ReviewItem(draft=draft_out(draft), email=email_summary(email)))
    return items


@router.get("/{draft_id}", response_model=EmailDetail)
def get_review(draft_id: int, db: Session = Depends(get_db), user: User = Depends(_user)) -> EmailDetail:
    draft = db.get(Draft, draft_id)
    if draft is None:
        raise AppError("Draft not found.", status_code=404)
    email = load_email(db, draft.email_id)
    if email is None or email.user_id != user.id:
        raise AppError("Draft not found.", status_code=404)
    return email_detail(db, email)
