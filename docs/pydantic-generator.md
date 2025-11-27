# Генерация документации из Pydantic (RepoSchema)

Запускайте этот скрипт перед сборкой документации (например, в CI), чтобы `docs/auto_repo_schema.md` всегда отражал актуальную модель.

```
python scripts/generate_repo_schema_docs.py
```bash

## Запуск

- Генерирует `docs/auto_repo_schema.md` с таблицей полей и примером JSON.
- Получает JSON-схему модели (`model_json_schema()` / `schema()`).
- Импортирует `RepoSchema` из `larek.models.repo`.

## Что делает скрипт

Файл скрипта: `scripts/generate_repo_schema_docs.py`

В проекте есть Pydantic-модель `RepoSchema` описывающая структуру файла `.larek/build.yaml`. Для поддержания документации в актуальном состоянии добавлен скрипт, который экспортирует схему модели в Markdown.


