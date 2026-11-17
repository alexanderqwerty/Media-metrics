"""Сборщики метрик TikTok, Telegram и Instagram (issue #6)."""

from .base import (
    BaseCollector,
    CollectionStatus,
    CollectorError,
    MetricRecord,
    NotFoundError,
    Platform,
    SCHEMA_VERSION,
    UnavailableError,
)
from .instagram import InstagramCollector
from .platforms import PlatformResolver
from .telegram import TelegramCollector
from .tiktok import TikTokCollector

__all__ = [
    "BaseCollector",
    "CollectionStatus",
    "CollectorError",
    "MetricRecord",
    "NotFoundError",
    "Platform",
    "PlatformResolver",
    "SCHEMA_VERSION",
    "UnavailableError",
    "TikTokCollector",
    "TelegramCollector",
    "InstagramCollector",
]
