#!/bin/bash

# Экспорт переменных окружения для cron
export DB_HOST=${DB_HOST:-postgres}
export DB_PORT=${DB_PORT:-5432}
export DB_NAME=${DB_NAME:-crypto_db}
export DB_USER=${DB_USER:-crypto_user}
export DB_PASSWORD=${DB_PASSWORD:-crypto_password}

echo "=================================================="
echo "Starting parser at $(date)"
echo "=================================================="

# Запуск парсера
cd /app
python3 parser_ohlcv.py

echo "Parser finished at $(date)"
echo ""