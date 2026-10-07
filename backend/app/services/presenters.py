from datetime import datetime

from sqlalchemy.orm import Session, selectinload

from app.db.models import AIProcessing, Activity, Draft, Email, Feedback
from app.db.schemas import (
    AIOut,
    ActivityOut,
    AttachmentOut,
    DraftOut,
    EmailDetail,
    EmailSummary,
    FeedbackOut,
    ThreadMessage,
)


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def latest_ai(email: Email) -> AIProcessing | None:
    runs = list(email.ai_runs or [])
    if not runs:
        return None
    return max(runs, key=lambda row: row.created_at or datetime.min)


def current_draft(email: Email) -> Draft | None:
    drafts = list(email.drafts or [])
    if not drafts:
        return None
    pending = [draft for draft in drafts if draft.status == "pending"]
    pool = pending or drafts
    return max(pool, key=lambda row: row.id or 0)


def email_summary(email: Email) -> EmailSummary:
    ai = latest_ai(email)
    draft = current_draft(email)
    return EmailSummary(
        id=email.id,
        sender_name=email.sender_name or "",
        sender_email=email.sender_email or "",
        subject=email.subject or "",
        snippet=email.snippet or "",
        received_at=email.received_at,
        category=email.category or None,
        urgency=email.urgency or None,
        status=email.status,
        is_processed=bool(email.is_processed),
        gmail_thread_id=email.gmail_thread_id or None,
        draft_id=draft.id if draft and draft.status == "pending" else None,
        confidence_score=ai.confidence_score if ai and ai.generated_reply else None,
        risk_level=ai.risk_level or None if ai else None,
    )


def ai_out(row: AIProcessing) -> AIOut:
    return AIOut(
        id=row.id,
        classification=_as_dict(row.classification),
        urgency=_as_dict(row.urgency),
        analysis=_as_dict(row.analysis),
        generated_reply=row.generated_reply or "",
        confidence_score=row.confidence_score,
        risk_score=row.risk_score,
        risk_level=row.risk_level or None,
        issues=[str(item) for item in _as_list(row.risk_issues)],
        recommendation=row.recommendation or None,
        routing_decision=row.routing_decision or None,
        processing_time=row.processing_time,
        model_name=row.model_name or None,
        error_message=row.error_message or None,
        created_at=row.created_at,
    )


def draft_out(row: Draft) -> DraftOut:
    return DraftOut(
        id=row.id,
        email_id=row.email_id,
        original_ai_draft=row.original_ai_draft or "",
        current_draft=row.current_draft or "",
        status=row.status,
        reviewed_by_user=bool(row.reviewed_by_user),
        approved_at=row.approved_at,
        sent_at=row.sent_at,
        rejected_at=row.rejected_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def activity_out(row: Activity) -> ActivityOut:
    return ActivityOut(
        id=row.id,
        email_id=row.email_id,
        activity_type=row.activity_type,
        message=row.message,
        created_at=row.created_at,
    )


def email_detail(db: Session, email: Email) -> EmailDetail:
    summary = email_summary(email)
    ai = latest_ai(email)
    draft = current_draft(email)
    thread_rows = []
    if email.gmail_thread_id:
        thread_rows = (
            db.query(Email)
            .filter(Email.gmail_thread_id == email.gmail_thread_id)
            .order_by(Email.received_at.asc())
            .all()
        )
    feedback = sorted(email.feedback_items or [], key=lambda item: item.created_at or datetime.min)
    activity = sorted(email.activities or [], key=lambda item: item.created_at or datetime.min, reverse=True)
    return EmailDetail(
        **summary.model_dump(),
        body=email.body or "",
        clean_body=email.clean_body or "",
        html_body=email.html_body or None,
        recipients=[str(item) for item in _as_list(email.recipients)],
        cc=[str(item) for item in _as_list(email.cc)],
        labels=[str(item) for item in _as_list(email.labels)],
        in_reply_to=email.in_reply_to or None,
        references=email.references_header or None,
        error_message=email.error_message or None,
        attachments=[
            AttachmentOut(
                id=item.id,
                filename=item.filename,
                mime_type=item.mime_type,
                size=item.size or 0,
                extracted_text=item.extracted_text or "",
            )
            for item in email.attachments or []
        ],
        ai=ai_out(ai) if ai else None,
        draft=draft_out(draft) if draft else None,
        thread=[
            ThreadMessage(
                id=item.id,
                sender_name=item.sender_name or "",
                sender_email=item.sender_email or "",
                subject=item.subject or "",
                clean_body=item.clean_body or item.body or "",
                received_at=item.received_at,
                is_current=item.id == email.id,
            )
            for item in thread_rows
        ],
        activity=[activity_out(item) for item in activity],
        feedback=[
            FeedbackOut(
                id=item.id,
                email_id=item.email_id,
                ai_draft=item.ai_draft or "",
                human_final_reply=item.human_final_reply or "",
                feedback_type=item.feedback_type,
                created_at=item.created_at,
            )
            for item in feedback
        ],
    )


def load_email(db: Session, email_id: int) -> Email | None:
    return (
        db.query(Email)
        .options(
            selectinload(Email.attachments),
            selectinload(Email.ai_runs),
            selectinload(Email.drafts),
            selectinload(Email.feedback_items),
            selectinload(Email.activities),
            selectinload(Email.user),
        )
        .filter(Email.id == email_id)
        .first()
    )
