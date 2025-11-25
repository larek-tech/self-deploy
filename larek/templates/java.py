"""Шаблон для Java/Kotlin проектов."""

from pathlib import Path

from larek.templates.base import LanguageTemplate


class JavaTemplate(LanguageTemplate):
    """Шаблон для Java/Kotlin проектов с Gradle."""

    def __init__(self, kotlin: bool = False):
        self._kotlin = kotlin

    @property
    def name(self) -> str:
        return "kotlin" if self._kotlin else "java"

    @property
    def extensions(self) -> list[str]:
        if self._kotlin:
            return [".kt", ".kts", ".java"]
        return [".java"]

    @property
    def package_managers(self) -> list[str]:
        return ["gradle", "maven"]

    @property
    def default_linters(self) -> list[str]:
        if self._kotlin:
            return ["ktlint", "detekt"]
        return ["checkstyle", "spotbugs"]

    def create_structure(self, project_path: Path, project_name: str) -> None:
        """Создать структуру Java/Kotlin проекта."""
        src_dir = (
            project_path / "src" / "main" / self.name / "com" / "example" / project_name
        )
        test_dir = (
            project_path / "src" / "test" / self.name / "com" / "example" / project_name
        )

        dirs = [
            src_dir,
            test_dir,
            project_path / "src" / "main" / "resources",
            project_path / "src" / "test" / "resources",
            project_path / "docs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # build.gradle.kts
        if self._kotlin:
            build_gradle = f"""plugins {{
    kotlin("jvm") version "1.9.22"
    application
}}

group = "com.example"
version = "0.1.0"

repositories {{
    mavenCentral()
}}

dependencies {{
    testImplementation(kotlin("test"))
}}

tasks.test {{
    useJUnitPlatform()
}}

kotlin {{
    jvmToolchain(21)
}}

application {{
    mainClass.set("com.example.{project_name}.MainKt")
}}
"""
        else:
            build_gradle = f"""plugins {{
    id 'java'
    id 'application'
}}

group = 'com.example'
version = '0.1.0'

java {{
    toolchain {{
        languageVersion = JavaLanguageVersion.of(21)
    }}
}}

repositories {{
    mavenCentral()
}}

dependencies {{
    testImplementation 'org.junit.jupiter:junit-jupiter:5.10.0'
    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
}}

tasks.named('test') {{
    useJUnitPlatform()
}}

application {{
    mainClass = 'com.example.{project_name}.Main'
}}
"""
        build_file = "build.gradle.kts" if self._kotlin else "build.gradle"
        (project_path / build_file).write_text(build_gradle)

        # settings.gradle.kts
        settings = f'rootProject.name = "{project_name}"\n'
        settings_file = "settings.gradle.kts" if self._kotlin else "settings.gradle"
        (project_path / settings_file).write_text(settings)

        # Main file
        if self._kotlin:
            main_content = f"""package com.example.{project_name}

fun main() {{
    println("Hello from {project_name}!")
}}
"""
            (src_dir / "Main.kt").write_text(main_content)
        else:
            main_content = f"""package com.example.{project_name};

public class Main {{
    public static void main(String[] args) {{
        System.out.println("Hello from {project_name}!");
    }}
}}
"""
            (src_dir / "Main.java").write_text(main_content)

        # README.md
        (project_path / "README.md").write_text(f"# {project_name}\n\n")

        # .gitignore
        gitignore = """.gradle/
build/
!gradle/wrapper/gradle-wrapper.jar
*.class
*.log
*.jar
*.war
*.nar
*.ear
*.zip
*.tar.gz
*.rar
.idea/
*.iml
.DS_Store
"""
        (project_path / ".gitignore").write_text(gitignore)

        # gradle wrapper properties
        gradle_wrapper_dir = project_path / "gradle" / "wrapper"
        gradle_wrapper_dir.mkdir(parents=True, exist_ok=True)
        gradle_properties = """distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-8.5-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
"""
        (gradle_wrapper_dir / "gradle-wrapper.properties").write_text(gradle_properties)

    def generate_dockerfile(self, version: str | None = None) -> str:
        """Сгенерировать Dockerfile для Java/Kotlin."""
        java_version = version or "21"
        return f"""FROM gradle:8.5-jdk{java_version} AS builder

WORKDIR /app
COPY . .
RUN gradle build --no-daemon

FROM eclipse-temurin:{java_version}-jre-alpine

WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar

CMD ["java", "-jar", "app.jar"]
"""

    def get_test_command(self) -> str:
        return "./gradlew test"
