import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

from larek.models.repo import Service


class PipelineBuilder(ABC):
    """Base class for GitLab CI pipeline builders."""

    def __init__(self, template_dir: str):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    @abstractmethod
    def generate(self, service: Service) -> str:
        """Generate GitLab CI pipeline content for the service."""
        pass

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)

    def get_stages(self, has_dockerfiles: bool = False) -> List[str]:
        """Return list of pipeline stages."""
        stages = ["lint", "test", "build"]
        if has_dockerfiles:
            stages.append("docker")
        return stages

    def get_docker_context(self, service: Service) -> Dict[str, Any]:
        """Get Docker build context for the service."""
        return {
            "has_dockerfiles": len(service.docker) > 0,
            "dockerfiles": service.docker,
            "image_name": service.name,
        }


class GoPipelineBuilder(PipelineBuilder):
    """
    Pipeline builder for Go projects.
    """

    def generate(self, service: Service) -> str:
        has_dockerfiles = len(service.docker) > 0
        context = {
            "service": service,
            "go_version": service.lang.version or "1.21",
            "stages": self.get_stages(has_dockerfiles),
            "lint_command": "golangci-lint run ./...",
            "test_command": service.tests or "go test ./...",
            "build_commands": (
                [f"go build -o bin/{service.name} {ep}" for ep in service.entrypoints]
                if service.entrypoints
                else [f"go build -o bin/{service.name} ./..."]
            ),
            **self.get_docker_context(service),
        }
        return self.render_template("go.gitlab-ci.yml.j2", context)


class PythonPipelineBuilder(PipelineBuilder):
    """Pipeline builder for Python projects."""

    def generate(self, service: Service) -> str:
        package_manager = service.dependencies.packet_manager
        has_dockerfiles = len(service.docker) > 0

        # Determine install and lint commands based on package manager
        if package_manager == "poetry":
            install_cmd = "poetry install"
            lint_cmd = "poetry run ruff check . && poetry run mypy ."
            test_cmd = (
                f"poetry run {service.tests}" if service.tests else "poetry run pytest"
            )
        else:  # pip
            install_cmd = "pip install -r requirements.txt"
            lint_cmd = "ruff check . && mypy ."
            test_cmd = service.tests or "pytest"

        context = {
            "service": service,
            "python_version": service.lang.version or "3.11",
            "stages": self.get_stages(has_dockerfiles),
            "package_manager": package_manager,
            "install_command": install_cmd,
            "lint_command": lint_cmd,
            "test_command": test_cmd,
            **self.get_docker_context(service),
        }
        return self.render_template("python.gitlab-ci.yml.j2", context)


class NodePipelineBuilder(PipelineBuilder):
    """Pipeline builder for JavaScript/TypeScript projects."""

    SPA_FRAMEWORKS = ["react", "vue", "angular", "svelte", "next", "nuxt"]

    def is_spa(self, service: Service) -> bool:
        for lib in service.dependencies.libs:
            if lib.name.lower() in self.SPA_FRAMEWORKS:
                return True
        return False

    def generate(self, service: Service) -> str:
        package_manager = service.dependencies.packet_manager
        is_typescript = service.lang.name == "typescript"
        is_spa = self.is_spa(service)
        has_dockerfiles = len(service.docker) > 0

        # Determine commands based on package manager
        if package_manager == "yarn":
            install_cmd = "yarn install --frozen-lockfile"
            lint_cmd = "yarn lint"
            test_cmd = "yarn test"
            build_cmd = "yarn build"
        elif package_manager == "pnpm":
            install_cmd = "pnpm install --frozen-lockfile"
            lint_cmd = "pnpm lint"
            test_cmd = "pnpm test"
            build_cmd = "pnpm build"
        else:  # npm
            install_cmd = "npm ci"
            lint_cmd = "npm run lint"
            test_cmd = "npm test"
            build_cmd = "npm run build"

        context = {
            "service": service,
            "node_version": service.lang.version or "20",
            "stages": self.get_stages(has_dockerfiles),
            "package_manager": package_manager,
            "install_command": install_cmd,
            "lint_command": lint_cmd,
            "test_command": service.tests or test_cmd,
            "build_command": build_cmd,
            "is_typescript": is_typescript,
            "is_spa": is_spa,
            **self.get_docker_context(service),
        }
        return self.render_template("node.gitlab-ci.yml.j2", context)


class JavaPipelineBuilder(PipelineBuilder):
    """Pipeline builder for Java projects."""

    def generate(self, service: Service) -> str:
        package_manager = service.dependencies.packet_manager
        has_dockerfiles = len(service.docker) > 0

        # Determine commands based on build tool
        if "gradle" in package_manager.lower():
            build_cmd = "./gradlew build"
            test_cmd = "./gradlew test"
            lint_cmd = "./gradlew checkstyleMain"
        else:  # maven
            build_cmd = "mvn package -DskipTests"
            test_cmd = "mvn test"
            lint_cmd = "mvn checkstyle:check"

        context = {
            "service": service,
            "java_version": service.lang.version or "17",
            "stages": self.get_stages(has_dockerfiles),
            "package_manager": package_manager,
            "lint_command": lint_cmd,
            "test_command": service.tests or test_cmd,
            "build_command": build_cmd,
            **self.get_docker_context(service),
        }
        return self.render_template("java.gitlab-ci.yml.j2", context)


class KotlinPipelineBuilder(PipelineBuilder):
    """Pipeline builder for Kotlin projects."""

    def generate(self, service: Service) -> str:
        package_manager = service.dependencies.packet_manager
        has_dockerfiles = len(service.docker) > 0

        if "maven" in package_manager.lower():
            build_cmd = "mvn package -DskipTests"
            test_cmd = "mvn test"
            lint_cmd = "mvn detekt:check"
        else:
            build_cmd = "./gradlew build"
            test_cmd = "./gradlew test"
            lint_cmd = "./gradlew detekt"

        context = {
            "service": service,
            "java_version": service.lang.version or "17",
            "stages": self.get_stages(has_dockerfiles),
            "package_manager": package_manager,
            "lint_command": lint_cmd,
            "test_command": service.tests or test_cmd,
            "build_command": build_cmd,
            **self.get_docker_context(service),
        }
        return self.render_template("kotlin.gitlab-ci.yml.j2", context)


class PipelineComposer:
    """Composer for generating GitLab CI pipelines with Docker build and push support."""

    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, "templates")
        self.builders: Dict[str, PipelineBuilder] = {
            "go": GoPipelineBuilder(template_dir),
            "python": PythonPipelineBuilder(template_dir),
            "javascript": NodePipelineBuilder(template_dir),
            "typescript": NodePipelineBuilder(template_dir),
            "java": JavaPipelineBuilder(template_dir),
            "kotlin": KotlinPipelineBuilder(template_dir),
        }

    def get_pipeline(self, service: Service) -> str:
        """Generate GitLab CI pipeline for a service."""
        builder = self.builders.get(service.lang.name)
        if not builder:
            raise ValueError(
                f"No pipeline builder found for language: {service.lang.name}"
            )
        return builder.generate(service)

    def get_multi_service_pipeline(self, services: List[Service]) -> str:
        """Generate a combined GitLab CI pipeline for multiple services."""
        all_stages = set()
        service_pipelines = []

        for service in services:
            builder = self.builders.get(service.lang.name)
            if builder:
                all_stages.update(builder.get_stages())
                service_pipelines.append(
                    {
                        "service": service,
                        "builder": builder,
                    }
                )

        # For multi-service, we'd need a different template approach
        # For now, return the first service's pipeline
        if service_pipelines:
            return service_pipelines[0]["builder"].generate(
                service_pipelines[0]["service"]
            )
        raise ValueError("No valid services found for pipeline generation")
