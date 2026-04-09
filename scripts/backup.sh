#!/bin/bash
"""
备份和维护脚本
"""

set -e

BACKUP_DIR="${BACKUP_DIR:-.backups}"
DB_HOST="${DB_HOST:-localhost}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-agent_db}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

# 备份 PostgreSQL
backup_database() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/postgresql_backup_${timestamp}.sql.gz"
    
    echo "Backing up PostgreSQL to $backup_file..."
    PGPASSWORD=$DB_PASSWORD pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" | gzip > "$backup_file"
    
    echo "✓ Database backup completed: $backup_file"
}

# 整理旧备份
cleanup_old_backups() {
    echo "Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "*backup*.sql.gz" | while read file; do
        if [ $(find "$file" -mtime +$RETENTION_DAYS 2>/dev/null | wc -l) -gt 0 ]; then
            rm -f "$file"
            echo "  Deleted: $file"
        fi
    done
    echo "✓ Cleanup completed"
}

# 恢复数据库（仅限手动调用）
restore_database() {
    local backup_file="$1"
    if [ -z "$backup_file" ]; then
        echo "Usage: $0 restore <backup_file>"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        echo "Backup file not found: $backup_file"
        exit 1
    fi
    
    echo "Warning: This will overwrite your database!"
    read -p "Are you sure? (y/N): " confirm
    if [ "$confirm" != "y" ]; then
        echo "Cancelled"
        exit 0
    fi
    
    echo "Restoring from $backup_file..."
    gunzip -c "$backup_file" | PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME"
    echo "✓ Restore completed"
}

# 主逻辑
case "${1:-backup}" in
    backup)
        backup_database
        cleanup_old_backups
        ;;
    restore)
        restore_database "$2"
        ;;
    *)
        echo "Usage: $0 {backup|restore <file>}"
        exit 1
        ;;
esac
