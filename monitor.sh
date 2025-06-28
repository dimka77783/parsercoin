#!/bin/bash

# Мониторинг состояния парсера и БД

# Настройки БД
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-crypto_db}"
export DB_USER="${DB_USER:-crypto_user}"
export DB_PASSWORD="${DB_PASSWORD:-crypto_password}"

clear

echo "📊 CRYPTO PARSER MONITOR"
echo "========================"
date

# Проверка PostgreSQL
echo -e "\n🐘 PostgreSQL:"
if docker ps | grep -q crypto_postgres; then
    echo "✅ Контейнер запущен"
    docker exec crypto_postgres pg_isready
else
    echo "❌ Контейнер не найден"
fi

# Статистика БД
echo -e "\n📈 Статистика БД:"
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='$DB_HOST', port='$DB_PORT', database='$DB_NAME',
        user='$DB_USER', password='$DB_PASSWORD'
    )
    cur = conn.cursor()

    # Общая статистика
    cur.execute('SELECT COUNT(*) FROM cryptocurrencies')
    total_cryptos = cur.fetchone()[0]

    cur.execute('SELECT COUNT(DISTINCT crypto_id) FROM ohlc_data')
    cryptos_with_ohlc = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM ohlc_data')
    total_ohlc = cur.fetchone()[0]

    print(f'Всего монет: {total_cryptos}')
    print(f'Монет с OHLC: {cryptos_with_ohlc}')
    print(f'Всего OHLC записей: {total_ohlc}')

    # Последние монеты
    print('\n🆕 Последние 5 монет:')
    cur.execute('''
        SELECT name, symbol, added_date, first_seen_at
        FROM cryptocurrencies
        ORDER BY first_seen_at DESC
        LIMIT 5
    ''')
    for row in cur.fetchall():
        print(f'  {row[0]} ({row[1]}) - добавлена {row[2]}, найдена {row[3]}')

    conn.close()
except Exception as e:
    print(f'❌ Ошибка подключения к БД: {e}')
"

# Последние логи
echo -e "\n📜 Последние логи:"
if [ -d "logs" ]; then
    ls -lt logs/*.log 2>/dev/null | head -5 | awk '{print "  " $6 " " $7 " " $8 " - " $9}'
else
    echo "  Директория logs не найдена"
fi

# Cron задачи
echo -e "\n⏰ Cron задачи:"
crontab -l 2>/dev/null | grep crypto_parser | head -3 || echo "  Задачи не настроены"

# Место на диске
echo -e "\n💾 Использование диска:"
df -h . | tail -1 | awk '{print "  Доступно: " $4 " из " $2 " (" $5 " использовано)"}'

echo -e "\n========================"
echo "Обновление каждые 10 секунд. Ctrl+C для выхода."