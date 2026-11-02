from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class RawMetrics:
    """Единый формат данных для всех площадок (подготовка к JSON)."""
    platform: str
    url: str
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    collected_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class BaseCollector(ABC):
    @abstractmethod
    def collect(self, url: str) -> RawMetrics:
        """Метод сбора данных, который обязаны реализовать все парсеры."""
        ...