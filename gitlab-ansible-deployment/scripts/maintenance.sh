#!/bin/bash
# GitLab Maintenance Scripts
# Place these in /opt/gitlab-scripts/

# ===== BACKUP SCRIPT =====
backup_gitlab() {
    echo "Starting GitLab backup at $(date)"
    
    # Create backup
    gitlab-backup create BACKUP=manual_$(date +%Y%m%d_%H%M%S)
    
    # Create config backup
    tar -czf /opt/gitlab-config-backup/gitlab-config-$(date +%Y%m%d_%H%M%S).tar.gz /etc/gitlab/
    
    # Remove old backups (keep last 7 days)
    find /var/opt/gitlab/backups -name "*.tar" -type f -mtime +7 -delete
    find /opt/gitlab-config-backup -name "*.tar.gz" -type f -mtime +7 -delete
    
    echo "GitLab backup completed at $(date)"
}

# ===== RESTORE SCRIPT =====
restore_gitlab() {
    local backup_file=$1
    
    if [[ -z "$backup_file" ]]; then
        echo "Usage: restore_gitlab <backup_timestamp>"
        echo "Available backups:"
        ls -la /var/opt/gitlab/backups/*.tar
        return 1
    fi
    
    echo "Starting GitLab restore from backup: $backup_file"
    
    # Stop GitLab services except PostgreSQL and Redis
    gitlab-ctl stop puma
    gitlab-ctl stop sidekiq
    
    # Restore from backup
    gitlab-backup restore BACKUP=$backup_file
    
    # Restart GitLab
    gitlab-ctl restart
    
    # Check GitLab health
    gitlab-rake gitlab:check SANITIZE=true
    
    echo "GitLab restore completed"
}

# ===== HEALTH CHECK SCRIPT =====
health_check() {
    echo "GitLab Health Check - $(date)"
    echo "================================="
    
    # Check GitLab status
    echo "GitLab Services Status:"
    gitlab-ctl status
    
    echo -e "\nDisk Usage:"
    df -h /var/opt/gitlab
    
    echo -e "\nMemory Usage:"
    free -h
    
    echo -e "\nGitLab Application Check:"
    gitlab-rake gitlab:check SANITIZE=true
    
    echo -e "\nRecent Logs (last 50 lines):"
    tail -n 50 /var/log/gitlab/gitlab-rails/production.log
}

# ===== MAINTENANCE SCRIPT =====
maintenance() {
    echo "Starting GitLab maintenance tasks - $(date)"
    
    # Clean up old logs
    find /var/log/gitlab -name "*.log" -type f -mtime +30 -delete
    
    # Clean repository storage
    gitlab-rake gitlab:cleanup:orphan_artifact_files
    gitlab-rake gitlab:cleanup:orphan_job_artifact_files
    
    # Update package lists (if needed)
    if command -v apt &> /dev/null; then
        apt update
    fi
    
    # Check for GitLab updates
    echo "Current GitLab version:"
    gitlab-rake gitlab:env:info | grep "GitLab information"
    
    echo "GitLab maintenance completed - $(date)"
}

# ===== SECURITY HARDENING SCRIPT =====
security_harden() {
    echo "Applying GitLab security hardening - $(date)"
    
    # Update system packages
    if command -v apt &> /dev/null; then
        apt update && apt upgrade -y
    elif command -v yum &> /dev/null; then
        yum update -y
    fi
    
    # Set proper file permissions
    chown -R git:git /var/opt/gitlab
    chmod 700 /etc/gitlab/ssl
    chmod 600 /etc/gitlab/ssl/*
    chmod 600 /etc/gitlab/gitlab.rb
    
    # Configure fail2ban for GitLab (if installed)
    if command -v fail2ban-client &> /dev/null; then
        cat > /etc/fail2ban/jail.d/gitlab.conf << EOF
[gitlab]
enabled = true
port = 80,443,22
protocol = tcp
filter = gitlab
logpath = /var/log/gitlab/nginx/gitlab_access.log
maxretry = 5
bantime = 600
findtime = 600

[gitlab-auth]
enabled = true
port = 80,443
protocol = tcp  
filter = gitlab-auth
logpath = /var/log/gitlab/gitlab-rails/auth.log
maxretry = 5
bantime = 600
findtime = 600
EOF
        systemctl restart fail2ban
    fi
    
    echo "Security hardening completed - $(date)"
}

# ===== MAIN EXECUTION =====
case "$1" in
    backup)
        backup_gitlab
        ;;
    restore)
        restore_gitlab "$2"
        ;;
    health)
        health_check
        ;;
    maintenance)
        maintenance
        ;;
    security)
        security_harden
        ;;
    *)
        echo "Usage: $0 {backup|restore|health|maintenance|security}"
        echo "  backup          - Create GitLab backup"
        echo "  restore <name>  - Restore GitLab from backup"
        echo "  health          - Run health check"
        echo "  maintenance     - Run maintenance tasks"
        echo "  security        - Apply security hardening"
        exit 1
        ;;
esac