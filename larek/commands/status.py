"""Команда проверки статуса инфраструктуры."""

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def status():
    """
    Проверка статуса всех сервисов инфраструктуры.
    """
    table = Table(title="Статус сервисов")

    table.add_column("Сервис", style="cyan", no_wrap=True)
    table.add_column("Статус", style="magenta")
    table.add_column("URL", style="green")

    # TODO: Реализовать реальную проверку статуса
    table.add_row("GitLab", "🟢 Работает", "http://gitlab.local")
    table.add_row("Nexus", "🟢 Работает", "http://localhost:8081")
    table.add_row("GitLab Runner", "🟢 Работает", "-")
    table.add_row("SonarQube", "🔴 Не настроен", "-")

    console.print(table)
