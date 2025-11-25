"""Шаблон для JavaScript/TypeScript проектов."""

from pathlib import Path

from larek.templates.base import LanguageTemplate


class JavaScriptTemplate(LanguageTemplate):
    """Шаблон для JavaScript/TypeScript проектов."""

    def __init__(self, typescript: bool = True):
        self._typescript = typescript

    @property
    def name(self) -> str:
        return "typescript" if self._typescript else "javascript"

    @property
    def extensions(self) -> list[str]:
        if self._typescript:
            return [".ts", ".tsx", ".js", ".jsx"]
        return [".js", ".jsx"]

    @property
    def package_managers(self) -> list[str]:
        return ["npm", "yarn", "pnpm", "bun"]

    @property
    def default_linters(self) -> list[str]:
        return ["eslint", "prettier"]

    def create_structure(self, project_path: Path, project_name: str) -> None:
        """Создать структуру JS/TS проекта."""
        # Основные директории
        dirs = [
            project_path / "src",
            project_path / "tests",
            project_path / "docs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # package.json
        package_json = f'''{{
  "name": "{project_name}",
  "version": "0.1.0",
  "description": "",
  "main": "dist/index.js",
  "scripts": {{
    "build": "{"tsc" if self._typescript else "echo 'No build step'"}",
    "start": "node dist/index.js",
    "dev": "{"ts-node src/index.ts" if self._typescript else "node src/index.js"}",
    "test": "jest",
    "lint": "eslint src/",
    "format": "prettier --write src/"
  }},
  "devDependencies": {{
    {"\"typescript\": \"^5.0\"," if self._typescript else ""}
    {"\"@types/node\": \"^20\"," if self._typescript else ""}
    {"\"ts-node\": \"^10\"," if self._typescript else ""}
    "eslint": "^9.0",
    "prettier": "^3.0",
    "jest": "^29.0"
  }}
}}
'''
        (project_path / "package.json").write_text(package_json)

        # index file
        if self._typescript:
            index_content = '''console.log("Hello, TypeScript!");
'''
            (project_path / "src" / "index.ts").write_text(index_content)

            # tsconfig.json
            tsconfig = '''{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
'''
            (project_path / "tsconfig.json").write_text(tsconfig)
        else:
            index_content = '''console.log("Hello, JavaScript!");
'''
            (project_path / "src" / "index.js").write_text(index_content)

        # README.md
        (project_path / "README.md").write_text(f"# {project_name}\n\n")

        # .gitignore
        gitignore = """node_modules/
dist/
.env
.env.local
*.log
npm-debug.log*
.DS_Store
coverage/
"""
        (project_path / ".gitignore").write_text(gitignore)

        # eslint.config.js
        eslint_config = '''export default [
  {
    rules: {
      "no-unused-vars": "warn",
      "no-console": "off"
    }
  }
];
'''
        (project_path / "eslint.config.js").write_text(eslint_config)

    def generate_dockerfile(self, version: str | None = None) -> str:
        """Сгенерировать Dockerfile для Node.js."""
        node_version = version or "20"
        return f'''FROM node:{node_version}-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
{"RUN npm run build" if self._typescript else ""}

FROM node:{node_version}-alpine

WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package*.json ./

CMD ["node", "dist/index.js"]
'''

    def get_test_command(self) -> str:
        return "npm test"
