from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import AuthStatus
from app.errors import AppError
from app.services.account_service import get_or_create_user
from app.services.gmail_service import authorization_url, disconnect, exchange_code, google_credentials_configured

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user(db: Session = Depends(get_db)) -> User:
    return get_or_create_user(db)


@router.get("/status", response_model=AuthStatus)
def auth_status(db: Session = Depends(get_db)) -> AuthStatus:
    settings = get_settings()
    user = get_or_create_user(db)
    db.commit()
    return AuthStatus(
        demo_mode=settings.demo_mode,
        google_connected=bool(user.google_connected),
        email=user.email or None,
        name=user.name or None,
        ai_provider=settings.ai_provider_name,
        ai_configured=settings.ai_configured,
        ai_message=settings.ai_status_message,
    )


@router.get("/google")
def google_login() -> RedirectResponse:
    if not google_credentials_configured() and not get_settings().demo_mode:
        raise AppError(
            "Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to backend/.env.",
            status_code=400,
        )
    return RedirectResponse(authorization_url())


@router.get("/google/callback")
def google_callback(code: str | None = None, state: str | None = None, error: str | None = None, db: Session = Depends(get_db)) -> RedirectResponse:
    settings = get_settings()
    target = settings.frontend_url.rstrip("/") + "/settings"
    if error or not code or not state:
        logger_message = error or "missing_code"
        return RedirectResponse(f"{target}?gmail=error&message={quote(logger_message)}")
    user = get_or_create_user(db)
    try:
        exchange_code(db, user, code, state)
    except AppError as exc:
        return RedirectResponse(f"{target}?gmail=error&message={quote(exc.message)}")
    return RedirectResponse(f"{target}?gmail=connected")


@router.post("/logout", response_model=AuthStatus)
def logout(db: Session = Depends(get_db), user: User = Depends(_user)) -> AuthStatus:
    disconnect(db, user)
    settings = get_settings()
    return AuthStatus(
        demo_mode=settings.demo_mode,
        google_connected=False,
        email=user.email or None,
        name=user.name or None,
        ai_provider=settings.ai_provider_name,
        ai_configured=settings.ai_configured,
        ai_message=settings.ai_status_message,
    )
