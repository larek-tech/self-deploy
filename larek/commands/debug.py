import typer
from rich.console import Console
from larek.analyzer import go
import pathlib


app = typer.Typer(help="Дебаг анализа репозитория")
console = Console()


@app.callback(invoke_without_command=True)
def debug(
    repo_path_raw: str = typer.Argument(
        ...,
        help="Путь до локального репозитория",
    ),
    branch: str = typer.Option(
        "main",
        "--branch",
        "-b",
        help="Ветка для анализа",
    ),
):
    """
    Инициализация нового проекта из репозитория.

    Пример использования:
        larek init ./repo/backend
    """
    console.print(
        f"[green]Инициализация проекта из репозитория:[/green] {repo_path_raw}"
    )
    console.print(f"[blue]Ветка:[/blue] {branch}")

    repo_path = pathlib.Path(repo_path_raw)
    go_analyzer = go.GoAnalyzer()
    go_service = go_analyzer.analyze(repo_path)
    if go_service is None:
        console.print(f"[red]{repo_path_raw} не является сервисом на Go.[/red]")
        return

    console.print(
        f"[green]Результат анализа Go репозитория: {go_service.model_dump_json()}[/green]"
    )
