# GitLab Ansible Deployment

This project deploys GitLab on a single VM using Ansible. It provides two deployment options:

1. **Native Installation** - Installs GitLab directly on the host
2. **Docker Compose** - Deploys GitLab, Nexus, and GitLab Runner via Docker Compose (recommended)

## Prerequisites

Install required Ansible collections:

```bash
ansible-galaxy collection install -r requirements.yml
```

## Option 1: Docker Compose Deployment (Recommended)

This method deploys the full stack (GitLab + Nexus + GitLab Runner) using Docker Compose, matching the local `setup.sh` configuration.

### Deploy

```bash
ansible-playbook -i inventory.ini docker-compose-playbook.yml
```

### What it deploys

-   **GitLab CE** (latest) - Source code management
-   **Nexus 3** - Docker registry and artifact repository
-   **GitLab Runner** - CI/CD runner with Docker executor

### Default Credentials

| Service         | URL                       | Username | Password               |
| --------------- | ------------------------- | -------- | ---------------------- |
| GitLab          | http://\<server-ip\>:80   | root     | SuperSecurePassword123 |
| Nexus           | http://\<server-ip\>:8081 | admin    | admin123               |
| Docker Registry | \<server-ip\>:8082        | admin    | admin123               |

### Configuration

Edit `group_vars/docker_compose.yml` to customize:

-   `gitlab_root_password` - GitLab root password
-   `gitlab_http_port` - GitLab HTTP port (default: 80)
-   `nexus_http_port` - Nexus web UI port (default: 8081)
-   `nexus_docker_port` - Docker registry port (default: 8082)

### Using the Docker Registry

```bash
# Login to the registry
docker login <server-ip>:8082 -u admin -p admin123

# Tag and push an image
docker tag myimage <server-ip>:8082/myimage:tag
docker push <server-ip>:8082/myimage:tag
```

---

## Option 2: Native GitLab Installation

Installs GitLab directly on the host (without Docker).

### Deploy

```bash
ansible-playbook -i inventory.ini gitlab-playbook.yml
```

### Backup

```bash
ansible-playbook -i inventory.ini gitlab-backup.yml
```

### Cleanup

```bash
ansible-playbook -i inventory.ini gitlab-cleanup.yml
```

---

## Inventory Configuration

Edit `inventory.ini` to configure your target server:

```ini
[gitlab_servers]
gitlab-host ansible_host=YOUR_SERVER_IP ansible_user=YOUR_USER ansible_ssh_private_key_file=~/.ssh/id_rsa
```

## Переменные окружения и секреты (нюансы)

Ниже — детальное описание переменных окружения и секретов, которые используются в Ansible шаблоне `gitlab.rb.j2`, где их задавать и на что обратить внимание при деплое на VPS.

1) Где задавать переменные
- `group_vars/` — глобальные значения по умолчанию для всех хостов.
- `host_vars/<hostname>.yml` — значения, специфичные для конкретного хоста (перезаписывают `group_vars`).
- Секреты (пароли, ключи) рекомендуется помещать в Ansible Vault и подключать через файлы в `host_vars/` или отдельный `vault.yml`.

2) Основные переменные, которые влияют на TLS и Registry
- `gitlab_external_url` — полный URL (например, `https://gitlab.example.com`). Обязательно корректно настроить DNS и порт.
- `gitlab_use_ssl` — boolean, разрешает HTTPS (в нашем шаблоне включено по умолчанию).
- `gitlab_letsencrypt_enable` — boolean, включает автоматическое получение TLS через Let's Encrypt (рекомендуется для VPS с публичным доменом).
- `gitlab_ssl_certificate_path` / `gitlab_ssl_certificate_key_path` — пути до сертификата и ключа на хосте, если не используете Let's Encrypt.
- `gitlab_registry_enabled` — включает встроенный Container Registry.
- `gitlab_registry_external_url` / `gitlab_registry_host` — URL/hostname для registry (например `https://registry.example.com`).

3) Nexus переменные (пример: интеграция с Nexus)
Мы добавили поддержку следующих переменных: `nexus_user`, `nexus_password`, `nexus_host`.
- `nexus_user` — логин (пример: `admin`).
- `nexus_password` — пароль (пример: `admin123`).
- `nexus_host` — URL до Nexus (пример: `http://nexus.internal:8081` или `https://nexus.example.com`).

Как это применяется:
- При рендере Ansible шаблона значения `nexus_*` попадают в блок `gitlab_rails['env']` в полученном `/etc/gitlab/gitlab.rb`.
- Omnibus GitLab экспортирует `gitlab_rails['env']` как переменные окружения для процессов Rails/sidekiq/etc — т.е. они будут доступны внутри GitLab как `ENV['NEXUS_USER']` и т.д.
- Пример фрагмента в `gitlab.rb`:

```ruby
gitlab_rails['env'] = {
  'NEXUS_USER' => 'admin',
  'NEXUS_PASSWORD' => 'admin123',
  'NEXUS_HOST' => 'http://nexus.local:8081',
}
```

4) Как безопасно хранить секреты (Ansible Vault)
- Рекомендуется не хранить пароли в репозитории в открытом виде. Используйте Ansible Vault:

```bash
# зашифровать строку и сразу получить YAML-поместить в host_vars
ansible-vault encrypt_string 'admin123' --name 'nexus_password'
```

- Пример создания отдельного зашифрованного файла:

```bash
ansible-vault create group_vars/vault.yml
# и добавить туда nexus_password: <значение>
```

- При запуске плейбука укажите `--ask-vault-pass` или `--vault-password-file`:

```bash
ansible-playbook -i inventory.ini gitlab-playbook.yml --ask-vault-pass
```

5) Проверка после деплоя
- Убедиться, что `/etc/gitlab/gitlab.rb` содержит ожидаемый `gitlab_rails['env']` блок с NEXUS_* переменными.

```bash
sudo grep -n "NEXUS_" /etc/gitlab/gitlab.rb || sudo sed -n '1,200p' /etc/gitlab/gitlab.rb
```

- Переконфигурировать GitLab и проверить статус:

```bash
sudo gitlab-ctl reconfigure
sudo gitlab-ctl status
```

- Проверить, что GitLab-процессы действительно имеют переменные в окружении (пример: через Rails console или проверку systemd окружения процессов gitlab-rails, если требуется).

6) Дополнительные советы
- Для публичного размещения на VPS используйте Let's Encrypt (`gitlab_letsencrypt_enable: true`) и откройте порты 80/443.
- Если используете внешний reverse-proxy (Traefik/nginx/LB) — убедитесь, что он корректно передаёт Host и TLS и что `registry_external_url` совпадает с публичным адресом.
- Для масштабирования Registry используйте объектное хранилище (S3/MinIO). Пример конфигурации приведён в шаблоне `gitlab.rb.j2` как комментированный блок — настройте креды через Vault.

---

## Troubleshooting

### Check Docker Compose logs

```bash
ssh user@server
cd /opt/larek-deploy
docker compose logs -f
```

### Restart services

```bash
docker compose restart
```

### Check service health

```bash
docker compose ps
docker inspect gitlab_server --format='{{.State.Health.Status}}'
```
