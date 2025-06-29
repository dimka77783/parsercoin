#!/bin/bash

# Crypto Parser - Простой скрипт запуска
# Запускает парсинг новых монет и обновление OHLC

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Настройки БД
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-crypto_db}"
export DB_USER="${DB_USER:-crypto_user}"
export DB_PASSWORD="${DB_PASSWORD:-crypto_password}"
export PARSER_MODE="${PARSER_MODE:-safe}"

# Директории
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/crypto_$(date +%Y%m%d_%H%M%S).log"

# Создание директории для логов
mkdir -p "$LOG_DIR"

# Функция логирования
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Начало работы
log "${GREEN}🚀 Crypto Parser - $(date)${NC}"
log "================================"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    log "${RED}❌ Docker не установлен${NC}"
    exit 1
fi

# Проверка БД
if ! docker ps | grep -q crypto_db; then
    log "${YELLOW}⚠️  БД не запущена. Пытаемся запустить...${NC}"
    docker-compose up -d
    sleep 5
fi

# Проверка подключения к БД
if docker exec crypto_db pg_isready -U crypto_user > /dev/null 2>&1; then
    log "${GREEN}✅ БД работает${NC}"
else
    log "${RED}❌ БД недоступна${NC}"
    exit 1
fi

# Проверка Python и зависимостей
if ! python3 -c "import psycopg2" 2>/dev/null; then
    log "${YELLOW}⚠️  psycopg2 не установлен. Установите: sudo apt-get install python3-psycopg2${NC}"
    exit 1
fi

# Парсинг новых монет
log ""
log "${GREEN}📊 Этап 1: Парсинг новых монет...${NC}"
log "--------------------------------"

if [ -f "$SCRIPT_DIR/parser.py" ]; then
    python3 "$SCRIPT_DIR/parser.py" >> "$LOG_FILE" 2>&1
    if [ $? -eq 0 ]; then
        log "${GREEN}✅ Парсинг завершен${NC}"
    else
        log "${RED}❌ Ошибка парсинга${NC}"
    fi
else
    log "${RED}❌ Файл parser.py не найден${NC}"
fi

# Пауза между этапами
sleep 10

# Обновление OHLC
log ""
log "${GREEN}🔄 Этап 2: Обновление OHLC данных...${NC}"
log "-----------------------------------"

if [ -f "$SCRIPT_DIR/updater.py" ]; then
    python3 "$SCRIPT_DIR/updater.py" >> "$LOG_FILE" 2>&1
    if [ $? -eq 0 ]; then
        log "${GREEN}✅ Обновление OHLC завершено${NC}"
    else
        log "${RED}❌ Ошибка обновления OHLC${NC}"
    fi
else
    log "${RED}❌ Файл updater.py не найден${NC}"
fi

# Краткая статистика
log ""
log "${GREEN}📈 Статистика:${NC}"
log "-------------"

docker exec crypto_db psql -U crypto_user -d crypto_db -t -c "
SELECT
    'Всего монет: ' || COUNT(*)
FROM cryptocurrencies
UNION ALL
SELECT
    'Монет с OHLC: ' || COUNT(*)
FROM cryptocurrencies
WHERE ohlc_table_name IS NOT NULL;
" | while read line; do
    log "$line"
done

log ""
log "${GREEN}✅ Готово!${NC}"
log "Лог сохранен: $LOG_FILE"
log "================================"

# Показать последние ошибки если есть
if grep -q "ERROR\|ОШИБКА\|Error" "$LOG_FILE"; then
    log ""
    log "${YELLOW}⚠️  Обнаружены ошибки в логе:${NC}"
    grep -E "ERROR|ОШИБКА|Error" "$LOG_FILE" | tail -5
fi