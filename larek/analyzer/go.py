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
        self.dockerfiles: list[str] = []
        self.entrypoints: list[str] = []
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
            dockerfiles=self.dockerfiles,
            entrypoints=self.entrypoints,
            tests="go test -coverpkg=./... -coverprofile=coverage.out ./...",
            linters=self.linters,
        )

    def _scan(self, root: Path):
        for f in root.iterdir():
            if f.is_file() and self._file_filter(f):
                self._parse_file(f)
            elif f.is_dir():
                self._scan(f)

    def _file_filter(self, file: Path) -> bool:
        match file.name:
            case "vendor/" | ".gitignore" | ".git":
                return False
        return True

    def _parse_file(self, file: Path):
        match file.name:
            case "main.go":
                self.entrypoints.append(str(file))

            case "Dockerfile":
                self.dockerfiles.append(str(file))

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
                    or ".env" in file.name
                ) and ".go" not in file.suffix:
                    self.configs.append(
                        models.Config(
                            name=file.name,
                            path=str(file),
                        )
                    )

                elif "Dockerfile" in file.name:
                    self.dockerfiles.append(str(file))

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
