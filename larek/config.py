"""Конфигурация приложения."""

from pathlib import Path

# Пути
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

# GitLab
GITLAB_URL = "http://localhost"
GITLAB_ADMIN_USER = "root"
GITLAB_ADMIN_PASSWORD = "SuperSecurePassword123"

# Nexus
NEXUS_URL = "http://localhost:8081"

# Docker
GITLAB_CONTAINER = "gitlab_server"
NEXUS_CONTAINER = "nexus"
RUNNER_CONTAINER = "gitlab_runner"
