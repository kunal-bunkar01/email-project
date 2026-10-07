from app.constants import BULK_CATEGORIES, RISK_LEVELS

RISK_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def route_email_processing(
    *,
    auto_send_enabled: bool,
    auto_send_max_risk: str,
    auto_send_min_confidence: float,
    review_high_urgency: bool,
    risk_level: str,
    urgency: str,
    confidence: float,
    category: str,
    ai_complete: bool,
) -> str:
    """Decide AUTO_SEND, PENDING_REVIEW, NO_REPLY, or FAILED.

    NO_REPLY keeps newsletters and promotions out of the outbox.
    FAILED is used when the AI result is incomplete. Those emails are never sent.
    """
    if not ai_complete:
        return "FAILED"
    if category in BULK_CATEGORIES and urgency != "High":
        return "NO_REPLY"

    if not auto_send_enabled:
        return "PENDING_REVIEW"

    max_risk = auto_send_max_risk if auto_send_max_risk in RISK_LEVELS else "LOW"
    level = risk_level if risk_level in RISK_LEVELS else "HIGH"
    if RISK_RANK[level] > RISK_RANK[max_risk]:
        return "PENDING_REVIEW"
    if review_high_urgency and urgency == "High":
        return "PENDING_REVIEW"
    if confidence < auto_send_min_confidence:
        return "PENDING_REVIEW"
    return "AUTO_SEND"
