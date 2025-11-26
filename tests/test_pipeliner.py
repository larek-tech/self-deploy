from pathlib import Path
from larek.models.repo import Service, Language, Dependencies, Lib
from larek.pipeliner import PipelineComposer


def test_go_pipeline():
    service = Service(
        path=Path("/tmp/go-app"),
        name="go-service",
        lang=Language(name="go", version="1.21"),
        dependencies=Dependencies(packet_manager="go mod", libs=[]),
        configs=[],
        docker=[],
        entrypoints=["./cmd/main.go"],
        tests="go test ./...",
        linters=[],
    )
    composer = PipelineComposer()
    pipeline = composer.get_pipeline(service)
    print("=== Go GitLab CI Pipeline ===")
    print(pipeline)
    print("=============================\n")
    assert "golangci-lint" in pipeline
    assert "go test" in pipeline


def test_python_poetry_pipeline():
    service = Service(
        path=Path("/tmp/py-app"),
        name="python-service",
        lang=Language(name="python", version="3.11"),
        dependencies=Dependencies(packet_manager="poetry", libs=[]),
        configs=[],
        docker=[],
        entrypoints=["python main.py"],
        tests="pytest",
        linters=[],
    )
    composer = PipelineComposer()
    pipeline = composer.get_pipeline(service)
    print("=== Python (Poetry) GitLab CI Pipeline ===")
    print(pipeline)
    print("==========================================\n")
    assert "poetry" in pipeline
    assert "pytest" in pipeline


def test_python_pip_pipeline():
    service = Service(
        path=Path("/tmp/py-app"),
        name="python-pip-service",
        lang=Language(name="python", version="3.12"),
        dependencies=Dependencies(packet_manager="pip", libs=[]),
        configs=[],
        docker=[],
        entrypoints=["python main.py"],
        tests="pytest tests/",
        linters=[],
    )
    composer = PipelineComposer()
    pipeline = composer.get_pipeline(service)
    print("=== Python (pip) GitLab CI Pipeline ===")
    print(pipeline)
    print("=======================================\n")
    assert "pip install" in pipeline
    assert "pytest tests/" in pipeline


def test_node_npm_pipeline():
    service = Service(
        path=Path("/tmp/node-app"),
        name="express-app",
        lang=Language(name="javascript", version="20"),
        dependencies=Dependencies(packet_manager="npm", libs=[]),
        configs=[],
        docker=[],
        entrypoints=["npm start"],
        tests="npm test",
        linters=[],
    )
    composer = PipelineComposer()
    pipeline = composer.get_pipeline(service)
    print("=== Node.js (npm) GitLab CI Pipeline ===")
    print(pipeline)
    print("========================================\n")
    assert "npm ci" in pipeline
    assert "npm test" in pipeline


def test_node_spa_pipeline():
    react_lib = Lib(name="react", version="18.0.0")
    service = Service(
        path=Path("/tmp/react-app"),
        name="react-app",
        lang=Language(name="typescript", version="20"),
        dependencies=Dependencies(packet_manager="npm", libs=[react_lib]),
        configs=[],
        docker=[],
        entrypoints=["npm start"],
        tests="npm test",
        linters=[],
    )
    composer = PipelineComposer()
    pipeline = composer.get_pipeline(service)
    print("=== React SPA GitLab CI Pipeline ===")
    print(pipeline)
    print("====================================\n")
    assert "npm run build" in pipeline
    assert "tsc --noEmit" in pipeline  # TypeScript check


def test_java_maven_pipeline():
    service = Service(
        path=Path("/tmp/java-app"),
        name="java-maven-app",
        lang=Language(name="java", version="17"),
        dependencies=Dependencies(packet_manager="maven", libs=[]),
        configs=[],
        docker=[],
        entrypoints=["java -jar app.jar"],
        tests="mvn test",
        linters=[],
    )
    composer = PipelineComposer()
    pipeline = composer.get_pipeline(service)
    print("=== Java (Maven) GitLab CI Pipeline ===")
    print(pipeline)
    print("=======================================\n")
    assert "mvn" in pipeline
    assert "eclipse-temurin:17-jdk" in pipeline


def test_java_gradle_pipeline():
    service = Service(
        path=Path("/tmp/java-app"),
        name="java-gradle-app",
        lang=Language(name="java", version="21"),
        dependencies=Dependencies(packet_manager="gradle", libs=[]),
        configs=[],
        docker=[],
        entrypoints=["java -jar app.jar"],
        tests="./gradlew test",
        linters=[],
    )
    composer = PipelineComposer()
    pipeline = composer.get_pipeline(service)
    print("=== Java (Gradle) GitLab CI Pipeline ===")
    print(pipeline)
    print("========================================\n")
    assert "gradlew" in pipeline
    assert "eclipse-temurin:21-jdk" in pipeline


def test_kotlin_pipeline():
    service = Service(
        path=Path("/tmp/kotlin-app"),
        name="kotlin-app",
        lang=Language(name="kotlin", version="17"),
        dependencies=Dependencies(packet_manager="gradle", libs=[]),
        configs=[],
        docker=[],
        entrypoints=["java -jar app.jar"],
        tests="./gradlew test",
        linters=[],
    )
    composer = PipelineComposer()
    pipeline = composer.get_pipeline(service)
    print("=== Kotlin GitLab CI Pipeline ===")
    print(pipeline)
    print("=================================\n")
    assert "detekt" in pipeline
    assert "gradlew" in pipeline


def test_go_pipeline_with_docker():
    """Test Go pipeline with Docker build and push to Nexus."""
    service = Service(
        path=Path("/tmp/go-app"),
        name="go-service",
        lang=Language(name="go", version="1.21"),
        dependencies=Dependencies(packet_manager="go mod", libs=[]),
        configs=[],
        docker=["Dockerfile"],
        entrypoints=["./cmd/main.go"],
        tests="go test ./...",
        linters=[],
    )
    composer = PipelineComposer()
    pipeline = composer.get_pipeline(service)
    print("=== Go GitLab CI Pipeline with Docker ===")
    print(pipeline)
    print("=========================================\n")
    assert "golangci-lint" in pipeline
    assert "docker" in pipeline
    assert "NEXUS_REGISTRY" in pipeline
    assert "docker-build-1" in pipeline
    assert "CI_COMMIT_REF_SLUG" in pipeline
    assert "CI_COMMIT_SHORT_SHA" in pipeline


def test_python_pipeline_with_multiple_dockerfiles():
    """Test Python pipeline with multiple Dockerfiles."""
    service = Service(
        path=Path("/tmp/py-app"),
        name="python-service",
        lang=Language(name="python", version="3.11"),
        dependencies=Dependencies(packet_manager="poetry", libs=[]),
        configs=[],
        docker=["Dockerfile", "Dockerfile.worker"],
        entrypoints=["python main.py"],
        tests="pytest",
        linters=[],
    )
    composer = PipelineComposer()
    pipeline = composer.get_pipeline(service)
    print("=== Python Pipeline with Multiple Dockerfiles ===")
    print(pipeline)
    print("=================================================\n")
    assert "docker-build-1" in pipeline
    assert "docker-build-2" in pipeline
    assert "Dockerfile.worker" in pipeline


def test_node_pipeline_with_docker():
    """Test Node.js pipeline with Docker build."""
    service = Service(
        path=Path("/tmp/node-app"),
        name="express-app",
        lang=Language(name="javascript", version="20"),
        dependencies=Dependencies(packet_manager="npm", libs=[]),
        configs=[],
        docker=["Dockerfile"],
        entrypoints=["npm start"],
        tests="npm test",
        linters=[],
    )
    composer = PipelineComposer()
    pipeline = composer.get_pipeline(service)
    print("=== Node.js Pipeline with Docker ===")
    print(pipeline)
    print("====================================\n")
    assert "docker" in pipeline
    assert "NEXUS_REGISTRY" in pipeline
    assert "express-app" in pipeline


if __name__ == "__main__":
    try:
        test_go_pipeline()
        test_python_poetry_pipeline()
        test_python_pip_pipeline()
        test_node_npm_pipeline()
        test_node_spa_pipeline()
        test_java_maven_pipeline()
        test_java_gradle_pipeline()
        test_kotlin_pipeline()
        # Docker tests
        test_go_pipeline_with_docker()
        test_python_pipeline_with_multiple_dockerfiles()
        test_node_pipeline_with_docker()
        print("All pipeline tests passed!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
