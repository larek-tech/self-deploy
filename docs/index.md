# self-deploy — документация

Добро пожаловать в документацию проекта self-deploy (larek).

Здесь вы найдёте описание формата `.larek/build.yaml`, структуру репозитория, пошаговую инструкцию по работе команды `larek init`, инструкцию по развёртыванию CI/CD с помощью Ansible и автоматический генератор документации для Pydantic-модели `RepoSchema`.

Навигация слева ведёт к подробным разделам.

Краткий quickstart:

1. Установите зависимости для разработки и документации:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-docs.txt
```

2. Сгенерируйте автодок (если нужно):

```bash
python scripts/generate_repo_schema_docs.py
```

3. Запустите предпросмотр:

```bash
mkdocs serve
```


