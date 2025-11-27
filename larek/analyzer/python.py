import typing as tp
from pathlib import Path
from larek.analyzer import BaseAnalyzer
from larek import models
import re
from typing import Tuple
from rich.console import Console

console = Console()


class PythonAnalyze(BaseAnalyzer):
    def __init__(self) -> None:
        super().__init__()
        self.configs: list[models.Config] = []
        self.environment: list[models.Environment] = []
        self.entrypoints: list[str] = []
        self.dockerfiles: list[str] = []
        self.compose_file: str = ""
        self.root_path: tp.Optional[Path] = None

    def analyze(self, root: Path) -> tp.Optional[models.Service]:
        if not root.is_dir():
            return None

        # Check if it's a Python project
        python_indicators = [
            "requirements.txt",
            "requirements-dev.txt",
            "setup.py",
            "setup.cfg",
            "pyproject.toml",
            "Pipfile",
            "poetry.lock",
        ]
        has_python_files = any(
            (root / indicator).exists() for indicator in python_indicators
        )
        # has_py_files = bool(list(root.glob("**/*.py"))[:1])

        if not has_python_files:
            return None

        # Reset instance variables
        self.configs = []
        self.environment = []
        self.entrypoints = []
        self.dockerfiles = []
        self.compose_file = ""
        self.root_path = root

        # Scan recursively like Go/JS analyzers
        self._scan(root)

        packet_managers = self.get_packet_managers(root)
        dec_libs = self.get_libs(root)
        py_version = self.detect_python_version_by_syntax(root)
        # Normalize version for use in Docker tags and other contexts
        py_version = self._normalize_python_version(py_version)

        return models.Service(
            android=None,
            path=root,
            name=root.name,
            lang=models.Language(name="python", version=py_version),
            dependencies=models.Dependencies(
                packet_manager=packet_managers if packet_managers else "pip",
                libs=dec_libs,
            ),
            configs=self.configs,
            docker=models.Docker(
                dockerfiles=self.dockerfiles,
                compose=self.compose_file if self.compose_file else None,
                environment=self.environment,
            ),
            entrypoints=self.entrypoints,
            tests=self.detected_tests(root),
            linters=self.get_linters(root),
        )

    def _scan(self, root: Path):
        """Recursively scan directory for files, similar to Go/JS analyzers."""
        for f in root.iterdir():
            if f.is_file() and self._file_filter(f):
                self._parse_file(f)
            elif f.is_dir() and self._dir_filter(f):
                self._scan(f)

    def _file_filter(self, file: Path) -> bool:
        """Filter out files that shouldn't be processed."""
        match file.name:
            case ".gitignore" | ".DS_Store" | "__pycache__" | ".pyc" | "*.pyc":
                return False
        return True

    def _dir_filter(self, dir_path: Path) -> bool:
        """Filter out directories that shouldn't be scanned."""
        match dir_path.name:
            case (
                "vendor"
                | "node_modules"
                | "__pycache__"
                | ".git"
                | ".idea"
                | ".vscode"
                | ".pytest_cache"
                | ".mypy_cache"
                | ".tox"
                | "dist"
                | "build"
                | "*.egg-info"
                | ".eggs"
            ):
                return False
        return True

    def _parse_file(self, file: Path):
        """Parse individual files to extract metadata."""
        # Check for entrypoints - only root-level files or files in specific directories
        if file.suffix == ".py" and self._is_potential_entrypoint(file):
            if self._is_entrypoint(file):
                self.entrypoints.append(str(file))

        # Docker files
        if "Dockerfile" in file.name:
            self.dockerfiles.append(str(file))

        # Docker compose
        if "compose" in file.name and (file.suffix == ".yml" or file.suffix == ".yaml"):
            self.compose_file = str(file)

        # Environment files
        if ".env" in file.name:
            self.environment.append(models.Environment(name=file.name, path=str(file)))

        # Config files
        if self._is_config_file(file):
            self.configs.append(models.Config(name=file.name, path=str(file)))

    def _is_potential_entrypoint(self, file: Path) -> bool:
        """Check if a file could be an entrypoint based on location and name."""
        if not self.root_path:
            return False

        # Common entrypoint filenames (check anywhere, but still respect excluded dirs)
        common_entrypoints = [
            "main.py",
            "app.py",
            "run.py",
            "manage.py",
            "wsgi.py",
            "asgi.py",
            "application.py",
            "server.py",
            "cli.py",
        ]

        # Check if file is at root level
        is_root_level = file.parent == self.root_path

        # Get relative path from root
        try:
            rel_path = file.relative_to(self.root_path)
            parent_name = (
                rel_path.parent.name.lower() if rel_path.parent != Path(".") else ""
            )
        except ValueError:
            # File is not under root, skip it
            return False

        # Exclude files in common module/plugin directories
        excluded_dirs = {
            "plugins",
            "plugin",
            "lib",
            "libs",
            "utils",
            "utilities",
            "helpers",
            "common",
            "core",
            "src",
            "tests",
            "test",
            "__pycache__",
            "vendor",
            "third_party",
            "modules",
            "module",
        }

        if parent_name in excluded_dirs:
            return False

        # If it's a common entrypoint name, allow it (even in subdirs like scripts/)
        if file.name in common_entrypoints:
            return True

        # Root-level files are potential entrypoints
        if is_root_level:
            return True

        # Include files in scripts/bin directories
        if parent_name in {"scripts", "script", "bin", "entrypoints"}:
            return True

        return False

    def _is_entrypoint(self, file: Path) -> bool:
        """Check if a Python file is an entrypoint."""
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
            # Primary check: has __main__ guard
            if "if __name__ == '__main__':" in content:
                return True
            # Secondary checks for framework-specific patterns
            if any(
                keyword in content
                for keyword in [
                    "app.run(",
                    "app.run()",
                    "manage.run(",
                    "application.run(",
                    'if __name__ == "__main__":',
                ]
            ):
                return True
        except Exception:
            pass
        return False

    def _is_config_file(self, file: Path) -> bool:
        """Check if a file is a configuration file."""
        config_patterns = [
            ".cfg",
            ".ini",
            ".yml",
            ".yaml",
            "requirements.txt",
            "setup.py",
            "setup.cfg",
            "pyproject.toml",
            "Pipfile",
            "poetry.lock",
            "pdm.lock",
            "requirements.lock",
            "uv.lock",
            "tox.ini",
            "pytest.ini",
            ".flake8",
            ".pylintrc",
            "pylintrc",
            "mypy.ini",
            ".mypy.ini",
            ".bandit",
            "bandit.yaml",
            ".pydocstyle",
            "pydocstyle.ini",
            ".pre-commit-config.yaml",
            ".gitlab-ci.yml",
            ".github/workflows",
        ]
        return any(
            file.name.endswith(pattern) or pattern in file.name
            for pattern in config_patterns
        ) or (
            file.parent.name == "config"
            and file.suffix in [".py", ".yaml", ".yml", ".json"]
        )

    def get_packet_managers(self, root: Path) -> tp.Optional[str]:
        package_managers = [
            ("poetry", self._is_poetry_project),
            ("pipenv", self._is_pipenv_project),
            ("pdm", self._is_pdm_project),
            ("rye", self._is_rye_project),
            ("hatch", self._is_hatch_project),
            ("uv", self._is_uv_project),
            ("setuptools", self._is_setuptools_project),
            ("pip", self._is_requirements_project),
        ]

        for name, validator in package_managers:
            if validator(root):
                return name
        return None

    def _is_poetry_project(self, root: Path) -> bool:
        if (root / "poetry.lock").exists():
            return True
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                return "[tool.poetry]" in pyproject.read_text()
            except Exception:
                return False
        return False

    def _is_pipenv_project(self, root: Path) -> bool:
        return (root / "Pipfile").exists()

    def _is_pdm_project(self, root: Path) -> bool:
        if (root / "pdm.lock").exists() or (root / "pdm.toml").exists():
            return True

        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                return "[tool.pdm]" in pyproject.read_text()
            except Exception:
                return False
        return False

    def _is_rye_project(self, root: Path) -> bool:
        return (root / "requirements.lock").exists() or (root / "rye.toml").exists()

    def _is_hatch_project(self, root: Path) -> bool:
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                return "[tool.hatch]" in pyproject.read_text()
            except Exception:
                return False
        return False

    def _is_uv_project(self, root: Path) -> bool:
        return (root / "uv.lock").exists()

    def _is_setuptools_project(self, root: Path) -> bool:
        return (root / "setup.py").exists() or (root / "setup.cfg").exists()

    def _is_requirements_project(self, root: Path) -> bool:
        requirements_files = list(root.glob("requirements*.txt"))
        return bool(requirements_files and not self._has_modern_package_manager(root))

    def _has_modern_package_manager(self, root: Path) -> bool:
        modern_indicators = [
            "pyproject.toml",
            "poetry.lock",
            "Pipfile",
            "pdm.lock",
            "requirements.lock",
            "uv.lock",
        ]
        return any((root / indicator).exists() for indicator in modern_indicators)

    def get_libs(self, root) -> list[models.Lib]:
        """Parse dependencies from requirements.txt and other dependency files."""
        libraries = []
        seen = set()

        try:
            # Parse requirements.txt files
            req_files = list(root.glob("**/requirements*.txt"))
            for file in req_files:
                try:
                    with open(file, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if (
                                line
                                and not line.startswith("#")
                                and not line.startswith("-r")
                                and not line.startswith("--")
                                and not line.startswith("-f")
                                and not line.startswith("git+")
                                and not line.startswith("http")
                            ):
                                lib = self._parse_requirement_line(line)
                                if lib and lib.name not in seen:
                                    libraries.append(lib)
                                    seen.add(lib.name)
                except Exception as e:
                    console.print(f"[red]Ошибка при чтении {file}: {e}[/red]")
                    continue

            # Parse pyproject.toml for dependencies
            pyproject = root / "pyproject.toml"
            if pyproject.exists():
                try:
                    content = pyproject.read_text()
                    # Simple regex to find dependencies (can be improved with toml parser)
                    # Look for [tool.poetry.dependencies] or [project.dependencies]
                    deps_section = re.search(
                        r"\[(?:tool\.poetry|project)\.dependencies\](.*?)(?=\[|$)",
                        content,
                        re.DOTALL,
                    )
                    if deps_section:
                        for line in deps_section.group(1).split("\n"):
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                lib = self._parse_requirement_line(
                                    line.split("=")[0].strip()
                                    + "="
                                    + line.split("=")[1].strip().strip('"').strip("'")
                                )
                                if lib and lib.name not in seen:
                                    libraries.append(lib)
                                    seen.add(lib.name)
                except Exception:
                    pass

            # Parse setup.py dependencies (basic extraction)
            setup_py = root / "setup.py"
            if setup_py.exists():
                try:
                    content = setup_py.read_text()
                    # Look for install_requires
                    install_requires = re.search(
                        r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL
                    )
                    if install_requires:
                        for line in install_requires.group(1).split("\n"):
                            line = line.strip().strip(",").strip('"').strip("'")
                            if line:
                                lib = self._parse_requirement_line(line)
                                if lib and lib.name not in seen:
                                    libraries.append(lib)
                                    seen.add(lib.name)
                except Exception:
                    pass

        except Exception as e:
            console.print(f"[red]Ошибка при анализе зависимостей: {e}[/red]")

        return libraries

    def _parse_requirement_line(self, line: str) -> tp.Optional[models.Lib]:
        """Parse a single requirement line into a Lib object."""
        line = line.strip().strip('"').strip("'")
        if not line or line.startswith("#"):
            return None

        # Handle different formats: package==version, package>=version, package~=version, etc.
        # Remove comments
        if "#" in line:
            line = line.split("#")[0].strip()

        # Parse version specifiers
        version = None
        name = line

        # Match patterns like: package==1.0.0, package>=1.0.0, package~=1.0.0, package<=1.0.0
        version_patterns = [r"==", r">=", r"<=", r"~=", r"!=", r"<", r">"]
        for pattern in version_patterns:
            if pattern in name:
                parts = name.split(pattern, 1)
                name = parts[0].strip()
                version = parts[1].strip() if len(parts) > 1 else None
                break

        # If no version specifier, check for version in parentheses or brackets
        if version is None:
            # Handle: package (1.0.0) or package[extra]
            match = re.match(r"^([a-zA-Z0-9_-]+(?:\[.*?\])?)\s*(?:\(([^)]+)\))?", line)
            if match:
                name = match.group(1).split("[")[0]  # Remove extras
                version = match.group(2) if match.group(2) else None

        # Clean up name (remove extras, whitespace)
        name = name.split("[")[0].strip()

        if not name:
            return None

        return models.Lib(name=name, version=version)

    def detected_tests(self, root) -> str:
        test_commands = []
        config_files = {
            "pytest.ini": "pytest",
            "pyproject.toml": "pytest",
            "setup.cfg": "pytest",
            "tox.ini": "pytest",
            "manage.py": "python manage.py test",
            "noxfile.py": "nox",
        }
        for config_file, command in config_files.items():
            if (root / config_file).exists():
                if config_file == "manage.py":
                    test_commands.append(command)
                else:
                    if self._has_test_config(root / config_file):
                        test_commands.append(command)

        setup_py = root / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text()
                if "test_suite" in content or "pytest" in content:
                    test_commands.append("python setup.py test")
            except:
                pass

        test_dirs = ["tests", "test", "spec"]
        for test_dir in test_dirs:
            if (root / test_dir).exists():
                test_commands.append("pytest")
                break

        makefile = root / "Makefile"
        if makefile.exists():
            try:
                content = makefile.read_text()
                if "test:" in content or "pytest" in content:
                    test_commands.append("make test")
            except:
                pass

        tox_ini = root / "tox.ini"
        if tox_ini.exists():
            try:
                content = tox_ini.read_text()
                if "[testenv]" in content:
                    test_commands.append("tox")
            except:
                pass

        python_files = list(root.glob("**/test_*.py")) + list(root.glob("**/*_test.py"))
        if python_files:
            try:
                if "unittest" in python_files[0].read_text():
                    test_commands.append("python -m unittest discover")
            except:
                pass

        return test_commands[0] if test_commands else ""

    def get_linters(self, root: Path) -> list[models.Linter]:

        detected_linters = set()
        for l in self._find_by_config_files(root):
            detected_linters.add(l)
        for l in self._find_by_dependencies(root):
            detected_linters.add(l)
        for l in self._find_by_build_tools(root):
            detected_linters.add(l)
        return list(detected_linters)

    def _find_by_config_files(self, root: Path) -> list[models.Linter]:
        linters = []

        # Check individual config files
        config_files = {
            ".flake8": "flake8",
            ".pylintrc": "pylint",
            "pylintrc": "pylint",
            "mypy.ini": "mypy .",
            ".mypy.ini": "mypy .",
            ".bandit": "bandit -r .",
            "bandit.yaml": "bandit -r .",
            ".pydocstyle": "pydocstyle",
            "pydocstyle.ini": "pydocstyle",
        }

        for config_file, linter_command in config_files.items():
            config_path = root / config_file
            if config_path.exists():
                linters.append(
                    models.Linter(name=linter_command, config=str(config_path))
                )

        # Check setup.cfg for multiple linters
        setup_cfg_path = root / "setup.cfg"
        if setup_cfg_path.exists():
            flake8_cmd = self._check_flake8_in_setup_cfg(root)
            if flake8_cmd:
                linters.append(
                    models.Linter(name=flake8_cmd, config=str(setup_cfg_path))
                )
            pylint_cmd = self._check_pylint_in_setup_cfg(root)
            if pylint_cmd:
                linters.append(
                    models.Linter(name=pylint_cmd, config=str(setup_cfg_path))
                )

        # Check pyproject.toml for multiple linters
        pyproject_path = root / "pyproject.toml"
        if pyproject_path.exists():
            black_cmd = self._check_black_in_pyproject(root)
            if black_cmd:
                linters.append(
                    models.Linter(name=black_cmd, config=str(pyproject_path))
                )
            mypy_cmd = self._check_mypy_in_pyproject(root)
            if mypy_cmd:
                linters.append(models.Linter(name=mypy_cmd, config=str(pyproject_path)))
            # Check for ruff
            try:
                content = pyproject_path.read_text()
                if "[tool.ruff]" in content:
                    linters.append(
                        models.Linter(name="ruff check .", config=str(pyproject_path))
                    )
            except:
                pass

        return linters

    def _find_by_dependencies(self, root: Path) -> list[models.Linter]:
        linters = []
        linter_packages = {
            "flake8": "flake8",
            "pylint": "pylint",
            "black": "black --check .",
            "isort": "isort --check-only .",
            "mypy": "mypy .",
            "bandit": "bandit -r .",
            "pydocstyle": "pydocstyle",
            "pycodestyle": "pycodestyle",
            "pyflakes": "pyflakes",
            "ruff": "ruff check .",
        }
        dependency_files = [
            "requirements.txt",
            "requirements-dev.txt",
            "dev-requirements.txt",
            "setup.py",
            "Pipfile",
            "pyproject.toml",
        ]

        for dep_file in dependency_files:
            dep_path = root / dep_file
            if dep_path.exists():
                try:
                    content = dep_path.read_text().lower()
                    for pkg, command in linter_packages.items():
                        if pkg in content:
                            linters.append(
                                models.Linter(name=command, config=str(dep_path))
                            )
                except:
                    continue

        return linters

    def _find_by_build_tools(self, root: Path) -> list[models.Linter]:
        linters = []

        makefile_path = root / "Makefile"
        if makefile_path.exists():
            try:
                content = makefile_path.read_text()
                if "lint:" in content:
                    linters.append(
                        models.Linter(name="make lint", config=str(makefile_path))
                    )
                elif "flake8" in content:
                    linters.append(
                        models.Linter(name="flake8", config=str(makefile_path))
                    )
                elif "pylint" in content:
                    linters.append(
                        models.Linter(name="pylint", config=str(makefile_path))
                    )
            except:
                pass
        tox_path = root / "tox.ini"
        if tox_path.exists():
            try:
                content = tox_path.read_text()
                if "[testenv:lint]" in content:
                    linters.append(
                        models.Linter(name="tox -e lint", config=str(tox_path))
                    )
            except:
                pass

        precommit_path = root / ".pre-commit-config.yaml"
        if precommit_path.exists():
            linters.append(
                models.Linter(
                    name="pre-commit run --all-files", config=str(precommit_path)
                )
            )

        return linters

    def _check_flake8_in_setup_cfg(self, root: Path) -> tp.Optional[str]:
        setup_cfg_path = root / "setup.cfg"
        if setup_cfg_path.exists():
            try:
                content = setup_cfg_path.read_text()
                if "[flake8]" in content or "[tool:flake8]" in content:
                    return "flake8"
            except:
                pass
        return None

    def _check_pylint_in_setup_cfg(self, root: Path) -> tp.Optional[str]:
        setup_cfg_path = root / "setup.cfg"
        if setup_cfg_path.exists():
            try:
                content = setup_cfg_path.read_text()
                if "[pylint]" in content or "[tool:pylint]" in content:
                    return "pylint"
            except:
                pass
        return None

    def _check_black_in_pyproject(self, root: Path) -> tp.Optional[str]:
        pyproject_path = root / "pyproject.toml"
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text()
                if "[tool.black]" in content:
                    return "black --check ."
            except:
                pass
        return None

    def _check_mypy_in_pyproject(self, root: Path) -> tp.Optional[str]:
        pyproject_path = root / "pyproject.toml"
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text()
                if "[tool.mypy]" in content:
                    return "mypy ."
            except:
                pass
        return None

    def _normalize_python_version(self, version: str) -> str:
        """Normalize Python version string to a clean format for Docker tags.

        Converts strings like "Python 3.7+", "3.8+", "Python 3.11" to "3.11"
        """
        if not version:
            return "3.11"

        # Remove "Python " prefix if present
        version = version.replace("Python ", "").strip()

        # Extract major.minor version (e.g., "3.7+" -> "3.7", "3.11" -> "3.11")
        match = re.search(r"(\d+)\.(\d+)", version)
        if match:
            major, minor = match.groups()
            return f"{major}.{minor}"

        # Fallback to default if we can't parse it
        return "3.11"

    def detect_python_version_by_syntax(self, root) -> str:
        version_features = {
            (3, 8): [
                "walrus_operator",
                "positional_only_args",
                "fstring_self_documenting",
            ],
            (3, 9): [
                "dict_union_operators",
                "str_remove_methods",
                "type_hinting_generics",
                "zoneinfo_module",
            ],
            (3, 10): [
                "match_statement",
                "union_operator_in_types",
                "parenthesized_context_managers",
            ],
            (3, 11): [
                "exception_group",
                "try_star_syntax",
                "variadic_generics",
                "tomllib_module",
            ],
            (3, 12): [
                "type_parameter_syntax",
                "fstring_debugging",
                "pattern_matching_enhancements",
            ],
        }

        found_features: tp.Set[str] = set()
        py_files = list(root.glob("**/*.py"))[:30]

        for py_file in py_files:
            if py_file.is_file():
                try:
                    content = py_file.read_text(encoding="utf-8")
                    if ":=" in content:
                        found_features.add("walrus_operator")
                    if re.search(r"\bmatch\b.*\bcase\b", content):
                        found_features.add("match_statement")
                    if "removeprefix" in content or "removesuffix" in content:
                        found_features.add("str_remove_methods")
                    if re.search(r"\w+\s*\|\s*\w+", content) and any(
                        word in content for word in ["dict", "Dict", "typing.Dict"]
                    ):
                        found_features.add("dict_union_operators")
                    if re.search(
                        r"def\s+\w+\(.*\)\s*->\s*[^:]+?\s*\|\s*[^:]+?:", content
                    ):
                        found_features.add("union_operator_in_types")
                    if "except*" in content:
                        found_features.add("exception_group")
                    if re.search(r"def\s+\w+\([^)]*\/[^)]*\)", content):
                        found_features.add("positional_only_args")

                except (UnicodeDecodeError, Exception):
                    continue
        min_version: Tuple[int, int] = (3, 7)
        major, minor = min_version
        sorted_versions = sorted(version_features.keys())
        for version in sorted_versions:
            features_in_version = version_features[version]
            if any(feature in found_features for feature in features_in_version):
                min_version = max(min_version, version)
                major, minor = min_version
        if min_version > (3, 7):
            return f"Python {major}.{minor}+"
        else:
            return "Python 3.7+"

    def _has_test_config(self, config_path: Path) -> bool:
        try:
            content = config_path.read_text()
            if config_path.name == "pyproject.toml":
                return (
                    "[tool.pytest]" in content or "[tool.pytest.ini_options]" in content
                )
            elif config_path.name == "setup.cfg":
                return "[tool:pytest]" in content or (
                    "[aliases]" in content and "test" in content
                )
            elif config_path.name == "tox.ini":
                return "[pytest]" in content or "[testenv]" in content
            return True
        except:
            return False
