import logging
import time

from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db.models import AIProcessing, Attachment, Draft, Email, Feedback, User
from app.errors import AppError
from app.services.account_service import get_or_create_settings, log_activity
from app.services.attachment_service import extract_attachment_text
from app.services.classifier import classify_email
from app.services.context_service import find_similar_previous_replies, get_conversation_context
from app.services.delivery import deliver_reply
from app.services.email_analyzer import analyze_email
from app.services.email_parser import ParsedEmail, parse_gmail_api_message
from app.services.reply_generator import generate_reply
from app.services.risk_evaluator import evaluate_risk
from app.services.routing import route_email_processing
from app.services.urgency_analyzer import analyze_urgency
from app.services import gmail_service
from app.utils.helpers import truncate, utcnow

logger = logging.getLogger(__name__)


def sync_inbox(db: Session, user: User) -> dict:
    settings = get_settings()
    if settings.demo_mode:
        processed, failed = process_unprocessed(db, user)
        logger.info("demo_sync processed=%s failed=%s", processed, failed)
        return {
            "created": 0,
            "updated": 0,
            "processed": processed,
            "failed": failed,
            "message": "Demo inbox checked. Sample mail stays on this machine, and nothing was fetched from Gmail.",
        }

    if not user.google_connected:
        raise AppError("Connect Gmail before syncing.", status_code=400)

    try:
        messages = gmail_service.list_recent_messages(db, user)
    except AppError:
        raise
    created = 0
    updated = 0
    for message in messages:
        try:
            parsed = parse_gmail_api_message(message)
        except Exception:
            logger.exception("email_parse_failed gmail_id=%s", message.get("id"))
            continue
        if not parsed.gmail_message_id:
            continue
        existing = db.query(Email).filter(Email.gmail_message_id == parsed.gmail_message_id).first()
        if existing:
            existing.labels = parsed.labels
            existing.snippet = parsed.snippet or existing.snippet
            updated += 1
            continue
        email = _email_from_parsed(user, parsed)
        db.add(email)
        db.flush()
        _store_attachments(db, user, email, parsed)
        created += 1
    db.commit()
    logger.info("gmail_sync created=%s updated=%s", created, updated)
    log_activity(db, "email_synced", f"Synced Gmail. {created} new, {updated} updated.")
    db.commit()
    processed, failed = process_unprocessed(db, user)
    return {
        "created": created,
        "updated": updated,
        "processed": processed,
        "failed": failed,
        "message": f"Synced {created} new email{'s' if created != 1 else ''}.",
    }


def process_unprocessed(db: Session, user: User) -> tuple[int, int]:
    settings_row = get_or_create_settings(db, user)
    if not settings_row.processing_enabled:
        return 0, 0
    rows = (
        db.query(Email)
        .filter(Email.user_id == user.id, Email.is_processed.is_(False), Email.status.in_(["unprocessed", "failed"]))
        .order_by(Email.received_at.asc())
        .all()
    )
    processed = 0
    failed = 0
    for row in rows:
        try:
            process_email(db, row.id)
            processed += 1
        except AppError:
            failed += 1
            logger.warning("process_skipped email_id=%s", row.id)
    return processed, failed


def process_email(
    db: Session,
    email_id: int,
    *,
    variant: int = 0,
    force: bool = False,
    hold_for_review: bool = False,
) -> Email:
    email = _load_email(db, email_id)
    if email is None:
        raise AppError("Email not found.", status_code=404)
    if email.is_processed and not force:
        return email
    user = email.user
    preferences = get_or_create_settings(db, user)
    started = time.perf_counter()
    email.status = "processing"
    email.error_message = ""
    db.commit()

    payload = _base_payload(db, email, preferences)
    provider_name = get_settings().ai_provider_name
    try:
        classification = classify_email(payload)
        payload["category"] = classification.category
        urgency = analyze_urgency(payload)
        payload["urgency"] = urgency.urgency
        analysis = analyze_email(payload)
        payload["analysis"] = analysis.model_dump()
        payload["variant"] = variant
        reply = generate_reply(payload)
        payload["reply"] = reply.reply
        risk = evaluate_risk(payload)
    except AppError as exc:
        _mark_failed(db, email, exc.message, time.perf_counter() - started, provider_name)
        raise

    decision = route_email_processing(
        auto_send_enabled=preferences.auto_send_enabled,
        auto_send_max_risk=preferences.auto_send_max_risk,
        auto_send_min_confidence=preferences.auto_send_min_confidence,
        review_high_urgency=preferences.review_high_urgency,
        risk_level=risk.risk_level,
        urgency=urgency.urgency,
        confidence=reply.confidence,
        category=classification.category,
        ai_complete=True,
    )
    if hold_for_review and decision == "AUTO_SEND":
        decision = "PENDING_REVIEW"
    elapsed = round(time.perf_counter() - started, 2)
    run = AIProcessing(
        email_id=email.id,
        classification=classification.model_dump(),
        urgency=urgency.model_dump(),
        analysis=analysis.model_dump(),
        generated_reply=reply.reply,
        confidence_score=reply.confidence,
        risk_score=risk.risk_score,
        risk_level=risk.risk_level,
        risk_issues=risk.issues,
        recommendation=risk.recommendation,
        routing_decision=decision,
        processing_time=elapsed,
        model_name=provider_name,
    )
    db.add(run)
    email.category = classification.category
    email.urgency = urgency.urgency
    email.is_processed = decision != "FAILED"
    draft = _upsert_draft(db, email, reply.reply, decision)

    subject = truncate(email.subject, 80)
    log_activity(db, "email_classified", f"Classified \"{subject}\" as {classification.category}.", email.id)
    log_activity(db, "reply_generated", f"Generated a reply for \"{subject}\".", email.id)

    if decision == "AUTO_SEND":
        try:
            message_id = deliver_reply(db, user, email, reply.reply)
        except AppError as exc:
            email.status = "pending_review"
            email.error_message = exc.message
            if draft:
                draft.status = "pending"
            log_activity(db, "email_failed", f"Automatic send failed for \"{subject}\". It is waiting for review.", email.id)
            db.commit()
            logger.warning("auto_send_failed email_id=%s", email.id)
            return _load_email(db, email.id) or email
        email.status = "auto_sent"
        if draft:
            draft.status = "sent"
            draft.sent_at = utcnow()
            draft.sent_message_id = message_id
            draft.approved_at = utcnow()
        log_activity(db, "email_auto_sent", f"Automatically sent a reply to \"{subject}\".", email.id)
    elif decision == "NO_REPLY":
        email.status = "processed"
        if draft:
            draft.status = "no_reply"
        log_activity(db, "email_classified", f"Processed \"{subject}\" with no reply.", email.id)
    elif decision == "FAILED":
        email.status = "failed"
        email.is_processed = False
        email.error_message = "The AI result was incomplete, so nothing was sent."
    else:
        email.status = "pending_review"

    db.commit()
    logger.info(
        "email_processed id=%s decision=%s category=%s urgency=%s risk=%s",
        email.id,
        decision,
        email.category,
        email.urgency,
        risk.risk_level,
    )
    return _load_email(db, email.id) or email


def regenerate_reply(db: Session, email_id: int) -> Email:
    email = _load_email(db, email_id)
    if email is None:
        raise AppError("Email not found.", status_code=404)
    runs = len(email.ai_runs or [])
    updated = process_email(db, email_id, variant=runs + 1, force=True, hold_for_review=True)
    log_activity(db, "reply_generated", f"Regenerated the reply for \"{truncate(updated.subject, 80)}\".", updated.id)
    db.commit()
    logger.info("reply_regenerated email_id=%s", email_id)
    return _load_email(db, email_id) or updated


def update_draft_text(db: Session, draft: Draft, text: str) -> Draft:
    draft.current_draft = text.strip()
    draft.updated_at = utcnow()
    db.commit()
    db.refresh(draft)
    return draft


def approve_draft(db: Session, draft: Draft, text: str | None = None) -> Draft:
    if draft.status == "sent":
        raise AppError("This reply has already been sent.", status_code=400)
    if text is not None:
        draft.current_draft = text.strip()
    _record_feedback(db, draft, "approved" if draft.current_draft.strip() == draft.original_ai_draft.strip() else "edited")
    draft.status = "approved"
    draft.reviewed_by_user = True
    draft.approved_at = utcnow()
    draft.updated_at = utcnow()
    log_activity(db, "email_approved", f"Approved a reply for \"{truncate(draft.email.subject, 80)}\".", draft.email_id)
    db.commit()
    logger.info("draft_approved id=%s", draft.id)
    db.refresh(draft)
    return draft


def reject_draft(db: Session, draft: Draft, text: str | None = None) -> Draft:
    if draft.status == "sent":
        raise AppError("This reply has already been sent.", status_code=400)
    if text is not None:
        draft.current_draft = text.strip()
    _record_feedback(db, draft, "rejected")
    draft.status = "rejected"
    draft.reviewed_by_user = True
    draft.rejected_at = utcnow()
    draft.updated_at = utcnow()
    email = draft.email
    email.status = "rejected"
    email.updated_at = utcnow()
    log_activity(db, "email_rejected", f"Rejected a reply for \"{truncate(email.subject, 80)}\".", email.id)
    db.commit()
    logger.info("draft_rejected id=%s", draft.id)
    db.refresh(draft)
    return draft


def send_draft(db: Session, user: User, draft: Draft, text: str | None = None) -> Draft:
    if draft.status == "sent":
        raise AppError("This reply has already been sent.", status_code=400)
    if draft.status == "rejected":
        raise AppError("This reply was rejected. Regenerate it before sending.", status_code=400)
    if text is not None:
        draft.current_draft = text.strip()
    if not draft.current_draft.strip():
        raise AppError("Write a reply before sending.", status_code=400)
    changed = draft.current_draft.strip() != (draft.original_ai_draft or "").strip()
    _record_feedback(db, draft, "edited" if changed else "approved")
    draft.reviewed_by_user = True
    draft.approved_at = draft.approved_at or utcnow()
    draft.updated_at = utcnow()
    db.commit()

    email = draft.email
    try:
        message_id = deliver_reply(db, user, email, draft.current_draft)
    except AppError as exc:
        email.status = "pending_review"
        email.error_message = exc.message
        draft.status = "pending"
        log_activity(db, "email_failed", f"Sending failed for \"{truncate(email.subject, 80)}\".", email.id)
        db.commit()
        raise

    now = utcnow()
    draft.status = "sent"
    draft.sent_at = now
    draft.sent_message_id = message_id
    email.status = "sent"
    email.error_message = ""
    email.updated_at = now
    log_activity(db, "email_sent", f"Sent a reply to \"{truncate(email.subject, 80)}\".", email.id)
    db.commit()
    logger.info("email_sent email_id=%s demo=%s", email.id, get_settings().demo_mode)
    db.refresh(draft)
    return draft


def _record_feedback(db: Session, draft: Draft, feedback_type: str) -> None:
    db.add(
        Feedback(
            email_id=draft.email_id,
            ai_draft=draft.original_ai_draft or "",
            human_final_reply=draft.current_draft or "",
            feedback_type=feedback_type,
        )
    )


def _upsert_draft(db: Session, email: Email, reply: str, decision: str) -> Draft | None:
    if decision == "FAILED":
        return None
    status = "pending"
    if decision == "NO_REPLY":
        status = "no_reply"
    draft = _latest_draft(email)
    if draft is None or draft.status == "sent":
        draft = Draft(email_id=email.id, original_ai_draft=reply, current_draft=reply, status=status)
        db.add(draft)
    else:
        draft.original_ai_draft = reply
        draft.current_draft = reply
        draft.status = status
        draft.reviewed_by_user = False
        draft.approved_at = None
        draft.sent_at = None
        draft.rejected_at = None
    return draft


def _latest_draft(email: Email) -> Draft | None:
    drafts = list(email.drafts or [])
    if not drafts:
        return None
    return max(drafts, key=lambda item: item.id or 0)


def _mark_failed(db: Session, email: Email, message: str, elapsed: float, provider_name: str) -> None:
    email.status = "failed"
    email.is_processed = False
    email.error_message = message
    db.add(
        AIProcessing(
            email_id=email.id,
            error_message=message,
            processing_time=round(elapsed, 2),
            model_name=provider_name,
            routing_decision="FAILED",
        )
    )
    log_activity(db, "email_failed", f"Processing failed for \"{truncate(email.subject, 80)}\".", email.id)
    db.commit()
    logger.error("ai_pipeline_failed email_id=%s", email.id)


def _base_payload(db: Session, email: Email, preferences) -> dict:
    excerpts = []
    for attachment in email.attachments or []:
        if attachment.extracted_text and "unavailable" not in attachment.extracted_text.lower():
            excerpts.append(f"{attachment.filename}: {truncate(attachment.extracted_text, 500)}")
    return {
        "sender_name": email.sender_name,
        "sender_email": email.sender_email,
        "subject": email.subject,
        "clean_body": truncate(email.clean_body or email.body, 6000),
        "thread": get_conversation_context(db, email.gmail_thread_id, email.id),
        "similar_replies": find_similar_previous_replies(db, email.subject, email.clean_body or email.body),
        "attachment_excerpts": excerpts[:3],
        "settings": {
            "tone": preferences.tone,
            "custom_instructions": preferences.custom_instructions,
            "signature": preferences.signature,
        },
    }


def _email_from_parsed(user: User, parsed: ParsedEmail) -> Email:
    return Email(
        user_id=user.id,
        gmail_message_id=parsed.gmail_message_id,
        gmail_thread_id=parsed.gmail_thread_id,
        rfc_message_id=parsed.rfc_message_id,
        sender_name=parsed.sender_name,
        sender_email=parsed.sender_email,
        recipients=parsed.recipients,
        cc=parsed.cc,
        subject=parsed.subject,
        body=parsed.body,
        html_body=parsed.html_body,
        clean_body=parsed.clean_body,
        snippet=parsed.snippet,
        labels=parsed.labels,
        in_reply_to=parsed.in_reply_to,
        references_header=parsed.references_header,
        received_at=parsed.received_at,
        status="unprocessed",
        is_processed=False,
    )


def _store_attachments(db: Session, user: User, email: Email, parsed: ParsedEmail) -> None:
    for item in parsed.attachments:
        data = item.data
        if not data and item.gmail_attachment_id and user.google_connected and not get_settings().demo_mode:
            try:
                data = gmail_service.download_attachment(db, user, parsed.gmail_message_id, item.gmail_attachment_id)
            except AppError:
                logger.warning("attachment_download_skipped email_id=%s", email.id)
                data = b""
        try:
            extracted = extract_attachment_text(item.filename, item.mime_type, data) if data else ""
        except Exception:
            logger.exception("attachment_pipeline_failed email_id=%s", email.id)
            extracted = "Attachment text extraction unavailable"
        db.add(
            Attachment(
                email_id=email.id,
                filename=item.filename,
                mime_type=item.mime_type,
                size=item.size or len(data),
                extracted_text=extracted,
                gmail_attachment_id=item.gmail_attachment_id,
            )
        )


def _load_email(db: Session, email_id: int) -> Email | None:
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
