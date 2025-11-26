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

    console.print("[yellow]Executing:[/yellow] docker compose down")
    subprocess.run(["docker", "compose", "down"], check=True)
    console.print("[green]Docker compose down executed successfully[/green]")
