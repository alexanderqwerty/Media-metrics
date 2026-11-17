from __future__ import annotations

import pytest
import requests

from collectors import http


class FakeResponse:
    def __init__(self, status: int, payload=None, text: str = "", headers=None):
        self.status_code = status
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(http.time, "sleep", lambda seconds: sleeps.append(seconds))
    return sleeps


def test_text_retries_503(no_sleep) -> None:
    session = FakeSession([FakeResponse(503, text="busy"), FakeResponse(200, text="ok")])

    assert http.fetch_text(session, "https://example.test", attempts=3) == "ok"
    assert len(session.calls) == 2
    assert len(no_sleep) == 1


def test_json_returns_object(no_sleep) -> None:
    session = FakeSession([FakeResponse(200, {"ok": True})])

    assert http.fetch_json(session, "https://example.test", attempts=2) == {"ok": True}


def test_404_is_not_retried(no_sleep) -> None:
    session = FakeSession([FakeResponse(404, text="not found"), FakeResponse(200, text="x")])

    with pytest.raises(http.FetchError) as exc_info:
        http.fetch_text(session, "https://example.test", attempts=3)

    assert exc_info.value.status == 404
    assert len(session.calls) == 1


def test_network_error_is_retried(no_sleep) -> None:
    session = FakeSession([requests.ConnectionError("boom"), FakeResponse(200, text="ok")])

    assert http.fetch_text(session, "https://example.test", attempts=2) == "ok"


def test_invalid_json_raises(no_sleep) -> None:
    session = FakeSession([FakeResponse(200, ValueError("no json"), text="<html>")])

    with pytest.raises(http.FetchError, match="не является JSON"):
        http.fetch_json(session, "https://example.test", attempts=1)


def test_retry_after_is_respected(no_sleep) -> None:
    session = FakeSession(
        [
            FakeResponse(429, text="slow", headers={"Retry-After": "2"}),
            FakeResponse(200, text="ok"),
        ]
    )

    http.fetch_text(session, "https://example.test", attempts=2)

    assert no_sleep == [2.0]
