import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.db.models import AIProcessing, Attachment, Draft, Email, Feedback
from app.services.account_service import get_or_create_settings, get_or_create_user, log_activity
from app.services.providers.demo_provider import DemoProvider
from app.services.routing import route_email_processing
from app.utils.helpers import truncate, utcnow

logger = logging.getLogger(__name__)

PROVIDER = DemoProvider()


def seed_demo_data(db: Session) -> None:
    user = get_or_create_user(db)
    get_or_create_settings(db, user)
    existing = db.query(Email).count()
    if existing:
        db.commit()
        return

    now = utcnow()
    for sample in SAMPLES:
        received = now - timedelta(hours=sample["hours_ago"])
        email = Email(
            user_id=user.id,
            gmail_message_id=sample["id"],
            gmail_thread_id=sample["thread"],
            rfc_message_id=f"<{sample['id']}@demo.local>",
            sender_name=sample["sender_name"],
            sender_email=sample["sender_email"],
            recipients=["Morgan Ellis <morgan@demo.local>"],
            cc=sample.get("cc") or [],
            subject=sample["subject"],
            body=sample["body"],
            html_body="",
            clean_body=sample["body"].strip(),
            snippet=truncate(" ".join(sample["body"].split()), 180),
            labels=sample.get("labels") or ["INBOX"],
            in_reply_to=sample.get("in_reply_to") or "",
            references_header=sample.get("references") or "",
            received_at=received,
            status="unprocessed",
            is_processed=False,
            created_at=received,
            updated_at=received,
        )
        db.add(email)
        db.flush()
        if sample.get("attachment"):
            db.add(
                Attachment(
                    email_id=email.id,
                    filename=sample["attachment"]["filename"],
                    mime_type=sample["attachment"]["mime_type"],
                    size=sample["attachment"]["size"],
                    extracted_text=sample["attachment"]["text"],
                    created_at=received,
                )
            )
        if sample.get("skip_ai"):
            log_activity(db, "email_synced", f"Imported \"{email.subject}\".", email.id, received)
            continue
        _apply_story(db, email, sample, received)

    db.commit()
    logger.info("demo_seed_complete count=%s", len(SAMPLES))


def _apply_story(db: Session, email: Email, sample: dict, received) -> None:
    payload = {
        "sender_name": email.sender_name,
        "sender_email": email.sender_email,
        "subject": email.subject,
        "clean_body": email.clean_body,
        "thread": [],
        "similar_replies": [],
        "attachment_excerpts": [],
        "settings": {
            "tone": "Professional",
            "custom_instructions": "Keep replies short and direct.",
            "signature": "Best regards,\nMorgan Ellis",
        },
    }
    classification = PROVIDER.classify_email(payload)
    payload["category"] = classification["category"]
    urgency = PROVIDER.analyze_urgency(payload)
    payload["urgency"] = urgency["urgency"]
    analysis = PROVIDER.analyze_email(payload)
    payload["analysis"] = analysis
    reply = PROVIDER.generate_reply(payload)
    payload["reply"] = reply["reply"]
    risk = PROVIDER.evaluate_risk(payload)
    decision = route_email_processing(
        auto_send_enabled=True,
        auto_send_max_risk="LOW",
        auto_send_min_confidence=0.80,
        review_high_urgency=True,
        risk_level=risk["risk_level"],
        urgency=urgency["urgency"],
        confidence=reply["confidence"],
        category=classification["category"],
        ai_complete=True,
    )
    outcome = sample.get("outcome") or _status_for(decision)
    email.category = classification["category"]
    email.urgency = urgency["urgency"]
    email.status = outcome
    email.is_processed = outcome != "unprocessed"
    processed_at = received + timedelta(minutes=3)
    db.add(
        AIProcessing(
            email_id=email.id,
            classification=classification,
            urgency=urgency,
            analysis=analysis,
            generated_reply=reply["reply"],
            confidence_score=reply["confidence"],
            risk_score=risk["risk_score"],
            risk_level=risk["risk_level"],
            risk_issues=risk["issues"],
            recommendation=risk["recommendation"],
            routing_decision=decision,
            processing_time=1.2,
            model_name="demo",
            created_at=processed_at,
        )
    )
    draft_status, reviewed = _draft_status(outcome)
    human_text = sample.get("human_reply") or reply["reply"]
    sent_at = processed_at + timedelta(minutes=12) if outcome in {"sent", "auto_sent"} else None
    rejected_at = processed_at + timedelta(minutes=8) if outcome == "rejected" else None
    db.add(
        Draft(
            email_id=email.id,
            original_ai_draft=reply["reply"],
            current_draft=human_text,
            status=draft_status,
            reviewed_by_user=reviewed,
            approved_at=sent_at,
            sent_at=sent_at,
            rejected_at=rejected_at,
            sent_message_id=f"demo-sent-{email.gmail_message_id}" if sent_at else "",
            created_at=processed_at,
            updated_at=sent_at or rejected_at or processed_at,
        )
    )
    log_activity(db, "email_classified", f"Classified \"{truncate(email.subject, 80)}\" as {email.category}.", email.id, processed_at)
    log_activity(db, "reply_generated", f"Generated a reply for \"{truncate(email.subject, 80)}\".", email.id, processed_at + timedelta(seconds=20))
    if outcome == "auto_sent":
        log_activity(db, "email_auto_sent", f"Automatically sent a reply to \"{truncate(email.subject, 80)}\".", email.id, sent_at)
    elif outcome == "sent":
        log_activity(db, "email_approved", f"Approved a reply for \"{truncate(email.subject, 80)}\".", email.id, sent_at)
        log_activity(db, "email_sent", f"Sent a reply to \"{truncate(email.subject, 80)}\".", email.id, sent_at)
        if human_text.strip() != reply["reply"].strip():
            db.add(
                Feedback(
                    email_id=email.id,
                    ai_draft=reply["reply"],
                    human_final_reply=human_text,
                    feedback_type="edited",
                    created_at=sent_at,
                )
            )
    elif outcome == "rejected":
        log_activity(db, "email_rejected", f"Rejected a reply for \"{truncate(email.subject, 80)}\".", email.id, rejected_at)
        db.add(
            Feedback(
                email_id=email.id,
                ai_draft=reply["reply"],
                human_final_reply="",
                feedback_type="rejected",
                created_at=rejected_at,
            )
        )


def _status_for(decision: str) -> str:
    return {"AUTO_SEND": "auto_sent", "NO_REPLY": "processed", "FAILED": "failed"}.get(decision, "pending_review")


def _draft_status(outcome: str) -> tuple[str, bool]:
    if outcome == "auto_sent":
        return "sent", False
    if outcome == "sent":
        return "sent", True
    if outcome == "rejected":
        return "rejected", True
    if outcome == "processed":
        return "no_reply", False
    return "pending", False


SAMPLES = [
    {
        "id": "demo-sarah-agenda",
        "thread": "thread-roadmap",
        "sender_name": "Sarah Chen",
        "sender_email": "sarah.chen@northwind.io",
        "subject": "Agenda for the Thursday roadmap review",
        "hours_ago": 30,
        "outcome": "sent",
        "in_reply_to": "",
        "body": """Hi Morgan,

Sharing the agenda for Thursday before I ask everyone to confirm.

We will cover the three Q3 milestones already on the doc: onboarding, billing, and the search beta. No new topics.

Thanks,
Sarah Chen
Product, Northwind""",
        "human_reply": """Hello Sarah,

Thanks for sending the agenda. I have the three milestones you listed.

Best regards,
Morgan Ellis""",
    },
    {
        "id": "demo-sarah-confirm",
        "thread": "thread-roadmap",
        "sender_name": "Sarah Chen",
        "sender_email": "sarah.chen@northwind.io",
        "subject": "Can you make the roadmap review on Thursday?",
        "hours_ago": 4,
        "in_reply_to": "<demo-sarah-agenda@demo.local>",
        "references": "<demo-sarah-agenda@demo.local>",
        "body": """Hi Morgan,

Can you confirm you can join the roadmap review this Thursday at 10:00 AM?

We will walk through the milestones from the agenda I sent yesterday. I need a yes or no before Thursday so I can book the room.

Thanks,
Sarah""",
    },
    {
        "id": "demo-marcus-checkout",
        "thread": "thread-checkout",
        "sender_name": "Marcus Webb",
        "sender_email": "marcus@harbor-supply.com",
        "subject": "Checkout is failing for two customers",
        "hours_ago": 2,
        "body": """Hi Morgan,

Checkout is not working for two customers this morning. Both see an error after they enter a card, and the order does not complete.

This is blocking a live purchase. I don't have a request id yet. Can you look at the behavior I described?

Marcus Webb
Harbor Supply""",
    },
    {
        "id": "demo-priya-invoice",
        "thread": "thread-invoice-1842",
        "sender_name": "Priya Nair",
        "sender_email": "billing@lumen-studio.com",
        "subject": "Invoice 1842 is overdue",
        "hours_ago": 6,
        "body": """Hello Morgan,

Invoice 1842 for $2,400 was due yesterday. The PDF attached lists the design sprint from September.

Please confirm whether the payment is scheduled. I am not asking you to share card details by email.

Priya Nair
Lumen Studio billing""",
        "attachment": {
            "filename": "invoice-1842.txt",
            "mime_type": "text/plain",
            "size": 96,
            "text": "Invoice 1842\nDesign sprint\nAmount: $2,400\nStatus: overdue",
        },
    },
    {
        "id": "demo-lena-contract",
        "thread": "thread-contract",
        "sender_name": "Lena Ortiz",
        "sender_email": "lena.ortiz@brightlegal.com",
        "subject": "Contract redlines needed before Friday",
        "hours_ago": 8,
        "body": """Hi Morgan,

Please review the contract redlines before Friday. Legal flagged the liability section and the payment terms.

I am not asking you to accept the terms in this email. I need your comments on the two sections mentioned above.

Lena Ortiz""",
    },
    {
        "id": "demo-daniel-lunch",
        "thread": "thread-lunch",
        "sender_name": "Daniel Okonkwo",
        "sender_email": "daniel.okonkwo@gmail.com",
        "subject": "Lunch this weekend?",
        "hours_ago": 20,
        "body": """Hey Morgan,

Are you around for lunch this weekend? No agenda, just a catch up if you are free.

Daniel""",
    },
    {
        "id": "demo-newsletter",
        "thread": "thread-newsletter",
        "sender_name": "The Pragmatic Engineer",
        "sender_email": "news@pragmatic.example",
        "subject": "This week in engineering newsletters",
        "hours_ago": 26,
        "labels": ["INBOX", "CATEGORY_PROMOTIONS"],
        "body": """This week in engineering.

Three essays on reviews, on-call, and hiring. You are receiving this newsletter because you subscribed.

Unsubscribe at the link in your account if you no longer want these notes.""",
    },
    {
        "id": "demo-promo",
        "thread": "thread-promo",
        "sender_name": "Northwind Events",
        "sender_email": "events@northwind.io",
        "subject": "30% off the October workshop",
        "hours_ago": 50,
        "labels": ["INBOX", "CATEGORY_PROMOTIONS"],
        "body": """A limited time discount: 30% off the October workshop if you register this week.

This is a promotion. No action is required.""",
    },
    {
        "id": "demo-spam",
        "thread": "thread-spam",
        "sender_name": "Rewards Desk",
        "sender_email": "prize@unknown-rewards.example",
        "subject": "You won a prize",
        "hours_ago": 70,
        "outcome": "rejected",
        "labels": ["INBOX", "SPAM"],
        "body": """Congratulations, you won a prize in our lottery drawing.

Claim your reward by replying with your account password. This is not a real notice.""",
    },
    {
        "id": "demo-jordan",
        "thread": "thread-intro",
        "sender_name": "Jordan Lee",
        "sender_email": "jordan.lee@fieldnote.co",
        "subject": "Thanks for the intro",
        "hours_ago": 15,
        "body": """Hi Morgan,

Thanks for the introduction yesterday. I have the note you forwarded and I don't need anything else from you right now.

Glad we could connect.

Jordan Lee""",
    },
    {
        "id": "demo-library",
        "thread": "thread-library",
        "sender_name": "City Library",
        "sender_email": "holds@citylibrary.example",
        "subject": "Your book hold is ready",
        "hours_ago": 40,
        "body": """Hello Morgan,

The book you reserved is ready at the main desk. This note is just a status update.

City Library""",
    },
    {
        "id": "demo-investor",
        "thread": "thread-investor",
        "sender_name": "Helena Brooks",
        "sender_email": "helena@ridgeventures.example",
        "subject": "Can you send the latest revenue numbers?",
        "hours_ago": 55,
        "outcome": "rejected",
        "body": """Hi Morgan,

Can you send the latest revenue numbers before our partner meeting this week?

I don't have a figure in this email, so please don't guess one.

Helena Brooks
Ridge Ventures""",
    },
    {
        "id": "demo-aisha",
        "thread": "thread-aisha",
        "sender_name": "Aisha Rahman",
        "sender_email": "aisha@paperlane.co",
        "subject": "Following up on the export bug",
        "hours_ago": 90,
        "outcome": "sent",
        "body": """Hi Morgan,

Following up on the export bug I wrote about last week. The CSV export was empty for one workspace.

Thanks for looking when you can.

Aisha Rahman
Paperlane support""",
        "human_reply": """Hello Aisha,

Thanks for following up. I have your note about the empty CSV export and I don't have a fix time yet.

Best regards,
Morgan Ellis""",
    },
    {
        "id": "demo-unprocessed-notes",
        "thread": "thread-notes",
        "sender_name": "Owen Park",
        "sender_email": "owen.park@northwind.io",
        "subject": "Project notes from yesterday",
        "hours_ago": 1,
        "skip_ai": True,
        "body": """Hi Morgan,

I dropped the project notes from yesterday in the shared folder. Nothing is time sensitive. Read them when you have a moment.

Owen Park""",
    },
    {
        "id": "demo-unprocessed-vendor",
        "thread": "thread-vendor",
        "sender_name": "Greta Holm",
        "sender_email": "accounts@holm-vendor.example",
        "subject": "Please approve the vendor payment today",
        "hours_ago": 3,
        "skip_ai": True,
        "body": """Hello Morgan,

Please approve the vendor payment of $18,000 today. The invoice is for the hosting renewal already on file.

I need a response before the end of the day. Do not send card details.

Greta Holm
Accounts""",
    },
]
