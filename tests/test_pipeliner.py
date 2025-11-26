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
        dockerfiles=[],
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
        dockerfiles=[],
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
        dockerfiles=[],
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
        dockerfiles=[],
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
        dockerfiles=[],
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
        dockerfiles=[],
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
        dockerfiles=[],
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
        dockerfiles=[],
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
        print("All pipeline tests passed!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
