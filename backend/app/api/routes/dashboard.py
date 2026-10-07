from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Activity, User
from app.db.schemas import ActivityPage, DashboardStats
from app.services.account_service import get_or_create_user
from app.services.dashboard_service import build_dashboard
from app.services.presenters import activity_out
from app.utils.helpers import paginate

router = APIRouter(tags=["dashboard"])


def _user(db: Session = Depends(get_db)) -> User:
    user = get_or_create_user(db)
    db.commit()
    return user


@router.get("/api/dashboard/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db), user: User = Depends(_user)) -> DashboardStats:
    return build_dashboard(db, user)


@router.get("/api/activity", response_model=ActivityPage)
def activity(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_user),
) -> ActivityPage:
    query = db.query(Activity).order_by(Activity.created_at.desc())
    items, total, _page, _size = paginate(query, page, page_size)
    if user.id is None:
        items = []
    return ActivityPage(items=[activity_out(item) for item in items], total=total)
