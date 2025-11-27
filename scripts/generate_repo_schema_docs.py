#!/usr/bin/env python3
"""Генератор Markdown-документации для Pydantic модели RepoSchema.

Скрипт импортирует модель `RepoSchema` из `larek.models.repo` и генерирует
`docs/auto_repo_schema.md` с таблицей полей, типами и описаниями.

Запуск:
    python scripts/generate_repo_schema_docs.py

"""

import pathlib
import sys
import json
from typing import Any, Dict

try:
    # Pydantic v2
    from pydantic import BaseModel
    from larek.models.repo import RepoSchema
    pydantic_v2 = True
except Exception:
    # Fallback for pydantic v1
    try:
        from larek.models.repo import RepoSchema  # type: ignore
        pydantic_v2 = False
    except Exception as e:
        print("Не удалось импортировать RepoSchema:", e, file=sys.stderr)
        raise

OUT = pathlib.Path("docs/auto_repo_schema.md")


def get_schema() -> Dict[str, Any]:
    """Возвращает словарь JSON-схемы модели в зависимости от версии Pydantic."""
    try:
        if pydantic_v2 and hasattr(RepoSchema, "model_json_schema"):
            return RepoSchema.model_json_schema()
        elif hasattr(RepoSchema, "schema"):
            return RepoSchema.schema()
        else:
            # Попробуем через BaseModel
            return RepoSchema.__pydantic_self__.model_json_schema()  # type: ignore
    except Exception:
        # Последняя попытка
        return RepoSchema.schema()  # type: ignore


def render_markdown(schema: Dict[str, Any]) -> str:
    lines = ["# RepoSchema — автосгенерированная документация", "", "Описание полей модели RepoSchema:", ""]

    props = schema.get("properties") or schema.get("definitions") or {}
    required = set(schema.get("required") or [])

    lines.append("| Поле | Тип | Обязательное | Описание |")
    lines.append("|---|---|---|---|")

    for name, info in props.items():
        t = info.get("type", "")
        desc = info.get("description", "")
        req = "Да" if name in required else "Нет"
        example = ""
        if "examples" in info:
            ex = info["examples"]
            if isinstance(ex, list) and ex:
                example = str(ex[0])
        if not example and "default" in info:
            example = str(info["default"])
        lines.append(f"| `{name}` | `{t}` | {req} | {desc} |")

    # Добавим раздел с JSON-примером
    try:
        example_obj = {}
        for name, info in props.items():
            if "default" in info:
                example_obj[name] = info.get("default")
            elif "examples" in info and isinstance(info["examples"], list):
                example_obj[name] = info["examples"][0]
            else:
                example_obj[name] = None

        lines.append("\n## Пример JSON (скелет)")
        lines.append("```json")
        lines.append(json.dumps(example_obj, indent=2, ensure_ascii=False))
        lines.append("```")
    except Exception:
        pass

    return "\n".join(lines)


def main() -> int:
    schema = get_schema()
    md = render_markdown(schema)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(md, encoding="utf-8")
    print(f"Сгенерирован {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
