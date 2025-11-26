from pathlib import Path
import json
import yaml


from larek.models.repo import (
    RepoSchema,
    Service,
    Language,
    Config,
    Linter,
    Dependencies,
)


def collect_go_app_data():

    service_path = Path("sample/go/go-app")

    go_service = Service(
        path=service_path,
        name="go-app",
        lang=Language(name="go", version="1.21"),
        dependencies=Dependencies(packet_manager="go mod", libs=[]),
        configs=[
            Config(name="sonar", path=str(service_path / "sonar-project.properties")),
            Config(name="jenkins", path=str(service_path / "Jenkinsfile")),
        ],
        dockerfiles=[str(service_path / "Dockerfile")],
        entrypoints=["main.go"],
        tests="go test ./...",
        linters=[
            Linter(
                name="sonarqube", config=str(service_path / "sonar-project.properties")
            )
        ],
    )
    larek_build_file = service_path / ".larek/build.yaml"
    repo_data = RepoSchema(services=[go_service])

    print("Collected Repo Data:")
    print(repo_data.model_dump_json(indent=2))
    build_file = yaml.dump(json.loads(repo_data.model_dump_json()))

    with open(larek_build_file, "w", encoding="utf-8") as file:
        file.write(build_file)


if __name__ == "__main__":
    collect_go_app_data()
