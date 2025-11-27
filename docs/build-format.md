# Формат файла `.larek/build.yaml`

Файл `.larek/build.yaml` описывает сервисы и инструкции по сборке/тестированию/деплою для проекта, который анализируется `larek`.

Расположение: `.larek/build.yaml` в корне клонированного репозитория.

## Общая структура (пример)

```yaml
is_monorepo: false
services:
  - path: "."
    name: my-service
    lang:
      name: python
      version: "3.11"
    dependencies:
      packet_manager: poetry
      libs:
        - name: requests
          version: ">=2.0"
    configs:
      - name: .env
        path: .env
    docker:
      dockerfiles: ["Dockerfile"]
      compose: docker-compose.yml
      environment:
        - name: PROD_ENV
          path: .env
    entrypoints: ["app.py"]
    tests: "pytest"
    linters:
      - name: flake8
        config: .flake8
deployment:
  type: compose
  path: docker-compose.yml
  environment:
    - name: PROD_ENV
      path: .env
```

## Пояснение полей

- `is_monorepo` (bool) — флаг, является ли репозиторий монорепо.
- `services` (list) — список сервисов в репозитории. Каждый сервис описывается объектом `Service` с полями описанными ниже.
- Service fields:
  - `path` (string) — путь к сервису внутри репозитория.
  - `name` (string) — имя сервиса.
  - `lang` (object) — объект `Language` (поля: `name`, `version`).
  - `dependencies` (object) — менеджер пакетов и список `libs` (имя + версия).
  - `configs` (list) — дополнительные конфигурационные файлы (объекты `Config` — `name`, `path`).
  - `docker` (object) — объект `Docker`: `dockerfiles`, `compose`, `environment` — список переменных окружения (объекты `Environment`).
  - `entrypoints` (list[str]) — точки входа приложения.
  - `tests` (string) — команда для запуска тестов.
  - `linters` (list) — список объектов `Linter`.
  - `android` (optional) — при Android-проектах — объект `AndroidConfig` с Android-специфичными полями.
- `deployment` (object) — общая конфигурация деплоя: `type` (dockerfile|compose|helm), `path`, `environment`.

## Советы и требования

- Для Python-проектов `lang.name` должен быть `python`; для Node.js — `javascript` или `typescript`.
- Если `docker.dockerfiles` пустой для Android — генерация Dockerfile пропускается.
- Для mono-repo указывайте `is_monorepo: true` и корректные `path` для каждого сервиса.

## Частые примеры

- Пример для Go-проекта: укажите `lang.name: go`, и в `dependencies.packet_manager` можно указывать `go`.
- Пример для Java/Maven-проекта: `lang.name: java`, `dependencies.packet_manager: maven`.


