#!/usr/bin/env python3
"""
Обновление OHLC данных для монет возрастом от 2 до 60 дней
"""
import urllib.request
import json
import os
from datetime import datetime, timedelta
import time
import ssl
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

# Настройки
API_BASE = "https://api.coingecko.com/api/v3"
MAX_AGE_DAYS = 60
MIN_AGE_DAYS = 1
BATCH_SIZE = 10  # Обработка пакетами

# Задержки
DELAYS = {
    'between_coins': 5,
    'before_api': 2,
    'rate_limit': 60
}

# База данных
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', 'crypto_db'),
    'user': os.environ.get('DB_USER', 'crypto_user'),
    'password': os.environ.get('DB_PASSWORD', 'crypto_password')
}


def get_db_connection():
    """Подключение к БД"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return None


def create_ssl_context():
    """SSL контекст"""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def get_coins_for_update(conn):
    """Получает список монет для обновления"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
    SELECT 
        c.id,
        c.name,
        c.symbol,
        c.coin_gecko_id,
        c.added_date,
        c.ohlc_table_name,
        CURRENT_DATE - c.added_date as age_days,
        c.last_updated_at,
        COALESCE(
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - c.last_updated_at))/3600,
            999
        ) as hours_since_update
    FROM cryptocurrencies c
    WHERE c.added_date BETWEEN CURRENT_DATE - INTERVAL '%s days' 
                          AND CURRENT_DATE - INTERVAL '%s days'
    AND c.coin_gecko_id IS NOT NULL
    AND c.ohlc_table_name IS NOT NULL
    ORDER BY hours_since_update DESC
    """

    cursor.execute(query, (MAX_AGE_DAYS, MIN_AGE_DAYS))
    coins = cursor.fetchall()
    cursor.close()

    # Фильтруем монеты, которые обновлялись недавно
    filtered = []
    for coin in coins:
        if coin['hours_since_update'] > 4:  # Обновляем не чаще раз в 4 часа
            filtered.append(coin)

    return filtered


def fetch_ohlc(coin_id, days=30):
    """Получает OHLC данные"""
    url = f"{API_BASE}/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"

    time.sleep(DELAYS['before_api'])

    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')

        context = create_ssl_context()
        response = urllib.request.urlopen(req, context=context, timeout=20)
        data = json.loads(response.read().decode('utf-8'))

        if data:
            ohlc_data = []
            for candle in data:
                if len(candle) >= 5:
                    timestamp = candle[0]
                    dt = datetime.fromtimestamp(timestamp / 1000)

                    ohlc_data.append({
                        'timestamp': timestamp,
                        'datetime': dt,
                        'date': dt.date(),
                        'time': dt.time(),
                        'open': candle[1],
                        'high': candle[2],
                        'low': candle[3],
                        'close': candle[4]
                    })

            return ohlc_data

    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"    ⚠️ Rate limit, ожидание {DELAYS['rate_limit']} сек...")
            time.sleep(DELAYS['rate_limit'])
        else:
            print(f"    ❌ HTTP ошибка {e.code}")
    except Exception as e:
        print(f"    ❌ Ошибка: {e}")

    return None


def save_ohlc(conn, table_name, ohlc_data):
    """Сохраняет OHLC в таблицу"""
    cursor = conn.cursor()
    saved = 0

    try:
        # Получаем существующие timestamps
        cursor.execute(f"SELECT timestamp FROM {table_name}")
        existing = set(row[0] for row in cursor.fetchall())

        # Сохраняем только новые
        for candle in ohlc_data:
            if candle['timestamp'] not in existing:
                cursor.execute(f"""
                    INSERT INTO {table_name} 
                    (timestamp, datetime, date, time, open, high, low, close)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp) DO NOTHING
                """, (
                    candle['timestamp'], candle['datetime'],
                    candle['date'], candle['time'],
                    candle['open'], candle['high'],
                    candle['low'], candle['close']
                ))
                saved += 1

        # Обновляем last_updated_at
        cursor.execute("""
            UPDATE cryptocurrencies 
            SET last_updated_at = CURRENT_TIMESTAMP 
            WHERE ohlc_table_name = %s
        """, (table_name,))

        conn.commit()

    except Exception as e:
        print(f"    ❌ Ошибка сохранения: {e}")
        conn.rollback()
    finally:
        cursor.close()

    return saved


def print_stats(conn):
    """Выводит статистику"""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN age < 60 THEN 1 END) as active,
            COUNT(CASE WHEN age BETWEEN 2 AND 60 THEN 1 END) as need_update
        FROM (
            SELECT CURRENT_DATE - added_date as age
            FROM cryptocurrencies
        ) t
    """)

    stats = cursor.fetchone()
    cursor.close()

    print(f"\n📊 Статистика БД:")
    print(f"  Всего монет: {stats[0]}")
    print(f"  Активных (<60 дней): {stats[1]}")
    print(f"  Требуют обновления: {stats[2]}")


def main():
    print("=" * 60)
    print("🔄 ОБНОВЛЕНИЕ OHLC ДАННЫХ")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Подключение к БД
    conn = get_db_connection()
    if not conn:
        sys.exit(1)

    # Статистика
    print_stats(conn)

    # Получаем монеты для обновления
    coins = get_coins_for_update(conn)
    print(f"\n🎯 Монет для обновления: {len(coins)}")

    if not coins:
        print("✅ Все монеты актуальны")
        conn.close()
        return

    # Обновляем пакетами
    success = 0
    errors = 0

    for i in range(0, len(coins), BATCH_SIZE):
        batch = coins[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(coins) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\n📦 Пакет {batch_num}/{total_batches}")

        for j, coin in enumerate(batch):
            if j > 0:
                time.sleep(DELAYS['between_coins'])

            print(f"\n🔄 {coin['name']} ({coin['symbol']})")
            print(f"   Возраст: {coin['age_days']} дней")
            print(f"   Обновлено: {coin['hours_since_update']:.1f} часов назад")

            # Получаем OHLC
            ohlc = fetch_ohlc(coin['coin_gecko_id'])

            if ohlc:
                saved = save_ohlc(conn, coin['ohlc_table_name'], ohlc)
                print(f"   ✅ Сохранено новых: {saved}")
                success += 1
            else:
                print(f"   ❌ Не удалось получить данные")
                errors += 1

        # Пауза между пакетами
        if i + BATCH_SIZE < len(coins):
            print(f"\n⏸️  Пауза между пакетами...")
            time.sleep(DELAYS['between_coins'] * 2)

    # Итоги
    print("\n" + "=" * 60)
    print(f"📊 ИТОГИ:")
    print(f"  Успешно: {success}")
    print(f"  Ошибок: {errors}")
    print(f"  Всего: {success + errors}")

    conn.close()
    print("\n✅ Обновление завершено")
    print("=" * 60)


if __name__ == "__main__":
    main()