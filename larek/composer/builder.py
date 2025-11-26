import os
from abc import ABC, abstractmethod
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader

from larek.models.repo import Service


class DockerfileBuilder(ABC):
    """Base class for Dockerfile builders."""

    def __init__(self, template_dir: str):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    @abstractmethod
    def generate(self, service: Service) -> str:
        """Generate Dockerfile content for the service."""
        pass

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)


class GoBuilder(DockerfileBuilder):
    def generate(self, service: Service) -> str:
        # Logic to determine build commands, entrypoints, etc.
        # For now, assuming simple structure or using service.entrypoint
        context = {
            "service": service,
            "go_version": service.lang.version or "1.21",
            # Add logic to find all main.go files if needed, or use entrypoint
        }
        return self.render_template("go.dockerfile.j2", context)


class PythonBuilder(DockerfileBuilder):
    def generate(self, service: Service) -> str:
        context = {
            "service": service,
            "python_version": service.lang.version or "3.11",
            "package_manager": service.dependencies.packet_manager,
        }
        return self.render_template("python.dockerfile.j2", context)


class NodeBuilder(DockerfileBuilder):
    SPA_FRAMEWORKS = ["react", "vue", "angular", "svelte", "next", "nuxt"]

    def is_spa(self, service: Service) -> bool:
        # Check dependencies for SPA frameworks
        for lib in service.dependencies.libs:
            if lib.name.lower() in self.SPA_FRAMEWORKS:
                return True
        return False

    def generate(self, service: Service) -> str:
        is_spa = self.is_spa(service)
        template_name = "node_spa.dockerfile.j2" if is_spa else "node_app.dockerfile.j2"

        context = {
            "service": service,
            "node_version": service.lang.version or "20",
            "package_manager": service.dependencies.packet_manager,
            "build_command": "build" if is_spa else None,  # Infer or get from config
        }
        return self.render_template(template_name, context)


class Composer:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, "templates")
        self.builders = {
            "go": GoBuilder(template_dir),
            "python": PythonBuilder(template_dir),
            "javascript": NodeBuilder(template_dir),
            "typescript": NodeBuilder(template_dir),
        }

    def get_dockerfile(self, service: Service) -> str:
        # if service.dockerfiles != "":
        # return

        builder = self.builders.get(service.lang.name)
        if not builder:
            raise ValueError(f"No builder found for language: {service.lang.name}")
        return builder.generate(service)
