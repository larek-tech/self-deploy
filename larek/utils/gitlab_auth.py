"""Утилиты аутентификации GitLab."""

import os
from pathlib import Path

import gitlab
from rich.console import Console
from urllib.parse import urlparse
from larek.config import GITLAB_URL


console = Console()


TOKEN_FILE = Path.home() / ".larek" / "gitlab_token"
URL_FILE = Path.home() / ".larek" / "gitlab_url"


def get_gitlab_url() -> str:
    url = os.getenv("GITLAB_URL")
    if url:
        return _ensure_scheme(url)

    url_file = Path(os.getenv("GITLAB_URL_FILE", URL_FILE))
    if url_file.exists():
        url = url_file.read_text(encoding="utf-8").strip()
        if url:
            return _ensure_scheme(url)

    return _ensure_scheme(GITLAB_URL)


def _ensure_scheme(url: str) -> str:

    if not urlparse(url).scheme:
        return f"http://{url}"
    return url


def get_access_token() -> str:
    token = os.getenv("GITLAB_ACCESS_TOKEN")
    if token:
        return token

    token_file = Path(os.getenv("GITLAB_TOKEN_FILE", TOKEN_FILE))
    if token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
        if token:
            return token

    raise RuntimeError("Токен доступа GitLab не найден.\n")


def get_authenticated_client() -> gitlab.Gitlab:
    gitlab_url = get_gitlab_url()
    token = get_access_token()

    gl = gitlab.Gitlab(url=gitlab_url, private_token=token)

    try:
        gl.auth()
        console.print("[green]✓[/green] Подключено к GitLab ✅")
    except Exception as e:
        raise RuntimeError("Не удалось аутентифицироваться в GitLab") from e

    return gl
