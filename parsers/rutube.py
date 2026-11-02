import re
import requests
from datetime import datetime, timezone
from .base import BaseCollector, RawMetrics


class RutubeCollector(BaseCollector):
    API_TEMPLATE = "https://rutube.ru/api/video/{video_id}/?format=json"

    def collect(self, url: str) -> RawMetrics:
        video_id = self._extract_video_id(url)
        api_url = self.API_TEMPLATE.format(video_id=video_id)

        try:
            # Пытаемся сделать запрос
            response = requests.get(api_url, timeout=10)

            # Если Rutube нас заблокировал (403)
            if response.status_code == 403:
                print(f"[Rutube] Доступ заблокирован (403). Требуется обход Cloudflare.")
                return RawMetrics(platform="rutube", url=url, collected_at=datetime.now(timezone.utc).isoformat())

            response.raise_for_status()
            data = response.json()

            views = data.get("hits") or data.get("view_count")
            likes = data.get("likes") or data.get("likes_count")
            comments = data.get("comments_count")

            return RawMetrics(
                platform="rutube", url=url,
                views=int(views) if views is not None else None,
                likes=int(likes) if likes is not None else None,
                comments=int(comments) if comments is not None else None,
                collected_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            print(f"[Rutube] Ошибка при сборе: {e}")
            return RawMetrics(platform="rutube", url=url, collected_at=datetime.now(timezone.utc).isoformat())

    @staticmethod
    def _extract_video_id(url: str) -> str:
        match = re.search(r"/video/([0-9a-f]{32})", url)
        if not match:
            raise ValueError(f"Не удалось извлечь video_id из URL: {url}")
        return match.group(1)