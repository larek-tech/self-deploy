# Self-deploy by larek.tech

## Инфраструктура проекта

### Gitlab comunity edition

www
login: admin
password: SuperSecurePassword123

### Nexus

w### SonarQube

## Структура проекта

```
self-deploy/
├── pyproject.toml          # Конфигурация Poetry и зависимости
├── readme.md               # Документация проекта
├── setup.sh                # Скрипт инициализации инфраструктуры
├── docker-compose.yaml     # Конфигурация Docker сервисов
├── .gitignore              # Игнорируемые файлы Git
│
├── larek/                  # Основной пакет CLI приложения
│   ├── __init__.py         # Инициализация пакета, версия
│   ├── main.py             # Точка входа CLI (Typer app)
│   ├── config.py           # Конфигурация приложения
│   │
│   ├── commands/           # Команды CLI
│   │   ├── __init__.py
│   │   ├── init.py         # Команда инициализации проекта
│   │   └── status.py       # Команда проверки статуса
│   │
│   └── utils/              # Вспомогательные утилиты
│       ├── __init__.py
│       └── docker.py       # Утилиты для работы с Docker
│
├── gitlab/                 # Данные GitLab
│   ├── config/             # Конфигурация GitLab
│   ├── data/               # Данные GitLab
│   └── logs/               # Логи GitLab
│
├── gitlab-runner/          # Конфигурация GitLab Runner
│   └── config/
│
└── nexus-data/             # Данные Nexus
```

## Установка и использование

### Требования

-   Python 3.12+
-   Poetry
-   Docker и Docker Compose

### Установка зависимостей

```bash
poetry install
```

### Запуск инфраструктуры

```bash
chmod +x setup.sh
./setup.sh
```

### Использование CLI

```bash
# Активация виртуального окружения
poetry shell

# Проверка статуса сервисов
larek status

# Инициализация проекта из репозитория
larek init <ссылка на репозиторий>

# Справка
larek --help
```

## Разработка

### Структура команд CLI

CLI построен на базе [Typer](https://typer.tiangolo.com/) - современном фреймворке для создания CLI приложений на Python.

#### Добавление новой команды

1. Создайте файл в `larek/commands/`
2. Определите команду с помощью декоратора `@app.command()`
3. Зарегистрируйте команду в `larek/main.py`

### Запуск тестов

```bash
poetry run pytest
```

### Линтинг

```bash
poetry run ruff check .
```

## Локальный запуск

```bash
chmod +x setup.sh

./setup.sh

larek init <ссылка на репозиторий>
```
