import os
import typer
from larek.composer import builder
from larek.models import RepoSchema

from rich.progress import Progress
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from pydantic_yaml import parse_yaml_raw_as


def docker(
    build_file: str = typer.Argument(
        "./.larek/build.yaml",
        help="Путь до файла build.yaml",
    ),
):
    """Команда для отладки генерации Dockerfile"""

    if not os.path.exists(build_file):
        rprint(f"[red]Ошибка: файл не найден: {build_file}[/red]")
        rprint(f"[yellow]Текущая директория: {os.getcwd()}[/yellow]")
        raise typer.Exit(code=1)

    with open(build_file, "r", encoding="utf-8") as f:
        yml = f.read()

    config = parse_yaml_raw_as(RepoSchema, yml)
    composer = builder.Composer()
    for srv in config.services:
        dockerfile = composer.get_dockerfile(srv)

        if dockerfile is None:

            rprint(
                f"[yellow]Пропускаем генерацию Dockerfile для {srv.name} (Android-проект)[/yellow]"
            )
            rprint(
                "[cyan]Примечание:[/cyan] Используйте pipeline builder для генерации GitLab CI для APK-сборок."
            )
            rprint("\n")
            continue

        with open(f"{srv.name}.Dockerfile", "w", encoding="utf-8") as f:
            f.write(dockerfile)

        rprint(f"Dockerfile сгенерирован: {srv.name}.Dockerfile")

        # Инструкции по сборке и запуску
        rprint("\n[cyan]Инструкции по сборке и запуску:[/cyan]")
        rprint(
            f"[green]1. Собрать образ:[/green] docker build -t {srv.name}:latest -f {srv.name}.Dockerfile ."
        )
        rprint(
            f"[green]2. Запустить контейнер:[/green] docker run --rm -it {srv.name}:latest"
        )
        rprint("\n")
