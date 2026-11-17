from __future__ import annotations

from conftest import fake_text, load_text
from collectors.base import CollectionStatus
from collectors.telegram import TelegramCollector, parse_post_url

POST_URL = "https://t.me/UniversitetMIET/6062"


def test_parse_post_url() -> None:
    assert parse_post_url(POST_URL) == ("UniversitetMIET", "6062")
    assert parse_post_url("https://telegram.me/chan/42?single") == ("chan", "42")


def test_collect_post() -> None:
    collector = TelegramCollector(
        text_fetcher=fake_text({"t.me/UniversitetMIET/6062": load_text("telegram_post.html")})
    )

    record = collector.collect(POST_URL)

    assert record.status is CollectionStatus.OK
    assert record.external_id == "UniversitetMIET/6062"
    assert record.views == 2380
    assert record.reactions == 67
    assert record.shares is None
    assert record.author == "НИУ МИЭТ"
    assert record.published_at == "2024-11-05T07:19:27+00:00"
    assert record.title and record.title.startswith("💫 Начинаем новую жизнь")
    assert record.meta["reactions_breakdown"][0]["count"] == 36


def test_missing_post_is_no_data() -> None:
    collector = TelegramCollector(
        text_fetcher=fake_text({"t.me": load_text("telegram_404.html")})
    )

    record = collector.collect("https://t.me/UniversitetMIET/999999999")

    assert record.status is CollectionStatus.NO_DATA
    assert record.views is None
    assert any("не найден" in warning.lower() for warning in record.warnings)
