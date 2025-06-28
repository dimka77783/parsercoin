#!/bin/bash

# Скрипт резервного копирования БД

# Настройки
BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/crypto_db_backup_$TIMESTAMP.sql"

# Настройки БД
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-crypto_db}"
DB_USER="${DB_USER:-crypto_user}"
DB_PASSWORD="${DB_PASSWORD:-crypto_password}"

# Создание директории
mkdir -p "$BACKUP_DIR"

echo "🔄 Создание резервной копии БД..."
echo "   Файл: $BACKUP_FILE"

# Создание дампа через Docker
if docker ps | grep -q crypto_postgres; then
    docker exec crypto_postgres pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"
else
    # Или напрямую, если PostgreSQL локальный
    PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"
fi

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Резервная копия создана успешно"
    echo "   Размер: $SIZE"

    # Удаление старых бэкапов (оставляем последние 7)
    echo "🧹 Очистка старых бэкапов..."
    cd "$BACKUP_DIR"
    ls -t crypto_db_backup_*.sql | tail -n +8 | xargs -r rm -f

    echo "📊 Текущие бэкапы:"
    ls -lh crypto_db_backup_*.sql | head -7
else
    echo "❌ Ошибка создания резервной копии"
    exit 1
fi