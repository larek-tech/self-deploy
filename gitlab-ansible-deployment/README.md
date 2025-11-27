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
