from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def load_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def load_json(name: str):
    return json.loads(load_text(name))


def fake_text(routes: dict[str, object]):
    def fetch(session, url, **kwargs):
        for marker, payload in routes.items():
            if marker in url:
                if isinstance(payload, Exception):
                    raise payload
                return payload
        raise AssertionError(f"Неожиданный URL в тесте: {url}")

    return fetch


def fake_json(routes: dict[str, object]):
    def fetch(session, url, **kwargs):
        for marker, payload in routes.items():
            if marker in url:
                if isinstance(payload, Exception):
                    raise payload
                return payload
        raise AssertionError(f"Неожиданный URL в тесте: {url}")

    return fetch
