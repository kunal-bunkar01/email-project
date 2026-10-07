import json
import logging
import re

from openai import APIConnectionError, APITimeoutError, OpenAI, OpenAIError

from app.config import get_settings
from app.errors import AppError
from app.utils.security import scrub

logger = logging.getLogger(__name__)


def parse_model_json(text: str) -> dict:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Model response was not a JSON object.")
    return data


CLASSIFY_SYSTEM = """You classify email into exactly one category: Work, Personal, Finance, Support, Promotion, Newsletter, Spam, Other.
Return JSON: {"category": "Work", "confidence": 0.0, "reason": "short reason"}.
confidence is a number from 0 to 1. Use only the email content."""

URGENCY_SYSTEM = """You rate how quickly a person should act on an email.
Return JSON: {"urgency": "High|Medium|Low", "confidence": 0.0, "reason": "short reason"}.
High means a deadline, outage, payment problem, escalation, or meeting that starts soon.
Low means newsletters, promotions, and informational mail."""

ANALYSIS_SYSTEM = """You analyze an email for the person who received it.
Return JSON with keys: intent, required_action, deadline, sentiment, key_points, entities, response_strategy.
deadline is a short string or null. key_points and entities are arrays of short strings.
Do not invent facts that are not in the email or thread."""

REPLY_SYSTEM = """You draft a reply for the mailbox owner.
Return JSON: {"reply": "plain text reply", "confidence": 0.0}.
The reply must be natural, concise, and grammatically correct.
Follow the requested tone, custom instructions, and signature.
Never invent prices, commitments, deadlines, meetings, policies, facts, or personal information unless they are present in the email, thread, or user settings.
If you cannot safely answer, say what is known and what still needs the owner to decide.
Do not mention that you are an AI."""

RISK_SYSTEM = """You review a draft email reply for risk before it is sent.
Return JSON: {"risk_level": "LOW|MEDIUM|HIGH", "risk_score": 0.0, "confidence": 0.0, "issues": [], "recommendation": "AUTO_SEND|HUMAN_REVIEW"}.
Flag sensitive information, financial or legal commitments, unsupported claims, possible hallucinations, wrong context, harmful wording, unclear intent, and missing information.
risk_score and confidence are numbers from 0 to 1. HIGH risk must use HUMAN_REVIEW."""


class OpenAIProvider:
    def __init__(self, name: str = "openai", api_key: str = "", model: str = "", base_url: str | None = None) -> None:
        settings = get_settings()
        self.name = name or settings.active_llm
        resolved_key = api_key or settings.llm_api_key
        self.configured = bool(resolved_key)
        self._model = model or settings.llm_model
        self._json_mode = True
        client_kwargs: dict = {"api_key": resolved_key, "timeout": 45.0}
        resolved_base = base_url if base_url is not None else settings.llm_base_url
        if resolved_base:
            client_kwargs["base_url"] = resolved_base
        self._client = OpenAI(**client_kwargs) if self.configured else None

    def classify_email(self, payload: dict) -> dict:
        return self._complete(CLASSIFY_SYSTEM, _email_prompt(payload), temperature=0.1)

    def analyze_urgency(self, payload: dict) -> dict:
        return self._complete(URGENCY_SYSTEM, _email_prompt(payload), temperature=0.1)

    def analyze_email(self, payload: dict) -> dict:
        return self._complete(ANALYSIS_SYSTEM, _email_prompt(payload, include_thread=True), temperature=0.2)

    def generate_reply(self, payload: dict) -> dict:
        return self._complete(REPLY_SYSTEM, _reply_prompt(payload), temperature=0.4)

    def evaluate_risk(self, payload: dict) -> dict:
        return self._complete(RISK_SYSTEM, _risk_prompt(payload), temperature=0.1)

    def _complete(self, system: str, user: str, temperature: float) -> dict:
        if not self._client:
            raise AppError(get_settings().ai_status_message, status_code=503)
        last_error = "invalid response"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user[:14000]},
        ]
        for attempt in range(2):
            try:
                request: dict = {
                    "model": self._model,
                    "temperature": temperature,
                    "messages": messages,
                }
                if self._json_mode:
                    request["response_format"] = {"type": "json_object"}
                response = self._client.chat.completions.create(**request)
                content = response.choices[0].message.content or ""
                return parse_model_json(content)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = scrub(str(exc))
                logger.warning("ai_invalid_json attempt=%s", attempt + 1)
                messages = [
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": user[:12000] + "\n\nReturn only one JSON object. Previous output was invalid.",
                    },
                ]
            except APITimeoutError:
                logger.warning("ai_timeout model=%s", self._model)
                raise AppError("The AI provider timed out. Please try again.", status_code=504) from None
            except APIConnectionError:
                logger.warning("ai_connection_failed model=%s", self._model)
                raise AppError("The AI provider is unavailable. Please try again.", status_code=503) from None
            except OpenAIError as exc:
                detail = scrub(str(exc)).lower()
                if self._json_mode and "response_format" in detail:
                    self._json_mode = False
                    logger.info("ai_json_mode_disabled provider=%s", self.name)
                    continue
                logger.error("ai_call_failed provider=%s error=%s", self.name, scrub(str(exc)))
                message = "Unable to complete the AI step right now. Please try again."
                if getattr(exc, "status_code", None) in {401, 403}:
                    message = f"The {self.name} API key was rejected. Check it in backend/.env."
                if getattr(exc, "status_code", None) == 429:
                    message = "The free model limit was reached. Wait a minute and try again."
                raise AppError(message, status_code=502) from None
        logger.error("ai_invalid_json_final error=%s", last_error)
        raise AppError("The AI provider returned an unreadable result. Please try again.", status_code=502)


def _email_prompt(payload: dict, include_thread: bool = False) -> str:
    lines = [
        f"From: {payload.get('sender_name', '')} <{payload.get('sender_email', '')}>",
        f"Subject: {payload.get('subject', '')}",
        "",
        str(payload.get("clean_body") or "")[:6000],
    ]
    excerpts = payload.get("attachment_excerpts") or []
    if excerpts:
        lines.extend(["", "Attachment excerpts:", *[str(item)[:500] for item in excerpts[:3]]])
    if include_thread and payload.get("thread"):
        lines.extend(["", "Earlier messages in this thread:"])
        for item in payload["thread"][:6]:
            lines.append(f"- {item.get('sender_name')}: {str(item.get('clean_body') or '')[:500]}")
    return "\n".join(lines)


def _reply_prompt(payload: dict) -> str:
    settings = payload.get("settings") or {}
    lines = [
        _email_prompt(payload, include_thread=True),
        "",
        f"Category: {payload.get('category')}",
        f"Urgency: {payload.get('urgency')}",
        f"Analysis: {json.dumps(payload.get('analysis') or {}, ensure_ascii=True)[:2000]}",
        f"Tone: {settings.get('tone', 'Professional')}",
        f"Custom instructions: {settings.get('custom_instructions', '')}",
        f"Signature to append if it fits: {settings.get('signature', '')}",
    ]
    similar = payload.get("similar_replies") or []
    if similar:
        lines.append("Examples of replies the owner previously approved. Match the spirit, not the facts:")
        for item in similar[:3]:
            lines.append(f"- About {item.get('subject')}: {str(item.get('reply') or '')[:400]}")
    variant = int(payload.get("variant") or 0)
    if variant:
        lines.append("Write a different wording from the previous draft. Do not add new facts.")
    return "\n".join(lines)


def _risk_prompt(payload: dict) -> str:
    return "\n".join(
        [
            _email_prompt(payload, include_thread=True),
            "",
            f"Category: {payload.get('category')}",
            f"Urgency: {payload.get('urgency')}",
            "Draft reply:",
            str(payload.get("reply") or "")[:5000],
        ]
    )
