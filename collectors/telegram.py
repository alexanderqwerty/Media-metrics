"""Сборщик Telegram.

Публичная веб-версия поста отдаёт embed-страницу без авторизации:

    GET https://t.me/<channel>/<post>?embed=1&mode=tme

В ней есть:
* ``.tgme_widget_message_views`` — просмотры (``2.38K``);
* ``.tgme_reaction`` — реакции, по элементу на эмодзи;
* ``.tgme_widget_message_forwards`` — число пересылок, если отображается;
* ``time[datetime]`` — дата публикации.

Текст комментариев не запрашивается; сохраняется только превью текста
поста (ТЗ, п. 4.7).
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base import (
    BaseCollector,
    CollectionStatus,
    CollectorError,
    MetricRecord,
    NotFoundError,
    Platform,
)
from .extractors import first_line, parse_count, preview

POST_RE = re.compile(
    r"https?://(?:t\.me|telegram\.me)/([A-Za-z0-9_]{3,})/(\d+)(?:[/?#]|$)",
    re.IGNORECASE,
)


def parse_post_url(url: str) -> tuple[str, str]:
    match = POST_RE.search(url)
    if not match:
        raise CollectorError(
            "Не удалось извлечь канал и номер поста Telegram. "
            "Ожидается https://t.me/<channel>/<post>"
        )
    return match.group(1), match.group(2)


def _text(element: Any) -> str | None:
    if element is None:
        return None
    value = element.get_text(" ", strip=True)
    return value or None


def _reaction_parts(message: Any) -> tuple[int | None, list[dict[str, Any]]]:
    elements = message.select(".tgme_reaction")
    if not elements:
        return 0, []

    total = 0
    parts: list[dict[str, Any]] = []
    for element in elements:
        raw = element.get_text(" ", strip=True)
        # В элементе лежит эмодзи и число: "🔥 36"; берём число с конца.
        match = re.search(r"([\d\s\u00a0\u202f.,]+[KMB]?)\s*$", raw, re.IGNORECASE)
        count = parse_count(match.group(1)) if match else None
        if count is None:
            continue
        total += count
        emoji = raw[: match.start()].strip() if match else raw
        parts.append({"emoji": emoji, "count": count})
    return total, parts


def _forwards(message: Any) -> int | None:
    element = message.select_one(".tgme_widget_message_forwards")
    if element is None:
        return None
    return parse_count(element.get_text(" ", strip=True))


class TelegramCollector(BaseCollector):
    platform = Platform.TELEGRAM
    source = "t.me/embed"

    def _collect(self, url: str) -> MetricRecord:
        channel, post_id = parse_post_url(url)
        canonical = f"https://t.me/{channel}/{post_id}"
        html = self._get_text(f"{canonical}?embed=1&mode=tme")
        soup = BeautifulSoup(html, "html.parser")

        page_text = soup.get_text(" ", strip=True)
        if "post not found" in page_text.lower():
            raise NotFoundError("Пост Telegram не найден или канал закрыт")

        message = soup.select_one(".tgme_widget_message")
        if message is None:
            raise CollectorError(
                "В embed-странице Telegram нет .tgme_widget_message — "
                "структура виджета изменилась"
            )

        views = parse_count(_text(message.select_one(".tgme_widget_message_views")))
        reactions, breakdown = _reaction_parts(message)
        forwards = _forwards(message)

        time_element = message.select_one("time[datetime]")
        published_at = time_element.get("datetime") if time_element else None
        author = _text(message.select_one(".tgme_widget_message_owner_name"))
        text = _text(message.select_one(".tgme_widget_message_text"))

        warnings: list[str] = []
        if views is None:
            warnings.append(
                "Telegram не отдал просмотры в embed-виджете (views = null)"
            )

        status = CollectionStatus.OK if views is not None else CollectionStatus.NO_DATA

        return MetricRecord(
            platform=self.platform,
            url=canonical,
            status=status,
            external_id=f"{channel}/{post_id}",
            title=first_line(text) or f"Пост {channel}/{post_id}",
            author=author,
            published_at=published_at,
            views=views,
            likes=None,
            comments=None,
            shares=forwards,
            reactions=reactions,
            source=self.source,
            meta={
                "channel": channel,
                "post_id": int(post_id),
                "text_preview": preview(text),
                "reactions_breakdown": breakdown,
            },
            warnings=warnings,
        )
