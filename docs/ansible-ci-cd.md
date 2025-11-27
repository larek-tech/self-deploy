# Развёртывание CI/CD инфраструктуры с Ansible

В этом репозитории содержится набор Ansible playbooks для развёртывания GitLab и сопутствующих сервисов. Playbooks находятся в `gitlab-ansible-deployment/`.

## Основные playbooks

- `gitlab-playbook.yml` — основной playbook для установки и настройки GitLab (Docker Compose).
- `gitlab-backup.yml` — создание резервных копий данных GitLab.
- `gitlab-cleanup.yml` — остановка и очистка окружения.
- `gitlab-ssl-setup.yml` — настройка SSL (Let's Encrypt) и сертификатов.

## Инвентарь и переменные

- `inventory.ini` / `inventory-prod.ini` — пример инвентарей. Разделите хосты по группам, например `gitlab_servers`.
- `group_vars/all.yml` — глобальные переменные (настройки docker-compose, порты, т. п.).
- `host_vars/gitlab-host.yml` — переменные конкретного хоста (например, `gitlab_external_url`).

Пример `inventory.ini`:

```ini
[gitlab_servers]
gitlab-host ansible_host=192.0.2.10 ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/id_rsa
```

## Запуск playbook

1. Подготовьте инвентарь и переменные (`inventory.ini`, `group_vars/`, `host_vars/`).
2. Выполните playbook (пример):

```bash
cd gitlab-ansible-deployment
ansible-playbook -i inventory.ini gitlab-playbook.yml --ask-become-pass
```

Если требуется Ansible Vault для секретов:

```bash
ANSIBLE_VAULT_PASSWORD_FILE=~/.vault_pass ansible-playbook -i inventory.ini gitlab-playbook.yml
```

## Проверка и отладка

- После успешного выполнения проверьте доступ по `gitlab_external_url`.
- На хосте проверьте контейнеры: `docker compose ps` и `docker compose logs -f`.
- Проверьте доступность портов (80/443/22) и настройки firewall.

## Рекомендации

- Используйте отдельный пользователь с passwordless sudo или запускайте с `--ask-become-pass`.
- Защищайте секреты и токены через Ansible Vault или внешние секреты.
- Настройте backup playbook на регулярный запуск (cron / systemd timer).


