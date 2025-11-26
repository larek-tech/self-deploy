"""Команда инициализации проекта."""

import os
import subprocess
import pathlib
import re
import random
import string


import pydantic_yaml

import typer
from rich.console import Console
from rich import print as rprint
from rich.panel import Panel

from larek.composer.builder import Composer
from larek.pipeliner.builder import PipelineComposer
from larek.models import RepoSchema
from larek.analyzer import repo, go, java, kotlin
from larek import utils
from larek.utils.gitlab_auth import get_authenticated_client


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

        rprint(f"docker file: {dockerfile_path} generated for: {srv.name}")
        rprint("\n")


def gitlab_step(repo_path_raw: str):
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
        pipeline_file = ".gitlab-ci.yml"
        with open(pipeline_file, "w", encoding="utf-8") as f:
            f.write(pipeline)

        rprint(f"pipeline file {pipeline_file} generated for: {srv.name}")
        rprint("\n")


def push_to_gitlab(repo_path_raw: str):
    repo_path = pathlib.Path(repo_path_raw).resolve()
    repo_name = repo_path.name

    repo_name = re.sub(r"[^a-zA-Z0-9_\-\. ]", "-", repo_name)
    repo_name = repo_name.strip("-_ .") or "default-repo"

    gl = get_authenticated_client()

    project = None
    original_repo_name = repo_name

    for attempt in range(3):
        console.print(
            f"[blue]Creating project on GitLab (Attempt {attempt + 1}/3):[/blue] {repo_name}"
        )
        try:
            project = gl.projects.create({"name": repo_name})
            break
        except Exception as e:
            if "has already been taken" in str(e):
                console.print(f"[yellow]Project '{repo_name}' already exists.[/yellow]")
                if attempt < 2:
                    suffix = "".join(
                        random.choices(string.ascii_lowercase + string.digits, k=4)
                    )
                    repo_name = f"{original_repo_name}-{suffix}"
                    console.print(
                        f"[yellow]Retrying with new name: {repo_name}[/yellow]"
                    )
                else:
                    rprint(
                        f"[red]Error: Could not create project after 3 attempts.[/red]"
                    )
                    raise typer.Exit(code=1)
            else:
                rprint(f"[red]Error creating project: {e}[/red]")
                raise typer.Exit(code=1)

    if not project:
        rprint("[red]Error: Project creation failed unexpectedly.[/red]")
        raise typer.Exit(code=1)

    http_url = utils.resolve_docker_url(project.http_url_to_repo)

    console.print(
        Panel(
            f"[green]✓ Project created successfully![/green]\n\n"
            f"[bold]Project:[/bold] {project.name}\n"
            f"[bold]URL:[/bold] {project.web_url}\n"
            f"[bold]SSH URL:[/bold] {project.ssh_url_to_repo}\n"
            f"[bold]HTTP URL:[/bold] {http_url}",
            title="[bold cyan]New GitLab Repository[/bold cyan]",
            border_style="green",
        )
    )

    console.print("[blue]Committing generated files...[/blue]")
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(
        ["git", "commit", "-m", "[ci]: generated by larek cli"],
        capture_output=True,
        text=True,
        check=True,
    )

    subprocess.run(
        ["git", "remote", "add", "gitlab", project.ssh_url_to_repo],
        check=True,
    )

    console.print("[blue]Pushing to GitLab...[/blue]")

    result = subprocess.run(
        ["git", "push", "-u", "gitlab", "--all"],
        capture_output=True,
        text=True,
        check=True,
    )

    if result.returncode != 0:
        console.print("[yellow]Standard push failed, trying with force...[/yellow]")
        subprocess.run(["git", "push", "-u", "gitlab", "--all", "--force"], check=True)

    console.print("[green]✓ Repository pushed to GitLab successfully![/green]")
    console.print(f"[blue]View your project at:[/blue] {project.web_url}")


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

    gitlab_step(git_directory)

    push_to_gitlab(git_directory)
