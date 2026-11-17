from __future__ import annotations

import json

from conftest import fake_json, fake_text, load_json
from collectors.base import CollectionStatus
from collectors.http import FetchError
from collectors.tiktok import TikTokCollector, parse_video_url

VIDEO_URL = "https://www.tiktok.com/@nasa/video/7685144199716408589"


def page(document) -> str:
    return (
        "<!doctype html><html><head>"
        '<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">'
        + json.dumps(document, ensure_ascii=False)
        + "</script></head><body></body></html>"
    )


def test_parse_video_url() -> None:
    assert parse_video_url(VIDEO_URL) == ("nasa", "7685144199716408589")


def test_collect_video() -> None:
    collector = TikTokCollector(
        text_fetcher=fake_text({"tiktok.com": page(load_json("tiktok_video.json"))})
    )

    record = collector.collect(VIDEO_URL)

    assert record.status is CollectionStatus.OK
    assert record.external_id == "7685144199716408589"
    assert record.views == 324400
    assert record.likes == 11100
    assert record.comments == 337
    assert record.shares == 248
    assert record.author == "nasa"
    assert record.published_at == "2026-09-13T22:04:47+00:00"
    assert record.meta["saves"] == 814


def test_missing_item_is_no_data() -> None:
    collector = TikTokCollector(
        text_fetcher=fake_text({"tiktok.com": page(load_json("tiktok_no_item.json"))})
    )

    record = collector.collect(VIDEO_URL)

    assert record.status is CollectionStatus.NO_DATA
    assert record.views is None


def test_oembed_fallback_keeps_metadata_only() -> None:
    collector = TikTokCollector(
        text_fetcher=fake_text({"tiktok.com": "<html><body>captcha</body></html>"}),
        json_fetcher=fake_json({"oembed": load_json("tiktok_oembed.json")}),
    )

    record = collector.collect(VIDEO_URL)

    assert record.status is CollectionStatus.NO_DATA
    assert record.views is None
    assert record.title == "POV: you are watching the Earth set"
    assert any("oEmbed" in warning for warning in record.warnings)


def test_oembed_failure_is_parse_error() -> None:
    collector = TikTokCollector(
        text_fetcher=fake_text({"tiktok.com": "<html><body>captcha</body></html>"}),
        json_fetcher=fake_json({"oembed": FetchError("HTTP 403", status=403)}),
    )

    record = collector.collect(VIDEO_URL)

    assert record.status is CollectionStatus.PARSE_ERROR
