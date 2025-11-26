import typer
import pathlib
import pydantic_yaml
import os
import pathlib
from rich.console import Console
from larek.analyzer import repo, go, java, kotlin


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
    repo_analyzer = repo.RepoAnalyzer()
    repo_analyzer.register_analyzer(lambda: go.GoAnalyzer())
    repo_analyzer.register_analyzer(lambda: java.JavaAnalyzer())
    repo_analyzer.register_analyzer(lambda: kotlin.KotlinAnalyzer())
    repo_schema = repo_analyzer.analyze(repo_path)

    build_path = pathlib.Path(".larek/build.yaml")
    os.mkdir(build_path.parent)
    pydantic_yaml.to_yaml_file(build_path, repo_schema)

    console.print(
        f"[green]Результат анализа репозитория записан в файл .larek/build.yaml.[/green]"
    )
