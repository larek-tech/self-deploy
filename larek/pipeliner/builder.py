import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from larek.models.repo import Service, Deployment


class PipelineBuilder(ABC):
    """Base class for GitLab CI pipeline builders."""

    def __init__(self, template_dir: str):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    @abstractmethod
    def generate(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> str:
        """Generate GitLab CI pipeline content for the service."""
        pass

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)

    def extra_stages(
        self, service: Optional[Service] = None, deployment: Optional[Deployment] = None
    ) -> List[str]:
        return []

    def get_stages(
        self, service: Optional[Service] = None, deployment: Optional[Deployment] = None
    ) -> List[str]:
        """Return list of pipeline stages.

        If `service` is provided, uses the Service model to decide whether
        to include `lint` and `test` stages and whether `docker` should be
        present. If `service` is None, returns the default stages.
        """

        default = ["lint", "test", "build"]
        if service is None and deployment is None:
            return default

        stages: List[str] = []
        if service and service.linters:
            stages.append("lint")

        if service and service.tests and "echo" not in service.tests.lower():
            stages.append("test")

        lang_name = (
            service.lang.name.lower()
            if service
            and getattr(service, "lang", None)
            and getattr(service.lang, "name", None)
            else ""
        )
        if lang_name in ("javascript", "typescript"):
            stages.append("build")
        else:
            if service and (
                getattr(service, "entrypoints", None)
                or len(service.docker.dockerfiles) > 0
            ):
                stages.append("build")

        if service and len(service.docker.dockerfiles) > 0:
            stages.append("docker")

        extra = self.extra_stages(service, deployment)
        for st in extra:
            if st not in stages:
                stages.append(st)

        return stages

    def get_docker_context(self, service: Service) -> Dict[str, Any]:
        """Get Docker build context for the service."""
        return {
            "has_dockerfiles": len(service.docker.dockerfiles) > 0,
            "dockerfiles": service.docker.dockerfiles,
            "image_name": service.name,
        }


class GoPipelineBuilder(PipelineBuilder):
    """
    Pipeline builder for Go projects.
    """

    default_linter_cmd = "golangci-lint run ./..."

    def generate(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> str:
        context = {
            "service": service,
            "go_version": service.lang.version or "1.21",
            "stages": self.get_stages(service, deployment),
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

    def generate(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> str:
        package_manager = service.dependencies.packet_manager

        has_lint = len(service.linters) > 0
        has_test = bool(service.tests)

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
        stages = self.get_stages(service, deployment)
        context = {
            "service": service,
            "python_version": service.lang.version or "3.11",
            "stages": stages,
            "package_manager": package_manager,
            "install_command": install_cmd,
            "lint_command": lint_cmd,
            "test_command": test_cmd,
            "has_lint": has_lint,
            "has_test": has_test,
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

    def generate(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> str:
        package_manager = service.dependencies.packet_manager
        is_typescript = service.lang.name == "typescript"
        is_spa = self.is_spa(service)
        has_dockerfiles = len(service.docker.dockerfiles) > 0

        has_lint = len(service.linters) > 0
        # Don't count placeholder "no tests" message as having tests
        has_test = bool(service.tests) and "echo" not in service.tests.lower()

        # Detect S3/MinIO/AWS credentials from deployment.environment (list[Environment]).
        # Look for common MinIO and AWS env var names (case-insensitive),
        # with a fallback to generic "access"/"secret"/"bucket" substrings.
        has_s3 = False
        s3_details: Dict[str, Any] = {}
        if deployment and getattr(deployment, "environment", None):
            env_names = [
                env.name for env in deployment.environment if getattr(env, "name", None)
            ]
            lower = [n.lower() for n in env_names]

            known_access = (
                "minio_root_user",
                "minio_access_key",
                "aws_access_key_id",
                "aws_access_key",
                "access_key",
                "accesskey",
            )
            known_secret = (
                "minio_root_password",
                "minio_secret_key",
                "aws_secret_access_key",
                "aws_secret_key",
                "secret_key",
                "secretkey",
                "secret",
            )
            known_bucket = (
                "minio_bucket",
                "s3_bucket",
                "bucket_name",
                "aws_bucket",
                "bucket",
            )

            has_access = any(n in known_access for n in lower) or any(
                "access" in n for n in lower
            )
            has_secret = any(n in known_secret for n in lower) or any(
                "secret" in n for n in lower
            )
            has_bucket = any(n in known_bucket for n in lower) or any(
                "bucket" in n for n in lower
            )

            if has_access and has_secret:
                has_s3 = True
                s3_details = {"env_names": env_names, "has_bucket": has_bucket}

        # Determine commands based on package manager
        if package_manager == "yarn":
            install_cmd = "yarn install --frozen-lockfile"
            lint_cmd = "yarn lint"
            test_cmd = "yarn test"
            build_cmd = "yarn build"
        elif package_manager == "pnpm":
            install_cmd = "pnpm install --no-frozen-lockfile"
            lint_cmd = "pnpm lint"
            test_cmd = "pnpm test"
            build_cmd = "pnpm build"
        else:  # npm
            install_cmd = "npm install --prefer-offline --no-audit"
            lint_cmd = "npm run lint"
            test_cmd = "npm test"
            build_cmd = "npm run build"

        stages = self.get_stages(service, deployment)

        has_deploy = is_spa and "deploy" in stages
        deploy_target = "pages"
        if deployment and getattr(deployment, "environment", None):
            env_names = [
                env.name.lower()
                for env in deployment.environment
                if getattr(env, "name", None)
            ]
            if any(
                n in ("ssh_private_key", "deploy_host", "deploy_user", "deploy_path")
                for n in env_names
            ):
                deploy_target = "ssh"

        context = {
            "service": service,
            "node_version": service.lang.version or "20",
            "stages": stages,
            "package_manager": package_manager,
            "install_command": install_cmd,
            "lint_command": lint_cmd,
            "test_command": service.tests or test_cmd,
            "has_lint": has_lint,
            "has_test": has_test,
            "has_s3": has_s3,
            "s3": s3_details,
            "build_command": build_cmd,
            "is_typescript": is_typescript,
            "is_spa": is_spa,
            "has_deploy": has_deploy,
            "deploy_target": deploy_target,
            **self.get_docker_context(service),
        }
        template_name = (
            "node-frontend.gitlab-ci.yml.j2"
            if is_spa
            else "node-backend.gitlab-ci.yml.j2"
        )
        return self.render_template(template_name, context)

    def extra_stages(
        self, service: Optional[Service] = None, deployment: Optional[Deployment] = None
    ) -> List[str]:
        if service is None and deployment is None:
            return []

        extra: List[str] = []

        if deployment and getattr(deployment, "environment", None):
            names = [
                env.name.lower()
                for env in deployment.environment
                if getattr(env, "name", None)
            ]

            known_access = (
                "minio_root_user",
                "minio_access_key",
                "aws_access_key_id",
                "aws_access_key",
                "access_key",
                "accesskey",
            )
            known_secret = (
                "minio_root_password",
                "minio_secret_key",
                "aws_secret_access_key",
                "aws_secret_key",
                "secret_key",
                "secretkey",
                "secret",
            )

            has_access = any(n in known_access for n in names) or any(
                "access" in n for n in names
            )
            has_secret = any(n in known_secret for n in names) or any(
                "secret" in n for n in names
            )
            if has_access and has_secret:
                extra.append("s3")

        if service:
            for cfg in service.configs:
                if cfg.name and cfg.name.lower() == "s3":
                    if "s3" not in extra:
                        extra.append("s3")
                    break

            for lib in service.dependencies.libs:
                name = (lib.name or "").lower()
                if "aws" in name or "s3" in name or "boto" in name:
                    if "s3" not in extra:
                        extra.append("s3")
                    break

        if service and self.is_spa(service) and len(service.docker.dockerfiles) == 0:
            extra.append("deploy")

        return extra


class JavaPipelineBuilder(PipelineBuilder):
    """Pipeline builder for Java projects."""

    def generate(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> str:
        package_manager = service.dependencies.package_manager
        has_lint = len(service.linters) > 0
        has_test = bool(service.tests)

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
            "stages": self.get_stages(service, deployment),
            "package_manager": package_manager,
            "lint_command": lint_cmd,
            "test_command": service.tests or test_cmd,
            "build_command": build_cmd,
            "has_lint": has_lint,
            "has_test": has_test,
            **self.get_docker_context(service),
        }
        return self.render_template("java.gitlab-ci.yml.j2", context)


class KotlinPipelineBuilder(PipelineBuilder):
    """Pipeline builder for Kotlin projects."""

    def generate(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> str:
        package_manager = service.dependencies.packet_manager
        has_dockerfiles = len(service.docker.dockerfiles) > 0
        has_lint = len(service.linters) > 0
        has_test = bool(service.tests)

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
            "stages": self.get_stages(service, deployment),
            "package_manager": package_manager,
            "lint_command": lint_cmd,
            "test_command": service.tests or test_cmd,
            "build_command": build_cmd,
            "has_lint": has_lint,
            "has_test": has_test,
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
                all_stages.update(builder.get_stages(service))
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
