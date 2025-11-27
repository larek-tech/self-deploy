"""Команда авторизации."""

import os
from pathlib import Path
import typer
import gitlab
from rich.console import Console
from rich.prompt import Prompt
from larek.utils.gitlab_auth import get_gitlab_url, TOKEN_FILE, URL_FILE

app = typer.Typer(help="Авторизация в GitLab")
console = Console()


@app.callback(invoke_without_command=True)
def login(
    token: str = typer.Option(
        None,
        "--token",
        "-t",
        help="GitLab Personal Access Token",
    ),
    url: str = typer.Option(
        None,
        "--url",
        "-u",
        help="GitLab URL",
    ),
):
    """
    Авторизация в GitLab с помощью Personal Access Token.
    Токен будет сохранён локально для использования в других командах.
    """
    console.print("[bold blue]Авторизация в Larek CLI[/bold blue]")

    # Запрос URL
    if not url:
        default_url = get_gitlab_url()
        url = Prompt.ask("GitLab URL", default=default_url)

    if not token:
        console.print("Пожалуйста, введите ваш GitLab Personal Access Token.")
        console.print(
            f"Вы можете создать его здесь: {url}/-/user_settings/personal_access_tokens"
        )
        console.print("Требуемые права: api, read_repository, write_repository")
        token = Prompt.ask("Access Token", password=True)

    if not token:
        console.print("[red]❗️ Токен не может быть пустым.[/red]")
        raise typer.Exit(code=1)

    # Проверка токена
    console.print(f"[yellow]🔎 Подключение к {url}...[/yellow]")

    try:
        gl = gitlab.Gitlab(url=url, private_token=token)
        gl.auth()
        console.print(f"[green]✅ Успешная авторизация[/green]")
    except Exception as e:
        console.print(f"[red]❌ Ошибка авторизации: {e}[/red]")
        console.print(
            "[yellow]Проверьте правильность токена и доступность GitLab.[/yellow]"
        )
        raise typer.Exit(code=1)

    token_path = Path(os.getenv("GITLAB_TOKEN_FILE", TOKEN_FILE))
    try:
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(token, encoding="utf-8")
        token_path.chmod(0o600)
        console.print(f"[green]🔒 Токен успешно сохранён в {token_path}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Ошибка при сохранении токена: {e}[/red]")
        raise typer.Exit(code=1)

    url_path = Path(os.getenv("GITLAB_URL_FILE", URL_FILE))
    try:
        url_path.parent.mkdir(parents=True, exist_ok=True)
        url_path.write_text(url, encoding="utf-8")
        console.print(f"[green]✅ URL успешно сохранён в {url_path}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Ошибка при сохранении URL: {e}[/red]")
        raise typer.Exit(code=1)
