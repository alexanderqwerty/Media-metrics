"""Общие типы и базовый класс сборщиков.

Issue #6: TikTok, Telegram, Instagram. Прототип складывает результат в
``MetricRecord`` и печатает JSON в консоль; Twenty CRM пока не подключена.
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

import requests

from .http import FetchError, RetryPolicy, fetch_json, fetch_text, make_session

SCHEMA_VERSION = "0.1"


class Platform(str, Enum):
    TIKTOK = "tiktok"
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"


class CollectionStatus(str, Enum):
    """Статус попытки сбора (ТЗ, п. 4.2)."""

    OK = "ok"
    NO_DATA = "no_data"
    PARSE_ERROR = "parse_error"
    UNAVAILABLE = "unavailable"


class CollectorError(RuntimeError):
    """Ответ получен, но структура не та."""


class NotFoundError(CollectorError):
    """Публикация удалена, скрыта или не существует."""


class UnavailableError(CollectorError):
    """Площадка требует вход/токен или закрыла публичный доступ."""


@dataclass
class MetricRecord:
    """Показатели одной публикации.

    ``None`` — «не удалось получить», не ноль. Ноль — реальное значение.
    """

    platform: Platform
    url: str
    status: CollectionStatus = CollectionStatus.OK
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    external_id: str | None = None
    title: str | None = None
    author: str | None = None
    published_at: str | None = None

    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    reactions: int | None = None

    source: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def has_data(self) -> bool:
        values = (self.views, self.likes, self.comments, self.shares, self.reactions)
        return any(value is not None for value in values)

    def is_complete(self) -> bool:
        values = (self.views, self.likes, self.comments, self.shares)
        return all(value is not None for value in values)

    def to_dict(self) -> dict[str, Any]:
        """Промежуточный JSON-формат (schema_version=0.1)."""
        collected_at = self.collected_at
        if collected_at.tzinfo is None:
            collected_at = collected_at.replace(tzinfo=timezone.utc)

        return {
            "schema_version": SCHEMA_VERSION,
            "platform": self.platform.value,
            "url": self.url,
            "status": self.status.value,
            "collected_at": collected_at.isoformat(timespec="seconds"),
            "publication": {
                "id": self.external_id,
                "title": self.title,
                "author": self.author,
                "published_at": self.published_at,
            },
            "metrics": {
                "views": self.views,
                "likes": self.likes,
                "comments": self.comments,
                "shares": self.shares,
                "reactions": self.reactions,
            },
            "source": self.source,
            "meta": copy.deepcopy(self.meta),
            "warnings": list(self.warnings),
        }


class BaseCollector(ABC):
    """Базовый сборщик: ошибки одной площадки не останавливают остальные."""

    platform: Platform
    source: str = ""

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        retry: RetryPolicy | None = None,
        text_fetcher: Callable[..., str] = fetch_text,
        json_fetcher: Callable[..., Any] = fetch_json,
    ) -> None:
        self.session = session or make_session()
        self.retry = retry or RetryPolicy()
        self._fetch_text = text_fetcher
        self._fetch_json = json_fetcher

    def collect(self, url: str) -> MetricRecord:
        try:
            return self._collect(url)
        except NotFoundError as exc:
            return self._failed(url, CollectionStatus.NO_DATA, exc)
        except UnavailableError as exc:
            return self._failed(url, CollectionStatus.UNAVAILABLE, exc)
        except FetchError as exc:
            return self._failed(url, CollectionStatus.UNAVAILABLE, exc)
        except CollectorError as exc:
            return self._failed(url, CollectionStatus.PARSE_ERROR, exc)
        except Exception as exc:  # защита от неожиданной ошибки разбора
            return self._failed(url, CollectionStatus.PARSE_ERROR, exc)

    @abstractmethod
    def _collect(self, url: str) -> MetricRecord:
        """Реализуется площадкой."""

    def _get_text(self, url: str, **kwargs: Any) -> str:
        return self._fetch_text(
            self.session,
            url,
            timeout=self.retry.timeout,
            attempts=self.retry.attempts,
            base_delay=self.retry.base_delay,
            max_delay=self.retry.max_delay,
            **kwargs,
        )

    def _get_json(self, url: str, **kwargs: Any) -> Any:
        return self._fetch_json(
            self.session,
            url,
            timeout=self.retry.timeout,
            attempts=self.retry.attempts,
            base_delay=self.retry.base_delay,
            max_delay=self.retry.max_delay,
            **kwargs,
        )

    def _failed(self, url: str, status: CollectionStatus, exc: Exception) -> MetricRecord:
        message = str(exc).strip() or exc.__class__.__name__
        return MetricRecord(
            platform=self.platform,
            url=url,
            status=status,
            source=self.source,
            warnings=[message],
        )
