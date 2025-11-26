"""Базовый класс для шаблонов языков."""

import typing as tp
from abc import ABC, abstractmethod
from pathlib import Path
from ..models import Service


class BaseAnalyzer(ABC):
    """Абстрактный базовый класс для шаблонов сервисов"""

    @abstractmethod
    def analyze(self, root: Path) -> tp.Optional[Service]: ...
