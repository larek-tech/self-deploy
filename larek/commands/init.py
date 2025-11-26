"""Команда инициализации проекта."""

import typer
from rich.console import Console


app = typer.Typer(help="Инициализация нового проекта")
console = Console()


@app.callback(invoke_without_command=True)
def init(
    repo_url: str = typer.Argument(
        ...,
        help="URL репозитория для клонирования",
    ),
    branch: str = typer.Option(
        "main",
        "--branch",
        "-b",
        help="Ветка для клонирования",
    ),
):
    """
    Инициализация нового проекта из репозитория.

    Пример использования:
        larek init https://gitlab.local/root/my-project.git
    """
    console.print(f"[green]Инициализация проекта из репозитория:[/green] {repo_url}")
    console.print(f"[blue]Ветка:[/blue] {branch}")

    # TODO: Реализовать клонирование репозитория
    # TODO: Настроить CI/CD
    # TODO: Подключить к Nexus

    console.print("[yellow]Функционал в разработке...[/yellow]")
