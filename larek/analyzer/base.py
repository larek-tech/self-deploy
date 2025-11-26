"""Базовый класс для шаблонов языков."""

import typing as tp
from abc import ABC, abstractmethod
from pathlib import Path
from ..models import Service


class BaseAnalyzer(ABC):
    """Абстрактный базовый класс для шаблонов сервисов"""

    @abstractmethod
    def analyze(self, root: Path) -> tp.Optional[Service]: ...

    def _find_repo_root(self, start_path: Path) -> tp.Optional[Path]:
        """Find the repository root by walking up the directory tree looking for .git"""
        current = start_path if start_path.is_dir() else start_path.parent
        max_depth = 10
        depth = 0

        while depth < max_depth:
            if (current / ".git").exists():
                return current
            if current.parent == current:
                return None
            current = current.parent
            depth += 1

        return None
