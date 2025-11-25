#!/bin/bash


if ! grep -q "gitlab.local" /etc/hosts; then
  echo "127.0.0.1 gitlab.local" >> /etc/hosts
fi

echo "Starting self-deploy instance"
docker compose up -d

echo "Waiting for GitLab to be healthy (this may take several minutes)..."
until [ "$(docker inspect -f '{{.State.Health.Status}}' gitlab_server)" == "healthy" ]; do
    sleep 10
    echo -n "."
done
echo ""
echo "GitLab is healthy."

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
    else
      puts "Failed to create project: #{project.errors.full_messages.join(', ')}"
    end
  else
    puts "Project 'demo-project' already exists."
  end

  # Create Runner Token
  runner = Ci::Runner.instance_type.find_by(description: 'Docker Runner')
  if runner.nil?
    runner = Ci::Runner.new(runner_type: 'instance_type', description: 'Docker Runner', run_untagged: true, locked: false)
    runner.tag_list = ['docker', 'ci', 'staging']
    runner.save!
  end
  puts "RUNNER_TOKEN:#{runner.token}"
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
    --access-level="not_protected"
else
  echo "Failed to get runner token."
fi

rm configure_gitlab.rb

