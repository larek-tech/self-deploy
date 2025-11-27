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
