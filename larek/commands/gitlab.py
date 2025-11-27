import os
import typer
from rich import print as rprint
from pydantic_yaml import parse_yaml_raw_as

from larek.pipeliner import builder
from larek.models import RepoSchema


def gitlab(
    build_file: str = typer.Argument(
        "./.larek/build.yaml",
        help="путь до build.yaml",
    ),
):
    """Команда для отладки этапа генерации gitlab-ci.yml"""

    if not os.path.exists(build_file):
        rprint(f"[red]Error: File not found: {build_file}[/red]")
        rprint(f"[yellow]Current working directory: {os.getcwd()}[/yellow]")
        raise typer.Exit(code=1)

    with open(build_file, "r", encoding="utf-8") as f:
        yml = f.read()

    config = parse_yaml_raw_as(RepoSchema, yml)
    composer = builder.PipelineComposer()

    pipeline = composer.generate_from_schema(config)
    pipeline_file = ".gitlab-ci.yml"
    with open(pipeline_file, "w", encoding="utf-8") as f:
        f.write(pipeline)

    service_names = ", ".join(srv.name for srv in config.services)
    rprint(f"pipeline file {pipeline_file} generated for: {service_names}")
    rprint("\n")
