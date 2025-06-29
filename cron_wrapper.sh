#!/bin/bash
# Wrapper для запуска crypto parser из cron
# Обеспечивает правильное окружение

# Базовые настройки
PROJECT_DIR="/home/odinokov/PycharmProjects/parsercoin"
LOG_DIR="$PROJECT_DIR/logs"
BACKUP_DIR="$PROJECT_DIR/backups"

# Переход в рабочую директорию
cd "$PROJECT_DIR" || exit 1

# Настройка окружения
export PATH="/usr/local/bin:/usr/bin:/bin"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="crypto_db"
export DB_USER="crypto_user"
export DB_PASSWORD="crypto_password"

# Создание необходимых директорий
mkdir -p "$LOG_DIR" "$BACKUP_DIR"

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Проверка Docker
if ! docker ps >/dev/null 2>&1; then
    log "ERROR: Docker is not running or accessible"
    exit 1
fi

# Проверка контейнера БД
if ! docker ps | grep -q crypto_db; then
    log "WARNING: Database container not running, starting..."
    docker-compose up -d
    sleep 10
fi

# Выполнение команды переданной как аргумент
case "$1" in
    "parser")
        log "Starting parser.py"
        /usr/bin/python3 parser.py
        ;;
    "updater")
        log "Starting updater.py"
        /usr/bin/python3 updater.py
        ;;
    "full")
        log "Starting full update (run.sh)"
        ./run.sh
        ;;
    "backup")
        log "Starting database backup"
        BACKUP_FILE="$BACKUP_DIR/crypto_db_$(date +%Y%m%d_%H%M%S).sql.gz"
        docker exec crypto_db pg_dump -U crypto_user crypto_db | gzip > "$BACKUP_FILE"
        log "Backup saved to: $BACKUP_FILE"
        # Удаление старых бэкапов (старше 7 дней)
        find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete
        ;;
    "stats")
        log "Getting database statistics"
        docker exec crypto_db psql -U crypto_user -d crypto_db -t -c "
            SELECT 'Timestamp: ' || NOW()::timestamp(0)
            UNION ALL
            SELECT 'Database size: ' || pg_size_pretty(pg_database_size('crypto_db'))
            UNION ALL
            SELECT 'Total coins: ' || COUNT(*) FROM cryptocurrencies
            UNION ALL
            SELECT 'Coins with OHLC: ' || COUNT(*) FROM cryptocurrencies WHERE ohlc_table_name IS NOT NULL
            UNION ALL
            SELECT 'Updated today: ' || COUNT(*) FROM cryptocurrencies WHERE DATE(last_updated_at) = CURRENT_DATE
            UNION ALL
            SELECT 'New today: ' || COUNT(*) FROM cryptocurrencies WHERE DATE(first_seen_at) = CURRENT_DATE;"
        ;;
    *)
        log "ERROR: Unknown command: $1"
        echo "Usage: $0 {parser|updater|full|backup|stats}"
        exit 1
        ;;
esac

# Проверка на ошибки
if [ $? -eq 0 ]; then
    log "Task completed successfully"
else
    log "ERROR: Task failed with exit code $?"
fi