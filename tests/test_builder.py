from pathlib import Path
from larek.models.repo import Service, Language, Dependencies, Lib
from larek.composer.builder import Composer


def test_go_builder():
    service = Service(
        path=Path("/tmp/go-app"),
        name="go-service",
        lang=Language(name="go", version="1.21"),
        dependencies=Dependencies(packet_manager="go mod", libs=[]),
        configs=[],
        dockerfile="",
        entrypoint="./cmd/main.go",
        tests="go test ./...",
        linters=[],
    )
    composer = Composer()
    dockerfile = composer.get_dockerfile(service)
    print("=== Go Dockerfile ===")
    print(dockerfile)
    print("=====================\n")


def test_python_builder():
    service = Service(
        path=Path("/tmp/py-app"),
        name="python-service",
        lang=Language(name="python", version="3.11"),
        dependencies=Dependencies(packet_manager="poetry", libs=[]),
        configs=[],
        dockerfile="",
        entrypoint="python main.py",
        tests="pytest",
        linters=[],
    )
    composer = Composer()
    dockerfile = composer.get_dockerfile(service)
    print("=== Python Dockerfile ===")
    print(dockerfile)
    print("=========================\n")


def test_node_spa_builder():
    # Mocking a React dependency
    react_lib = Lib(name="react", version="18.0.0")

    service = Service(
        path=Path("/tmp/node-spa"),
        name="react-app",
        lang=Language(name="typescript", version="5.0"),
        dependencies=Dependencies(packet_manager="npm", libs=[react_lib]),
        configs=[],
        dockerfile="",
        entrypoint="npm start",
        tests="npm test",
        linters=[],
    )
    composer = Composer()
    dockerfile = composer.get_dockerfile(service)
    print("=== Node SPA Dockerfile ===")
    print(dockerfile)
    print("===========================\n")


def test_node_app_builder():
    service = Service(
        path=Path("/tmp/node-app"),
        name="express-app",
        lang=Language(name="javascript", version="20"),
        dependencies=Dependencies(packet_manager="npm", libs=[]),
        configs=[],
        dockerfile="",
        entrypoint="npm start",
        tests="npm test",
        linters=[],
    )
    composer = Composer()
    dockerfile = composer.get_dockerfile(service)
    print("=== Node App Dockerfile ===")
    print(dockerfile)
    print("===========================\n")


if __name__ == "__main__":
    try:
        test_go_builder()
        test_python_builder()
        test_node_spa_builder()
        test_node_app_builder()
    except Exception as e:
        print(f"Error: {e}")
