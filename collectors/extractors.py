"""Разбор чисел и текста, общий для площадок."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

_SUFFIXES = {
    "k": 1_000,
    "m": 1_000_000,
    "b": 1_000_000_000,
    "тыс": 1_000,
    "тыс.": 1_000,
    "млн": 1_000_000,
    "млн.": 1_000_000,
    "млрд": 1_000_000_000,
    "млрд.": 1_000_000_000,
}

_COUNT_RE = re.compile(
    r"(\d[\d\s\u00a0\u202f.,]*)\s*(k|m|b|тыс\.?|млн\.?|млрд\.?)?",
    re.IGNORECASE,
)


def parse_count(value: Any) -> int | None:
    """Приводит ``2.38K``, ``87K``, ``3,004``, ``1 234`` к int.

    Возвращает ``None``, если числа нет: нельзя превращать «нет данных»
    в ноль.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)

    text = str(value)
    text = text.replace("\u00a0", " ").replace("\u202f", " ").strip()
    match = _COUNT_RE.search(text)
    if not match:
        return None

    number = (match.group(1) or "").strip()
    suffix = (match.group(2) or "").lower().rstrip(".")
    if not number:
        return None

    if suffix in _SUFFIXES:
        cleaned = number.replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")
        try:
            base = float(cleaned)
        except ValueError:
            return None
        return int(round(base * _SUFFIXES[suffix]))

    digits = re.sub(r"\D", "", number)
    if not digits:
        return None
    return int(digits)


def first_line(text: Any, limit: int = 200) -> str | None:
    if not isinstance(text, str):
        return None
    line = next((part.strip() for part in text.splitlines() if part.strip()), "")
    if not line:
        return None
    return line[:limit] + ("…" if len(line) > limit else "")


def preview(text: Any, limit: int = 280) -> str | None:
    if not isinstance(text, str):
        return None
    value = " ".join(text.split())
    if not value:
        return None
    return value[:limit] + ("…" if len(value) > limit else "")


def epoch_to_iso(value: Any) -> str | None:
    """Unix-время (секунды) → ISO-8601 UTC."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(timespec="seconds")


def as_int(value: Any) -> int | None:
    """Строгий int: строка из цифр или целое число, иначе None."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None
