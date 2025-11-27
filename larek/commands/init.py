"""Команда инициализации проекта."""

import os
import subprocess
import pathlib
import re
import random
import string


import pydantic_yaml
import yaml

import typer
from rich.console import Console
from rich import print as rprint
from rich.panel import Panel

from larek.composer.builder import Composer
from larek.pipeliner.builder import PipelineComposer
from larek.models import RepoSchema
from larek.analyzer import repo, go, java, kotlin, javascript, python
from larek import utils
from larek.utils import git_ops
from larek.utils.gitlab_auth import get_authenticated_client


app = typer.Typer(help="Инициализация нового проекта")
console = Console()


def write_yaml_file(path: pathlib.Path, model) -> None:
    """Write pydantic model to YAML file with wide line width to prevent wrapping."""
    yaml_str = pydantic_yaml.to_yaml_str(model)
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


def clone_step(repo_path: str, branch: str) -> str:
    repo_name = repo_path.split("/")[-1].split(".")[0]

    if os.path.isdir(".git"):
        try:
            res = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            )
            if res.returncode == 0 and (
                repo_path in res.stdout.strip() or repo_name == pathlib.Path.cwd().name
            ):
                console.print("[green]Using current directory as repository.[/green]")
                return "."
        except Exception:
            pass

    if os.path.exists(repo_name):
        console.print(
            f"[yellow]Directory {repo_name} already exists. Skipping clone.[/yellow]"
        )
        return repo_name

    console.print(f"[green]Клонируем репозиторий:[/green] {repo_path}")
    console.print(f"[blue]Ветка:[/blue] {branch}")

    subprocess.run(
        ["git", "clone", "--branch", branch, repo_path],
        check=True,
    )

    console.print(f"[green]Репозиторий {repo_path} склонирован.[/green]")
    return repo_name


def analyze(repo_path_raw: str):
    # переходим в директорию с репозиторием и генерируем отчет + build.yaml
    repo_path = pathlib.Path(repo_path_raw)
    repo_analyzer = repo.RepoAnalyzer()

    repo_analyzer.register_analyzer(go.GoAnalyzer)
    repo_analyzer.register_analyzer(java.JavaAnalyzer)
    repo_analyzer.register_analyzer(kotlin.KotlinAnalyzer)
    repo_analyzer.register_analyzer(javascript.JavaScriptAnalyzer)
    repo_analyzer.register_analyzer(python.PythonAnalyze)
    repo_schema = repo_analyzer.analyze(repo_path)

    build_path = repo_path / ".larek/build.yaml"
    os.makedirs(build_path.parent, exist_ok=True)
    write_yaml_file(build_path, repo_schema)


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
        if dockerfile is None:
            rprint(
                f"[yellow]Skipping Dockerfile generation for {srv.name} (Android project)[/yellow]"
            )
            rprint("\n")
            continue

        dockerfile_path = repo_path / f".larek/{srv.name}.Dockerfile"
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

    pipeline = composer.generate_from_schema(config)
    pipeline_file = ".gitlab-ci.yml"
    with open(pipeline_file, "w", encoding="utf-8") as f:
        f.write(pipeline)

    service_names = ", ".join(srv.name for srv in config.services)
    rprint(f"pipeline file {pipeline_file} generated for: {service_names}")
    rprint("\n")


def push_to_gitlab(repo_path_raw: str):
    repo_path = pathlib.Path(repo_path_raw).resolve()
    repo_name = repo_path.name

    repo_name = re.sub(r"[^a-zA-Z0-9_\-\. ]", "-", repo_name)
    repo_name = repo_name.strip("-_ .") or "default-repo"

    gl = get_authenticated_client()

    project = None

    try:
        candidates = gl.projects.list(search=repo_name)
        for p in candidates:
            if (
                p.name == repo_name
                or p.path == repo_name
                or p.path_with_namespace.endswith(f"/{repo_name}")
            ):
                project = p
                console.print(
                    f"[green]Found existing project on GitLab: {p.path_with_namespace}[/green]"
                )
                break
    except Exception:
        project = None

    if not project:
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
                    console.print(
                        f"[yellow]Project '{repo_name}' already exists.[/yellow]"
                    )
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

    prev_branch = git_ops.create_and_checkout_branch("ci")

    console.print("[blue]Committing generated files on 'ci' branch...[/blue]")
    git_ops.add_all()
    if not git_ops.commit("[ci]: generated by larek cli"):
        console.print("[yellow]Nothing to commit.[/yellow]")

    res = None
    try:
        res = git_ops.ensure_remote("gitlab", project.ssh_url_to_repo)
        if res == "added":
            console.print("[green]Remote 'gitlab' added.[/green]")
        else:
            console.print("[yellow]Remote 'gitlab' updated with new URL.[/yellow]")
    except Exception as e:
        console.print(f"[red]Failed to configure remote: {e}[/red]")

    console.print("[blue]Pushing to GitLab...[/blue]")

    if not git_ops.push_all("gitlab"):
        console.print(
            "[yellow]Push failed. Attempting to reconcile with remote and retry...[/yellow]"
        )
        current_branch = git_ops.current_branch() or "main"
        console.print(
            f"[blue]Fetching from remote 'gitlab' and pulling branch '{current_branch}'...[/blue]"
        )
        try:
            git_ops.fetch("gitlab")
            git_ops.pull_rebase("gitlab", current_branch)
        except Exception as pull_err:
            console.print(
                f"[red]Git pull failed: {pull_err}\nWill attempt force-push as last resort.[/red]"
            )

        if not git_ops.push_all("gitlab"):
            console.print(
                "[yellow]Retry push failed, trying force-with-lease...[/yellow]"
            )
            git_ops.push_force_with_lease("gitlab")

    console.print("[green]✓ Repository pushed to GitLab successfully![/green]")
    console.print(f"[blue]View your project at:[/blue] {project.web_url}")

    try:
        if prev_branch and prev_branch != "ci":
            console.print(
                f"[blue]Checking out previous branch '{prev_branch}'...[/blue]"
            )
            git_ops.checkout(prev_branch)
    except Exception:
        console.print(
            "[yellow]Could not switch back to previous branch automatically.[/yellow]"
        )


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

    git_directory = clone_step(repo_url, branch)

    analyze(git_directory)

    docker(git_directory)

    os.chdir(git_directory)
    git_directory = "."

    gitlab_step(git_directory)

    # push_to_gitlab(git_directory)
