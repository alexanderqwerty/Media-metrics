from __future__ import annotations

import pytest

from collectors.extractors import epoch_to_iso, first_line, parse_count


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2.38K", 2380),
        ("87K", 87000),
        ("3,004", 3004),
        ("1 234", 1234),
        ("1.2M", 1_200_000),
        ("1,2 тыс.", 1200),
        ("814", 814),
        ("0", 0),
        (36, 36),
        ("🔥 36", 36),
        ("—", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_count(raw, expected) -> None:
    assert parse_count(raw) == expected


def test_first_line_and_epoch() -> None:
    assert first_line("\n\n  Первая строка  \nВторая") == "Первая строка"
    assert first_line(None) is None
    assert epoch_to_iso(1789337087) == "2026-09-13T22:04:47+00:00"
    assert epoch_to_iso("bad") is None
