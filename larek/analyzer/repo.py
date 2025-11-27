import typing as tp
import os
from pathlib import Path
from larek.analyzer import BaseAnalyzer
from larek import models


class RepoAnalyzer:
    """Анализатор репозитория, который использует разные анализаторы языков."""

    def __init__(self) -> None:
        self.analyzers: list[tp.Callable[[], BaseAnalyzer]] = []

    def register_analyzer(self, analyzer: tp.Callable[[], BaseAnalyzer]) -> None:
        """Регистрация нового анализатора языка."""
        self.analyzers.append(analyzer)

    def analyze(self, root: Path) -> models.RepoSchema:
        """Анализ репозитория и сбор информации о сервисах."""

        deployment = self._find_deployment_info(root, self._find_environment_vars(root))

        dirs = [d for d in root.iterdir() if d.is_dir() and self._file_filter(d)]
        services: list[models.Service] = []

        is_monorepo = False
        for get_analyzer in self.analyzers:
            analyzer = get_analyzer()
            service = analyzer.analyze(root)
            if service is not None:
                services.append(service)
                break
        else:
            for d in dirs:
                for get_analyzer in self.analyzers:
                    analyzer = get_analyzer()
                    service = analyzer.analyze(d)
                    if service is not None:
                        services.append(service)
                        break
            if len(services) > 1:
                is_monorepo = True

        return models.RepoSchema(
            is_monorepo=is_monorepo,
            services=services,
            deployment=deployment,
        )

    def _file_filter(self, file: Path) -> bool:
        match file.name:
            case (
                ".gitignore"
                | ".git"
                | "vendor/"
                | "node_modules/"
                | "__pycache__/"
                | ".idea/"
                | ".vscode/"
                | ".venv/"
            ):
                return False
        return True

    def _find_deployment_info(
        self, root: Path, env: list[models.Environment]
    ) -> tp.Optional[models.Deployment]:
        if (dockerfile := root / "Dockerfile").exists():
            return models.Deployment(
                type="dockerfile",
                path=str(dockerfile),
                environment=env,
            )
        elif (compose := root / "docker-compose.yml").exists() or (
            compose := root / "docker-compose.yaml"
        ).exists():
            return models.Deployment(
                type="compose",
                path=str(compose),
                environment=env,
            )
        else:
            for d in root.iterdir():
                if d.is_dir():
                    for chart in d.glob("Chart.y*ml"):
                        return models.Deployment(
                            type="helm",
                            path=str(chart),
                            environment=env,
                        )
        return None

    def _find_environment_vars(self, root: Path) -> list[models.Environment]:
        env_vars: list[models.Environment] = []
        env_files = root.glob("*.env")
        for env_file in env_files:
            environment = models.Environment(
                name=env_file.name,
                path=str(env_file),
            )
            env_vars.append(environment)
        for d in root.iterdir():
            if d.is_dir():
                for values_file in d.glob("values.y*ml"):
                    environment = models.Environment(
                        name=values_file.name,
                        path=str(values_file),
                    )
                    env_vars.append(environment)
        return env_vars
