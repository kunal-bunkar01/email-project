import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import getaddresses, parsedate_to_datetime

from bs4 import BeautifulSoup

from app.utils.helpers import truncate, utcnow

logger = logging.getLogger(__name__)

SIGNATURE_MARKERS = ("\n-- \n", "\n--\n", "\nSent from my ", "\nGet Outlook for ")


@dataclass
class ParsedAttachment:
    filename: str
    mime_type: str
    size: int
    gmail_attachment_id: str = ""
    data: bytes = b""


@dataclass
class ParsedEmail:
    gmail_message_id: str
    gmail_thread_id: str
    rfc_message_id: str
    sender_name: str
    sender_email: str
    recipients: list[str]
    cc: list[str]
    subject: str
    body: str
    html_body: str
    clean_body: str
    snippet: str
    labels: list[str]
    in_reply_to: str
    references_header: str
    received_at: datetime
    attachments: list[ParsedAttachment] = field(default_factory=list)


def decode_b64(data: str) -> bytes:
    import base64

    if not data:
        return b""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript", "head"]):
        tag.decompose()
    for image in soup.find_all("img"):
        width = str(image.get("width") or "")
        height = str(image.get("height") or "")
        src = str(image.get("src") or "")
        if width in {"0", "1"} or height in {"0", "1"} or "track" in src or "pixel" in src:
            image.decompose()
    text = soup.get_text("\n")
    return normalize_whitespace(text)


def normalize_whitespace(text: str) -> str:
    cleaned = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def strip_quotes_and_signature(text: str) -> str:
    cleaned = text or ""
    lowered = cleaned.lower()
    cut_at = len(cleaned)
    for marker in ("\non ", "\nfrom: ", "\n-----original message-----"):
        index = lowered.find(marker)
        if index > 40:
            cut_at = min(cut_at, index)
    wrote = re.search(r"\nOn .+wrote:\s*$", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if wrote and wrote.start() > 40:
        cut_at = min(cut_at, wrote.start())
    cleaned = cleaned[:cut_at]
    for marker in SIGNATURE_MARKERS:
        index = cleaned.find(marker)
        if index > 40:
            cleaned = cleaned[:index]
            break
    lines = []
    for line in cleaned.splitlines():
        if line.strip().startswith(">"):
            continue
        lines.append(line)
    return normalize_whitespace("\n".join(lines))


def clean_email_text(text: str) -> str:
    return strip_quotes_and_signature(normalize_whitespace(text))


def _header_map(payload: dict) -> dict[str, str]:
    headers = {}
    for item in payload.get("headers") or []:
        name = str(item.get("name") or "").lower()
        if name and name not in headers:
            headers[name] = str(item.get("value") or "")
    return headers


def _walk_parts(payload: dict, plain: list[str], html: list[str], attachments: list[ParsedAttachment]) -> None:
    filename = payload.get("filename") or ""
    mime = payload.get("mimeType") or ""
    body = payload.get("body") or {}
    data = body.get("data")
    attachment_id = body.get("attachmentId") or ""
    if filename:
        raw = decode_b64(data) if data else b""
        attachments.append(
            ParsedAttachment(
                filename=filename,
                mime_type=mime or "application/octet-stream",
                size=int(body.get("size") or len(raw)),
                gmail_attachment_id=attachment_id,
                data=raw,
            )
        )
    elif data and mime == "text/plain":
        plain.append(decode_b64(data).decode("utf-8", errors="replace"))
    elif data and mime == "text/html":
        html.append(decode_b64(data).decode("utf-8", errors="replace"))
    for part in payload.get("parts") or []:
        _walk_parts(part, plain, html, attachments)


def _parse_date(value: str, internal_ms: str | None) -> datetime:
    if value:
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError, IndexError):
            logger.info("email_date_unparsed")
    if internal_ms:
        try:
            return datetime.fromtimestamp(int(internal_ms) / 1000, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
    return utcnow()


def _format_addresses(header_value: str) -> list[str]:
    formatted = []
    for name, address in getaddresses([header_value or ""]):
        if not address:
            continue
        formatted.append(f"{name} <{address}>" if name else address)
    return formatted


def parse_gmail_api_message(message: dict) -> ParsedEmail:
    payload = message.get("payload") or {}
    headers = _header_map(payload)
    plain: list[str] = []
    html_parts: list[str] = []
    attachments: list[ParsedAttachment] = []
    _walk_parts(payload, plain, html_parts, attachments)

    html_body = "\n".join(part for part in html_parts if part.strip())
    if plain:
        body = normalize_whitespace("\n".join(plain))
    elif html_body:
        body = html_to_text(html_body)
    else:
        body = message.get("snippet") or ""

    clean_body = clean_email_text(body)
    sender_name, sender_email = _split_sender(headers.get("from", ""))
    snippet = normalize_whitespace(message.get("snippet") or truncate(clean_body or body, 180))

    return ParsedEmail(
        gmail_message_id=str(message.get("id") or ""),
        gmail_thread_id=str(message.get("threadId") or ""),
        rfc_message_id=headers.get("message-id", ""),
        sender_name=sender_name,
        sender_email=sender_email,
        recipients=_format_addresses(headers.get("to", "")),
        cc=_format_addresses(headers.get("cc", "")),
        subject=headers.get("subject", "(no subject)"),
        body=body,
        html_body=html_body,
        clean_body=clean_body or body,
        snippet=truncate(snippet, 240),
        labels=list(message.get("labelIds") or []),
        in_reply_to=headers.get("in-reply-to", ""),
        references_header=headers.get("references", ""),
        received_at=_parse_date(headers.get("date", ""), message.get("internalDate")),
        attachments=attachments,
    )


def _split_sender(value: str) -> tuple[str, str]:
    pairs = getaddresses([value or ""])
    if not pairs:
        return "", ""
    name, address = pairs[0]
    return (name or address or "").strip(), (address or "").strip()
