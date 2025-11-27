import typer
from rich.console import Console
import subprocess


app = typer.Typer(help="Клонирование репозитория")
console = Console()


@app.callback(invoke_without_command=True)
def clone(
    repo_path: str = typer.Argument(
        ...,
        help="URL Git-репозитория (ssh/https)",
    ),
    branch: str = typer.Option(
        "main",
        "--branch",
        "-b",
        help="Ветка для клонирования/анализа",
    ),
):
    """
    Клонирует репозиторий.

    Пример использования:
        larek clone ssh://<repository> --branch main
    """
    console.print(f"[green]▶️ Клонируем репозиторий:[/green] {repo_path}")
    console.print(f"[blue]Ветка:[/blue] {branch}")

    subprocess.run(
        ["git", "clone", "--branch", branch, repo_path],
        check=True,
    )

    console.print(f"[green]✨ Репозиторий успешно склонирован.[/green]")
