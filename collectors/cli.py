"""CLI: собрать метрики TikTok, Telegram, Instagram и напечатать JSON."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Sequence

from .base import CollectionStatus, MetricRecord, Platform
from .http import RetryPolicy, make_session
from .instagram import InstagramCollector
from .platforms import PlatformResolver
from .telegram import TelegramCollector
from .tiktok import TikTokCollector

EXAMPLES = (
    "https://www.tiktok.com/@nasa/video/7685144199716408589",
    "https://t.me/UniversitetMIET/6062",
    "https://www.instagram.com/reel/DeTUk4sDSp-/",
)


def _format_value(value: int | None) -> str:
    if value is None:
        return "—"
    return f"{value:,}".replace(",", "\u202f")


def _print_record(record: MetricRecord) -> None:
    print(f"[{record.status.value.upper()}] {record.platform.value}  {record.url}")
    if record.title:
        print(f"    {record.title}")
    if record.author:
        print(f"    автор: {record.author}")
    print(
        "    просмотры={views}  лайки={likes}  комментарии={comments}  "
        "репосты={shares}  реакции={reactions}".format(
            views=_format_value(record.views),
            likes=_format_value(record.likes),
            comments=_format_value(record.comments),
            shares=_format_value(record.shares),
            reactions=_format_value(record.reactions),
        )
    )
    for warning in record.warnings:
        print(f"    ! {warning}")
    print()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Сбор метрик публикаций TikTok, Telegram и Instagram. "
            "Прототип issue #6: результаты складываются в объекты и "
            "печатаются в консоль."
        ),
        epilog=(
            "Примеры адресов:\n  "
            + "\n  ".join(EXAMPLES)
            + "\n\nПример: python main.py "
            + " ".join(EXAMPLES)
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("urls", nargs="*", help="адреса публикаций")
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="печатать только JSON (удобно для перенаправления в файл)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="таймаут одного HTTP-запроса, секунд (по умолчанию 15)",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=3,
        help="число попыток запроса (по умолчанию 3)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="пауза между адресами, секунд (по умолчанию 0.5)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="вернуть код 1, если были ошибки сбора или неподдерживаемые адреса",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.urls:
        parser.print_help()
        return 2

    retry = RetryPolicy(timeout=args.timeout, attempts=max(1, args.attempts))
    session = make_session()
    collectors = {
        Platform.TIKTOK: TikTokCollector(session=session, retry=retry),
        Platform.TELEGRAM: TelegramCollector(session=session, retry=retry),
        Platform.INSTAGRAM: InstagramCollector(session=session, retry=retry),
    }

    records: list[MetricRecord] = []
    unsupported: list[str] = []

    for index, raw_url in enumerate(args.urls):
        url = PlatformResolver.normalize(raw_url)
        platform = PlatformResolver.resolve(url)

        if platform is None:
            unsupported.append(url)
            if not args.json_only:
                print(f"[SKIP] неподдерживаемая площадка: {url}\n")
            else:
                print(f"SKIP: неподдерживаемая площадка: {url}", file=sys.stderr)
            continue

        if index > 0 and args.delay > 0:
            time.sleep(args.delay)

        record = collectors[platform].collect(url)
        records.append(record)

        if not args.json_only:
            _print_record(record)

    payload = [record.to_dict() for record in records]
    if args.json_only:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("=== JSON ===")
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.strict:
        has_errors = bool(unsupported) or any(
            record.status in (CollectionStatus.UNAVAILABLE, CollectionStatus.PARSE_ERROR)
            for record in records
        )
        if has_errors:
            return 1

    return 0
