"""Определение площадки по URL (issue #6)."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from .base import Platform


class PlatformResolver:
    _HOSTS: dict[str, Platform] = {
        "tiktok.com": Platform.TIKTOK,
        "www.tiktok.com": Platform.TIKTOK,
        "m.tiktok.com": Platform.TIKTOK,
        "vm.tiktok.com": Platform.TIKTOK,
        "vt.tiktok.com": Platform.TIKTOK,
        "t.me": Platform.TELEGRAM,
        "telegram.me": Platform.TELEGRAM,
        "instagram.com": Platform.INSTAGRAM,
        "www.instagram.com": Platform.INSTAGRAM,
        "m.instagram.com": Platform.INSTAGRAM,
    }

    @staticmethod
    def normalize(url: str) -> str:
        value = (url or "").strip()
        if value.startswith("//"):
            value = "https:" + value
        elif "://" not in value:
            value = "https://" + value
        parts = urlsplit(value)
        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc,
                parts.path,
                parts.query,
                "",
            )
        )

    @classmethod
    def resolve(cls, url: str) -> Platform | None:
        normalized = cls.normalize(url)
        host = (urlsplit(normalized).hostname or "").lower()
        return cls._HOSTS.get(host)
