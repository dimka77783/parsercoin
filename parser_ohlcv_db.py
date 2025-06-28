#!/usr/bin/env python3
"""
Модифицированная версия парсера с отдельными таблицами OHLC для каждой монеты
"""
import urllib.request
import urllib.parse
import json
import os
import re
from datetime import datetime, timedelta
import time
import ssl
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

# URL страницы с новыми криптовалютами
BASE_URL = "https://www.coingecko.com/ru/new-cryptocurrencies"
API_BASE = "https://api.coingecko.com/api/v3"

# Количество монет для парсинга
MAX_COINS = 50

# Настройки базы данных
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', 'crypto_db'),
    'user': os.environ.get('DB_USER', 'crypto_user'),
    'password': os.environ.get('DB_PASSWORD', 'crypto_password')
}


def get_db_connection():
    """Создает подключение к базе данных"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}", flush=True)
        return None


def create_ssl_context():
    """Создает SSL контекст для HTTPS запросов"""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def fetch_page():
    """Загружает HTML страницу"""
    print(f"🌐 Загрузка страницы: {BASE_URL}", flush=True)

    try:
        req = urllib.request.Request(BASE_URL)
        req.add_header('User-Agent',
                       'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
        req.add_header('Accept',
                       'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8')
        req.add_header('Accept-Language', 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7')
        req.add_header('Accept-Encoding', 'gzip, deflate')
        req.add_header('Connection', 'keep-alive')
        req.add_header('Upgrade-Insecure-Requests', '1')

        context = create_ssl_context()
        response = urllib.request.urlopen(req, context=context, timeout=30)

        if response.info().get('Content-Encoding') == 'gzip':
            import gzip
            html = gzip.decompress(response.read()).decode('utf-8')
        else:
            html = response.read().decode('utf-8')

        print(f"✅ Страница загружена, размер: {len(html)} байт", flush=True)
        return html

    except urllib.error.HTTPError as e:
        print(f"❌ HTTP ошибка: {e.code} {e.reason}", flush=True)
        if e.code == 403:
            print("💡 CoinGecko блокирует запросы. Попробуйте использовать VPN", flush=True)
        return None
    except Exception as e:
        print(f"❌ Ошибка при загрузке: {e}", flush=True)
        return None


def search_coin_id(coin_name, coin_symbol, retry_count=0):
    """Ищет ID монеты в CoinGecko API"""
    print(f"  🔍 Поиск ID для {coin_name} ({coin_symbol})...", flush=True)

    search_query = coin_symbol.lower()
    url = f"{API_BASE}/search?query={urllib.parse.quote(search_query)}"

    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')

        context = create_ssl_context()
        response = urllib.request.urlopen(req, context=context, timeout=15)
        data = json.loads(response.read().decode('utf-8'))

        if 'coins' in data:
            for coin in data['coins']:
                if coin.get('symbol', '').upper() == coin_symbol.upper():
                    found_id = coin['id']
                    found_name = coin.get('name', '')
                    found_symbol = coin.get('symbol', '').upper()

                    print(f"    📌 Найден кандидат: {found_name} ({found_symbol}) - ID: {found_id}", flush=True)

                    if coin_name.lower() in found_name.lower() or found_name.lower() in coin_name.lower():
                        print(f"    ✅ Подтверждено совпадение по названию и символу", flush=True)
                        return found_id

        # Пробуем поиск по названию
        search_query = coin_name.lower()
        url = f"{API_BASE}/search?query={urllib.parse.quote(search_query)}"

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')

        response = urllib.request.urlopen(req, context=context, timeout=15)
        data = json.loads(response.read().decode('utf-8'))

        if 'coins' in data and len(data['coins']) > 0:
            for coin in data['coins'][:5]:
                found_id = coin['id']
                found_symbol = coin.get('symbol', '').upper()

                if found_symbol == coin_symbol.upper():
                    print(f"    ✅ Найдено точное совпадение по символу", flush=True)
                    return found_id

    except urllib.error.HTTPError as e:
        if e.code == 429 and retry_count < 3:
            wait_time = 60 * (retry_count + 1)
            print(f"    ⚠️ Rate limit превышен. Ожидание {wait_time} секунд...", flush=True)
            time.sleep(wait_time)
            return search_coin_id(coin_name, coin_symbol, retry_count + 1)
        else:
            print(f"    ❌ Ошибка поиска: {e}", flush=True)
    except Exception as e:
        print(f"    ❌ Ошибка поиска: {e}", flush=True)

    return None


def fetch_ohlc_data(coin_id, days=30, retry_count=0):
    """Получает OHLCV данные для монеты"""
    url = f"{API_BASE}/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"

    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')

        context = create_ssl_context()
        response = urllib.request.urlopen(req, context=context, timeout=15)

        data = json.loads(response.read().decode('utf-8'))

        if data and len(data) > 0:
            ohlc_processed = []

            for candle in data:
                if len(candle) >= 5:
                    timestamp = candle[0]
                    dt = datetime.fromtimestamp(timestamp / 1000)

                    ohlc_processed.append({
                        'timestamp': timestamp,
                        'datetime': dt.isoformat(),
                        'date': dt.strftime('%Y-%m-%d'),
                        'time': dt.strftime('%H:%M:%S'),
                        'open': candle[1],
                        'high': candle[2],
                        'low': candle[3],
                        'close': candle[4]
                    })

            print(f"    ✅ Получено {len(ohlc_processed)} 4-часовых OHLC свечей", flush=True)
            return ohlc_processed

    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"    ⚠️ OHLC данные не найдены", flush=True)
        elif e.code == 429:
            if retry_count < 3:
                print(f"    ⚠️ Превышен лимит API. Ожидание 60 секунд...", flush=True)
                time.sleep(60)
                print(f"    🔄 Повторная попытка получения OHLC для {coin_id}...", flush=True)
                return fetch_ohlc_data(coin_id, days, retry_count + 1)
            else:
                print(f"    ❌ Превышен лимит попыток для получения OHLC", flush=True)
        else:
            print(f"    ❌ HTTP ошибка {e.code}", flush=True)
    except Exception as e:
        print(f"    ❌ Ошибка: {e}", flush=True)

    return None


def is_older_than_two_days(added_date_str):
    """Проверяет, старше ли монета двух дней"""
    try:
        added_date = datetime.strptime(added_date_str, '%Y-%m-%d')
        now = datetime.now()
        days_diff = (now - added_date).days
        return days_diff >= 2
    except:
        return False


def parse_html_limited(html, limit=MAX_COINS):
    """Парсит HTML и извлекает данные о монетах"""
    print(f"🔍 Парсинг HTML (ограничение: {limit} монет)...", flush=True)

    cryptos = []

    try:
        table_pattern = r'<tr[^>]*class="[^"]*hover:tw-bg[^"]*"[^>]*>(.*?)</tr>'
        rows = re.findall(table_pattern, html, re.DOTALL)

        print(f"📊 Найдено строк в таблице: {len(rows)}", flush=True)
        print(f"🎯 Будут обработаны первые {limit} строк", flush=True)

        rows_to_process = rows[:limit] if len(rows) > limit else rows

        for i, row in enumerate(rows_to_process):
            try:
                crypto = parse_row(row)
                if crypto:
                    cryptos.append(crypto)
                    print(f"✅ [{i + 1}/{limit}] Найдена монета: {crypto['name']} ({crypto['symbol']})", flush=True)
            except Exception as e:
                print(f"⚠️ Ошибка при парсинге строки {i + 1}: {e}", flush=True)
                continue

        return cryptos

    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}", flush=True)
        return []


def parse_row(row_html):
    """Парсит одну строку таблицы"""
    crypto = {}

    td_pattern = r'<td[^>]*>(.*?)</td>'
    cells = re.findall(td_pattern, row_html, re.DOTALL)

    if len(cells) < 11:
        return None

    # Парсинг названия и символа
    name_cell = cells[2]
    text_pattern = r'>([^<>]+)<'
    all_texts = re.findall(text_pattern, name_cell)

    crypto['name'] = "Unknown"
    crypto['symbol'] = ""

    for text in all_texts:
        clean = text.strip()
        if clean and len(clean) > 1:
            if not clean.startswith('$') and not clean.startswith('%') and not clean.replace(',', '').replace('.',
                                                                                                              '').isdigit():
                if any(c.isalpha() for c in clean):
                    if len(clean) > 5 or not clean.isupper():
                        crypto['name'] = clean
                        break
                    elif crypto['symbol'] == "":
                        crypto['symbol'] = clean

    # Альтернативные методы поиска названия
    if crypto['name'] == "Unknown":
        img_pattern = r'<img[^>]*alt="([^"]+)"[^>]*>'
        img_match = re.search(img_pattern, name_cell)
        if img_match:
            crypto['name'] = img_match.group(1).strip()

    if crypto['name'] == "Unknown":
        title_pattern = r'title="([^"]+)"'
        title_matches = re.findall(title_pattern, name_cell)
        for title in title_matches:
            if title and len(title) > 2 and not title.startswith('$'):
                crypto['name'] = title
                break

    # Поиск символа
    if not crypto['symbol']:
        for text in all_texts:
            clean = text.strip()
            if clean and 2 <= len(clean) <= 10 and clean.isupper() and clean.isalpha():
                crypto['symbol'] = clean
                break

    # Остальные поля
    crypto['price'] = clean_text(cells[3]) if len(cells) > 3 else "N/A"

    change_text = clean_text(cells[4]) if len(cells) > 4 else ""
    percent_match = re.search(r'([-+]?\d+[,.]?\d*%)', change_text)
    if percent_match:
        crypto['change_24h'] = percent_match.group(1)
    else:
        crypto['change_24h'] = change_text if change_text else "N/A"

    crypto['chain'] = clean_text(cells[5]) if len(cells) > 5 else "Unknown"
    crypto['market_cap'] = clean_text(cells[7]) if len(cells) > 7 else "N/A"
    crypto['fdv'] = clean_text(cells[9]) if len(cells) > 9 else "N/A"

    added_text = clean_text(cells[10]) if len(cells) > 10 else "недавно"
    crypto['added'] = parse_added_date(added_text)
    crypto['added_raw'] = added_text

    crypto['parsed_at'] = datetime.now().isoformat()

    return crypto


def clean_text(html):
    """Очищает HTML от тегов"""
    text = re.sub(r'<[^>]+>', '', html)
    text = ' '.join(text.split())
    return text.strip()


def parse_added_date(added_text):
    """Преобразует текст даты в формат YYYY-MM-DD"""
    now = datetime.now()

    if "недавно" in added_text:
        return (now - timedelta(minutes=30)).strftime('%Y-%m-%d')
    elif "около 1 часа" in added_text:
        return (now - timedelta(hours=1)).strftime('%Y-%m-%d')
    elif "около" in added_text and "час" in added_text:
        hours_match = re.search(r'около (\d+) час', added_text)
        if hours_match:
            hours = int(hours_match.group(1))
            return (now - timedelta(hours=hours)).strftime('%Y-%m-%d')
    elif "около 1 дня" in added_text or "около дня" in added_text:
        return (now - timedelta(days=1)).strftime('%Y-%m-%d')
    elif "около" in added_text and "дн" in added_text:
        days_match = re.search(r'около (\d+) дн', added_text)
        if days_match:
            days = int(days_match.group(1))
            return (now - timedelta(days=days)).strftime('%Y-%m-%d')
    elif "дн" in added_text:
        days_match = re.search(r'(\d+)\s*дн', added_text)
        if days_match:
            days = int(days_match.group(1))
            return (now - timedelta(days=days)).strftime('%Y-%m-%d')

    return now.strftime('%Y-%m-%d')


def save_to_database_with_separate_tables(cryptos):
    """Сохраняет данные в БД с отдельными таблицами для OHLC"""
    conn = get_db_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных", flush=True)
        return

    cursor = conn.cursor()
    saved_count = 0
    updated_count = 0
    ohlc_saved_count = 0

    try:
        for crypto in cryptos:
            try:
                # Проверяем существование монеты
                cursor.execute("""
                    SELECT id, ohlc_table_name FROM cryptocurrencies 
                    WHERE symbol = %s AND added_date = %s
                """, (crypto['symbol'], crypto['added']))

                existing = cursor.fetchone()

                if existing:
                    crypto_id = existing[0]
                    ohlc_table_name = existing[1]

                    # Обновляем данные монеты
                    cursor.execute("""
                        UPDATE cryptocurrencies SET
                            name = %s,
                            chain = %s,
                            price = %s,
                            change_24h = %s,
                            market_cap = %s,
                            fdv = %s,
                            added_raw = %s,
                            coin_gecko_id = %s
                        WHERE id = %s
                    """, (
                        crypto['name'],
                        crypto['chain'],
                        crypto['price'],
                        crypto['change_24h'],
                        crypto['market_cap'],
                        crypto['fdv'],
                        crypto['added_raw'],
                        crypto.get('coin_id'),
                        crypto_id
                    ))
                    updated_count += 1
                else:
                    # Вставляем новую монету (триггер автоматически создаст OHLC таблицу)
                    cursor.execute("""
                        INSERT INTO cryptocurrencies 
                        (name, symbol, chain, price, change_24h, market_cap, fdv, 
                         added_date, added_raw, coin_gecko_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, ohlc_table_name
                    """, (
                        crypto['name'],
                        crypto['symbol'],
                        crypto['chain'],
                        crypto['price'],
                        crypto['change_24h'],
                        crypto['market_cap'],
                        crypto['fdv'],
                        crypto['added'],
                        crypto['added_raw'],
                        crypto.get('coin_id')
                    ))
                    result = cursor.fetchone()
                    crypto_id = result[0]
                    ohlc_table_name = result[1]
                    saved_count += 1
                    print(f"    📊 Создана таблица OHLC: {ohlc_table_name}", flush=True)

                # Сохраняем OHLC данные в отдельную таблицу
                if 'ohlcv' in crypto and crypto['ohlcv'] and ohlc_table_name:
                    # Получаем существующие timestamp для этой монеты
                    cursor.execute(f"""
                        SELECT timestamp FROM {ohlc_table_name}
                    """)
                    existing_timestamps = set(row[0] for row in cursor.fetchall())

                    # Подготавливаем данные для вставки (только новые)
                    new_ohlc_data = []
                    for candle in crypto['ohlcv']:
                        if candle['timestamp'] not in existing_timestamps:
                            new_ohlc_data.append((
                                candle['timestamp'],
                                datetime.fromisoformat(candle['datetime']),
                                datetime.strptime(candle['date'], '%Y-%m-%d').date(),
                                datetime.strptime(candle['time'], '%H:%M:%S').time(),
                                float(candle['open']),
                                float(candle['high']),
                                float(candle['low']),
                                float(candle['close'])
                            ))

                    # Вставляем только новые OHLC данные
                    if new_ohlc_data:
                        insert_query = f"""
                            INSERT INTO {ohlc_table_name} 
                            (timestamp, datetime, date, time, open, high, low, close)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (timestamp) DO NOTHING
                        """
                        cursor.executemany(insert_query, new_ohlc_data)
                        ohlc_saved_count += len(new_ohlc_data)

                conn.commit()

            except Exception as e:
                print(f"⚠️ Ошибка при сохранении {crypto['name']}: {e}", flush=True)
                conn.rollback()
                continue

        print(f"\n💾 Сохранено в БД:", flush=True)
        print(f"   - Новых монет: {saved_count}", flush=True)
        print(f"   - Обновлено монет: {updated_count}", flush=True)
        print(f"   - Новых OHLC записей: {ohlc_saved_count}", flush=True)

    except Exception as e:
        print(f"❌ Общая ошибка при сохранении в БД: {e}", flush=True)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def get_database_stats_separate_tables():
    """Получает статистику из БД с отдельными таблицами"""
    conn = get_db_connection()
    if not conn:
        return None

    cursor = conn.cursor(cursor_factory=RealDictCursor)
    stats = {}

    try:
        # Общее количество монет
        cursor.execute("SELECT COUNT(*) as total FROM cryptocurrencies")
        stats['total_cryptos'] = cursor.fetchone()['total']

        # Монеты с OHLC таблицами
        cursor.execute("""
            SELECT COUNT(*) as with_ohlc 
            FROM cryptocurrencies 
            WHERE ohlc_table_name IS NOT NULL
        """)
        stats['cryptos_with_ohlc'] = cursor.fetchone()['with_ohlc']

        # Статистика по каждой таблице OHLC
        cursor.execute("""
            SELECT 
                c.name, 
                c.symbol, 
                c.ohlc_table_name,
                c.added_date
            FROM cryptocurrencies c
            WHERE c.ohlc_table_name IS NOT NULL
            ORDER BY c.first_seen_at DESC
            LIMIT 10
        """)

        recent_cryptos = []
        for row in cursor.fetchall():
            # Получаем количество записей в OHLC таблице
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {row['ohlc_table_name']}")
                ohlc_count = cursor.fetchone()['count']
            except:
                ohlc_count = 0

            recent_cryptos.append({
                'name': row['name'],
                'symbol': row['symbol'],
                'added_date': row['added_date'],
                'ohlc_table': row['ohlc_table_name'],
                'ohlc_count': ohlc_count
            })

        stats['recent_cryptos'] = recent_cryptos

        return stats

    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}", flush=True)
        return None
    finally:
        cursor.close()
        conn.close()


def main():
    print("=" * 80, flush=True)
    print("🚀 ПАРСЕР КРИПТОВАЛЮТ С ОТДЕЛЬНЫМИ ТАБЛИЦАМИ OHLC", flush=True)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 80 + "\n", flush=True)

    # Проверяем подключение к БД
    conn = get_db_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных. Проверьте настройки.", flush=True)
        sys.exit(1)
    else:
        conn.close()
        print("✅ Подключение к базе данных успешно установлено\n", flush=True)

    # Показываем текущую статистику
    print("📊 Текущая статистика БД:", flush=True)
    stats = get_database_stats_separate_tables()
    if stats:
        print(f"   - Всего монет: {stats['total_cryptos']}", flush=True)
        print(f"   - Монет с OHLC таблицами: {stats['cryptos_with_ohlc']}", flush=True)

        if stats['recent_cryptos']:
            print("\n   Последние монеты с OHLC:", flush=True)
            for crypto in stats['recent_cryptos'][:5]:
                print(
                    f"   - {crypto['name']} ({crypto['symbol']}) - таблица: {crypto['ohlc_table']}, записей: {crypto['ohlc_count']}",
                    flush=True)
        print()

    # Загружаем страницу
    html = fetch_page()

    if not html:
        print("❌ Не удалось загрузить страницу", flush=True)
        return

    # Парсим данные
    cryptos = parse_html_limited(html, limit=MAX_COINS)

    if cryptos:
        print(f"\n✅ Успешно распарсено {len(cryptos)} монет", flush=True)

        # Получаем OHLCV для монет старше 2 дней
        print(f"\n📊 Получение 4-часовых OHLCV данных для монет старше 2 дней...\n", flush=True)

        ohlcv_count = 0
        for crypto in cryptos:
            if is_older_than_two_days(crypto['added']):
                print(f"🔍 {crypto['name']} ({crypto['symbol']}) - монета старше 2 дней", flush=True)

                # Ищем ID монеты
                coin_id = search_coin_id(crypto['name'], crypto['symbol'])

                if coin_id:
                    time.sleep(3)  # Задержка для соблюдения лимитов API

                    # Получаем OHLCV данные
                    ohlcv = fetch_ohlc_data(coin_id, days=30)

                    if ohlcv:
                        crypto['ohlcv'] = ohlcv
                        crypto['coin_id'] = coin_id
                        ohlcv_count += 1
                else:
                    print(f"    ⚠️ Не удалось найти ID монеты\n", flush=True)
            else:
                print(f"ℹ️ {crypto['name']} ({crypto['symbol']}) - монета младше 2 дней, OHLC не требуется", flush=True)

        print(f"\n✅ Получено OHLCV для {ohlcv_count} монет", flush=True)

        # Сохраняем данные в БД с отдельными таблицами
        save_to_database_with_separate_tables(cryptos)

        # Показываем обновленную статистику
        print("\n📊 Обновленная статистика БД:", flush=True)
        stats = get_database_stats_separate_tables()
        if stats:
            print(f"   - Всего монет: {stats['total_cryptos']}", flush=True)
            print(f"   - Монет с OHLC таблицами: {stats['cryptos_with_ohlc']}", flush=True)

    else:
        print("\n❌ Не удалось найти данные о монетах", flush=True)

    print("\n✅ Парсер завершил работу", flush=True)
    print("=" * 80 + "\n", flush=True)


if __name__ == "__main__":
    main()