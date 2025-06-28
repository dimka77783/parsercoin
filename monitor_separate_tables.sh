#!/bin/bash

# Мониторинг состояния парсера с отдельными таблицами OHLC

# Настройки БД
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-crypto_db}"
export DB_USER="${DB_USER:-crypto_user}"
export DB_PASSWORD="${DB_PASSWORD:-crypto_password}"

clear

echo "📊 CRYPTO PARSER MONITOR (Separate OHLC Tables)"
echo "=============================================="
date

# Проверка PostgreSQL
echo -e "\n🐘 PostgreSQL:"
if docker ps | grep -q crypto_postgres; then
    echo "✅ Контейнер запущен"
    docker exec crypto_postgres pg_isready
else
    echo "❌ Контейнер не найден"
fi

# Статистика БД с отдельными таблицами
echo -e "\n📈 Статистика БД:"
docker exec crypto_postgres psql -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- Общая статистика
WITH stats AS (
    SELECT
        COUNT(*) as total_cryptos,
        COUNT(ohlc_table_name) as cryptos_with_tables
    FROM cryptocurrencies
),
table_stats AS (
    SELECT
        c.name,
        c.symbol,
        c.ohlc_table_name,
        pg_size_pretty(pg_relation_size(c.ohlc_table_name::regclass)) as table_size
    FROM cryptocurrencies c
    WHERE c.ohlc_table_name IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = c.ohlc_table_name
    )
)
SELECT
    'Всего монет: ' || s.total_cryptos || E'\n' ||
    'Монет с OHLC таблицами: ' || s.cryptos_with_tables as statistics
FROM stats s;

-- Топ 10 таблиц по размеру
SELECT E'\n📊 Топ 10 OHLC таблиц по размеру:' as title;
SELECT
    c.symbol || ' (' || c.name || ')' as crypto,
    c.ohlc_table_name as table_name,
    pg_size_pretty(pg_relation_size(c.ohlc_table_name::regclass)) as size,
    (SELECT COUNT(*) FROM pg_class WHERE relname = c.ohlc_table_name) as records
FROM cryptocurrencies c
WHERE c.ohlc_table_name IS NOT NULL
AND EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = c.ohlc_table_name
)
ORDER BY pg_relation_size(c.ohlc_table_name::regclass) DESC
LIMIT 10;

-- Последние добавленные монеты
SELECT E'\n🆕 Последние 5 монет с OHLC:' as title;
SELECT
    c.name || ' (' || c.symbol || ')' as crypto,
    c.added_date,
    c.ohlc_table_name,
    c.first_seen_at::date as first_seen
FROM cryptocurrencies c
WHERE c.ohlc_table_name IS NOT NULL
ORDER BY c.first_seen_at DESC
LIMIT 5;

-- Общий размер всех OHLC таблиц
SELECT E'\n💾 Общий размер OHLC данных:' as title;
SELECT
    pg_size_pretty(
        COALESCE(SUM(pg_relation_size(c.ohlc_table_name::regclass)), 0)
    ) as total_size
FROM cryptocurrencies c
WHERE c.ohlc_table_name IS NOT NULL
AND EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = c.ohlc_table_name
);
EOF

# Последние логи
echo -e "\n📜 Последние логи:"
if [ -d "logs" ]; then
    ls -lt logs/*.log 2>/dev/null | head -5 | awk '{print "  " $6 " " $7 " " $8 " - " $9}'
else
    echo "  Директория logs не найдена"
fi

# Место на диске
echo -e "\n💾 Использование диска:"
df -h . | tail -1 | awk '{print "  Доступно: " $4 " из " $2 " (" $5 " использовано)"}'

echo -e "\n=============================================="
echo "Нажмите Ctrl+C для выхода"