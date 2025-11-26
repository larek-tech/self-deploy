import pathlib
from typing import Literal, Optional, Any

from pydantic import BaseModel, Field


class Lib(BaseModel):
    """Внешняя зависимость фреймворк"""

    name: str = Field(..., description="Название библиотеки")
    version: Optional[str] = Field(None, description="Версия библиотеки")


class Dependencies(BaseModel):
    """Зависимости проекта (библиотека)."""

    packet_manager: str = Field(..., description="Менеджер зависимостей проекта")
    libs: list[Lib] = Field(default_factory=list, description="Используемые библиотеки")


class Linter(BaseModel):
    """Конфигурация линтера."""

    name: str = Field(..., description="Название линтера")
    config: str = Field(..., description="Путь до конфига линтера")


class Config(BaseModel):
    """Конфигурационный файл проекта."""

    name: str = Field(..., description="Название конфига")
    path: str = Field(..., description="Путь до конфига")


class Language(BaseModel):
    """Информация о языке программирования."""

    name: Literal["go", "python", "javascript", "typescript", "java", "kotlin"] = Field(
        ..., description="Название языка программирования"
    )
    version: Optional[str] = Field(None, description="Версия языка")


class Environment(BaseModel):
    """Переменные окружения для деплоя."""

    name: str = Field(..., description="Название переменной окружения")
    path: str = Field(..., description="Путь до файла с переменными окружения")


class Docker(BaseModel):
    """Информация о сборке в Docker."""

    dockerfiles: list[str] = Field(
        default_factory=list, description="Пути до Dockerfile'ов"
    )
    compose: Optional[str] = Field(None, description="Путь до docker-compose файла")
    environment: list[Environment] = Field(
        ..., description="Переменные окружения для Docker"
    )


class Service(BaseModel):
    """Сервис в репозитории."""

    path: pathlib.Path = Field(..., description="Путь до сервиса в репозитории")
    name: str = Field(..., description="Название сервиса")
    lang: Language = Field(..., description="Язык программирования")
    dependencies: Dependencies = Field(..., description="Зависимости проекта")
    configs: list[Config] = Field(
        default_factory=list, description="Конфигурационные файлы"
    )
    docker: Docker = Field(..., description="Информация о Docker сборке")
    entrypoints: list[str] = Field(
        default_factory=list, description="Точки входа приложения"
    )
    tests: str = Field(..., description="Команда для запуска тестов")
    linters: list[Linter] = Field(
        default_factory=list, description="Настроенные линтеры"
    )


class Deployment(BaseModel):
    """Информация о деплое сервиса."""

    type: Literal["dockerfile", "compose", "helm"] = Field(
        ..., description="Тип деплоя"
    )
    path: str = Field(..., description="Путь до файла деплоя")
    environment: list[Environment] = Field(
        default_factory=list, description="Переменные окружения для деплоя"
    )


class RepoSchema(BaseModel):
    """Схема данных репозитория."""

    is_monorepo: bool = Field(
        ..., description="Флаг, указывающий, является ли репозиторий монорепой."
    )
    services: list[Service] = Field(
        default_factory=list, description="Список сервисов в репозитории"
    )
    deployment: Optional[Deployment] = Field(
        ..., description="Информация о деплое сервиса"
    )
