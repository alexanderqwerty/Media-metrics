from __future__ import annotations

from conftest import fake_text, load_text
from collectors.base import CollectionStatus
from collectors.instagram import InstagramCollector, parse_media_url

REEL_URL = "https://www.instagram.com/reel/DeTUk4sDSp-/"


def test_parse_media_url() -> None:
    assert parse_media_url(REEL_URL) == ("reel", "DeTUk4sDSp-")
    assert parse_media_url("https://www.instagram.com/pubity/p/DeO4ZwFDUxH/") == (
        "p",
        "DeO4ZwFDUxH",
    )
    assert parse_media_url("https://www.instagram.com/p/DeO4ZwFDUxH/") == (
        "p",
        "DeO4ZwFDUxH",
    )


def test_collect_reel() -> None:
    collector = InstagramCollector(
        text_fetcher=fake_text({"instagram.com": load_text("instagram_reel.html")})
    )

    record = collector.collect(REEL_URL)

    assert record.status is CollectionStatus.OK
    assert record.external_id == "DeTUk4sDSp-"
    assert record.likes == 783_000
    assert record.comments == 7947
    assert record.views is None
    assert record.author == "nasa"
    assert record.published_at == "2026-10-09"
    assert record.title and record.title.startswith("POV: you're watching the Earth set")
    assert any("просмотры" in warning.lower() for warning in record.warnings)


def test_login_wall_is_unavailable() -> None:
    collector = InstagramCollector(
        text_fetcher=fake_text({"instagram.com": load_text("instagram_login.html")})
    )

    record = collector.collect(REEL_URL)

    assert record.status is CollectionStatus.UNAVAILABLE
    assert record.likes is None
    assert any("вход" in warning.lower() for warning in record.warnings)
