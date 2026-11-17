"""Сборщик TikTok.

Публичная страница видео содержит JSON в
``<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">``. В нём:

* ``webapp.video-detail.itemInfo.itemStruct.stats`` —
  ``playCount`` (просмотры), ``diggCount`` (лайки),
  ``commentCount``, ``shareCount`` (репосты), ``collectCount`` (сохранения);
* ``author.uniqueId`` / ``author.nickname``;
* ``desc``, ``createTime``, ``video.duration``.

Если страница отдала заглушку/капчу, используется oEmbed — но он даёт
только метаданные, поэтому результат будет ``no_data`` без выдуманных чисел.
"""

from __future__ import annotations

import json
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
from .extractors import as_int, epoch_to_iso, first_line, parse_count, preview

VIDEO_RE = re.compile(r"/@([^/]+)/video/(\d+)")
REHYDRATION_ID = "__UNIVERSAL_DATA_FOR_REHYDRATION__"


def parse_video_url(url: str) -> tuple[str, str]:
    match = VIDEO_RE.search(url)
    if not match:
        raise CollectorError(
            "Не удалось извлечь пользователя и id видео TikTok. "
            "Ожидается https://www.tiktok.com/@user/video/<id>; "
            "короткие ссылки vm.tiktok.com нужно предварительно развернуть"
        )
    return match.group(1), match.group(2)


def _stat(stats: dict[str, Any], key: str) -> int | None:
    value = stats.get(key)
    number = as_int(value)
    if number is not None:
        return number
    return parse_count(value)


class TikTokCollector(BaseCollector):
    platform = Platform.TIKTOK
    source = "tiktok.com/__UNIVERSAL_DATA_FOR_REHYDRATION__"

    def _collect(self, url: str) -> MetricRecord:
        username, video_id = parse_video_url(url)
        canonical = f"https://www.tiktok.com/@{username}/video/{video_id}"
        html = self._get_text(canonical)
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", id=REHYDRATION_ID)

        if script is None or not script.string:
            return self._oembed_fallback(
                canonical,
                username,
                video_id,
                CollectorError(
                    "TikTok не вернул __UNIVERSAL_DATA_FOR_REHYDRATION__ "
                    "(капча, региональная блокировка или смена вёрстки)"
                ),
            )

        try:
            document = json.loads(script.string)
        except json.JSONDecodeError as exc:
            raise CollectorError("JSON TikTok не разобрался") from exc

        scope = document.get("__DEFAULT_SCOPE__")
        if not isinstance(scope, dict):
            raise CollectorError("В JSON TikTok нет __DEFAULT_SCOPE__")

        detail = scope.get("webapp.video-detail")
        if not isinstance(detail, dict):
            raise CollectorError("В JSON TikTok нет webapp.video-detail")

        status_code = as_int(detail.get("statusCode"))
        if status_code == 10204:
            raise NotFoundError(
                "TikTok: видео не существует или недоступно в регионе запроса"
            )
        if status_code not in (None, 0):
            raise CollectorError(
                f"TikTok вернул statusCode={status_code}: {detail.get('statusMsg')}"
            )

        item = (detail.get("itemInfo") or {}).get("itemStruct")
        if not isinstance(item, dict):
            raise CollectorError("В JSON TikTok нет itemStruct")

        stats = item.get("stats") or item.get("statsV2")
        if not isinstance(stats, dict):
            raise CollectorError("В JSON TikTok нет stats — структура изменилась")

        views = _stat(stats, "playCount")
        if views is None:
            raise CollectorError(
                "В stats TikTok нет playCount; записывать 0 вместо просмотров нельзя"
            )

        likes = _stat(stats, "diggCount")
        comments = _stat(stats, "commentCount")
        shares = _stat(stats, "shareCount")
        saves = _stat(stats, "collectCount")

        author = item.get("author") if isinstance(item.get("author"), dict) else {}
        desc = item.get("desc")
        video = item.get("video") if isinstance(item.get("video"), dict) else {}
        music = item.get("music") if isinstance(item.get("music"), dict) else {}

        return MetricRecord(
            platform=self.platform,
            url=canonical,
            status=CollectionStatus.OK,
            external_id=video_id,
            title=first_line(desc) or f"Видео @{username}",
            author=author.get("uniqueId") or username,
            published_at=epoch_to_iso(item.get("createTime")),
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            reactions=None,
            source=self.source,
            meta={
                "author_nickname": author.get("nickname"),
                "saves": saves,
                "duration_seconds": video.get("duration"),
                "music_title": music.get("title"),
                "description_preview": preview(desc),
            },
            warnings=[],
        )

    def _oembed_fallback(
        self,
        canonical: str,
        username: str,
        video_id: str,
        reason: Exception,
    ) -> MetricRecord:
        """oEmbed даёт только заголовок/автора, но не счётчики."""
        try:
            payload = self._get_json(
                "https://www.tiktok.com/oembed", params={"url": canonical}
            )
        except Exception as exc:
            raise reason from exc

        if not isinstance(payload, dict):
            raise reason

        title = payload.get("title")
        author = payload.get("author_name") or username
        if not title and not author:
            raise reason

        return MetricRecord(
            platform=self.platform,
            url=canonical,
            status=CollectionStatus.NO_DATA,
            external_id=video_id,
            title=first_line(title) or f"Видео @{username}",
            author=author,
            views=None,
            likes=None,
            comments=None,
            shares=None,
            reactions=None,
            source="tiktok.com/oembed",
            meta={"author_nickname": payload.get("author_name")},
            warnings=[
                f"TikTok не отдал статистику: {reason}. "
                "Сохранены только метаданные из oEmbed."
            ],
        )
