"""Базовый класс для шаблонов языков."""

from abc import ABC, abstractmethod
from pathlib import Path
from ..models import RepoSchema


class BaseAnalyzer(ABC):
    """Абстрактный базовый класс для шаблонов сервисов"""

    @abstractmethod
    def analyze(self, root: Path) -> RepoSchema: ...
