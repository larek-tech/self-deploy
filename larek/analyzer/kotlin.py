import typing as tp
from pathlib import Path
from larek.analyzer import BaseAnalyzer
from larek import models
import re


class KotlinAnalyzer(BaseAnalyzer):
    """Анализатор Kotlin проектов (Gradle)."""

    def __init__(self) -> None:
        self.is_kotlin_service: bool = False
        self.build_tool: str = "gradle"

        self.kotlin_version: str = ""
        self.java_version: str = ""
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

        # Check for Kotlin project indicators
        gradle_file = root / "build.gradle"
        gradle_kts_file = root / "build.gradle.kts"

        # Check if it's a Kotlin project
        has_kotlin_src = (root / "src" / "main" / "kotlin").exists()
        has_kotlin_files = any(root.rglob("*.kt"))

        if gradle_kts_file.exists():
            self.build_tool = "gradle"
            self.kotlin_version, self.java_version, self.libs = self._parse_gradle_kts(
                gradle_kts_file
            )
            self.is_kotlin_service = True
        elif gradle_file.exists() and (has_kotlin_src or has_kotlin_files):
            self.build_tool = "gradle"
            self.kotlin_version, self.java_version, self.libs = self._parse_gradle(
                gradle_file
            )
            self.is_kotlin_service = True
        else:
            return None

        # If we couldn't detect Kotlin, this might be a Java project
        if not self.kotlin_version and not has_kotlin_src and not has_kotlin_files:
            return None

        if not self.kotlin_version:
            self.kotlin_version = "1.9"  # Default Kotlin version

        if not self.java_version:
            self.java_version = "17"  # Default JVM target

        self._scan(root)

        test_command = self._get_test_command(root)

        return models.Service(
            path=root,
            name=root.name,
            lang=models.Language(name="kotlin", version=self.kotlin_version),
            dependencies=models.Dependencies(
                packet_manager=self.build_tool,
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

    def _get_test_command(self, root: Path) -> str:
        if (root / "gradlew").exists():
            return "./gradlew test"
        return "gradle test"

    def _scan(self, root: Path):
        for f in root.glob("*"):
            if f.is_file() and self._file_filter(f):
                self._parse_file(f)
            elif f.is_dir() and self._dir_filter(f):
                self._scan(f)

    def _file_filter(self, file: Path) -> bool:
        return True

    def _dir_filter(self, directory: Path) -> bool:
        excluded = {
            ".git",
            ".idea",
            ".gradle",
            "build",
            "target",
            "out",
            "node_modules",
        }
        return directory.name not in excluded

    def _parse_file(self, file: Path):
        match file.name:
            case "Dockerfile":
                self.dockerfiles.append(str(file))

            case "docker-compose.yml" | "docker-compose.yaml":
                self.compose_file = str(file)

            case "detekt.yml" | "detekt.yaml" | "detekt-config.yml":
                self.linters.append(
                    models.Linter(
                        name="detekt",
                        config=str(file),
                    )
                )

            case "ktlint.xml" | ".editorconfig":
                if file.name == ".editorconfig":
                    # Check if it has ktlint config
                    try:
                        content = file.read_text(errors="ignore")
                        if "ktlint" in content.lower():
                            self.linters.append(
                                models.Linter(
                                    name="ktlint",
                                    config=str(file),
                                )
                            )
                    except Exception:
                        pass
                else:
                    self.linters.append(
                        models.Linter(
                            name="ktlint",
                            config=str(file),
                        )
                    )

            case ".sonar-project.properties" | "sonar-project.properties":
                self.linters.append(
                    models.Linter(
                        name="sonar",
                        config=str(file),
                    )
                )

            case _:
                # Check for main function entry points in Kotlin
                if file.suffix == ".kt":
                    try:
                        content = file.read_text(errors="ignore")
                        if "fun main(" in content or "fun main()" in content:
                            self.entrypoints.append(str(file))
                    except Exception:
                        pass

                # Config files
                if (
                    "config" in file.name.lower()
                    or "application" in file.name.lower()
                    or "settings" in file.name.lower()
                ) and file.suffix in {
                    ".yml",
                    ".yaml",
                    ".properties",
                    ".xml",
                    ".json",
                    ".conf",
                }:
                    self.configs.append(
                        models.Config(
                            name=file.name,
                            path=str(file),
                        )
                    )

                if "Dockerfile" in file.name:
                    self.dockerfiles.append(str(file))

                if "compose" in file.name and file.suffix in {".yml", ".yaml"}:
                    self.compose_file = str(file)

                if ".env" in file.name:
                    self.environment.append(
                        models.Environment(
                            name=file.name,
                            path=str(file),
                        )
                    )

    def _parse_gradle_kts(self, gradle_file: Path) -> tuple[str, str, list[models.Lib]]:
        """Parse Gradle build.gradle.kts file (Kotlin DSL)."""
        kotlin_version = ""
        java_version = ""
        libs: list[models.Lib] = []

        try:
            content = gradle_file.read_text(errors="ignore")

            # Find Kotlin version
            kotlin_patterns = [
                r'kotlin\("jvm"\)\s+version\s+"([^"]+)"',
                r'kotlin\("jvm"\)\s+version\s+\'([^\']+)\'',
                r'id\("org\.jetbrains\.kotlin\.jvm"\)\s+version\s+"([^"]+)"',
                r'kotlin_version\s*=\s*"([^"]+)"',
                r"kotlinVersion\s*=\s*\"([^\"]+)\"",
            ]
            for pattern in kotlin_patterns:
                match = re.search(pattern, content)
                if match:
                    kotlin_version = match.group(1)
                    break

            # Find Java/JVM target version
            jvm_patterns = [
                r"jvmTarget\s*=\s*['\"](\d+)['\"]",
                r"jvmToolchain\((\d+)\)",
                r"JavaVersion\.VERSION_(\d+)",
            ]
            for pattern in jvm_patterns:
                match = re.search(pattern, content)
                if match:
                    java_version = match.group(1)
                    break

            # Parse dependencies
            dep_patterns = [
                r'implementation\("([^"]+):([^"]+):([^"]+)"\)',
                r"implementation\('([^']+):([^']+):([^']+)'\)",
                r'api\("([^"]+):([^"]+):([^"]+)"\)',
                r'testImplementation\("([^"]+):([^"]+):([^"]+)"\)',
                r'runtimeOnly\("([^"]+):([^"]+):([^"]+)"\)',
            ]
            for pattern in dep_patterns:
                for match in re.finditer(pattern, content):
                    group_id, artifact_id, version = match.groups()
                    libs.append(
                        models.Lib(
                            name=f"{group_id}:{artifact_id}",
                            version=version,
                        )
                    )

        except Exception:
            pass

        return kotlin_version, java_version, libs

    def _parse_gradle(self, gradle_file: Path) -> tuple[str, str, list[models.Lib]]:
        """Parse Gradle build.gradle file (Groovy DSL)."""
        kotlin_version = ""
        java_version = ""
        libs: list[models.Lib] = []

        try:
            content = gradle_file.read_text(errors="ignore")

            # Find Kotlin version
            kotlin_patterns = [
                r"kotlin_version\s*=\s*['\"]([^'\"]+)['\"]",
                r"kotlinVersion\s*=\s*['\"]([^'\"]+)['\"]",
                r"org\.jetbrains\.kotlin:kotlin-[^:]+:([^'\"]+)",
            ]
            for pattern in kotlin_patterns:
                match = re.search(pattern, content)
                if match:
                    kotlin_version = match.group(1)
                    break

            # Find Java/JVM target version
            jvm_patterns = [
                r"jvmTarget\s*=\s*['\"](\d+)['\"]",
                r"sourceCompatibility\s*=\s*['\"]?(\d+)['\"]?",
                r"targetCompatibility\s*=\s*['\"]?(\d+)['\"]?",
            ]
            for pattern in jvm_patterns:
                match = re.search(pattern, content)
                if match:
                    java_version = match.group(1)
                    break

            # Parse dependencies
            dep_patterns = [
                r"implementation\s+['\"]([^'\"]+):([^'\"]+):([^'\"]+)['\"]",
                r"compile\s+['\"]([^'\"]+):([^'\"]+):([^'\"]+)['\"]",
                r"api\s+['\"]([^'\"]+):([^'\"]+):([^'\"]+)['\"]",
                r"testImplementation\s+['\"]([^'\"]+):([^'\"]+):([^'\"]+)['\"]",
            ]
            for pattern in dep_patterns:
                for match in re.finditer(pattern, content):
                    group_id, artifact_id, version = match.groups()
                    libs.append(
                        models.Lib(
                            name=f"{group_id}:{artifact_id}",
                            version=version,
                        )
                    )

        except Exception:
            pass

        return kotlin_version, java_version, libs
