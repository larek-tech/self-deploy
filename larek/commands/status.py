"""Команда проверки статуса инфраструктуры."""

import typer
from rich.console import Console
from rich.table import Table
import requests

console = Console()


def status():
    """
    Проверка статуса всех сервисов инфраструктуры.
    """
    table = Table(title="Статус сервисов")
    table.add_column("Сервис", style="cyan", no_wrap=True)
    table.add_column("Статус", style="magenta")
    table.add_column("URL", style="green")
    services = [
        {"name": "GitLab", "url": "http://gitlab.local"},
        {"name": "Nexus", "url": "http://localhost:8081"},
        {"name": "GitLab Runner", "url": None},
        {"name": "SonarQube", "url": None},
    ]
    for service in services:
        try:
            if service["url"]:
                response = requests.get(service["url"], timeout=5)
                if response.status_code == 200:
                    table.add_row(service["name"], "🟢 Работает", service["url"])
                    console.print(f"[green]✔[/green] {service['name']} is ready")
                else:
                    table.add_row(service["name"], "🔴 Недоступен", service["url"])
                    console.print(
                        f"[red]✖[/red] {service['name']} returned status code {response.status_code}"
                    )
            else:
                table.add_row(service["name"], "🔴 Не настроен", "-")
                console.print(f"[yellow]⚠[/yellow] {service['name']} is not configured")
        except requests.RequestException as e:
            table.add_row(service["name"], "🔴 Недоступен", service["url"] or "-")
            console.print(f"[red]✖[/red] {service['name']} is not reachable: {e}")
    console.print(table)
