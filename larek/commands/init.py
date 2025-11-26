"""Команда инициализации проекта."""

import os
import subprocess
import pathlib
import pydantic_yaml

import typer
from rich.console import Console
from rich import print as rprint

from larek.composer.builder import Composer
from larek.pipeliner.builder import PipelineComposer
from larek.models import RepoSchema
from larek.analyzer import repo, go, java, kotlin


app = typer.Typer(help="Инициализация нового проекта")
console = Console()


def clone_step(repo_path: str, branch: str):
    console.print(f"[green]Клонируем репозиторий:[/green] {repo_path}")
    console.print(f"[blue]Ветка:[/blue] {branch}")

    subprocess.run(
        ["git", "clone", "--branch", branch, repo_path],
        check=True,
    )

    console.print(f"[green]Репозиторий {repo_path} склонирован.[/green]")


def analyze(repo_path_raw: str):
    # переходим в директорию с репозиторием и генерируем отчет + build.yaml
    repo_path = pathlib.Path(repo_path_raw)
    repo_analyzer = repo.RepoAnalyzer()

    repo_analyzer.register_analyzer(go.GoAnalyzer)
    repo_analyzer.register_analyzer(java.JavaAnalyzer)
    repo_analyzer.register_analyzer(kotlin.KotlinAnalyzer)
    repo_schema = repo_analyzer.analyze(repo_path)

    build_path = pathlib.Path(".larek/build.yaml")
    os.mkdir(build_path.parent)
    pydantic_yaml.to_yaml_file(build_path, repo_schema)


def docker(repo_path_raw: str):
    repo_path = pathlib.Path(repo_path_raw)
    build_file = repo_path / ".larek" / "build.yaml"

    if not os.path.exists(build_file):
        rprint(f"[red]Error: File not found: {build_file}[/red]")
        rprint(f"[yellow]Current working directory: {os.getcwd()}[/yellow]")
        raise typer.Exit(code=1)

    with open(build_file, "r", encoding="utf-8") as f:
        yml = f.read()

    config = pydantic_yaml.parse_yaml_raw_as(RepoSchema, yml)
    composer = Composer()
    for srv in config.services:
        dockerfile = composer.get_dockerfile(srv)
        dockerfile_path = f".larek/{srv.name}.Dockerfile"
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(dockerfile)

        rprint("docker file generated for " + srv.name)

        rprint("\n[cyan]Build and Run Instructions:[/cyan]")
        rprint(
            f"[green]1. Build the Docker image:[/green] docker build -t {srv.name}:latest -f {srv.name}.Dockerfile ."
        )
        rprint(
            f"[green]2. Run the Docker container:[/green] docker run --rm -it {srv.name}:latest"
        )
        rprint("\n")


def gitlab(repo_path_raw: str):
    repo_path = pathlib.Path(repo_path_raw)
    build_file = repo_path / ".larek" / "build.yaml"
    if not os.path.exists(build_file):
        rprint(f"[red]Error: File not found: {build_file}[/red]")
        rprint(f"[yellow]Current working directory: {os.getcwd()}[/yellow]")
        raise typer.Exit(code=1)

    with open(build_file, "r", encoding="utf-8") as f:
        yml = f.read()

    config = pydantic_yaml.parse_yaml_raw_as(RepoSchema, yml)
    composer = PipelineComposer()
    for srv in config.services:
        pipeline = composer.get_pipeline(srv)
        pipeline_file = f".larek/{srv.name}.gitlab-ci.yml"
        with open(pipeline_file, "w", encoding="utf-8") as f:
            f.write(pipeline)

        rprint(f"pipeline file {pipeline_file} generated for: {srv.name}")
        rprint("\n")


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

    clone_step(repo_url, branch)
    git_directory = repo_url.split("/")[-1].split(".")[0]
    os.chdir(git_directory)
    git_directory = "."

    analyze(git_directory)

    docker(git_directory)

    gitlab(git_directory)

    console.print("[yellow]Функционал в разработке...[/yellow]")
