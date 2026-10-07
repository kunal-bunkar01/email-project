from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.constants import RISK_LEVELS, TONES


class HealthResponse(BaseModel):
    status: str
    demo_mode: bool
    database: str


class AuthStatus(BaseModel):
    demo_mode: bool
    google_connected: bool
    email: str | None = None
    name: str | None = None
    ai_provider: str
    ai_configured: bool
    ai_message: str


class AttachmentOut(BaseModel):
    id: int
    filename: str
    mime_type: str
    size: int
    extracted_text: str = ""


class AIOut(BaseModel):
    id: int
    classification: dict[str, Any] = Field(default_factory=dict)
    urgency: dict[str, Any] = Field(default_factory=dict)
    analysis: dict[str, Any] = Field(default_factory=dict)
    generated_reply: str = ""
    confidence_score: float | None = None
    risk_score: float | None = None
    risk_level: str | None = None
    issues: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    routing_decision: str | None = None
    processing_time: float | None = None
    model_name: str | None = None
    error_message: str | None = None
    created_at: datetime


class DraftOut(BaseModel):
    id: int
    email_id: int
    original_ai_draft: str
    current_draft: str
    status: str
    reviewed_by_user: bool
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    rejected_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ThreadMessage(BaseModel):
    id: int
    sender_name: str
    sender_email: str
    subject: str
    clean_body: str
    received_at: datetime
    is_current: bool


class ActivityOut(BaseModel):
    id: int
    email_id: int | None = None
    activity_type: str
    message: str
    created_at: datetime


class FeedbackOut(BaseModel):
    id: int
    email_id: int
    ai_draft: str
    human_final_reply: str
    feedback_type: str
    created_at: datetime


class EmailSummary(BaseModel):
    id: int
    sender_name: str
    sender_email: str
    subject: str
    snippet: str
    received_at: datetime
    category: str | None = None
    urgency: str | None = None
    status: str
    is_processed: bool
    gmail_thread_id: str | None = None
    draft_id: int | None = None
    confidence_score: float | None = None
    risk_level: str | None = None


class EmailDetail(EmailSummary):
    body: str = ""
    clean_body: str = ""
    html_body: str | None = None
    recipients: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    in_reply_to: str | None = None
    references: str | None = None
    error_message: str | None = None
    attachments: list[AttachmentOut] = Field(default_factory=list)
    ai: AIOut | None = None
    draft: DraftOut | None = None
    thread: list[ThreadMessage] = Field(default_factory=list)
    activity: list[ActivityOut] = Field(default_factory=list)
    feedback: list[FeedbackOut] = Field(default_factory=list)


class EmailPage(BaseModel):
    items: list[EmailSummary]
    total: int
    page: int
    page_size: int


class ReviewItem(BaseModel):
    draft: DraftOut
    email: EmailSummary


class ReviewDetail(BaseModel):
    draft: DraftOut
    email: EmailDetail


class DashboardStats(BaseModel):
    cards: dict[str, int]
    by_category: list[dict[str, Any]]
    by_urgency: list[dict[str, Any]]
    routing: list[dict[str, Any]]
    over_time: list[dict[str, Any]]
    recent_emails: list[EmailSummary]
    review_queue: list[EmailSummary]
    activity: list[ActivityOut]


class SettingsOut(BaseModel):
    auto_send_enabled: bool
    auto_send_max_risk: str
    auto_send_min_confidence: float
    tone: str
    custom_instructions: str
    signature: str
    processing_enabled: bool
    polling_enabled: bool
    poll_interval_seconds: int
    review_high_urgency: bool
    demo_mode: bool
    ai_provider: str
    ai_configured: bool
    ai_message: str
    google_connected: bool
    account_email: str
    account_name: str
    google_configured: bool


class SettingsUpdate(BaseModel):
    auto_send_enabled: bool | None = None
    auto_send_max_risk: str | None = None
    auto_send_min_confidence: float | None = Field(default=None, ge=0, le=1)
    tone: str | None = None
    custom_instructions: str | None = Field(default=None, max_length=4000)
    signature: str | None = Field(default=None, max_length=1000)
    processing_enabled: bool | None = None
    polling_enabled: bool | None = None
    poll_interval_seconds: int | None = Field(default=None, ge=15, le=3600)
    review_high_urgency: bool | None = None

    def validate_choices(self) -> None:
        if self.auto_send_max_risk is not None and self.auto_send_max_risk not in RISK_LEVELS:
            raise ValueError("Maximum risk must be LOW, MEDIUM, or HIGH.")
        if self.tone is not None and self.tone not in TONES:
            raise ValueError("Choose a supported tone.")


class DraftUpdate(BaseModel):
    current_draft: str = Field(min_length=1, max_length=20000)


class DraftAction(BaseModel):
    current_draft: str | None = Field(default=None, max_length=20000)


class SyncResult(BaseModel):
    created: int
    updated: int
    processed: int
    failed: int
    message: str


class ActivityPage(BaseModel):
    items: list[ActivityOut]
    total: int
