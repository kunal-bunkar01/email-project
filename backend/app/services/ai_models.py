from typing import Any, Protocol

from pydantic import BaseModel, Field, field_validator

from app.constants import CATEGORIES, RISK_LEVELS, URGENCIES
from app.utils.helpers import clamp_unit_interval


class ClassificationResult(BaseModel):
    category: str
    confidence: float
    reason: str = ""

    @field_validator("category")
    @classmethod
    def known_category(cls, value: str) -> str:
        cleaned = (value or "").strip()
        for category in CATEGORIES:
            if category.lower() == cleaned.lower():
                return category
        return "Other"

    @field_validator("confidence", mode="before")
    @classmethod
    def unit_confidence(cls, value: Any) -> float:
        return clamp_unit_interval(value, 0.5)

    @field_validator("reason", mode="before")
    @classmethod
    def reason_text(cls, value: Any) -> str:
        return str(value or "").strip()


class UrgencyResult(BaseModel):
    urgency: str
    confidence: float
    reason: str = ""

    @field_validator("urgency")
    @classmethod
    def known_urgency(cls, value: str) -> str:
        cleaned = (value or "").strip()
        for urgency in URGENCIES:
            if urgency.lower() == cleaned.lower():
                return urgency
        raise ValueError("Urgency must be High, Medium, or Low.")

    @field_validator("confidence", mode="before")
    @classmethod
    def unit_confidence(cls, value: Any) -> float:
        return clamp_unit_interval(value, 0.5)

    @field_validator("reason", mode="before")
    @classmethod
    def reason_text(cls, value: Any) -> str:
        return str(value or "").strip()


class AnalysisResult(BaseModel):
    intent: str
    required_action: str
    deadline: str | None = None
    sentiment: str = "Neutral"
    key_points: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    response_strategy: str = ""

    @field_validator("intent", "required_action", "sentiment", "response_strategy", mode="before")
    @classmethod
    def text_field(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("deadline", mode="before")
    @classmethod
    def deadline_field(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"none", "null", "n/a", "unknown"}:
            return None
        return text

    @field_validator("key_points", "entities", mode="before")
    @classmethod
    def string_list(cls, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [value]
        return [str(item).strip() for item in value if str(item).strip()]


class ReplyResult(BaseModel):
    reply: str
    confidence: float

    @field_validator("reply")
    @classmethod
    def non_empty_reply(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("Reply was empty.")
        return text

    @field_validator("confidence", mode="before")
    @classmethod
    def unit_confidence(cls, value: Any) -> float:
        return clamp_unit_interval(value, 0.0)


class RiskResult(BaseModel):
    risk_level: str
    risk_score: float
    confidence: float
    issues: list[str] = Field(default_factory=list)
    recommendation: str

    @field_validator("risk_level")
    @classmethod
    def known_level(cls, value: str) -> str:
        cleaned = (value or "").strip().upper()
        if cleaned not in RISK_LEVELS:
            raise ValueError("Risk level must be LOW, MEDIUM, or HIGH.")
        return cleaned

    @field_validator("risk_score", "confidence", mode="before")
    @classmethod
    def unit_score(cls, value: Any) -> float:
        return clamp_unit_interval(value, 0.5)

    @field_validator("issues", mode="before")
    @classmethod
    def issue_list(cls, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [value]
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator("recommendation")
    @classmethod
    def known_recommendation(cls, value: str) -> str:
        cleaned = (value or "").strip().upper().replace(" ", "_")
        if cleaned not in {"AUTO_SEND", "HUMAN_REVIEW"}:
            return "HUMAN_REVIEW"
        return cleaned


class AIProvider(Protocol):
    name: str
    configured: bool

    def classify_email(self, payload: dict) -> dict: ...

    def analyze_urgency(self, payload: dict) -> dict: ...

    def analyze_email(self, payload: dict) -> dict: ...

    def generate_reply(self, payload: dict) -> dict: ...

    def evaluate_risk(self, payload: dict) -> dict: ...
