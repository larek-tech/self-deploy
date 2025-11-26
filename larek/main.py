"""Главный модуль CLI приложения."""

import typer
from rich.console import Console

from larek.commands import init, status, debug, clear, docker, gitlab, clone

app = typer.Typer(
    name="larek",
    help="CLI инструмент для управления инфраструктурой self-deploy",
    add_completion=False,
)

console = Console()

# Регистрация команд
app.add_typer(init.app, name="init")
app.add_typer(debug.app, name="debug")
app.add_typer(clone.app, name="clone")
app.command()(status.status)
app.command()(clear.clear)
app.command()(docker.docker)
app.command()(gitlab.gitlab)


@app.callback()
def main():
    """
    Larek CLI - инструмент для управления инфраструктурой self-deploy от larek.tech
    """
    pass


if __name__ == "__main__":
    app()
