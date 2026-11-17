#!/usr/bin/env python3
"""Точка входа парсеров TikTok, Telegram, Instagram (issue #6).

Запуск:
    python main.py https://t.me/<channel>/<post> \
        https://www.tiktok.com/@user/video/<id> \
        https://www.instagram.com/reel/<code>/
"""

from collectors.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
