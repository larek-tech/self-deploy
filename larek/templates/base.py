"""Базовый класс для шаблонов языков."""

from abc import ABC, abstractmethod
from pathlib import Path


class LanguageTemplate(ABC):
    """Абстрактный базовый класс для шаблонов языков программирования."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Название языка."""
        ...

    @property
    @abstractmethod
    def extensions(self) -> list[str]:
        """Расширения файлов для данного языка."""
        ...

    @property
    @abstractmethod
    def package_managers(self) -> list[str]:
        """Поддерживаемые пакетные менеджеры."""
        ...

    @property
    @abstractmethod
    def default_linters(self) -> list[str]:
        """Линтеры по умолчанию."""
        ...

    @abstractmethod
    def create_structure(self, project_path: Path, project_name: str) -> None:
        """Создать структуру проекта."""
        ...

    @abstractmethod
    def generate_dockerfile(self, version: str | None = None) -> str:
        """Сгенерировать Dockerfile."""
        ...

    @abstractmethod
    def get_test_command(self) -> str:
        """Получить команду для запуска тестов."""
        ...
