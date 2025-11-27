"""Главный модуль CLI приложения."""

import typer
from rich.console import Console

from larek.commands import init, status, debug, clear, docker, gitlab, clone, login

app = typer.Typer(
    name="larek",
    help="Удобный CLI для управления self-deploy-инфраструктурой ⚙️",
    add_completion=False,
)

console = Console()

# Регистрация команд
app.add_typer(init.app, name="init")
app.add_typer(debug.app, name="debug")
app.add_typer(clone.app, name="clone")
app.add_typer(login.app, name="login")
app.command()(status.status)
app.command()(clear.clear)
app.command()(docker.docker)
app.command()(gitlab.gitlab)


@app.callback()
def main():
    """
    Larek CLI — инструмент для управления self-deploy (larek.tech).

    Используйте команды для инициализации проектов, отладки и работы с GitLab.
    """
    pass


if __name__ == "__main__":
    app()
