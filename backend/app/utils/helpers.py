import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_json(value: Any, fallback: Any) -> Any:
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def clamp_unit_interval(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number > 1 and number <= 100:
        number = number / 100
    return max(0.0, min(1.0, number))


def truncate(text: str | None, limit: int) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def start_of_day(day: datetime) -> datetime:
    aware = day if day.tzinfo else day.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def day_key(day: datetime) -> str:
    aware = day if day.tzinfo else day.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).date().isoformat()


def recent_days(count: int) -> list[str]:
    today = utcnow().date()
    return [(today - timedelta(days=offset)).isoformat() for offset in range(count - 1, -1, -1)]


def first_name(name: str | None, fallback: str = "there") -> str:
    parts = re.split(r"\s+", (name or "").strip())
    return parts[0] if parts and parts[0] else fallback


def paginate(query, page: int, page_size: int):
    safe_page = max(page, 1)
    safe_size = min(max(page_size, 1), 100)
    total = query.count()
    items = query.offset((safe_page - 1) * safe_size).limit(safe_size).all()
    return items, total, safe_page, safe_size
