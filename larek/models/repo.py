"""Pydantic схемы для хранения данных GitHub репозитория."""

import pathlib
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Lib(BaseModel):
    """Внешняя зависимость фреймворк"""

    name: str = Field(..., description="Название библиотеки")
    version: Optional[str] = Field(None, description="Версия библиотеки")


class Dependency(BaseModel):
    """Зависимость проекта (библиотека)."""

    packet_manager: str = Field(..., description="менеджер зависимостей проекта")
    libs: list[Lib]


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


class Service(BaseModel):
    """Сервис в репозитории."""

    path: pathlib.Path = Field(..., description="Путь до сервиса в репозитории")
    name: str = Field(..., description="Название сервиса")
    lang: Language = Field(..., description="Язык программирования")
    dependencies: list[Dependency] = Field(
        default_factory=list, description="Зависимости проекта"
    )
    packet_manager: str = Field(
        ..., description="Пакетный менеджер (poetry, npm, gradle, go mod)"
    )
    libs: list[Dependency] = Field(
        default_factory=list, description="Используемые библиотеки"
    )
    configs: list[Config] = Field(
        default_factory=list, description="Конфигурационные файлы"
    )
    dockerfile: str = Field(..., description="Путь до Dockerfile")
    entrypoint: str = Field(..., description="Точка входа приложения")
    tests: str = Field(..., description="Команда для запуска тестов")
    linters: list[Linter] = Field(
        default_factory=list, description="Настроенные линтеры"
    )


class RepoSchema(BaseModel):
    """Схема данных репозитория."""

    services: list[Service] = Field(
        default_factory=list, description="Список сервисов в репозитории"
    )
