import os
import shutil
import subprocess
from rich.console import Console

console = Console()


def clear():
    """
    Очищает локальное окружение
    """

    folders_to_clear = ["gitlab", "gitlab-runner"]

    for folder in folders_to_clear:
        folder_path = os.path.join(os.getcwd(), folder)
        if os.path.exists(folder_path):
            console.print(f"[yellow]Clearing contents of folder:[/yellow] {folder}")
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            console.print(f"[green]Successfully cleared folder:[/green] {folder}")
        else:
            console.print(f"[blue]Folder not found, skipping:[/blue] {folder}")
    console.print("[yellow]Executing:[/yellow] docker compose down -v --remove-orphans")
    try:
        subprocess.run(
            ["docker", "compose", "down", "-v", "--remove-orphans"], check=True
        )
        console.print("[green]Docker compose down executed successfully[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]docker compose down failed:[/red] {e}")

    volumes = [
        "gitlab_config",
        "gitlab_logs",
        "gitlab_data",
        "nexus_data",
        "gitlab_runner_config",
    ]
    for vol in volumes:
        console.print(f"[yellow]Removing Docker volume:[/yellow] {vol}")
        try:
            subprocess.run(
                ["docker", "volume", "rm", "-f", vol],
                capture_output=True,
                text=True,
                check=True,
            )
            console.print(f"[green]Removed volume:[/green] {vol}")
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or e.stdout or str(e)).strip()
            console.print(
                f"[blue]Volume not found or could not remove:[/blue] {vol} ({stderr})"
            )
        except OSError as e:
            console.print(f"[red]Error removing volume {vol}:[/red] {e}")
