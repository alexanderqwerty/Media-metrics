"""Сборщик Instagram.

Публичная страница поста/Reels без входа отдаёт только заглушку. Если
запросить её user-agent'ом бота-превью, Instagram возвращает корректный
``og:description``::

    87K likes, 3,004 comments - pubity on October 8, 2026: "..."

Просмотры Instagram в публичном описании не отдаёт, поэтому ``views``
остаётся ``None``. Лайки/комментарии из ``og:description`` могут быть
округлены (``87K``) — это то, что площадка показывает в публичном
описании; точные значения требуют авторизованного API.

Это экспериментальный источник: Instagram может потребовать вход или
изменить разметку. В таком случае сборщик честно вернёт ``unavailable``,
а не нули.
"""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from .base import (
    BaseCollector,
    CollectionStatus,
    CollectorError,
    MetricRecord,
    Platform,
    UnavailableError,
)
from .extractors import first_line, parse_count, preview

INSTAGRAM_UA = (
    "Mozilla/5.0 (compatible; MediaMetricsBot/0.1; "
    "+https://github.com/alexanderqwerty/Media-metrics)"
)
INSTAGRAM_HEADERS = {
    "User-Agent": INSTAGRAM_UA,
    "Accept-Language": "en-US,en;q=0.9",
}

MEDIA_RE = re.compile(r"/(p|reel|reels|tv)/([A-Za-z0-9_-]{5,})")
LIKES_RE = re.compile(r"([\d\s\u00a0\u202f.,]+[KMB]?)\s+likes?", re.IGNORECASE)
COMMENTS_RE = re.compile(r"([\d\s\u00a0\u202f.,]+[KMB]?)\s+comments?", re.IGNORECASE)
AUTHOR_RE = re.compile(r"comments?\s*-\s*([^\s]+)\s+on\s+", re.IGNORECASE)
DATE_RE = re.compile(r"\bon\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})")


def parse_media_url(url: str) -> tuple[str, str]:
    match = MEDIA_RE.search(url)
    if not match:
        raise CollectorError(
            "Не удалось извлечь shortcode Instagram. "
            "Ожидается https://www.instagram.com/p/<code>/ или /reel/<code>/"
        )
    kind, code = match.group(1), match.group(2)
    if kind == "reels":
        kind = "reel"
    return kind, code


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%B %d, %Y")
    except ValueError:
        return None
    return parsed.date().isoformat()


class InstagramCollector(BaseCollector):
    platform = Platform.INSTAGRAM
    source = "instagram.com/og:description"

    def _collect(self, url: str) -> MetricRecord:
        kind, code = parse_media_url(url)
        canonical = f"https://www.instagram.com/{kind}/{code}/"
        html = self._get_text(canonical, headers=INSTAGRAM_HEADERS)
        soup = BeautifulSoup(html, "html.parser")

        description = None
        meta = soup.find("meta", attrs={"property": "og:description"})
        if meta is not None:
            description = meta.get("content")
        if not description:
            meta = soup.find("meta", attrs={"name": "description"})
            if meta is not None:
                description = meta.get("content")

        if not description:
            raise UnavailableError(
                "Instagram не отдал og:description: вероятно, требует вход "
                "или ограничил доступ"
            )

        if "log in" in description.lower() and "likes" not in description.lower():
            raise UnavailableError(
                "Instagram вернул страницу входа вместо данных публикации"
            )

        likes_match = LIKES_RE.search(description)
        likes = parse_count(likes_match.group(1)) if likes_match else None
        comments_match = COMMENTS_RE.search(description)
        comments = parse_count(comments_match.group(1)) if comments_match else None

        author_match = AUTHOR_RE.search(description)
        author = author_match.group(1) if author_match else None
        if author:
            author = author.lstrip("@")

        date_match = DATE_RE.search(description)
        published_at = _parse_date(date_match.group(1) if date_match else None)

        caption = None
        if ": " in description:
            caption = description.split(": ", 1)[1].strip()
            caption = caption.strip('"').rstrip('". ').strip()

        warnings: list[str] = [
            "Instagram не отдаёт просмотры в публичном описании (views = null)"
        ]
        if likes is None or comments is None:
            warnings.append(
                "Instagram вернул неполное описание: часть счётчиков недоступна"
            )

        status = (
            CollectionStatus.OK
            if likes is not None or comments is not None
            else CollectionStatus.NO_DATA
        )

        return MetricRecord(
            platform=self.platform,
            url=canonical,
            status=status,
            external_id=code,
            title=first_line(caption) or f"Публикация {code}",
            author=author,
            published_at=published_at,
            views=None,
            likes=likes,
            comments=comments,
            shares=None,
            reactions=None,
            source=self.source,
            meta={
                "shortcode": code,
                "caption_preview": preview(caption),
                "description": preview(description, 400),
            },
            warnings=warnings,
        )
