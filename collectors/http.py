"""HTTP-слой: вежливые повторы и единая сессия.

По ТЗ, п. 4.2 — не менее трёх попыток с нарастающей задержкой.
Повторяем сетевые ошибки, 429 и 5xx; 401/403/404 не повторяем.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Mapping

import requests

USER_AGENT = (
    "Mozilla/5.0 (compatible; MediaMetricsBot/0.1; "
    "+https://github.com/alexanderqwerty/Media-metrics)"
)

RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


class FetchError(RuntimeError):
    """Сеть, HTTP-ошибка или не-JSON ответ."""

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        status: int | None = None,
        body: str = "",
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status = status
        self.body = body

    def __str__(self) -> str:
        base = super().__str__()
        if self.status is not None:
            return f"HTTP {self.status}: {base}"
        return base


@dataclass(frozen=True)
class RetryPolicy:
    timeout: float = 15.0
    attempts: int = 3
    base_delay: float = 0.8
    max_delay: float = 8.0


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        }
    )
    return session


def _retry_after(response: requests.Response, max_delay: float) -> float | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return max(0.0, min(seconds, max_delay))


def _request(
    session: requests.Session,
    url: str,
    *,
    timeout: float,
    attempts: int,
    base_delay: float,
    max_delay: float,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> requests.Response:
    if attempts < 1:
        raise ValueError("attempts должно быть >= 1")

    last_error: FetchError | None = None

    for attempt in range(1, attempts + 1):
        response: requests.Response | None = None
        try:
            response = session.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            last_error = FetchError(f"сетевая ошибка: {exc}", url=url)
        else:
            if response.status_code == 200:
                return response

            body = (response.text or "")[:500]
            error = FetchError(
                "площадка вернула ошибку",
                url=url,
                status=response.status_code,
                body=body,
            )
            if response.status_code not in RETRYABLE_STATUSES:
                raise error
            last_error = error

        if attempt == attempts:
            break

        delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
        if response is not None:
            retry_after = _retry_after(response, max_delay)
            if retry_after is not None:
                delay = retry_after
            else:
                delay += random.uniform(0, 0.25)
        else:
            delay += random.uniform(0, 0.25)
        time.sleep(delay)

    assert last_error is not None
    raise last_error


def fetch_text(
    session: requests.Session,
    url: str,
    *,
    timeout: float = 15.0,
    attempts: int = 3,
    base_delay: float = 0.8,
    max_delay: float = 8.0,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> str:
    response = _request(
        session,
        url,
        timeout=timeout,
        attempts=attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        params=params,
        headers=headers,
    )
    return response.text


def fetch_json(
    session: requests.Session,
    url: str,
    *,
    timeout: float = 15.0,
    attempts: int = 3,
    base_delay: float = 0.8,
    max_delay: float = 8.0,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> Any:
    response = _request(
        session,
        url,
        timeout=timeout,
        attempts=attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        params=params,
        headers=headers,
    )
    try:
        return response.json()
    except ValueError as exc:
        raise FetchError(
            "ответ не является JSON",
            url=url,
            status=response.status_code,
            body=(response.text or "")[:500],
        ) from exc
