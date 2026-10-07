import re

from sqlalchemy.orm import Session

from app.db.models import Draft, Email
from app.utils.helpers import truncate

STOP_WORDS = {
    "the",
    "and",
    "for",
    "you",
    "your",
    "this",
    "that",
    "with",
    "from",
    "have",
    "are",
    "was",
    "were",
    "but",
    "not",
    "can",
    "just",
    "about",
    "thanks",
    "thank",
    "please",
    "hello",
    "hi",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", (text or "").lower())
    return {word for word in words if len(word) > 2 and word not in STOP_WORDS}


def _overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def get_conversation_context(db: Session, thread_id: str, current_email_id: int | None = None, limit: int = 8) -> list[dict]:
    if not thread_id:
        return []
    query = db.query(Email).filter(Email.gmail_thread_id == thread_id)
    if current_email_id is not None:
        query = query.filter(Email.id != current_email_id)
    rows = query.order_by(Email.received_at.asc()).limit(limit).all()
    context = []
    for row in rows:
        sent = (
            db.query(Draft)
            .filter(Draft.email_id == row.id, Draft.status.in_(["sent", "approved"]))
            .order_by(Draft.updated_at.desc())
            .first()
        )
        context.append(
            {
                "sender_name": row.sender_name,
                "sender_email": row.sender_email,
                "subject": row.subject,
                "received_at": row.received_at.isoformat() if row.received_at else "",
                "clean_body": truncate(row.clean_body or row.body, 1200),
                "our_reply": truncate(sent.current_draft, 800) if sent else "",
            }
        )
    return context


def find_similar_previous_replies(db: Session, subject: str, body: str, limit: int = 3) -> list[dict]:
    target = _tokens(f"{subject} {body}")
    if not target:
        return []
    drafts = (
        db.query(Draft)
        .filter(Draft.status.in_(["sent", "approved"]))
        .order_by(Draft.sent_at.desc(), Draft.updated_at.desc())
        .limit(40)
        .all()
    )
    scored: list[tuple[float, Draft]] = []
    for draft in drafts:
        email = draft.email
        if email is None:
            continue
        score = _overlap(target, _tokens(f"{email.subject} {email.clean_body}"))
        if score >= 0.12:
            scored.append((score, draft))
    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, draft in scored[:limit]:
        email = draft.email
        results.append(
            {
                "subject": email.subject if email else "",
                "reply": truncate(draft.current_draft, 700),
                "similarity": round(score, 2),
            }
        )
    return results
