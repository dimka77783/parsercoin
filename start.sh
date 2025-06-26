#!/bin/bash

# Настройка
SCRIPT_PATH="/app/parser.py"
LOG_FILE="/app/logs/start.log"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Создание директории для логов если не существует
mkdir -p /app/logs

# Запуск скрипта с перенаправлением вывода в файл
echo "[$TIMESTAMP] ==> Запуск скрипта парсера..." >> "$LOG_FILE"

# Проверяем доступность базы данных
echo "[$TIMESTAMP] Проверка подключения к БД..." >> "$LOG_FILE"

# Экспорт переменных окружения (на случай если cron их не передает)
export DB_HOST=${DB_HOST:-db}
export DB_NAME=${DB_NAME:-coingecko_db}
export DB_USER=${DB_USER:-user}
export DB_PASSWORD=${DB_PASSWORD:-password}

echo "[$TIMESTAMP] DB_HOST: $DB_HOST" >> "$LOG_FILE"
echo "[$TIMESTAMP] DB_NAME: $DB_NAME" >> "$LOG_FILE"

# Запуск Python скрипта
cd /app
/usr/local/bin/python "$SCRIPT_PATH" >> "$LOG_FILE" 2>&1
RETURN_CODE=$?

# Проверка кода возврата и логирование
if [ $RETURN_CODE -eq 0 ]; then
  echo "[$TIMESTAMP] ✅ Скрипт успешно завершен." >> "$LOG_FILE"
else
  echo "[$TIMESTAMP] ❌ ОШИБКА: Скрипт завершился с кодом $RETURN_CODE." >> "$LOG_FILE"
fi

echo "[$TIMESTAMP] ==> Завершение работы" >> "$LOG_FILE"
echo "===========================================" >> "$LOG_FILE"