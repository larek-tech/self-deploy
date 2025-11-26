"""Главный модуль CLI приложения."""

import typer
from rich.console import Console

from larek.commands import init, status, debug

app = typer.Typer(
    name="larek",
    help="CLI инструмент для управления инфраструктурой self-deploy",
    add_completion=False,
)

console = Console()

# Регистрация команд
app.add_typer(init.app, name="init")
app.add_typer(debug.app, name="debug")
app.command()(status.status)


@app.callback()
def main():
    """
    Larek CLI - инструмент для управления инфраструктурой self-deploy от larek.tech
    """
    pass


if __name__ == "__main__":
    app()
