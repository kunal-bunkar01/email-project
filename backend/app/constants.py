CATEGORIES = [
    "Work",
    "Personal",
    "Finance",
    "Support",
    "Promotion",
    "Newsletter",
    "Spam",
    "Other",
]

URGENCIES = ["High", "Medium", "Low"]
RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]
TONES = ["Professional", "Friendly", "Concise", "Formal", "Casual", "Custom"]

EMAIL_STATUSES = [
    "unprocessed",
    "processing",
    "pending_review",
    "auto_sent",
    "sent",
    "rejected",
    "processed",
    "failed",
]

BULK_CATEGORIES = {"Newsletter", "Promotion", "Spam"}

GMAIL_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
