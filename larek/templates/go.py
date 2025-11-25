"""Шаблон для Go проектов."""

from pathlib import Path

from larek.templates.base import LanguageTemplate


class GoTemplate(LanguageTemplate):
    """Шаблон для Go проектов."""

    @property
    def name(self) -> str:
        return "go"

    @property
    def extensions(self) -> list[str]:
        return [".go"]

    @property
    def package_managers(self) -> list[str]:
        return ["go mod"]

    @property
    def default_linters(self) -> list[str]:
        return ["golangci-lint"]

    def create_structure(self, project_path: Path, project_name: str) -> None:
        """Создать структуру Go проекта."""
        # Основные директории
        dirs = [
            project_path / "cmd" / project_name,
            project_path / "internal",
            project_path / "pkg",
            project_path / "api",
            project_path / "configs",
            project_path / "docs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # go.mod
        go_mod = f"""module github.com/example/{project_name}

go 1.22
"""
        (project_path / "go.mod").write_text(go_mod)

        # main.go
        main_go = f"""package main

import "fmt"

func main() {{
    fmt.Println("Hello from {project_name}!")
}}
"""
        (project_path / "cmd" / project_name / "main.go").write_text(main_go)

        # README.md
        (project_path / "README.md").write_text(f"# {project_name}\n\n")

        # .gitignore
        gitignore = """# Binaries
*.exe
*.exe~
*.dll
*.so
*.dylib
bin/

# Test binary
*.test

# Output
*.out

# Dependency directories
vendor/

# IDE
.idea/
.vscode/
"""
        (project_path / ".gitignore").write_text(gitignore)

        # golangci-lint config
        golangci = """run:
  timeout: 5m

linters:
  enable:
    - errcheck
    - gosimple
    - govet
    - ineffassign
    - staticcheck
    - unused
    - gofmt
    - goimports
"""
        (project_path / ".golangci.yml").write_text(golangci)

    def generate_dockerfile(self, version: str | None = None) -> str:
        """Сгенерировать Dockerfile для Go."""
        go_version = version or "1.22"
        return f"""FROM golang:{go_version}-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/bin/app ./cmd/app

FROM alpine:latest

WORKDIR /app
COPY --from=builder /app/bin/app .

CMD ["./app"]
"""

    def get_test_command(self) -> str:
        return "go test ./..."
