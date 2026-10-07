import asyncio
import logging

from app.config import get_settings
from app.db import database
from app.services.account_service import get_or_create_settings, get_or_create_user
from app.services.email_processor import sync_inbox

logger = logging.getLogger(__name__)

_stop = asyncio.Event()
_task: asyncio.Task | None = None
_skip_logged = False


def start_worker() -> None:
    global _task, _stop
    _stop = asyncio.Event()
    _task = asyncio.create_task(_loop())


async def stop_worker() -> None:
    _stop.set()
    if _task is not None:
        try:
            await _task
        except asyncio.CancelledError:
            pass


async def _loop() -> None:
    while not _stop.is_set():
        interval = 60
        try:
            interval = await asyncio.to_thread(_poll_once)
        except Exception:
            logger.exception("email_poll_failed")
        try:
            await asyncio.wait_for(_stop.wait(), timeout=max(15, interval))
        except asyncio.TimeoutError:
            continue


def _poll_once() -> int:
    global _skip_logged
    if database.SessionLocal is None:
        return get_settings().email_poll_interval
    db = database.SessionLocal()
    try:
        user = get_or_create_user(db)
        settings_row = get_or_create_settings(db, user)
        interval = settings_row.poll_interval_seconds or get_settings().email_poll_interval
        if not settings_row.polling_enabled:
            return interval
        if get_settings().demo_mode and not user.google_connected:
            if not _skip_logged:
                logger.info("email_poll_skipped reason=demo_mode")
                _skip_logged = True
            return interval
        if not user.google_connected:
            if not _skip_logged:
                logger.info("email_poll_skipped reason=gmail_not_connected")
                _skip_logged = True
            return interval
        _skip_logged = False
        result = sync_inbox(db, user)
        logger.info(
            "email_poll_complete created=%s processed=%s failed=%s",
            result["created"],
            result["processed"],
            result["failed"],
        )
        return interval
    finally:
        db.close()
