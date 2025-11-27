import typer
import pathlib
import pydantic_yaml
import yaml
import os
import pathlib
from rich.console import Console
from larek.analyzer import repo, go, java, kotlin, javascript, python


app = typer.Typer(help="Дебаг анализа репозитория")
console = Console()


def write_yaml_file(path: pathlib.Path, model) -> None:
    """Write pydantic model to YAML file with wide line width to prevent wrapping."""
    yaml_str = pydantic_yaml.to_yaml_str(model)
    # Re-dump with wider line width
    data = yaml.safe_load(yaml_str)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            width=10000,
            allow_unicode=True,
            sort_keys=False,
        )


def to_yaml_str_wide(model) -> str:
    """Convert pydantic model to YAML string with wide line width."""
    yaml_str = pydantic_yaml.to_yaml_str(model)
    data = yaml.safe_load(yaml_str)
    return yaml.dump(
        data, default_flow_style=False, width=10000, allow_unicode=True, sort_keys=False
    )


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
    repo_analyzer.register_analyzer(go.GoAnalyzer)
    repo_analyzer.register_analyzer(java.JavaAnalyzer)
    repo_analyzer.register_analyzer(kotlin.KotlinAnalyzer)
    repo_analyzer.register_analyzer(javascript.JavaScriptAnalyzer)
    repo_analyzer.register_analyzer(python.PythonAnalyze)

    repo_schema = repo_analyzer.analyze(repo_path)

    build_path = pathlib.Path(".larek/build.yaml")

    console.print(f"[blue]Запись результата в файл:[/blue] {build_path}")
    os.makedirs(build_path.parent, exist_ok=True)
    write_yaml_file(build_path, repo_schema)
    print(to_yaml_str_wide(repo_schema))
