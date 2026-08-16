#!/bin/bash
# ==============================================================================
# YouTube Video Automation Platform - Automated Backup Script
# Creates timestamped archives of the database, environment, and state files.
# ==============================================================================

set -euo pipefail

BACKUP_DIR="/opt/yt_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"
RETENTION_DAYS=14

mkdir -p "$BACKUP_PATH"

echo "Starting backup at $(date)..."

# 1. Backup .env configuration (Secure)
if [ -f "/opt/ytvideosautomation/.env" ]; then
    cp /opt/ytvideosautomation/.env "$BACKUP_PATH/.env.backup"
    chmod 600 "$BACKUP_PATH/.env.backup"
    echo "Backed up .env configuration."
fi

# 2. Backup SQLite Database via Docker volume
if docker volume inspect yt_automation_data &> /dev/null; then
    docker run --rm \
        -v yt_automation_data:/source:ro \
        -v "$BACKUP_PATH":/target \
        alpine cp -r /source/. /target/data/
    echo "Backed up database volume (yt_automation_data)."
fi

# 3. Create compressed tarball
cd "$BACKUP_DIR"
tar -czf "yt_backup_$TIMESTAMP.tar.gz" "backup_$TIMESTAMP"
rm -rf "backup_$TIMESTAMP"
chmod 600 "yt_backup_$TIMESTAMP.tar.gz"
echo "Created archive: $BACKUP_DIR/yt_backup_$TIMESTAMP.tar.gz"

# 4. Remove backups older than retention window
find "$BACKUP_DIR" -name "yt_backup_*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete
echo "Cleaned backups older than $RETENTION_DAYS days."

echo "Backup finished successfully at $(date)."
