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
        self.dockerfile: str = ""
        self.entrypoint: str = ""
        self.linters: list[models.Linter] = []

    def analyze(self, root: Path) -> tp.Optional[models.Service]:
        if not root.is_dir():
            return None

        files = self._scan(root)
        if not self.is_go_service:
            return None

        return models.Service(
            path=root,
            name=root.name,
            lang=models.Language(name="go", version=self.go_version),
            dependencies=models.Dependencies(
                packet_manager="go mod",
                libs=self.libs,
            ),
            configs=self.configs,
            dockerfile=self.dockerfile,
            entrypoint=self.entrypoint,
            tests="go test -coverpkg=./... -coverprofile=coverage.out ./...",
            linters=self.linters,
        )

    def _scan(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for f in root.iterdir():
            if f.is_file() and self._file_filter(f):
                files.append(f)
                if (
                    not self.is_go_service or self.go_version == ""
                ) and self._is_go_service(f):
                    self.is_go_service = True
            elif f.is_dir():
                nested_files = self._scan(f)
                files.extend(nested_files)

        return files

    def _file_filter(self, file: Path) -> bool:
        match file.name:
            case "vendor/" | ".gitignore" | ".git":
                return False
        return True

    def _is_go_service(self, file: Path) -> bool:
        match file.name:
            case "go.mod":
                self.go_version, self.libs = self._parse_go_mod(file)
                if self.go_version == "":
                    raise ValueError("inconsistent go.mod")

            case "main.go":
                return True
        return False

    def _parse_go_mod(self, go_mod_file: Path) -> tuple[str, list[models.Lib]]:
        go_version_pattern = re.compile(r"\d.\d+.\d+")
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
