from __future__ import annotations

import json
from datetime import datetime, timezone

from collectors.base import CollectionStatus, MetricRecord, Platform, SCHEMA_VERSION


def test_to_dict_contract() -> None:
    record = MetricRecord(
        platform=Platform.TELEGRAM,
        url="https://t.me/chan/1",
        status=CollectionStatus.OK,
        collected_at=datetime(2026, 11, 17, 13, 0, tzinfo=timezone.utc),
        external_id="chan/1",
        title="Пост",
        views=100,
        reactions=5,
        meta={"channel": "chan"},
        warnings=["нет лайков"],
    )

    payload = record.to_dict()

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["platform"] == "telegram"
    assert payload["status"] == "ok"
    assert payload["collected_at"] == "2026-11-17T13:00:00+00:00"
    assert payload["publication"]["id"] == "chan/1"
    assert payload["metrics"] == {
        "views": 100,
        "likes": None,
        "comments": None,
        "shares": None,
        "reactions": 5,
    }
    json.dumps(payload, ensure_ascii=False)


def test_none_is_not_zero() -> None:
    record = MetricRecord(platform=Platform.INSTAGRAM, url="https://instagram.com/p/x/")
    assert record.has_data() is False
    assert record.is_complete() is False
