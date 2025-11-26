import typing as tp
from pathlib import Path
from larek.analyzer import BaseAnalyzer
from larek import models
import re


class GoAnalyzer(BaseAnalyzer):
    def __init__(self) -> None:
        self.is_go_service: bool = False

        self.go_version: str = ""
        self.libs: list[models.Lib] = []
        self.configs: list[models.Config] = []
        self.entrypoints: list[str] = []
        self.compose_file: str = ""
        self.dockerfiles: list[str] = []
        self.environment: list[models.Environment] = []
        self.linters: list[models.Linter] = []

    def analyze(self, root: Path) -> tp.Optional[models.Service]:
        if not root.is_dir():
            return None

        go_mod_file = root / "go.mod"
        if not go_mod_file.exists():
            return None

        self.go_version, self.libs = self._parse_go_mod(go_mod_file)
        if self.go_version == "":
            raise ValueError("inconsistent go.mod")
        self.is_go_service = True

        self._scan(root)

        return models.Service(
            path=root,
            name=root.name,
            lang=models.Language(name="go", version=self.go_version),
            dependencies=models.Dependencies(
                packet_manager="go mod",
                libs=self.libs,
            ),
            configs=self.configs,
            docker=models.Docker(
                dockerfiles=self.dockerfiles,
                compose=self.compose_file if self.compose_file else None,
                environment=self.environment,
            ),
            entrypoints=self.entrypoints,
            tests="go test -coverpkg=./... -coverprofile=coverage.out ./...",
            linters=self._linters(self.linters, root),
        )

    def _scan(self, root: Path):
        for f in root.glob("*"):
            if f.is_file() and self._file_filter(f):
                self._parse_file(f)
            elif f.is_dir() and self._dir_filter(f):
                self._scan(f)

    def _file_filter(self, file: Path) -> bool:
        match file.name:
            case ".gitignore":
                return False
        return True

    def _dir_filter(self, dir: Path) -> bool:
        match dir.name:
            case (
                "vendor"
                | "node_modules"
                | "__pycache__"
                | ".idea"
                | ".git"
                | ".vscode"
                | "mock"
                | "mocks"
            ):
                return False
        return True

    def _parse_file(self, file: Path):
        match file.name:
            case "main.go":
                self.entrypoints.append(str(file))

            case "Dockerfile":
                self.dockerfiles.append(str(file))

            case "docker-compose.yml" | "docker-compose.yaml":
                self.compose_file = str(file)

            case ".golangci.yml" | ".golangci.yaml":
                self.linters.append(
                    models.Linter(
                        name="golangci-lint",
                        config=str(file),
                    )
                )

            case ".sonar-project.properties":
                self.linters.append(
                    models.Linter(
                        name="sonar",
                        config=str(file),
                    )
                )

            case _:
                if (
                    "config" in file.name
                    or "cfg" in file.name
                    or "settings" in file.name
                    or "conf" in file.name
                ) and ".go" not in file.suffix:
                    self.configs.append(
                        models.Config(
                            name=file.name,
                            path=str(file),
                        )
                    )

                if "Dockerfile" in file.name:
                    self.dockerfiles.append(str(file))

                if "compose" in file.name and (
                    file.suffix == ".yml" or file.suffix == ".yaml"
                ):
                    self.compose_file = str(file)

                if ".env" in file.name:
                    self.environment.append(
                        models.Environment(
                            name=file.name,
                            path=str(file),
                        )
                    )

    def _parse_go_mod(self, go_mod_file: Path) -> tuple[str, list[models.Lib]]:
        go_version_pattern = re.compile(r"\d.\d*")
        version = ""
        libs: list[models.Lib] = []
        with go_mod_file.open() as f:
            parsing_libs = False
            for line in f.readlines():
                if line.startswith("go "):
                    version = go_version_pattern.findall(line)[0]
                    continue

                if line.startswith("require ("):
                    parsing_libs = True
                    continue

                if parsing_libs and line.startswith(")"):
                    parsing_libs = False
                    continue

                if parsing_libs:
                    lib_data = line.split()
                    libs.append(
                        models.Lib(
                            name=lib_data[0],
                            version=lib_data[1],
                        )
                    )

        return version, libs

    def _linters(
        self, found_linters: list[models.Linter], root: Path
    ) -> list[models.Linter]:
        if len(found_linters) > 0:
            return found_linters

        linters: list[models.Linter] = []
        golangci_configs = [cfg for cfg in root.glob(".golangci.y*ml")]
        if len(golangci_configs) > 0:
            for config in golangci_configs:
                linters.append(
                    models.Linter(
                        name="golangci-lint",
                        config=str(config),
                    )
                )
        else:
            linters.append(
                models.Linter(
                    name="golangci-lint",
                    config="default",
                )
            )

        sonar_config = root / ".sonar-project.properties"
        if sonar_config.exists():
            linters.append(
                models.Linter(
                    name="sonar",
                    config=str(sonar_config),
                )
            )

        return linters
