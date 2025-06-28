#!/bin/bash

# Crypto Parser - запуск с сохранением в PostgreSQL

# Настройки БД
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-crypto_db}"
export DB_USER="${DB_USER:-crypto_user}"
export DB_PASSWORD="${DB_PASSWORD:-crypto_password}"

# Директории
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/parser_$(date +%Y%m%d_%H%M%S).log"

# Создание директории для логов
mkdir -p "$LOG_DIR"

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Начало работы
log "======================================"
log "🚀 Запуск Crypto Parser"
log "======================================"
log "БД: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"

# Проверка подключения к БД
log "🔍 Проверка подключения к БД..."
if python3 "$SCRIPT_DIR/test_db_connection.py" >> "$LOG_FILE" 2>&1; then
    log "✅ Подключение к БД успешно"
else
    log "❌ Ошибка подключения к БД"
    log "Проверьте, что PostgreSQL запущен:"
    log "  docker ps | grep crypto_postgres"
    exit 1
fi

# Выбор способа запуска
if [ -f "$SCRIPT_DIR/parser_ohlcv_db.py" ]; then
    # Используем модифицированную версию с поддержкой БД
    log "📊 Запуск parser_ohlcv_db.py (версия с БД)..."
    cd "$SCRIPT_DIR"
    python3 parser_ohlcv_db.py >> "$LOG_FILE" 2>&1
    RESULT=$?
elif [ -f "$SCRIPT_DIR/load_json_to_db.py" ] && [ -f "$SCRIPT_DIR/parser_ohlcv.py" ]; then
    # Используем оригинальную версию + загрузчик
    log "📊 Запуск через load_json_to_db.py..."
    cd "$SCRIPT_DIR"
    python3 load_json_to_db.py >> "$LOG_FILE" 2>&1
    RESULT=$?
else
    log "❌ Не найден парсер!"
    log "Необходим один из файлов:"
    log "  - parser_ohlcv_db.py"
    log "  - parser_ohlcv.py + load_json_to_db.py"
    exit 1
fi

# Проверка результата
if [ $RESULT -eq 0 ]; then
    log "✅ Парсер выполнен успешно"

    # Показываем статистику
    log "📈 Статистика БД:"
    python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='$DB_HOST',
    port='$DB_PORT',
    database='$DB_NAME',
    user='$DB_USER',
    password='$DB_PASSWORD'
)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM cryptocurrencies')
total = cur.fetchone()[0]
cur.execute('SELECT COUNT(DISTINCT crypto_id) FROM ohlc_data')
with_ohlc = cur.fetchone()[0]
print(f'   Всего монет: {total}')
print(f'   Монет с OHLC: {with_ohlc}')
conn.close()
" | tee -a "$LOG_FILE"
else
    log "❌ Ошибка выполнения парсера (код: $RESULT)"
fi

log "======================================"
log "✅ Завершено"
log "Лог сохранен: $LOG_FILE"
log "======================================