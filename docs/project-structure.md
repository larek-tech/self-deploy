# Структура проекта

Ниже — обзор ключевых директорий и файлов в репозитории `self-deploy`.

## Верхний уровень

- `mkdocs.yml` — конфигурация MkDocs для документации.
- `readme.md` — общая документация проекта.
- `setup.sh` — скрипт для локальной подготовки инфраструктуры.
- `docker-compose.yaml` — docker-compose для локальной инфраструктуры (GitLab, Nexus и пр.).

## Важные директории

- `larek/` — основной пакет CLI-приложения:
  - `larek/main.py` — точка входа (Typer app).
  - `larek/commands/` — реализации команд CLI (`init.py`, `docker.py`, `gitlab.py`, `login.py` и т.д.).
  - `larek/analyzer/` — анализаторы кода для разных языков (go, java, kotlin, javascript, python).
  - `larek/composer/` — генерация Dockerfile (шаблоны и builder).
  - `larek/pipeliner/` — генерация GitLab CI пайплайнов.
  - `larek/models/` — Pydantic модели (схемы данных, например `repo.py`).
  - `larek/utils/` — вспомогательные утилиты (git_ops, gitlab_auth, docker helpers).

- `gitlab-ansible-deployment/` — Ansible playbooks и конфигурация для развёртывания GitLab и связанных сервисов:
  - `gitlab-playbook.yml` — основной playbook для установки.
  - `inventory.ini` / `inventory-prod.ini` — примеры инвентарей.
  - `group_vars/` и `host_vars/` — переменные и настройки для инвентарей.

- `sample/` — примеры проектов (go, java, javascript, python) для тестирования анализаторов и генерации.

- `data/` — вспомогательные CSV, примеры данных и макеты (включая `Makefile` и `pyproject.toml`).

- `results/` — результаты анализа/сборки, которые сохраняет инструмент при выполнении (разбитые по языкам).

- `tests/` — unit-тесты для библиотеки (например, `test_builder.py`, `test_pipeliner.py`).

## Где искать ключевые вещи

- Генерация Dockerfile: `larek/composer/builder.py` и шаблоны в `larek/composer/templates/`.
- Генерация gitlab-ci: `larek/pipeliner/builder.py` и `larek/pipeliner/templates/`.
- Модель данных репозитория: `larek/models/repo.py` — используется для сериализации/парсинга `build.yaml`.
- Автоматизация развёртывания GitLab: `gitlab-ansible-deployment/`.


