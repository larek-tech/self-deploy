#!/bin/bash

# Ensure `gitlab.local` entry exists in /etc/hosts
# if ! grep -q "gitlab.local" /etc/hosts; then
#   echo "127.0.0.1 gitlab.local" >> /etc/hosts
# fi

set -euo pipefail

echo "Ensuring Docker named volumes exist (gitlab, nexus, runner)..."
# Create named volumes used by docker-compose to avoid macOS host permission problems.
docker volume create gitlab_config >/dev/null || true
docker volume create gitlab_logs >/dev/null || true
docker volume create gitlab_data >/dev/null || true
docker volume create nexus_data >/dev/null || true
docker volume create gitlab_runner_config >/dev/null || true

echo "Starting self-deploy instance"
docker compose up -d

echo "Waiting for GitLab to become ready (this may take several minutes)..."

# Wait for container to exist
until docker inspect gitlab_server >/dev/null 2>&1; do
  sleep 2
  echo -n "."
done
echo ""

# Loop until we see a healthy status or a responsive HTTP endpoint
while true; do
  STATUS=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' gitlab_server 2>/dev/null || echo "")

  if [ "${STATUS}" = "healthy" ]; then
    echo "GitLab container reports healthy." && break
  fi

  if [ "${STATUS}" = "running" ]; then
    # Check mapped HTTP port on host (default 80)
    if command -v curl >/dev/null 2>&1 && curl -fsS --connect-timeout 2 http://localhost/ >/dev/null 2>&1; then
      echo "GitLab HTTP is responsive on localhost:80." && break
    fi
  fi

  sleep 10
  echo -n "."
done
echo ""
echo "GitLab appears ready."

# Create configuration script
cat <<EOF > configure_gitlab.rb
begin
  # Fix root account
  u = User.find_by(username: 'root')
  if u.nil?
    puts "Creating root user..."
    params = { name: "Administrator", username: "root", email: "admin@larek.tech", password: "SuperSecurePassword123", password_confirmation: "SuperSecurePassword123", admin: true, skip_confirmation: true }
    u = Users::CreateService.new(nil, params).execute
    if u.persisted?
      puts "Root user created."
    else
      puts "Failed to create root user: #{u.errors.full_messages.join(', ')}"
    end
  else
    u.password = 'SuperSecurePassword123'
    u.password_confirmation = 'SuperSecurePassword123'
    u.save!
    puts "Root password reset."
  end

  # Create Initial Project
  admin_user = User.find_by(username: 'root')
  project = Project.find_by(path: 'demo-project')
  if project.nil?
    puts "Creating demo-project..."
    params = {
      name: 'Demo Project',
      path: 'demo-project',
      visibility_level: 0, # Private
      initialize_with_readme: true
    }
    project = Projects::CreateService.new(admin_user, params).execute
    if project.persisted?
      puts "Project 'demo-project' created."
      
      # Remove branch protection from main branch
      protected_branch = project.protected_branches.find_by(name: 'main')
      if protected_branch
        protected_branch.destroy
        puts "Removed protection from main branch."
      end
    else
      puts "Failed to create project: #{project.errors.full_messages.join(', ')}"
    end
  else
    puts "Project 'demo-project' already exists."
    
    # Remove branch protection from main branch if it exists
    protected_branch = project.protected_branches.find_by(name: 'main')
    if protected_branch
      protected_branch.destroy
      puts "Removed protection from main branch."
    end
  end

  # Create Runner Token
  runner = Ci::Runner.instance_type.find_by(description: 'Docker Runner')
  if runner.nil?
    runner = Ci::Runner.new(runner_type: 'instance_type', description: 'Docker Runner', run_untagged: true, locked: false)
    runner.tag_list = ['docker', 'ci', 'staging']
    runner.save!
  end
  puts "RUNNER_TOKEN:#{runner.token}"

  # Add Nexus CI/CD variables to root group (or instance-level)
  # First, try to find or create a root group for shared variables
  root_group = Group.find_by(path: 'root')
  if root_group.nil?
    puts "Creating root group for shared CI/CD variables..."
    params = {
      name: 'Root',
      path: 'root',
      visibility_level: 0
    }
    root_group = Groups::CreateService.new(admin_user, params).execute
    if root_group.persisted?
      puts "Root group created."
    else
      puts "Failed to create root group: #{root_group.errors.full_messages.join(', ')}"
    end
  end

  if root_group && root_group.persisted?
    # Add NEXUS_REGISTRY variable
    nexus_registry = root_group.variables.find_by(key: 'NEXUS_REGISTRY')
    if nexus_registry.nil?
      root_group.variables.create!(key: 'NEXUS_REGISTRY', value: 'nexus:8082', protected: false, masked: false)
      puts "Added NEXUS_REGISTRY variable."
    else
      puts "NEXUS_REGISTRY variable already exists."
    end

    # Add NEXUS_USER variable
    nexus_user = root_group.variables.find_by(key: 'NEXUS_USER')
    if nexus_user.nil?
      root_group.variables.create!(key: 'NEXUS_USER', value: 'admin', protected: false, masked: false)
      puts "Added NEXUS_USER variable."
    else
      puts "NEXUS_USER variable already exists."
    end

    # Add NEXUS_PASSWORD variable (masked for security)
    nexus_password = root_group.variables.find_by(key: 'NEXUS_PASSWORD')
    if nexus_password.nil?
      root_group.variables.create!(key: 'NEXUS_PASSWORD', value: 'admin123', protected: false, masked: true)
      puts "Added NEXUS_PASSWORD variable."
    else
      puts "NEXUS_PASSWORD variable already exists."
    end
  end

  # Also add instance-level CI/CD variables as fallback
  puts "Adding instance-level CI/CD variables..."
  [
    { key: 'NEXUS_REGISTRY', value: 'nexus:8082', protected: false, masked: false },
    { key: 'NEXUS_USER', value: 'admin', protected: false, masked: false },
    { key: 'NEXUS_PASSWORD', value: 'admin123', protected: false, masked: true }
  ].each do |var|
    existing = Ci::InstanceVariable.find_by(key: var[:key])
    if existing.nil?
      Ci::InstanceVariable.create!(var)
      puts "Added instance variable: #{var[:key]}"
    else
      puts "Instance variable #{var[:key]} already exists."
    end
  end

rescue => e
  puts "Error: #{e.message}"
end
EOF


docker cp configure_gitlab.rb gitlab_server:/tmp/configure_gitlab.rb
OUTPUT=$(docker exec gitlab_server gitlab-rails runner /tmp/configure_gitlab.rb)
echo "$OUTPUT"

RUNNER_TOKEN=$(echo "$OUTPUT" | grep "RUNNER_TOKEN:" | cut -d':' -f2)

if [ -n "$RUNNER_TOKEN" ]; then
  echo "Registering GitLab Runner..."
  docker exec gitlab_runner gitlab-runner register \
    --non-interactive \
    --url "http://gitlab_server" \
    --token "$RUNNER_TOKEN" \
    --executor "docker" \
    --docker-image "alpine:latest" \
    --description "Docker Runner" \
    --tag-list "docker,ci,staging" \
    --run-untagged="true" \
    --locked="false" \
    --access-level="not_protected" \
    --docker-network-mode "larek-cli_gitlab-network" \
    --clone-url "http://gitlab_server"
  
  echo "Updating runner config for proper network resolution..."
  # Ensure CI job containers can resolve gitlab_server via the Docker network
  docker exec gitlab_runner sh -c '
    if ! grep -q "extra_hosts" /etc/gitlab-runner/config.toml; then
      sed -i "/\[runners.docker\]/a\    extra_hosts = [\"gitlab_server:host-gateway\"]" /etc/gitlab-runner/config.toml
    fi
  '
  docker restart gitlab_runner
else
  echo "Failed to get runner token."
fi

rm configure_gitlab.rb

# Configure Nexus Repository
echo "Waiting for Nexus to become ready..."
until curl -fsS --connect-timeout 2 http://localhost:8081/service/rest/v1/status >/dev/null 2>&1; do
  sleep 5
  echo -n "."
done
echo ""
echo "Nexus is ready."

# Get Nexus admin password
NEXUS_ADMIN_PASSWORD=""
if docker exec nexus cat /nexus-data/admin.password >/dev/null 2>&1; then
  NEXUS_ADMIN_PASSWORD=$(docker exec nexus cat /nexus-data/admin.password)
  echo "Retrieved initial Nexus admin password."
else
  NEXUS_ADMIN_PASSWORD="admin123"
  echo "Using default Nexus admin password."
fi

# Function to make Nexus API calls
nexus_api() {
  local method=$1
  local endpoint=$2
  local data=$3
  curl -s -X "$method" \
    -u "admin:${NEXUS_ADMIN_PASSWORD}" \
    -H "Content-Type: application/json" \
    "http://localhost:8081/service/rest/v1/${endpoint}" \
    ${data:+-d "$data"}
}

# Change admin password to admin123 if using initial password
if [ "$NEXUS_ADMIN_PASSWORD" != "admin123" ]; then
  echo "Changing Nexus admin password..."
  curl -s -X PUT \
    -u "admin:${NEXUS_ADMIN_PASSWORD}" \
    -H "Content-Type: text/plain" \
    "http://localhost:8081/service/rest/v1/security/users/admin/change-password" \
    -d "admin123"
  NEXUS_ADMIN_PASSWORD="admin123"
  echo "Nexus admin password changed to admin123."
fi

# Enable anonymous access
echo "Enabling anonymous access..."
nexus_api PUT "security/anonymous" '{"enabled": true, "userId": "anonymous", "realmName": "NexusAuthorizingRealm"}'

# Activate Docker Bearer Token Realm
echo "Activating Docker Bearer Token Realm..."
nexus_api PUT "security/realms/active" '["NexusAuthenticatingRealm", "NexusAuthorizingRealm", "DockerToken"]'

# Create Docker hosted repository
echo "Creating Docker hosted repository..."
DOCKER_REPO_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" -u "admin:${NEXUS_ADMIN_PASSWORD}" "http://localhost:8081/service/rest/v1/repositories/docker/hosted/docker-hosted")

if [ "$DOCKER_REPO_EXISTS" != "200" ]; then
  nexus_api POST "repositories/docker/hosted" '{
    "name": "docker-hosted",
    "online": true,
    "storage": {
      "blobStoreName": "default",
      "strictContentTypeValidation": true,
      "writePolicy": "ALLOW"
    },
    "docker": {
      "v1Enabled": false,
      "forceBasicAuth": false,
      "httpPort": 8082
    }
  }'
  echo "Docker hosted repository created."
else
  echo "Docker hosted repository already exists."
fi

# Create content selector for all Docker images
echo "Creating content selector for Docker images..."
SELECTOR_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" -u "admin:${NEXUS_ADMIN_PASSWORD}" "http://localhost:8081/service/rest/v1/security/content-selectors/docker-all")

if [ "$SELECTOR_EXISTS" != "200" ]; then
  nexus_api POST "security/content-selectors" '{
    "name": "docker-all",
    "description": "Select all Docker content",
    "expression": "format == \"docker\""
  }'
  echo "Content selector created."
else
  echo "Content selector already exists."
fi

# Create content selector privilege
echo "Creating content selector privilege..."
PRIVILEGE_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" -u "admin:${NEXUS_ADMIN_PASSWORD}" "http://localhost:8081/service/rest/v1/security/privileges/docker-all-privilege")

if [ "$PRIVILEGE_EXISTS" != "200" ]; then
  nexus_api POST "security/privileges/repository-content-selector" '{
    "name": "docker-all-privilege",
    "description": "Full access to all Docker repositories",
    "actions": ["READ", "BROWSE", "EDIT", "ADD", "DELETE"],
    "format": "docker",
    "repository": "*",
    "contentSelector": "docker-all"
  }'
  echo "Content selector privilege created."
else
  echo "Content selector privilege already exists."
fi

# Create a role with Docker privileges
echo "Creating Docker admin role..."
ROLE_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" -u "admin:${NEXUS_ADMIN_PASSWORD}" "http://localhost:8081/service/rest/v1/security/roles/docker-admin")

if [ "$ROLE_EXISTS" != "200" ]; then
  nexus_api POST "security/roles" '{
    "id": "docker-admin",
    "name": "Docker Admin",
    "description": "Full access to Docker repositories",
    "privileges": ["docker-all-privilege", "nx-repository-view-docker-*-*"],
    "roles": []
  }'
  echo "Docker admin role created."
else
  echo "Docker admin role already exists."
fi

# Add Docker admin role to admin user
echo "Adding Docker admin role to admin user..."
# Nexus API requires a 'source' field when updating users — include it to avoid validation errors
nexus_api PUT "security/users/admin" '{
  "userId": "admin",
  "source": "default",
  "firstName": "Administrator",
  "lastName": "User",
  "emailAddress": "admin@example.org",
  "status": "active",
  "roles": ["nx-admin", "docker-admin"]
}'

echo ""
echo "============================================"
echo "Setup complete!"
echo "============================================"
echo "GitLab: http://localhost (root / SuperSecurePassword123)"
echo "Nexus:  http://localhost:8081 (admin / admin123)"
echo "Docker Registry: localhost:8082"
echo ""
echo "To push Docker images:"
echo "  docker login localhost:8082 -u admin -p admin123"
echo "  docker tag myimage localhost:8082/myimage:tag"
echo "  docker push localhost:8082/myimage:tag"
echo "============================================"

