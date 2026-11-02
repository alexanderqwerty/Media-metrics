from datetime import datetime, timezone
from .base import BaseCollector, RawMetrics


class MaxCollector(BaseCollector):
    def __init__(self, token: str = None):
        # Здесь в будущем будет токен от API MAX
        self._token = token

    def collect(self, url: str) -> RawMetrics:
        print(f"[MAX] Парсинг {url}...")
        print("[MAX] Внимание: для реального сбора нужен токен бота и авторизация.")

        # Возвращаем тестовые данные (заглушку), чтобы пайплайн работал
        return RawMetrics(
            platform="max",
            url=url,
            views=1250,  # Тестовые данные
            likes=84,  # Тестовые данные
            comments=12,  # Тестовые данные
            collected_at=datetime.now(timezone.utc).isoformat(),
        )