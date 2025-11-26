import typing as tp
from pathlib import Path
from larek.analyzer import BaseAnalyzer
from larek import models


class RepoAnalyzer:
    """Анализатор репозитория, который использует разные анализаторы языков."""

    def __init__(self) -> None:
        self.analyzers: list[tp.Callable[[], BaseAnalyzer]] = []

    def register_analyzer(self, analyzer: tp.Callable[[], BaseAnalyzer]) -> None:
        """Регистрация нового анализатора языка."""
        self.analyzers.append(analyzer)

    def analyze(self, root: Path) -> models.RepoSchema:
        """Анализ репозитория и сбор информации о сервисах."""

        dirs = [d for d in root.iterdir() if d.is_dir() and self._file_filter(d)]
        dirs.append(root)

        services: list[models.Service] = []
        for d in dirs:
            for get_analyzer in self.analyzers:
                service = get_analyzer().analyze(d)
                if service is not None:
                    services.append(service)
                    break
        return models.RepoSchema(services=services)

    def _file_filter(self, file: Path) -> bool:
        match file.name:
            case (
                ".gitignore"
                | ".git"
                | "vendor/"
                | "node_modules/"
                | "__pycache__/"
                | ".idea/"
                | ".vscode/"
                | ".venv/"
            ):
                return False
        return True
