import json
import typing as tp
from pathlib import Path
from larek.analyzer import BaseAnalyzer
from larek import models


class JavaScriptAnalyzer(BaseAnalyzer):
    def __init__(self) -> None:
        self.is_js_service: bool = False

        self.js_version: str = ""
        self.libs: list[models.Lib] = []
        self.configs: list[models.Config] = []
        self.dockerfiles: list[str] = []
        self.entrypoints: list[str] = []
        self.linters: list[models.Linter] = []
        self.compose_file: str = ""
        self.environment: list[models.Environment] = []

    def analyze(self, root: Path) -> tp.Optional[models.Service]:
        if not root.is_dir():
            return None

        package_json_file = root / "package.json"
        if not package_json_file.exists():
            return None

        self.js_version, self.libs, scripts = self._parse_package_json(
            package_json_file
        )
        self.is_js_service = True

        self._scan(root)

        packet_manager = self._detect_package_manager(root)
        lang_name = "typescript" if self._is_typescript(root) else "javascript"
        test_command = self._get_test_command(scripts, packet_manager)

        return models.Service(
            path=root,
            name=root.name,
            lang=models.Language(name=lang_name, version=self.js_version),
            dependencies=models.Dependencies(
                packet_manager=packet_manager,
                libs=self.libs,
            ),
            configs=self.configs,
            docker=models.Docker(
                dockerfiles=self.dockerfiles,
                compose=self.compose_file if self.compose_file else None,
                environment=self.environment,
            ),
            entrypoints=self.entrypoints,
            tests=test_command,
            linters=self.linters,
        )

    def _find_repo_root(self, path: Path) -> tp.Optional[Path]:
        current = path
        while current.parent != current:
            if (current / ".git").exists():
                return current
            current = current.parent
        return None
    
    def _detect_package_manager(self, root: Path) -> str:
        if (root / "bun.lockb").exists():
            return "bun"
        if (root / "yarn.lock").exists():
            return "yarn"
        if (root / "pnpm-lock.yaml").exists():
            return "pnpm"
        
        repo_root = self._find_repo_root(root)
        if repo_root:
            if (repo_root / "bun.lockb").exists():
                return "bun"
            if (repo_root / "yarn.lock").exists():
                return "yarn"
            if (repo_root / "pnpm-lock.yaml").exists():
                return "pnpm"
        
        return "npm"

    def _is_typescript(self, root: Path) -> bool:
        if (root / "tsconfig.json").exists():
            return True

        for lib in self.libs:
            if lib.name == "typescript":
                return True

        for ep in self.entrypoints:
            if ep.endswith(".ts"):
                return True

        return False

    def _get_test_command(self, scripts: dict[str, str], packet_manager: str) -> str:
        if "test" in scripts:
            return f"{packet_manager} test" if packet_manager != "npm" else "npm test"
        return "echo 'No tests found'"

    def _scan(self, root: Path):
        for f in root.iterdir():
            if f.is_file() and self._file_filter(f):
                self._parse_file(f)
            elif f.is_dir() and self._dir_filter(f):
                self._scan(f)

    def _dir_filter(self, dir_path: Path) -> bool:
        match dir_path.name:
            case (
                "node_modules"
                | ".git"
                | "dist"
                | "build"
                | "coverage"
                | ".idea"
                | ".vscode"
            ):
                return False
        return True

    def _file_filter(self, file: Path) -> bool:
        match file.name:
            case "package-lock.json" | "yarn.lock" | "pnpm-lock.yaml" | ".DS_Store":
                return False
        return True

    def _parse_file(self, file: Path):
        match file.name:
            case (
                "index.js"
                | "main.js"
                | "server.js"
                | "app.js"
                | "index.ts"
                | "main.ts"
                | "server.ts"
                | "app.ts"
            ):
                self.entrypoints.append(str(file))

            case "Dockerfile":
                self.dockerfiles.append(str(file))

            case "docker-compose.yml" | "docker-compose.yaml":
                self.compose_file = str(file)

            case "tsconfig.json":
                self.configs.append(models.Config(name=file.name, path=str(file)))

            case (
                ".eslintrc"
                | ".eslintrc.js"
                | ".eslintrc.json"
                | ".eslintrc.yaml"
                | ".eslintrc.yml"
                | "eslint.config.js"
            ):
                self.linters.append(
                    models.Linter(
                        name="eslint",
                        config=str(file),
                    )
                )

            case (
                ".prettierrc"
                | ".prettierrc.js"
                | ".prettierrc.json"
                | ".prettierrc.yaml"
                | ".prettierrc.yml"
                | "prettier.config.js"
            ):
                self.linters.append(
                    models.Linter(
                        name="prettier",
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
                if ".env" in file.name:
                    self.environment.append(
                        models.Environment(name=file.name, path=str(file))
                    )
                elif (
                    "config" in file.name
                    or "cfg" in file.name
                    or "settings" in file.name
                ):
                    self.configs.append(models.Config(name=file.name, path=str(file)))

                if "Dockerfile" in file.name and file.name != "Dockerfile":
                    self.dockerfiles.append(str(file))

                if "compose" in file.name and (
                    file.suffix == ".yml" or file.suffix == ".yaml"
                ):
                    self.compose_file = str(file)

    def _parse_package_json(
        self, package_json_file: Path
    ) -> tuple[str, list[models.Lib], dict[str, str]]:
        version = ""
        libs: list[models.Lib] = []
        scripts: dict[str, str] = {}

        try:
            with package_json_file.open() as f:
                data = json.load(f)

                engines = data.get("engines", {})
                if isinstance(engines, dict):
                    version = engines.get("node", "")

                scripts = data.get("scripts", {})

                for dep_type in [
                    "dependencies",
                    "devDependencies",
                    "peerDependencies",
                    "optionalDependencies",
                ]:
                    deps = data.get(dep_type, {})
                    if isinstance(deps, dict):
                        for name, ver in deps.items():
                            libs.append(models.Lib(name=name, version=str(ver)))

        except (json.JSONDecodeError, OSError):
            pass

        return version, libs, scripts
