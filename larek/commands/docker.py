import os
import typer
from larek.composer import builder
from larek.models import RepoSchema

from rich.progress import Progress
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from pydantic_yaml import parse_yaml_raw_as, to_yaml_str


def docker(
    build_file: str = typer.Argument(
        "./.larek/build.yaml",
        help="путь до build.yaml",
    ),
):
    """Команда для отладки этапа генерации Dockerfile"""

    if not os.path.exists(build_file):
        rprint(f"[red]Error: File not found: {build_file}[/red]")
        rprint(f"[yellow]Current working directory: {os.getcwd()}[/yellow]")
        raise typer.Exit(code=1)

    with open(build_file, "r", encoding="utf-8") as f:
        yml = f.read()

    config = parse_yaml_raw_as(RepoSchema, yml)
    composer = builder.Composer()
    for srv in config.services:
        dockerfile = composer.get_dockerfile(srv)

        # rprint(
        #     Panel(dockerfile, title=f"Dockerfile for {srv.name}", border_style="green")
        # )
        with open(f"{srv.name}.Dockerfile", "w", encoding="utf-8") as f:
            f.write(dockerfile)

        rprint("docker file generated for " + srv.name)

        # Instructions for building and running the Docker image
        rprint("\n[cyan]Build and Run Instructions:[/cyan]")
        rprint(
            f"[green]1. Build the Docker image:[/green] docker build -t {srv.name}:latest -f {srv.name}.Dockerfile ."
        )
        rprint(
            f"[green]2. Run the Docker container:[/green] docker run --rm -it {srv.name}:latest"
        )
        rprint("\n")
