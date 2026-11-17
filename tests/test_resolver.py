from __future__ import annotations

import pytest

from collectors.base import Platform
from collectors.platforms import PlatformResolver


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.tiktok.com/@nasa/video/7685144199716408589", Platform.TIKTOK),
        ("https://m.tiktok.com/@nasa/video/7685144199716408589", Platform.TIKTOK),
        ("tiktok.com/@nasa/video/7685144199716408589", Platform.TIKTOK),
        ("https://t.me/UniversitetMIET/6062", Platform.TELEGRAM),
        ("https://telegram.me/chan/42", Platform.TELEGRAM),
        ("https://www.instagram.com/reel/DeTUk4sDSp-/", Platform.INSTAGRAM),
        ("instagram.com/p/DeO4ZwFDUxH/", Platform.INSTAGRAM),
        ("https://example.com/post/1", None),
        ("", None),
    ],
)
def test_resolve(url: str, expected: Platform | None) -> None:
    assert PlatformResolver.resolve(url) is expected


def test_normalize() -> None:
    assert (
        PlatformResolver.normalize("t.me/UniversitetMIET/6062#comments")
        == "https://t.me/UniversitetMIET/6062"
    )
