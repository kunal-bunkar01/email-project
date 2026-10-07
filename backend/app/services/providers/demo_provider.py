import re

from app.utils.helpers import first_name


class DemoProvider:
    """Deterministic stand-in so the full pipeline runs without an API key."""

    name = "demo"
    configured = True

    def classify_email(self, payload: dict) -> dict:
        text = _blob(payload)
        rules = [
            ("Spam", ["you won", "lottery", "prize", "crypto giveaway", "claim your reward"]),
            ("Newsletter", ["unsubscribe", "newsletter", "view in browser", "this week in"]),
            ("Promotion", ["% off", "sale ends", "limited time", "discount", "upgrade your plan"]),
            ("Finance", ["invoice", "payment", "receipt", "payroll", "vendor", "overdue", "bank"]),
            ("Support", ["not working", "bug", "error", "checkout", "support", "broken", "issue"]),
            ("Personal", ["lunch", "dinner", "weekend", "birthday", "family", "catch up"]),
            ("Work", ["meeting", "roadmap", "deadline", "contract", "project", "pull request", "standup", "agenda"]),
        ]
        for category, words in rules:
            if any(word in text for word in words):
                return {
                    "category": category,
                    "confidence": 0.93,
                    "reason": f"The message uses language typical of {category.lower()} mail.",
                }
        return {"category": "Other", "confidence": 0.62, "reason": "No strong category signal was found."}

    def analyze_urgency(self, payload: dict) -> dict:
        text = _blob(payload)
        category = (payload.get("category") or self.classify_email(payload)["category"]).lower()
        if category in {"newsletter", "promotion", "spam"}:
            return {"urgency": "Low", "confidence": 0.95, "reason": "This is bulk or promotional mail."}
        high_markers = ["today", "asap", "urgent", "eod", "immediately", "overdue", "before friday", "production"]
        if any(word in text for word in high_markers) or "deadline" in text:
            return {
                "urgency": "High",
                "confidence": 0.91,
                "reason": "The sender is asking for action around a deadline or an active problem.",
            }
        medium_markers = ["this week", "tomorrow", "please review", "when you can", "follow up", "thursday", "confirm"]
        if any(word in text for word in medium_markers):
            return {"urgency": "Medium", "confidence": 0.84, "reason": "A response is requested, but it is not an emergency."}
        return {"urgency": "Low", "confidence": 0.8, "reason": "The message is informational."}

    def analyze_email(self, payload: dict) -> dict:
        text = _blob(payload)
        category = payload.get("category") or "Other"
        urgency = payload.get("urgency") or "Low"
        intent = _intent(text, category)
        action = _action(text, category)
        points = _key_points(payload.get("clean_body") or "")
        entities = [payload.get("sender_name") or ""]
        entities.extend(re.findall(r"\$[\d,]+(?:\.\d{2})?", payload.get("clean_body") or ""))
        deadline = None
        if "friday" in text:
            deadline = "Friday"
        elif "today" in text or "eod" in text:
            deadline = "Today"
        elif "tomorrow" in text:
            deadline = "Tomorrow"
        elif "thursday" in text:
            deadline = "Thursday"
        sentiment = "Neutral"
        if any(word in text for word in ["angry", "frustrated", "unacceptable", "broken", "failing"]):
            sentiment = "Negative"
        elif any(word in text for word in ["thanks", "thank you", "appreciate", "glad"]):
            sentiment = "Positive"
        strategy = "A short, careful reply is enough."
        if category in {"Newsletter", "Promotion", "Spam"}:
            strategy = "No reply is needed."
        elif urgency == "High" or category in {"Finance", "Support"}:
            strategy = "Hold for a person to review before anything is sent."
        return {
            "intent": intent,
            "required_action": action,
            "deadline": deadline,
            "sentiment": sentiment,
            "key_points": points,
            "entities": [item for item in entities if item],
            "response_strategy": strategy,
        }

    def generate_reply(self, payload: dict) -> dict:
        settings = payload.get("settings") or {}
        sender = first_name(payload.get("sender_name"))
        subject = payload.get("subject") or "your email"
        signature = (settings.get("signature") or "").strip()
        tone = settings.get("tone") or "Professional"
        category = payload.get("category") or "Other"
        variant = int(payload.get("variant") or 0)
        text = _blob(payload)
        body = _template(category, text, sender, subject, tone, variant)
        if signature and signature not in body:
            body = f"{body.rstrip()}\n\n{signature}"
        confidence = 0.91
        if "meeting" in text or "thursday" in text or "agenda" in text:
            confidence = 0.78
        if category in {"Finance", "Support"}:
            confidence = 0.74
        elif category in {"Newsletter", "Promotion", "Spam"}:
            confidence = 0.66
        if "contract" in text or "legal" in text:
            confidence = 0.58
        return {"reply": body, "confidence": confidence}

    def evaluate_risk(self, payload: dict) -> dict:
        text = _blob(payload)
        reply = (payload.get("reply") or "").lower()
        category = payload.get("category") or "Other"
        urgency = payload.get("urgency") or "Low"
        issues: list[str] = []
        level = "LOW"
        score = 0.08
        if category == "Finance" and urgency == "High":
            level, score = "HIGH", 0.84
            issues.append("The email is a high-urgency financial request.")
        elif any(word in text for word in ["contract", "legal", "redline", "liability"]):
            level, score = "HIGH", 0.88
            issues.append("The thread discusses a contract or legal terms.")
        elif category == "Finance":
            level, score = "MEDIUM", 0.46
            issues.append("The reply is about money, so it should be checked.")
        elif category == "Support":
            level, score = "MEDIUM", 0.41
            issues.append("A support reply can imply a commitment the owner has not made.")
        elif category in {"Newsletter", "Promotion", "Spam"}:
            level, score = "MEDIUM", 0.36
            issues.append("This looks like bulk mail, so an automatic reply is unnecessary.")
        risky_phrases = ["$", "guarantee", "i approve", "we will pay", "refund issued", "see you at"]
        if any(phrase in reply for phrase in risky_phrases):
            level, score = "HIGH", max(score, 0.9)
            issues.append("The draft contains language that could create a commitment or a new fact.")
        recommendation = "AUTO_SEND" if level == "LOW" else "HUMAN_REVIEW"
        return {
            "risk_level": level,
            "risk_score": score,
            "confidence": 0.9,
            "issues": issues,
            "recommendation": recommendation,
        }


def _blob(payload: dict) -> str:
    parts = [
        payload.get("subject") or "",
        payload.get("clean_body") or "",
        payload.get("sender_email") or "",
    ]
    return " ".join(str(part) for part in parts).lower()


def _intent(text: str, category: str) -> str:
    if "meeting" in text or "agenda" in text:
        return "Meeting coordination"
    if "invoice" in text or "payment" in text:
        return "Payment follow-up"
    if "not working" in text or "bug" in text or "checkout" in text:
        return "Support request"
    if category == "Newsletter":
        return "Newsletter"
    if category == "Promotion":
        return "Promotion"
    if category == "Personal":
        return "Personal note"
    return f"{category} message"


def _action(text: str, category: str) -> str:
    if category in {"Newsletter", "Promotion", "Spam"}:
        return "No reply needed"
    if "confirm" in text or "meeting" in text:
        return "Check the request before confirming"
    if "payment" in text or "invoice" in text:
        return "Review the payment details before responding"
    if category == "Support":
        return "Acknowledge the issue without promising a fix time"
    return "Read and reply only with information already in the thread"


def _key_points(body: str) -> list[str]:
    lines = [line.strip(" -•\t") for line in (body or "").splitlines()]
    points = [line for line in lines if len(line) > 30][:3]
    if points:
        return points
    compact = " ".join((body or "").split())
    return [compact[:180]] if compact else ["No additional details were extracted."]


def _template(category: str, text: str, sender: str, subject: str, tone: str, variant: int) -> str:
    greeting = "Hi" if tone in {"Friendly", "Casual", "Concise"} else "Hello"
    if category in {"Newsletter", "Promotion", "Spam"}:
        options = [
            f"{greeting} {sender},\n\nThanks for sending \"{subject}\". I don't need to reply to this one.",
            f"{greeting} {sender},\n\nI've noted \"{subject}\". No response is required.",
        ]
    elif "meeting" in text or "agenda" in text or "thursday" in text:
        options = [
            f"{greeting} {sender},\n\nThanks for the note about \"{subject}\". I have the details you sent and will check my schedule before I confirm.",
            f"{greeting} {sender},\n\nThanks for sharing \"{subject}\". I need to look at my calendar before I can confirm.",
        ]
    elif category == "Finance":
        options = [
            f"{greeting} {sender},\n\nThanks for flagging \"{subject}\". I can see this needs attention. I'm not confirming any payment or amount in this reply.",
            f"{greeting} {sender},\n\nI received \"{subject}\". I'll review the details you included before I respond about any payment.",
        ]
    elif category == "Support":
        options = [
            f"{greeting} {sender},\n\nThanks for reporting this. I have the description in \"{subject}\" and will look into what you described. I don't have a fix time to share yet.",
            f"{greeting} {sender},\n\nSorry this is getting in the way. I have the details from \"{subject}\" and I'm looking into the behavior you described.",
        ]
    elif "contract" in text or "redline" in text:
        options = [
            f"{greeting} {sender},\n\nThanks for sending \"{subject}\". I've received the notes and will review them before I comment on any terms.",
            f"{greeting} {sender},\n\nI have \"{subject}\". I won't comment on the terms until I've read them carefully.",
        ]
    else:
        options = [
            f"{greeting} {sender},\n\nThanks for the email about \"{subject}\". I have what you sent and will follow up with only the details I can confirm.",
            f"{greeting} {sender},\n\nThanks for writing. I read \"{subject}\" and will come back once I've checked the points you raised.",
        ]
    return options[variant % len(options)]
