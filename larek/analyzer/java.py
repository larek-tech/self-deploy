import typing as tp
from pathlib import Path
from larek.analyzer import BaseAnalyzer
from larek import models
import re
import xml.etree.ElementTree as ET


class JavaAnalyzer(BaseAnalyzer):
    """Анализатор Java проектов (Maven и Gradle)."""

    def __init__(self) -> None:
        self.is_java_service: bool = False
        self.build_tool: str = ""  # "maven" or "gradle"

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

        pom_file = root / "pom.xml"
        gradle_file = root / "build.gradle"
        gradle_kts_file = root / "build.gradle.kts"

        if pom_file.exists():
            self.build_tool = "maven"
            self.java_version, self.libs = self._parse_pom(pom_file)
            self.is_java_service = True
        elif gradle_file.exists():
            self.build_tool = "gradle"
            self.java_version, self.libs = self._parse_all_gradle_files(root)
            self.is_java_service = True
        elif gradle_kts_file.exists():
            self.build_tool = "gradle"
            self.java_version, self.libs = self._parse_all_gradle_files(root)
            self.is_java_service = True
        else:
            return None

        if not self.java_version:
            self.java_version = "17"  # Default to Java 17

        self._scan(root)

        test_command = self._get_test_command(root)

        return models.Service(
            path=root,
            name=root.name,
            lang=models.Language(name="java", version=self.java_version),
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

    def _parse_all_gradle_files(self, root: Path) -> tuple[str, list[models.Lib]]:
        """Parse all build.gradle and build.gradle.kts files in the project."""
        java_version = ""
        all_libs: list[models.Lib] = []
        libs_by_name: dict[str, models.Lib] = {}

        # First, collect variables from root build.gradle files
        root_variables: dict[str, str] = {}
        root_gradle = root / "build.gradle"
        root_gradle_kts = root / "build.gradle.kts"

        if root_gradle.exists():
            root_variables = self._extract_variables(root_gradle)
        elif root_gradle_kts.exists():
            root_variables = self._extract_variables(root_gradle_kts)

        # Find all gradle files
        gradle_files = list(root.glob("**/build.gradle")) + list(
            root.glob("**/build.gradle.kts")
        )

        for gradle_file in gradle_files:
            # Skip files in build directories
            if "build" in gradle_file.parts or ".gradle" in gradle_file.parts:
                continue

            version, libs = self._parse_gradle(gradle_file, root_variables)
            if version and not java_version:
                java_version = version

            for lib in libs:
                # Prefer resolved versions over unresolved ($variable)
                existing = libs_by_name.get(lib.name)
                if existing is None:
                    libs_by_name[lib.name] = lib
                elif lib.version and not lib.version.startswith("$"):
                    # Replace if new version is resolved and old is not
                    if existing.version is None or existing.version.startswith("$"):
                        libs_by_name[lib.name] = lib

        return java_version, list(libs_by_name.values())

    def _extract_variables(self, gradle_file: Path) -> dict[str, str]:
        """Extract variable definitions from a gradle file."""
        variables: dict[str, str] = {}
        try:
            content = gradle_file.read_text(errors="ignore")

            # Extract variables (ext block and top-level)
            var_patterns = [
                r"ext\.(\w+)\s*=\s*['\"]([^'\"]+)['\"]",
                r"ext\s*\{\s*(\w+)\s*=\s*['\"]([^'\"]+)['\"]",
                r"(\w+)\s*=\s*['\"]([^'\"]+)['\"]",
                r"set\(['\"](\w+)['\"],\s*['\"]([^'\"]+)['\"]\)",
                r"val\s+(\w+)\s*=\s*['\"]([^'\"]+)['\"]",
                r"def\s+(\w+)\s*=\s*['\"]([^'\"]+)['\"]",
            ]
            for pattern in var_patterns:
                for match in re.finditer(pattern, content):
                    var_name, var_value = match.groups()
                    variables[var_name] = var_value
        except Exception:
            pass
        return variables

    def _get_test_command(self, root: Path) -> str:
        if self.build_tool == "maven":
            if (root / "mvnw").exists():
                return "./mvnw test"
            return "mvn test"
        else:  # gradle
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
            ".mvn",
            "node_modules",
        }
        return directory.name not in excluded

    def _parse_file(self, file: Path):
        match file.name:
            case "Dockerfile":
                self.dockerfiles.append(str(file))

            case "docker-compose.yml" | "docker-compose.yaml":
                self.compose_file = str(file)

            case "checkstyle.xml":
                self.linters.append(
                    models.Linter(
                        name="checkstyle",
                        config=str(file),
                    )
                )

            case "spotbugs.xml" | "spotbugs-exclude.xml":
                self.linters.append(
                    models.Linter(
                        name="spotbugs",
                        config=str(file),
                    )
                )

            case "pmd.xml" | "pmd-ruleset.xml":
                self.linters.append(
                    models.Linter(
                        name="pmd",
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
                # Check for main class entry points
                if file.suffix == ".java" and "Main" in file.name:
                    self.entrypoints.append(str(file))
                elif file.suffix == ".java":
                    # Check if file contains main method
                    try:
                        content = file.read_text(errors="ignore")
                        if "public static void main" in content:
                            self.entrypoints.append(str(file))
                    except Exception:
                        pass

                # Config files
                if (
                    "config" in file.name.lower()
                    or "application" in file.name.lower()
                    or "settings" in file.name.lower()
                ) and file.suffix in {".yml", ".yaml", ".properties", ".xml", ".json"}:
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

    def _parse_pom(self, pom_file: Path) -> tuple[str, list[models.Lib]]:
        """Parse Maven pom.xml file."""
        java_version = ""
        libs: list[models.Lib] = []

        try:
            tree = ET.parse(pom_file)
            root = tree.getroot()

            # Handle Maven namespace
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}

            # Try to find Java version in properties
            props = root.find("m:properties", ns) or root.find("properties")
            if props is not None:
                # Check various Java version properties
                for prop_name in [
                    "java.version",
                    "maven.compiler.source",
                    "maven.compiler.target",
                    "maven.compiler.release",
                ]:
                    prop = props.find(f"m:{prop_name}", ns) or props.find(prop_name)
                    if prop is not None and prop.text:
                        java_version = self._normalize_java_version(prop.text)
                        break

            # Parse dependencies
            deps = root.find("m:dependencies", ns) or root.find("dependencies")
            if deps is not None:
                for dep in deps.findall("m:dependency", ns) or deps.findall(
                    "dependency"
                ):
                    group_id = dep.find("m:groupId", ns) or dep.find("groupId")
                    artifact_id = dep.find("m:artifactId", ns) or dep.find("artifactId")
                    version = dep.find("m:version", ns) or dep.find("version")

                    if group_id is not None and artifact_id is not None:
                        lib_name = f"{group_id.text}:{artifact_id.text}"
                        lib_version = version.text if version is not None else None
                        libs.append(models.Lib(name=lib_name, version=lib_version))

        except ET.ParseError:
            pass

        return java_version, libs

    def _parse_gradle(
        self, gradle_file: Path, root_variables: dict[str, str] = None
    ) -> tuple[str, list[models.Lib]]:
        """Parse Gradle build.gradle file."""
        java_version = ""
        libs: list[models.Lib] = []
        variables: dict[str, str] = root_variables.copy() if root_variables else {}

        try:
            content = gradle_file.read_text(errors="ignore")

            # Extract local variables and merge with root variables
            local_vars = self._extract_variables(gradle_file)
            variables.update(local_vars)

            # Find Java version
            version_patterns = [
                r"sourceCompatibility\s*=\s*['\"]?(\d+)['\"]?",
                r"targetCompatibility\s*=\s*['\"]?(\d+)['\"]?",
                r"JavaVersion\.VERSION_(\d+)",
                r"languageVersion\.set\(JavaLanguageVersion\.of\((\d+)\)\)",
                r"jvmTarget\s*=\s*['\"](\d+)['\"]",
            ]
            for pattern in version_patterns:
                match = re.search(pattern, content)
                if match:
                    java_version = match.group(1)
                    break

            # Parse dependencies - expanded patterns
            # Pattern for full version: 'group:artifact:version'
            dep_patterns_full = [
                r"implementation\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
                r"compile\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
                r"api\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
                r"testImplementation\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
                r"runtimeOnly\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
                r"classpath\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
                r"compileOnly\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
                r"annotationProcessor\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
                r"kapt\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
                r"debugImplementation\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
                r"releaseImplementation\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
                r"androidTestImplementation\s+['\"]([^'\":]+):([^'\":]+):([^'\"]+)['\"]",
            ]

            for pattern in dep_patterns_full:
                for match in re.finditer(pattern, content):
                    group_id, artifact_id, version = match.groups()
                    # Resolve variable references like $kotlin_version or ${kotlin_version}
                    version = self._resolve_variable(version, variables)
                    libs.append(
                        models.Lib(
                            name=f"{group_id}:{artifact_id}",
                            version=version,
                        )
                    )

            # Pattern for no version (managed by BOM or platform): 'group:artifact'
            dep_patterns_no_version = [
                r"implementation\s+['\"]([^'\":]+):([^'\":]+)['\"](?!\s*:)",
                r"api\s+['\"]([^'\":]+):([^'\":]+)['\"](?!\s*:)",
                r"testImplementation\s+['\"]([^'\":]+):([^'\":]+)['\"](?!\s*:)",
            ]

            for pattern in dep_patterns_no_version:
                for match in re.finditer(pattern, content):
                    group_id, artifact_id = match.groups()
                    # Skip if this looks like it has a version (already matched above)
                    if not artifact_id.endswith(("'", '"')):
                        libs.append(
                            models.Lib(
                                name=f"{group_id}:{artifact_id}",
                                version=None,
                            )
                        )

            # Also scan app/build.gradle if this is root build.gradle
            app_gradle = gradle_file.parent / "app" / "build.gradle"
            if app_gradle.exists() and gradle_file.name == "build.gradle":
                _, app_libs = self._parse_gradle(app_gradle)
                libs.extend(app_libs)

        except Exception:
            pass

        return java_version, libs

    def _resolve_variable(self, value: str, variables: dict[str, str]) -> str:
        """Resolve Gradle variable references like $var or ${var}."""
        # Match $variable or ${variable}
        pattern = r"\$\{?(\w+)\}?"

        def replace_var(match):
            var_name = match.group(1)
            return variables.get(var_name, match.group(0))

        return re.sub(pattern, replace_var, value)

    def _parse_gradle_kts(self, gradle_file: Path) -> tuple[str, list[models.Lib]]:
        """Parse Gradle build.gradle.kts file (Kotlin DSL)."""
        # Similar to Groovy DSL but with Kotlin syntax
        return self._parse_gradle(gradle_file)

    def _normalize_java_version(self, version: str) -> str:
        """Normalize Java version string."""
        version = version.strip()
        # Handle versions like "1.8", "11", "17", etc.
        if version.startswith("1."):
            return version[2:]  # "1.8" -> "8"
        return version
