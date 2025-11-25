"""Шаблон для Python проектов."""

from pathlib import Path

from larek.templates.base import LanguageTemplate


class PythonTemplate(LanguageTemplate):
    """Шаблон для Python проектов с Poetry."""

    @property
    def name(self) -> str:
        return "python"

    @property
    def extensions(self) -> list[str]:
        return [".py", ".pyi"]

    @property
    def package_managers(self) -> list[str]:
        return ["poetry", "pip", "pipenv", "uv"]

    @property
    def default_linters(self) -> list[str]:
        return ["ruff", "mypy"]

    def create_structure(self, project_path: Path, project_name: str) -> None:
        """Создать структуру Python проекта."""
        # Основные директории
        dirs = [
            project_path / "src" / project_name,
            project_path / "tests",
            project_path / "docs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # __init__.py файлы
        (project_path / "src" / project_name / "__init__.py").write_text(
            f'"""Пакет {project_name}."""\n\n__version__ = "0.1.0"\n'
        )
        (project_path / "tests" / "__init__.py").write_text("")

        # pyproject.toml
        pyproject = f"""[tool.poetry]
name = "{project_name}"
version = "0.1.0"
description = ""
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{{include = "{project_name}", from = "src"}}]

[tool.poetry.dependencies]
python = "^3.12"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
ruff = "^0.8"
mypy = "^1.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.12"
strict = true
"""
        (project_path / "pyproject.toml").write_text(pyproject)

        # README.md
        (project_path / "README.md").write_text(f"# {project_name}\n\n")

        # .gitignore
        gitignore = """__pycache__/
*.py[cod]
*$py.class
.Python
env/
venv/
.env
.venv
dist/
build/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
"""
        (project_path / ".gitignore").write_text(gitignore)

    def generate_dockerfile(self, version: str | None = None) -> str:
        """Сгенерировать Dockerfile для Python."""
        py_version = version or "3.12"
        return f"""FROM python:{py_version}-slim

WORKDIR /app

RUN pip install poetry && \\
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-dev --no-interaction --no-ansi

COPY src/ ./src/

CMD ["python", "-m", "src.main"]
"""

    def get_test_command(self) -> str:
        return "poetry run pytest"
