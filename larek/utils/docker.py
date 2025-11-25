"""Утилиты для работы с Docker."""

import subprocess
from rich.console import Console

console = Console()


def check_container_status(container_name: str) -> bool:
    """
    Проверяет, запущен ли контейнер.

    Args:
        container_name: Имя контейнера

    Returns:
        True если контейнер запущен, False в противном случае
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "true"
    except Exception:
        return False


def get_container_health(container_name: str) -> str:
    """
    Получает статус здоровья контейнера.

    Args:
        container_name: Имя контейнера

    Returns:
        Статус здоровья контейнера
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", container_name],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"
