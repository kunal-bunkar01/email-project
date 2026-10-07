from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.constants import CATEGORIES, URGENCIES
from app.db.models import Activity, Email, User
from app.db.schemas import DashboardStats
from app.services.presenters import activity_out, email_summary
from app.utils.helpers import day_key, recent_days, utcnow


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def build_dashboard(db: Session, user: User) -> DashboardStats:
    emails = (
        db.query(Email)
        .options(selectinload(Email.ai_runs), selectinload(Email.drafts))
        .filter(Email.user_id == user.id)
        .all()
    )
    today = utcnow().date()
    cards = {
        "total": len(emails),
        "processed": sum(1 for email in emails if email.is_processed),
        "needs_review": sum(1 for email in emails if email.status == "pending_review"),
        "auto_sent": sum(1 for email in emails if email.status == "auto_sent"),
        "today": sum(1 for email in emails if _aware(email.received_at) and _aware(email.received_at).date() == today),
    }
    category_counts = {name: 0 for name in CATEGORIES}
    urgency_counts = {name: 0 for name in URGENCIES}
    for email in emails:
        if email.category in category_counts:
            category_counts[email.category] += 1
        if email.urgency in urgency_counts:
            urgency_counts[email.urgency] += 1

    human = sum(1 for email in emails if email.status in {"pending_review", "sent", "rejected"})
    no_reply = sum(1 for email in emails if email.status == "processed")
    processed_by_day: dict[str, int] = {day: 0 for day in recent_days(10)}
    for email in emails:
        if not email.is_processed or email.received_at is None:
            continue
        key = day_key(email.received_at)
        if key in processed_by_day:
            processed_by_day[key] += 1

    recent = sorted(emails, key=lambda item: item.received_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:6]
    queue = sorted(
        [email for email in emails if email.status == "pending_review"],
        key=lambda item: item.received_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )[:5]
    activity_rows = (
        db.query(Activity).order_by(Activity.created_at.desc()).limit(8).all()
    )
    return DashboardStats(
        cards=cards,
        by_category=[{"name": name, "value": category_counts[name]} for name in CATEGORIES if category_counts[name]],
        by_urgency=[{"name": name, "value": urgency_counts[name]} for name in URGENCIES],
        routing=[
            {"name": "Auto sent", "value": cards["auto_sent"]},
            {"name": "Human review", "value": human},
            {"name": "No reply", "value": no_reply},
        ],
        over_time=[{"date": day, "count": processed_by_day[day]} for day in processed_by_day],
        recent_emails=[email_summary(email) for email in recent],
        review_queue=[email_summary(email) for email in queue],
        activity=[activity_out(row) for row in activity_rows],
    )


def count_pending(db: Session, user: User) -> int:
    return (
        db.query(func.count(Email.id))
        .filter(Email.user_id == user.id, Email.status == "pending_review")
        .scalar()
        or 0
    )
