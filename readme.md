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
├── pyproject.toml              # Конфигурация Poetry и зависимости
├── readme.md                   # Документация проекта
├── setup.sh                    # Скрипт инициализации локальной инфраструктуры
├── docker-compose.yaml         # Конфигурация Docker сервисов
├── .gitignore                  # Игнорируемые файлы Git
│
├── larek/                      # Основной пакет CLI приложения
│   ├── __init__.py             # Инициализация пакета, версия
│   ├── main.py                 # Точка входа CLI (Typer app)
│   ├── config.py               # Конфигурация приложения
│   │
│   ├── commands/               # Команды CLI
│   │   ├── __init__.py
│   │   ├── login.py            # Авторизация в GitLab
│   │   ├── init.py             # Полная инициализация проекта
│   │   ├── clone.py            # Клонирование репозитория
│   │   ├── debug.py            # Отладка анализа репозитория
│   │   ├── docker.py           # Генерация Dockerfile
│   │   ├── gitlab.py           # Генерация gitlab-ci.yml
│   │   ├── status.py           # Проверка статуса сервисов
│   │   └── clear.py            # Очистка
│   │
│   ├── analyzer/               # Анализаторы проектов
│   │   ├── __init__.py
│   │   ├── base.py             # Базовый анализатор
│   │   ├── repo.py             # Анализатор репозитория
│   │   ├── go.py               # Анализатор Go проектов
│   │   ├── java.py             # Анализатор Java проектов
│   │   ├── kotlin.py           # Анализатор Kotlin проектов
│   │   ├── javascript.py       # Анализатор JavaScript проектов
│   │   └── python.py           # Анализатор Python проектов
│   │
│   ├── composer/               # Генерация Dockerfile
│   │   ├── builder.py          # Билдер Dockerfile
│   │   └── templates/          # Шаблоны Dockerfile
│   │
│   ├── pipeliner/              # Генерация CI/CD пайплайнов
│   │   ├── builder.py          # Билдер пайплайнов
│   │   └── templates/          # Шаблоны gitlab-ci.yml
│   │
│   ├── models/                 # Pydantic модели
│   │   ├── __init__.py
│   │   └── repo.py             # Схема репозитория
│   │
│   └── utils/                  # Вспомогательные утилиты
│       ├── __init__.py
│       ├── docker.py           # Утилиты для работы с Docker
│       ├── git_ops.py          # Git операции
│       ├── gitlab_auth.py      # Авторизация GitLab
│       └── local.py            # Локальные утилиты
│
├── gitlab-ansible-deployment/  # Ansible playbooks для удалённого развёртывания
│   ├── docker-compose-playbook.yml
│   ├── docker-compose-cleanup.yml
│   ├── inventory-prod.ini
│   ├── requirements.yml
│   └── group_vars/
│
├── tests/                      # Тесты
│
├── sample/                     # Примеры проектов для тестирования
│   ├── go/
│   ├── java/
│   ├── js/
│   └── python/
│
└── results/                    # Результаты анализа
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

# Справка
larek --help
```

## Команды CLI

### Основные команды (для работы)

#### `larek login`

Авторизация в GitLab с помощью Personal Access Token.

```bash
# Интерактивный режим (запросит URL и токен)
larek login

# С параметрами
larek login --url http://gitlab.local --token <YOUR_TOKEN>
larek login -u http://gitlab.local -t <YOUR_TOKEN>
```

**Что делает:**

-   Запрашивает URL GitLab сервера
-   Запрашивает Personal Access Token (необходимые права: `api`, `read_repository`, `write_repository`)
-   Проверяет валидность токена
-   Сохраняет токен локально для использования в других командах

---

#### `larek init`

Полная инициализация проекта из репозитория — анализ, генерация Dockerfile и CI/CD, пуш в GitLab.

```bash
# Инициализация из репозитория
larek init https://github.com/user/repo.git

# С указанием ветки
larek init https://github.com/user/repo.git --branch develop
larek init https://github.com/user/repo.git -b develop
```

**Что делает:**

1. Клонирует репозиторий (или использует текущую директорию)
2. Анализирует структуру проекта (Go, Java, Kotlin, JavaScript, Python)
3. Генерирует файл `.larek/build.yaml` с описанием сервисов
4. Генерирует Dockerfile для каждого сервиса
5. Генерирует `.gitlab-ci.yml` для CI/CD пайплайна
6. Создаёт проект в GitLab и пушит код

---

### Команды для отладки и отдельного запуска

#### `larek debug`

Анализ локального репозитория без генерации файлов и пуша.

```bash
# Анализ локальной директории
larek debug ./path/to/repo

# С указанием ветки
larek debug ./path/to/repo --branch main
```

**Что делает:**

-   Анализирует структуру проекта
-   Определяет язык программирования и фреймворки
-   Создаёт файл `.larek/build.yaml` с результатами анализа

---

#### `larek docker`

Генерация Dockerfile на основе файла `build.yaml`.

```bash
# Использование файла по умолчанию (.larek/build.yaml)
larek docker

# С указанием пути к build.yaml
larek docker ./custom/path/build.yaml
```

**Что делает:**

-   Читает конфигурацию из `build.yaml`
-   Генерирует Dockerfile для каждого сервиса
-   Выводит инструкции для сборки и запуска образа

---

#### `larek gitlab`

Генерация `.gitlab-ci.yml` на основе файла `build.yaml`.

```bash
# Использование файла по умолчанию (.larek/build.yaml)
larek gitlab

# С указанием пути к build.yaml
larek gitlab ./custom/path/build.yaml
```

**Что делает:**

-   Читает конфигурацию из `build.yaml`
-   Генерирует `.gitlab-ci.yml` с этапами сборки, тестирования и деплоя

---

### Дополнительные команды

#### `larek status`

Проверка статуса сервисов инфраструктуры.

```bash
larek status
```

#### `larek clear`

Очистка сгенерированных файлов.

```bash
larek clear
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

## Использование Docker образа

Рекомендуемый способ — использовать публичный образ из GitHub Container Registry:

```bash
# Скачиваем последний публичный образ
docker pull ghcr.io/larek-tech/larek:latest

# Показать справку
docker run --rm ghcr.io/larek-tech/larek:latest --help
```

Далее — удобные примеры запуска команд из образа (замените `ghcr.io/larek-tech/larek:latest` на нужный тег при необходимости).

1) Запуск команды `larek` с монтированием текущей директории как рабочей области:

```bash
# Монтируем текущую директорию в /workdir внутри контейнера
docker run --rm -it \
  -v "$(pwd)":/workdir -w /workdir \
  ghcr.io/larek-tech/larek:latest \
  larek init https://github.com/user/repo.git
```

2) Доступ к приватным репозиториям — два варианта (рекомендуется первый):

- A) Forward SSH agent (рекомендуемый, безопаснее, не копирует ключи в контейнер):

```bash
# Перед использованием убедитесь, что ssh-agent запущен и ключ добавлен (ssh-add)
# Пробрасываем сокет агента в контейнер
docker run --rm -it \
  -v "$(pwd)":/workdir -w /workdir \
  -v "$SSH_AUTH_SOCK":/ssh-agent \
  -e SSH_AUTH_SOCK=/ssh-agent \
  ghcr.io/larek-tech/larek:latest \
  larek init git@github.com:user/repo.git
```

- B) Монтирование приватного ключа (менее безопасно, простейший, если нет агента):

```bash
docker run --rm -it \
  -v "$(pwd)":/workdir -w /workdir \
  -v ~/.ssh:/root/.ssh:ro \
  ghcr.io/larek-tech/larek:latest \
  larek init git@github.com:user/repo.git
```

3) Сохранение файлов с корректными правами: запуск контейнера от вашего UID

```bash
docker run --rm -it \
  -u "$(id -u):$(id -g)" \
  -v "$(pwd)":/workdir -w /workdir \
  ghcr.io/larek-tech/larek:latest \
  larek docker
```

4) Использование переменных окружения / автоматизация логина

```bash
export GITLAB_TOKEN="<your_token>"
docker run --rm -it \
  -v "$(pwd)":/workdir -w /workdir \
  -e GITLAB_TOKEN="$GITLAB_TOKEN" \
  ghcr.io/larek-tech/larek:latest \
  larek login --url https://gitlab.example --token "$GITLAB_TOKEN"
```

5) Примечание для разработчиков (опция — локальная сборка образа)

Если вы разрабатываете `larek` и хотите собирать собственный образ локально, можно использовать `Dockerfile.larek`:

```bash
# Собрать локальный образ (для разработки)
docker build -f Dockerfile.larek -t larek-cli:local .
# Затем запускать его вместо публичного образа:
# docker run --rm -it -v "$(pwd)":/workdir -w /workdir larek-cli:local larek --help
```

6) Быстрые рекомендации и отладка

- Запустите контейнер с `-it` чтобы работать интерактивно.
- Если создаваемые файлы внутри контейнера появляются с root-владельцем, используйте `-u $(id -u):$(id -g)`.
- Для безопасного доступа к приватным репозиториям используйте SSH agent forwarding (вариант 2A).
- Если контейнеру нужен доступ к Docker (например, для запуска docker внутри контейнера), используйте docker-in-docker / монтирование `-v /var/run/docker.sock:/var/run/docker.sock` с осторожностью.

---

## Развёртывание на удалённом сервере (Ansible)

Для развёртывания инфраструктуры на удалённом сервере используется Ansible с Docker Compose.

### Требования для управляющей машины (откуда запускается Ansible)

-   Python 3.8+
-   Ansible 2.12+
-   SSH-доступ к удалённому серверу

### Требования для целевого сервера

-   Ubuntu 20.04+ / Debian 11+
-   SSH-доступ с ключом
-   Пользователь с правами `sudo`

### Установка Ansible и зависимостей

```bash
# Установка Ansible (macOS)
brew install ansible

# Установка Ansible (Ubuntu/Debian)
sudo apt update && sudo apt install ansible -y

# Установка необходимых коллекций Ansible
cd gitlab-ansible-deployment
ansible-galaxy collection install -r requirements.yml
```

### Настройка инвентаря

Отредактируйте файл `gitlab-ansible-deployment/inventory-prod.ini`:

```ini
[gitlab_servers]
gitlab-host ansible_host=<IP_СЕРВЕРА> ansible_user=<ПОЛЬЗОВАТЕЛЬ> ansible_ssh_private_key_file=~/.ssh/id_rsa
```

**Важно:** Между `key=value` не должно быть пробелов!

### Настройка sudo на удалённом сервере

Если у пользователя нет passwordless sudo, есть два варианта:

**Вариант 1:** Использовать флаг `--ask-become-pass` при запуске playbook (будет запрошен пароль sudo)

**Вариант 2:** Настроить passwordless sudo на сервере:

```bash
# На удалённом сервере
sudo visudo
# Добавить строку:
# <ПОЛЬЗОВАТЕЛЬ> ALL=(ALL) NOPASSWD: ALL
```

### Запуск развёртывания

```bash
cd gitlab-ansible-deployment

# С запросом пароля sudo
ansible-playbook -i inventory-prod.ini docker-compose-playbook.yml --ask-become-pass

# Без пароля (если настроен passwordless sudo)
ansible-playbook -i inventory-prod.ini docker-compose-playbook.yml
```

### Что будет развёрнуто

| Сервис          | URL                        | Логин | Пароль                 |
| --------------- | -------------------------- | ----- | ---------------------- |
| GitLab          | http://\<IP_СЕРВЕРА\>:80   | root  | SuperSecurePassword123 |
| Nexus           | http://\<IP_СЕРВЕРА\>:8081 | admin | admin123               |
| Docker Registry | \<IP_СЕРВЕРА\>:8082        | admin | admin123               |

### Использование Docker Registry

```bash
# Авторизация в реестре
docker login <IP_СЕРВЕРА>:8082 -u admin -p admin123

# Тегирование и отправка образа
docker tag myimage <IP_СЕРВЕРА>:8082/myimage:tag
docker push <IP_СЕРВЕРА>:8082/myimage:tag
```

### Очистка развёртывания

```bash
# Удалить контейнеры, сохранить данные
ansible-playbook -i inventory-prod.ini docker-compose-cleanup.yml --ask-become-pass

# Полная очистка (включая данные)
ansible-playbook -i inventory-prod.ini docker-compose-cleanup.yml --ask-become-pass -e "remove_volumes=true"
```

### Устранение неполадок

**Ошибка "Missing sudo password":**

-   Добавьте флаг `--ask-become-pass` при запуске playbook

**Ошибка парсинга inventory:**

-   Проверьте, что в `inventory-prod.ini` нет пробелов вокруг `=`

**Проверка логов на сервере:**

```bash
ssh user@server
cd /opt/larek-deploy
docker compose logs -f
docker compose ps
```
