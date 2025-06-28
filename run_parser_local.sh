#!/bin/bash

# Настройки подключения к БД
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=crypto_db
export DB_USER=crypto_user
export DB_PASSWORD=crypto_password

# Путь к директории с парсером
PARSER_DIR="/path/to/your/parser/directory"
LOG_FILE="$PARSER_DIR/logs/parser_$(date +%Y%m%d_%H%M%S).log"

# Создание директории для логов
mkdir -p "$PARSER_DIR/logs"

echo "===========================================" >> "$LOG_FILE"
echo "Starting parser at $(date)" >> "$LOG_FILE"
echo "===========================================" >> "$LOG_FILE"

# Запуск парсера
cd "$PARSER_DIR"
python3 parser_ohlcv_db.py >> "$LOG_FILE" 2>&1

echo "Parser finished at $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"