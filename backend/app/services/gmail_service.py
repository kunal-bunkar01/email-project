import base64
import logging
from datetime import timezone
from email.mime.text import MIMEText

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.config import CREDENTIALS_DIR, get_settings
from app.constants import GMAIL_SCOPES
from app.db.models import Email, OAuthToken, User
from app.errors import AppError
from app.utils.helpers import utcnow
from app.utils.security import scrub

logger = logging.getLogger(__name__)

_pending_states: dict[str, float] = {}


def google_credentials_configured() -> bool:
    client_id, client_secret = _client_pair()
    return bool(client_id and client_secret)


def authorization_url() -> str:
    settings = get_settings()
    if settings.demo_mode:
        raise AppError(
            "Demo mode uses a sample inbox. Set DEMO_MODE=false after you add Google OAuth credentials.",
            status_code=400,
        )
    client_id, client_secret = _client_pair()
    if not client_id or not client_secret:
        raise AppError(
            "Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to backend/.env.",
            status_code=400,
        )
    flow = _flow(client_id, client_secret)
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    _pending_states[state] = utcnow().timestamp()
    return url


def exchange_code(db: Session, user: User, code: str, state: str) -> User:
    if state not in _pending_states:
        raise AppError("That sign-in expired. Connect Gmail again.", status_code=400)
    _pending_states.pop(state, None)
    client_id, client_secret = _client_pair()
    flow = _flow(client_id, client_secret, state=state)
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        logger.error("oauth_exchange_failed error=%s", scrub(str(exc)))
        raise AppError("Google sign-in did not finish. Please try again.", status_code=400) from None

    credentials = flow.credentials
    profile = _fetch_profile(credentials.token)
    token = user.oauth_token or OAuthToken(user_id=user.id)
    token.access_token = credentials.token or ""
    if credentials.refresh_token:
        token.refresh_token = credentials.refresh_token
    token.token_expiry = credentials.expiry
    token.scopes = " ".join(credentials.scopes or GMAIL_SCOPES)
    if token not in db:
        db.add(token)
    user.google_connected = True
    if profile.get("email"):
        user.email = profile["email"]
    if profile.get("name"):
        user.name = profile["name"]
    user.updated_at = utcnow()
    db.commit()
    logger.info("gmail_connected email=%s", user.email)
    return user


def disconnect(db: Session, user: User) -> None:
    if user.oauth_token:
        db.delete(user.oauth_token)
    user.google_connected = False
    user.updated_at = utcnow()
    db.commit()
    logger.info("gmail_disconnected user_id=%s", user.id)


def list_recent_messages(db: Session, user: User) -> list[dict]:
    service = _gmail(db, user)
    limit = max(1, min(get_settings().gmail_sync_limit, 50))
    try:
        listed = service.users().messages().list(userId="me", maxResults=limit, q="newer_than:45d").execute()
        refs = listed.get("messages") or []
        messages = []
        for ref in refs:
            full = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
            messages.append(full)
        return messages
    except HttpError as exc:
        logger.error("gmail_list_failed error=%s", scrub(str(exc)))
        raise AppError("Gmail is unavailable right now. Please try again.", status_code=502) from None


def download_attachment(db: Session, user: User, message_id: str, attachment_id: str) -> bytes:
    if not attachment_id:
        return b""
    service = _gmail(db, user)
    try:
        result = (
            service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
    except HttpError as exc:
        logger.warning("gmail_attachment_failed message_id=%s error=%s", message_id, scrub(str(exc)))
        return b""
    return _decode_attachment(result.get("data") or "")


def send_reply(db: Session, user: User, email: Email, body_text: str) -> str:
    service = _gmail(db, user)
    message = MIMEText(body_text, "plain", "utf-8")
    message["To"] = email.sender_email
    subject = email.subject or ""
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    message["Subject"] = subject
    if email.rfc_message_id:
        message["In-Reply-To"] = email.rfc_message_id
        message["References"] = email.references_header or email.rfc_message_id
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    payload: dict = {"raw": raw}
    if email.gmail_thread_id:
        payload["threadId"] = email.gmail_thread_id
    try:
        sent = service.users().messages().send(userId="me", body=payload).execute()
    except HttpError as exc:
        logger.error("gmail_send_failed email_id=%s error=%s", email.id, scrub(str(exc)))
        raise AppError("Gmail could not send this reply. Please try again.", status_code=502) from None
    logger.info("gmail_sent email_id=%s", email.id)
    return str(sent.get("id") or "")


def _gmail(db: Session, user: User):
    credentials = _authorized_credentials(db, user)
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def _authorized_credentials(db: Session, user: User) -> Credentials:
    token = user.oauth_token
    if not user.google_connected or token is None or not token.access_token:
        raise AppError("Connect Gmail before continuing.", status_code=400)
    client_id, client_secret = _client_pair()
    credentials = Credentials(
        token=token.access_token,
        refresh_token=token.refresh_token or None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=GMAIL_SCOPES,
    )
    expiry = token.token_expiry
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    expired = expiry is not None and expiry <= utcnow()
    if expired or not credentials.valid:
        if not credentials.refresh_token:
            _mark_disconnected(db, user)
            raise AppError("Gmail authorization expired. Reconnect your account.", status_code=401)
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            logger.error("gmail_refresh_failed error=%s", scrub(str(exc)))
            _mark_disconnected(db, user)
            raise AppError("Gmail authorization expired. Reconnect your account.", status_code=401) from None
        token.access_token = credentials.token or ""
        token.token_expiry = credentials.expiry
        token.updated_at = utcnow()
        db.commit()
    return credentials


def _mark_disconnected(db: Session, user: User) -> None:
    user.google_connected = False
    db.commit()


def _fetch_profile(access_token: str) -> dict:
    import httpx

    try:
        response = httpx.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        logger.warning("userinfo_failed error=%s", scrub(str(exc)))
        return {}


def _flow(client_id: str, client_secret: str, state: str | None = None) -> Flow:
    settings = get_settings()
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    options: dict = {"redirect_uri": settings.google_redirect_uri}
    if state:
        options["state"] = state
    return Flow.from_client_config(client_config, scopes=GMAIL_SCOPES, **options)


def _client_pair() -> tuple[str, str]:
    settings = get_settings()
    if settings.google_client_id.strip() and settings.google_client_secret.strip():
        return settings.google_client_id.strip(), settings.google_client_secret.strip()
    path = CREDENTIALS_DIR / "client_secret.json"
    if not path.exists():
        return "", ""
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("google_credentials_file_unreadable")
        return "", ""
    block = data.get("web") or data.get("installed") or {}
    return str(block.get("client_id") or ""), str(block.get("client_secret") or "")


def _decode_attachment(data: str) -> bytes:
    if not data:
        return b""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))
