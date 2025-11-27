import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from larek.models.repo import Service, Deployment, RepoSchema


def _strip_leading_repo_component(path_str: str, service) -> str:
    if not path_str:
        return "."
    wildcard = ""
    if path_str.endswith("/..."):
        path_base = path_str[:-4]
        wildcard = "/..."
    else:
        path_base = path_str
    p = Path(path_base)

    if p.is_absolute():
        return str(p) + wildcard
    parts = [part for part in p.parts if part and part != "."]

    svc_first = None
    try:
        if getattr(service, "path", None):
            svc_first = str(service.path).split(os.path.sep)[0]
    except Exception:
        svc_first = None
    if svc_first and parts and parts[0] == svc_first:
        parts = parts[1:]
    result = os.path.join(*parts) if parts else "."
    return result + wildcard


def _repo_relative(path_str: str, service) -> str:
    if not path_str:
        return "./"
    if any(tok in path_str for tok in (" ", "&&", "|")):
        return path_str
    normalized = _strip_leading_repo_component(path_str, service)
    p = Path(normalized)
    if p.is_absolute():
        return str(p)
    s = normalized
    if s in (".", "./", ""):
        return "./"
    if not s.startswith(".") and not s.startswith("/"):
        s = "./" + s
    return s


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
        raw = getattr(service.docker, "dockerfiles", []) or []
        normalized = []
        for df in raw:
            if isinstance(df, dict):
                entry = dict(df)
                entry.setdefault("context", str(service.path))
                normalized.append(entry)
                continue
            s = str(df)
            if os.path.isabs(s) or ("/" in s or os.path.sep in s):
                dockerfile_path = s
            else:
                dockerfile_path = str(service.path.joinpath(s))
            normalized.append(
                {"dockerfile": dockerfile_path, "context": str(service.path)}
            )

        return {
            "has_dockerfiles": len(normalized) > 0,
            "dockerfiles": normalized,
            "image_name": service.name,
        }

    def get_service_config(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> Dict[str, Any]:
        """Get service configuration for monorepo pipeline.

        Override in subclasses to provide language-specific configuration.
        """
        stages = self.get_stages(service, deployment)
        return {
            "service": service,
            "stages": stages,
            "has_lint": "lint" in stages,
            "has_test": "test" in stages,
            "has_build": "build" in stages,
            "has_docker": len(service.docker.dockerfiles) > 0,
            "dockerfiles": service.docker.dockerfiles,
            "lint_image": "alpine:latest",
            "test_image": "alpine:latest",
            "build_image": "alpine:latest",
            "lint_command": "echo 'No lint configured'",
            "test_command": service.tests or "echo 'No tests'",
            "build_commands": ["echo 'No build configured'"],
            "before_script": None,
            "cache": None,
            "coverage_regex": "/coverage: \\d+.\\d+%/",
            "artifacts_path": "build/",
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
                [f"go build -o bin/{service.name} {_repo_relative(ep, service)}" for ep in service.entrypoints]
                if service.entrypoints
                else [f"go build -o bin/{service.name} {_repo_relative(str(service.path) + '/...', service)}"]
            ),
            **self.get_docker_context(service),
        }
        return self.render_template("go.gitlab-ci.yml.j2", context)

    def get_service_config(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> Dict[str, Any]:
        go_version = service.lang.version or "1.21"
        stages = self.get_stages(service, deployment)

        def _service_relative(pth: str) -> str:
            if not pth:
                return "./"
            wildcard = ""
            if pth.endswith("/..."):
                wildcard = "/..."
                pth = pth[:-4]
            p = Path(pth)
            if p.is_absolute():
                return str(p) + wildcard
            parts = [pp for pp in p.parts if pp and pp != "."]
            svc_parts = [pp for pp in Path(str(service.path)).parts if pp and pp != "."]
            if svc_parts and parts[: len(svc_parts)] == svc_parts:
                parts = parts[len(svc_parts) :]
            res = os.path.join(*parts) if parts else "."
            if not res.startswith(".") and not res.startswith("/"):
                res = "./" + res
            return res + wildcard

        return {
            "service": service,
            "stages": stages,
            "has_lint": "lint" in stages,
            "has_test": "test" in stages,
            "has_build": "build" in stages,
            "has_docker": len(service.docker.dockerfiles) > 0,
            "dockerfiles": service.docker.dockerfiles,
            "lint_image": "golangci/golangci-lint:latest",
            "test_image": f"golang:{go_version}-alpine",
            "build_image": f"golang:{go_version}-alpine",
            "lint_command": "golangci-lint run ./...",
            "test_command": service.tests or "go test ./...",
            "build_commands": (
                [f"go build -o bin/{service.name} {_service_relative(ep)}" for ep in service.entrypoints]
                if service.entrypoints
                else [f"go build -o bin/{service.name} ./..."]
            ),
            "before_script": "- go mod download",
            "cache": "- .cache/go/pkg/mod/",
            "coverage_regex": "/coverage: \\d+.\\d+% of statements/",
            "artifacts_path": "bin/",
        }


class PythonPipelineBuilder(PipelineBuilder):
    """Pipeline builder for Python projects."""

    def generate(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> str:
        package_manager = service.dependencies.packet_manager

        has_lint = len(service.linters) > 0
        has_test = bool(service.tests)

        svc_dir = _repo_relative(str(service.path), service)
        prefix = f"cd {svc_dir} && " if svc_dir not in ("./", "./.") and not svc_dir.startswith("/") else ""

        if package_manager == "poetry":
            install_cmd = prefix + "poetry install"
            lint_cmd = prefix + "poetry run ruff check . && poetry run mypy ."
            format_cmd = prefix + "poetry run ruff format --check . && poetry run black --check ."
            test_cmd = (
                prefix + (f"poetry run {service.tests}" if service.tests else "poetry run pytest")
            )
        else:  # pip
            install_cmd = prefix + "pip install -r requirements.txt"
            lint_cmd = prefix + "ruff check . && mypy ."
            format_cmd = prefix + "ruff format --check . && black --check ."
            test_cmd = prefix + (service.tests or "pytest")
        stages = self.get_stages(service, deployment)
        context = {
            "service": service,
            "python_version": service.lang.version or "3.11",
            "stages": stages,
            "package_manager": package_manager,
            "install_command": install_cmd,
            "lint_command": lint_cmd,
            "format_command": format_cmd,
            "test_command": test_cmd,
            "has_lint": has_lint,
            "has_test": has_test,
            **self.get_docker_context(service),
        }
        return self.render_template("python.gitlab-ci.yml.j2", context)

    def get_service_config(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> Dict[str, Any]:
        python_version = service.lang.version or "3.11"
        package_manager = service.dependencies.packet_manager
        stages = self.get_stages(service, deployment)

        if package_manager == "poetry":
            before_script = """- pip install poetry
- poetry config virtualenvs.in-project true
- poetry install"""
            lint_cmd = "poetry run ruff check . && poetry run mypy ."
            test_cmd = f"poetry run {service.tests}" if service.tests else "poetry run pytest"
        else:
            before_script = """- pip install ruff mypy pytest
- pip install -r requirements.txt"""
            lint_cmd = "ruff check . && mypy ."
            test_cmd = service.tests or "pytest"

        return {
            "service": service,
            "stages": stages,
            "has_lint": True,  # Always lint Python
            "has_test": "test" in stages,
            "has_build": False,  # Python typically doesn't have build stage
            "has_docker": len(service.docker.dockerfiles) > 0,
            "dockerfiles": service.docker.dockerfiles,
            "lint_image": f"python:{python_version}-slim",
            "test_image": f"python:{python_version}-slim",
            "build_image": f"python:{python_version}-slim",
            "lint_command": lint_cmd,
            "test_command": test_cmd,
            "build_commands": [],
            "before_script": before_script,
            "cache": "- .cache/pip/\n- .venv/",
            "coverage_regex": "/TOTAL.*\\s+(\\d+%)$/",
            "artifacts_path": "dist/",
        }

    def get_stages(
        self, service: Optional[Service] = None, deployment: Optional[Deployment] = None
    ) -> List[str]:

        stages: List[str] = []

        stages.append("lint")

        if service and service.tests and "echo" not in service.tests.lower():
            stages.append("test")

        if service and len(service.docker.dockerfiles) > 0:
            stages.append("docker")

        extra = self.extra_stages(service, deployment)
        for st in extra:
            if st not in stages:
                stages.append(st)

        return stages


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

        has_test = bool(service.tests) and "echo" not in service.tests.lower()

        svc_dir = _repo_relative(str(service.path), service)
        prefix = f"cd {svc_dir} && " if svc_dir not in ("./", "./.") and not svc_dir.startswith("/") else ""

        if package_manager == "yarn":
            install_cmd = prefix + "yarn install --frozen-lockfile"
            lint_cmd = prefix + "yarn lint"
            test_cmd = prefix + "yarn test"
            build_cmd = prefix + "yarn build"
        elif package_manager == "pnpm":
            install_cmd = prefix + "pnpm install --no-frozen-lockfile"
            lint_cmd = prefix + "pnpm lint"
            test_cmd = prefix + "pnpm test"
            build_cmd = prefix + "pnpm build"
        else:  # npm
            install_cmd = prefix + "npm install --prefer-offline --no-audit"
            lint_cmd = prefix + "npm run lint"
            test_cmd = prefix + "npm test"
            build_cmd = prefix + "npm run build"


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

    def get_service_config(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> Dict[str, Any]:
        node_version = service.lang.version or "20"
        package_manager = service.dependencies.packet_manager
        stages = self.get_stages(service, deployment)
        has_test = bool(service.tests) and "echo" not in service.tests.lower()

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
        else:
            install_cmd = "npm install --prefer-offline --no-audit"
            lint_cmd = "npm run lint"
            test_cmd = "npm test"
            build_cmd = "npm run build"

        return {
            "service": service,
            "stages": stages,
            "has_lint": len(service.linters) > 0,
            "has_test": has_test,
            "has_build": "build" in stages,
            "has_docker": len(service.docker.dockerfiles) > 0,
            "dockerfiles": service.docker.dockerfiles,
            "lint_image": f"node:{node_version}-alpine",
            "test_image": f"node:{node_version}-alpine",
            "build_image": f"node:{node_version}-alpine",
            "lint_command": lint_cmd,
            "test_command": service.tests or test_cmd,
            "build_commands": [build_cmd],
            "before_script": f"- {install_cmd}",
            "cache": "- node_modules/",
            "coverage_regex": "/All files.*?\\s+(\\d+\\.?\\d*)\\s/",
            "artifacts_path": "dist/",
        }


class JavaPipelineBuilder(PipelineBuilder):
    """Pipeline builder for Java projects."""

    def generate(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> str:
        package_manager = service.dependencies.package_manager
        has_lint = len(service.linters) > 0
        has_test = bool(service.tests)

        svc_dir = _repo_relative(str(service.path), service)
        prefix = f"cd {svc_dir} && " if svc_dir not in ("./", "./.") and not svc_dir.startswith("/") else ""

        if "gradle" in package_manager.lower():
            build_cmd = prefix + "./gradlew build"
            test_cmd = prefix + "./gradlew test"
            lint_cmd = prefix + "./gradlew checkstyleMain"
        else:  # maven
            build_cmd = prefix + "mvn package -DskipTests"
            test_cmd = prefix + "mvn test"
            lint_cmd = prefix + "mvn checkstyle:check"

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

    def get_service_config(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> Dict[str, Any]:
        java_version = service.lang.version or "17"
        package_manager = service.dependencies.packet_manager
        stages = self.get_stages(service, deployment)

        if "gradle" in package_manager.lower():
            build_cmd = "./gradlew build"
            test_cmd = "./gradlew test"
            lint_cmd = "./gradlew checkstyleMain"
        else:
            build_cmd = "mvn package -DskipTests"
            test_cmd = "mvn test"
            lint_cmd = "mvn checkstyle:check"

        return {
            "service": service,
            "stages": stages,
            "has_lint": len(service.linters) > 0,
            "has_test": "test" in stages,
            "has_build": "build" in stages,
            "has_docker": len(service.docker.dockerfiles) > 0,
            "dockerfiles": service.docker.dockerfiles,
            "lint_image": (
                f"maven:{java_version}-eclipse-temurin"
                if "maven" in package_manager.lower()
                else f"gradle:{java_version}-jdk"
            ),
            "test_image": (
                f"maven:{java_version}-eclipse-temurin"
                if "maven" in package_manager.lower()
                else f"gradle:{java_version}-jdk"
            ),
            "build_image": (
                f"maven:{java_version}-eclipse-temurin"
                if "maven" in package_manager.lower()
                else f"gradle:{java_version}-jdk"
            ),
            "lint_command": lint_cmd,
            "test_command": service.tests or test_cmd,
            "build_commands": [build_cmd],
            "before_script": None,
            "cache": (
                "- .m2/repository/"
                if "maven" in package_manager.lower()
                else "- .gradle/"
            ),
            "coverage_regex": "/Total.*?(\\d+%)/",
            "artifacts_path": (
                "target/" if "maven" in package_manager.lower() else "build/libs/"
            ),
        }


class KotlinPipelineBuilder(PipelineBuilder):
    """Pipeline builder for Kotlin projects."""

    def generate(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> str:
        package_manager = service.dependencies.packet_manager
        has_lint = len(service.linters) > 0
        has_test = bool(service.tests)

        svc_dir = _repo_relative(str(service.path), service)
        prefix = f"cd {svc_dir} && " if svc_dir not in ("./", "./.") and not svc_dir.startswith("/") else ""

        if "maven" in package_manager.lower():
            build_cmd = prefix + "mvn package -DskipTests"
            test_cmd = prefix + "mvn test"
            lint_cmd = prefix + "mvn detekt:check"
        else:
            build_cmd = prefix + "./gradlew build"
            test_cmd = prefix + "./gradlew test"
            lint_cmd = prefix + "./gradlew detekt"

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

    def get_service_config(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> Dict[str, Any]:
        java_version = service.lang.version or "17"
        package_manager = service.dependencies.packet_manager
        stages = self.get_stages(service, deployment)

        if "maven" in package_manager.lower():
            build_cmd = "mvn package -DskipTests"
            test_cmd = "mvn test"
            lint_cmd = "mvn detekt:check"
        else:
            build_cmd = "./gradlew build"
            test_cmd = "./gradlew test"
            lint_cmd = "./gradlew detekt"

        return {
            "service": service,
            "stages": stages,
            "has_lint": len(service.linters) > 0,
            "has_test": "test" in stages,
            "has_build": "build" in stages,
            "has_docker": len(service.docker.dockerfiles) > 0,
            "dockerfiles": service.docker.dockerfiles,
            "lint_image": f"gradle:{java_version}-jdk",
            "test_image": f"gradle:{java_version}-jdk",
            "build_image": f"gradle:{java_version}-jdk",
            "lint_command": lint_cmd,
            "test_command": service.tests or test_cmd,
            "build_commands": [build_cmd],
            "before_script": None,
            "cache": "- .gradle/",
            "coverage_regex": "/Total.*?(\\d+%)/",
            "artifacts_path": "build/libs/",
        }


class AndroidPipelineBuilder(PipelineBuilder):
    """Pipeline builder for Android projects."""

    def generate(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> str:
        """Generate GitLab CI pipeline for Android project."""
        if not service.android:
            raise ValueError("Service is not an Android project")

        android = service.android
        package_manager = service.dependencies.packet_manager
        has_lint = len(service.linters) > 0
        has_test = bool(service.tests) and "echo" not in service.tests.lower()

        build_variants = []
        if android.product_flavors:
            for flavor in android.product_flavors:
                # Capitalize first letter of flavor
                flavor_cap = flavor.capitalize() if flavor else ""
                for build_type in android.build_types:
                    build_type_cap = build_type.capitalize() if build_type else ""
                    build_variants.append(f"{flavor_cap}{build_type_cap}")
        else:
            # No flavors, just build types
            for build_type in android.build_types:
                build_variants.append(build_type.capitalize())


        build_commands = []
        for variant in build_variants:
            if package_manager == "gradle":
                gradlew_path = service.path / "gradlew"
                gradle_cmd = "./gradlew" if gradlew_path.exists() else "gradle"
                svc_dir = _repo_relative(str(service.path), service)
                prefix = f"cd {svc_dir} && " if svc_dir not in ("./", "./.") and not svc_dir.startswith("/") else ""
                build_commands.append(f"{prefix}{gradle_cmd} assemble{variant}")

        if package_manager == "gradle":
            gradlew_path = service.path / "gradlew"
            gradle_cmd = "./gradlew" if gradlew_path.exists() else "gradle"
            svc_dir = _repo_relative(str(service.path), service)
            prefix = f"cd {svc_dir} && " if svc_dir not in ("./", "./.") and not svc_dir.startswith("/") else ""
            lint_cmd = f"{prefix}{gradle_cmd} lint"
            test_cmd = service.tests or f"{prefix}{gradle_cmd} test"
        else:
            lint_cmd = "mvn checkstyle:check"
            test_cmd = service.tests or "mvn test"

        stages = self.get_stages(service, deployment)

        context = {
            "service": service,
            "java_version": service.lang.version or "17",
            "android": android,
            "stages": stages,
            "package_manager": package_manager,
            "lint_command": lint_cmd,
            "test_command": test_cmd,
            "build_commands": build_commands,
            "build_variants": build_variants,
            "has_lint": has_lint,
            "has_test": has_test,
            "has_signing": android.has_signing_config,
            **self.get_docker_context(service),
        }
        return self.render_template("android.gitlab-ci.yml.j2", context)

    def get_service_config(
        self, service: Service, deployment: Optional[Deployment] = None
    ) -> Dict[str, Any]:
        if not service.android:
            return super().get_service_config(service, deployment)

        android = service.android
        stages = self.get_stages(service, deployment)
        has_test = bool(service.tests) and "echo" not in service.tests.lower()

        gradlew_path = service.path / "gradlew"
        gradle_cmd = "./gradlew" if gradlew_path.exists() else "gradle"

        build_variants = []
        if android.product_flavors:
            for flavor in android.product_flavors:
                flavor_cap = flavor.capitalize() if flavor else ""
                for build_type in android.build_types:
                    build_type_cap = build_type.capitalize() if build_type else ""
                    build_variants.append(f"{flavor_cap}{build_type_cap}")
        else:
            for build_type in android.build_types:
                build_variants.append(build_type.capitalize())

        build_commands = [f"{gradle_cmd} assemble{v}" for v in build_variants]

        return {
            "service": service,
            "stages": stages,
            "has_lint": len(service.linters) > 0,
            "has_test": has_test,
            "has_build": True,
            "has_docker": False,  # Android apps don't use Docker
            "dockerfiles": [],
            "lint_image": f"circleci/android:api-{android.compile_sdk_version or '33'}",
            "test_image": f"circleci/android:api-{android.compile_sdk_version or '33'}",
            "build_image": f"circleci/android:api-{android.compile_sdk_version or '33'}",
            "lint_command": f"{gradle_cmd} lint",
            "test_command": service.tests or f"{gradle_cmd} test",
            "build_commands": build_commands,
            "before_script": None,
            "cache": "- .gradle/\n- ~/.android/",
            "coverage_regex": "/Total.*?(\\d+%)/",
            "artifacts_path": "app/build/outputs/apk/",
        }



class PipelineComposer:
    """Composer for generating GitLab CI pipelines"""

    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.template_dir = os.path.join(current_dir, "templates")
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.builders: Dict[str, PipelineBuilder] = {
            "go": GoPipelineBuilder(self.template_dir),
            "python": PythonPipelineBuilder(self.template_dir),
            "javascript": NodePipelineBuilder(self.template_dir),
            "typescript": NodePipelineBuilder(self.template_dir),
            "java": JavaPipelineBuilder(self.template_dir),
            "kotlin": KotlinPipelineBuilder(self.template_dir),
            "android": AndroidPipelineBuilder(self.template_dir),
        }

    def get_pipeline(self, service: Service) -> str:
        """Generate GitLab CI pipeline for a service."""
        builder = self.builders.get(service.lang.name)
        if not builder:
            raise ValueError(
                f"No pipeline builder found for language: {service.lang.name}"
            )
        return builder.generate(service)

    def generate_from_schema(
        self, schema: RepoSchema, deployment: Optional[Deployment] = None
    ) -> str:
        if not schema.services:
            raise ValueError("No services found in schema")

        if len(schema.services) == 1:
            return self.get_pipeline(schema.services[0])

        return self.get_multi_service_pipeline(
            schema.services, deployment or schema.deployment
        )

    def _convert_leading_underscore_keys_to_dot(self, yaml_str: str) -> str:
        return re.sub(r"(?m)^_([A-Za-z0-9_-]+)(\s*:)", r".\1\2", yaml_str)

    def get_multi_service_pipeline(
            self, services: List[Service], deployment: Optional[Deployment] = None
        ) -> str:

        all_stages: List[str] = []
        service_configs: List[Dict[str, Any]] = []

        stage_order = ["lint", "test", "build", "docker", "sign", "deploy", "s3"]

        for service in services:
            builder = self.builders.get(service.lang.name)
            if not builder:
                continue

            config = builder.get_service_config(service, deployment)
            raw_dfs = config.get("dockerfiles", []) or []
            normalized = []
            for df in raw_dfs:
                if isinstance(df, dict):
                    entry = dict(df)
                    if "context" not in entry:
                        entry.setdefault("context", str(service.path))
                    normalized.append(entry)
                    continue

                s = str(df)
                if os.path.isabs(s) or ("/" in s or os.path.sep in s):
                    dockerfile_path = s
                else:
                    dockerfile_path = str(service.path.joinpath(s))

                normalized.append(
                    {"dockerfile": dockerfile_path, "context": str(service.path)}
                )

            config["dockerfiles"] = normalized
            config["has_docker"] = len(normalized) > 0
            service_configs.append(config)

        common_prefix = None
        try:
            first_parts = [
                str(s.path).split(os.path.sep)[0] for s in services if str(s.path)
            ]
            if first_parts and all(p == first_parts[0] for p in first_parts):
                common_prefix = first_parts[0]
        except Exception:
            common_prefix = None

        if common_prefix:
            for cfg in service_configs:
                svc_obj = cfg.get("service")
                svc_path = str(svc_obj.path)
                if svc_path.startswith(common_prefix + os.path.sep):
                    display_path = svc_path[len(common_prefix + os.path.sep) :]
                else:
                    display_path = svc_path
                cfg["display_path"] = display_path

                dfs = cfg.get("dockerfiles", []) or []
                adjusted = []
                for df in dfs:
                    df_path = df.get("dockerfile") if isinstance(df, dict) else str(df)
                    if df_path.startswith(common_prefix + os.path.sep):
                        df_path_adj = df_path[len(common_prefix + os.path.sep) :]
                    else:
                        df_path_adj = df_path
                    ctx = df.get("context") if isinstance(df, dict) else svc_path
                    if isinstance(ctx, str) and ctx.startswith(common_prefix + os.path.sep):
                        ctx_adj = ctx[len(common_prefix + os.path.sep) :]
                    else:
                        ctx_adj = display_path
                    adjusted.append({"dockerfile": df_path_adj, "context": ctx_adj})
                cfg["dockerfiles"] = adjusted

        for cfg in service_configs:
            for st in cfg.get("stages", []):
                if st not in all_stages:
                    all_stages.append(st)

        all_stages = sorted(
            all_stages,
            key=lambda s: (stage_order.index(s) if s in stage_order else len(stage_order)),
        )

        if not service_configs:
            raise ValueError("No valid services found for pipeline generation")

        template = self.env.get_template("monorepo.gitlab-ci.yml.j2")
        rendered = template.render(
            services=services,
            stages=all_stages,
            service_configs=service_configs,
            deployment=deployment,
        )

        rendered = self._convert_leading_underscore_keys_to_dot(rendered)
        return rendered

    def get_pipeline_for_services(
        self, services: List[Service], deployment: Optional[Deployment] = None
    ) -> str:
        """Alias for get_multi_service_pipeline for backward compatibility."""
        if len(services) == 1:
            return self.get_pipeline(services[0])
        return self.get_multi_service_pipeline(services, deployment)
