#!/usr/bin/env python3
"""
Минимальный парсер новых криптовалют с CoinGecko
Находит новые монеты и получает OHLC для монет старше 1 дня
"""
import urllib.request
import json
import os
import re
from datetime import datetime, timedelta
import time
import ssl
import psycopg2
import sys

# Настройки
BASE_URL = "https://www.coingecko.com/ru/new-cryptocurrencies"
API_BASE = "https://api.coingecko.com/api/v3"
MAX_COINS = int(os.environ.get('MAX_COINS', 30))
MIN_AGE_DAYS = 1  # Начинаем собирать OHLC после 1 дня

# Задержки для избежания блокировки
DELAYS = {
    'between_coins': 5,
    'before_search': 2,
    'after_ohlc': 3,
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
    """SSL контекст для HTTPS"""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def fetch_page():
    """Загружает страницу с новыми монетами"""
    print(f"🌐 Загрузка страницы CoinGecko...")

    try:
        req = urllib.request.Request(BASE_URL)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        req.add_header('Accept', 'text/html,application/xhtml+xml')

        context = create_ssl_context()
        response = urllib.request.urlopen(req, context=context, timeout=30)

        if response.info().get('Content-Encoding') == 'gzip':
            import gzip
            html = gzip.decompress(response.read()).decode('utf-8')
        else:
            html = response.read().decode('utf-8')

        print(f"✅ Страница загружена: {len(html)} байт")
        return html

    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return None


def parse_html(html):
    """Парсит HTML и извлекает данные о монетах"""
    print(f"🔍 Парсинг данных о монетах...")

    cryptos = []

    # Ищем строки таблицы
    table_pattern = r'<tr[^>]*class="[^"]*hover:tw-bg[^"]*"[^>]*>(.*?)</tr>'
    rows = re.findall(table_pattern, html, re.DOTALL)

    print(f"📊 Найдено строк: {len(rows)}, обработаем: {min(len(rows), MAX_COINS)}")

    for i, row in enumerate(rows[:MAX_COINS]):
        crypto = parse_row(row)
        if crypto:
            cryptos.append(crypto)
            print(f"  [{i + 1}] {crypto['name']} ({crypto['symbol']})")

    return cryptos


def parse_row(row_html):
    """Парсит одну строку таблицы"""
    crypto = {}

    # Извлекаем ячейки
    cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
    if len(cells) < 11:
        return None

    # Название и символ (ячейка 2) - улучшенный парсинг
    name_cell = cells[2]

    # Сначала ищем ссылку с названием монеты
    name_link = re.search(r'<a[^>]*href="[^"]*"[^>]*>([^<]+)</a>', name_cell)
    if name_link:
        crypto['name'] = name_link.group(1).strip()
    else:
        crypto['name'] = "Unknown"

    # Ищем символ в span с классом
    symbol_match = re.search(r'<span[^>]*class="[^"]*tw-text-gray-500[^"]*"[^>]*>([^<]+)</span>', name_cell)
    if symbol_match:
        crypto['symbol'] = symbol_match.group(1).strip()
    else:
        # Альтернативный поиск символа
        texts = re.findall(r'>([^<>]+)<', name_cell)
        crypto['symbol'] = ""
        for text in texts:
            clean = text.strip()
            if clean and len(clean) <= 10 and clean.isupper() and clean != crypto['name']:
                crypto['symbol'] = clean
                break

    # Остальные поля
    crypto['price'] = clean_text(cells[3]) if len(cells) > 3 else "N/A"
    crypto['change_24h'] = extract_percent(cells[4]) if len(cells) > 4 else "N/A"
    crypto['chain'] = clean_text(cells[5]) if len(cells) > 5 else "Unknown"
    crypto['market_cap'] = clean_text(cells[7]) if len(cells) > 7 else "N/A"
    crypto['fdv'] = clean_text(cells[9]) if len(cells) > 9 else "N/A"

    # Дата добавления
    added_text = clean_text(cells[10]) if len(cells) > 10 else "недавно"
    crypto['added'] = parse_date(added_text)
    crypto['added_raw'] = added_text

    return crypto


def clean_text(html):
    """Очищает HTML от тегов"""
    text = re.sub(r'<[^>]+>', '', html)
    return ' '.join(text.split()).strip()


def extract_percent(cell):
    """Извлекает процент из ячейки"""
    text = clean_text(cell)
    match = re.search(r'([-+]?\d+[,.]?\d*%)', text)
    return match.group(1) if match else text or "N/A"


def parse_date(text):
    """Преобразует текст даты в YYYY-MM-DD"""
    now = datetime.now()

    if "недавно" in text or "около 1 часа" in text:
        return now.strftime('%Y-%m-%d')

    # Извлекаем числа
    days_match = re.search(r'(\d+)\s*дн', text)
    if days_match:
        days = int(days_match.group(1))
        return (now - timedelta(days=days)).strftime('%Y-%m-%d')

    hours_match = re.search(r'(\d+)\s*час', text)
    if hours_match:
        hours = int(hours_match.group(1))
        return (now - timedelta(hours=hours)).strftime('%Y-%m-%d')

    return now.strftime('%Y-%m-%d')


def search_coin_id(name, symbol):
    """Ищет ID монеты в CoinGecko API с улучшенной проверкой"""
    print(f"  🔍 Поиск ID для {name} ({symbol})...")

    time.sleep(DELAYS['before_search'])

    # Пробуем разные варианты поиска
    search_queries = []
    if symbol:
        search_queries.append(symbol.lower())
    if name and name != "Unknown":
        search_queries.append(name.lower())

    for query in search_queries:
        if not query:
            continue

        url = f"{API_BASE}/search?query={urllib.parse.quote(query)}"

        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Accept', 'application/json')

            context = create_ssl_context()
            response = urllib.request.urlopen(req, context=context, timeout=15)
            data = json.loads(response.read().decode('utf-8'))

            if 'coins' in data and data['coins']:
                # Ищем точное совпадение по символу
                if symbol:
                    for coin in data['coins']:
                        if coin.get('symbol', '').upper() == symbol.upper():
                            # Проверяем, что это новая монета (не старая с таким же символом)
                            print(f"    ✅ Найден: {coin['id']}")
                            return coin['id']

                # Ищем по частичному совпадению названия
                if name and name != "Unknown":
                    name_lower = name.lower()
                    for coin in data['coins']:
                        coin_name = coin.get('name', '').lower()
                        if name_lower in coin_name or coin_name in name_lower:
                            print(f"    ⚠️ Найден по названию: {coin['id']}")
                            return coin['id']

                # Если точного нет, берем первый результат только если он подходящий
                first_coin = data['coins'][0]
                first_symbol = first_coin.get('symbol', '').upper()

                # Проверяем, что символы хотя бы частично совпадают
                if symbol and (first_symbol == symbol.upper() or
                               symbol.upper() in first_symbol or
                               first_symbol in symbol.upper()):
                    print(f"    ⚠️ Использован первый результат: {first_coin['id']}")
                    return first_coin['id']

        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    ⚠️ Rate limit, ожидание {DELAYS['rate_limit']} сек...")
                time.sleep(DELAYS['rate_limit'])
            else:
                print(f"    ❌ HTTP ошибка {e.code}")
        except Exception as e:
            print(f"    ❌ Ошибка: {e}")

    print(f"    ❌ ID не найден")
    return None


def fetch_ohlc(coin_id, age_days):
    """Получает OHLC данные с учетом возраста монеты"""
    # Ограничиваем количество дней для запроса
    # Для новых монет берем данные только за их время существования + 1 день
    days_to_fetch = min(age_days + 1, 30)

    url = f"{API_BASE}/coins/{coin_id}/ohlc?vs_currency=usd&days={days_to_fetch}"

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

            print(f"    ✅ Получено {len(ohlc_data)} свечей (за {days_to_fetch} дней)")
            time.sleep(DELAYS['after_ohlc'])
            return ohlc_data

    except Exception as e:
        print(f"    ❌ Ошибка OHLC: {e}")

    return None


def save_to_database(cryptos):
    """Сохраняет данные в БД"""
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    new_count = 0
    updated_count = 0
    ohlc_count = 0

    print("\n💾 Сохранение в БД...")

    try:
        for crypto in cryptos:
            # Проверяем существование
            cursor.execute("""
                SELECT id, ohlc_table_name, coin_gecko_id FROM cryptocurrencies 
                WHERE symbol = %s AND added_date = %s
            """, (crypto['symbol'], crypto['added']))

            existing = cursor.fetchone()

            if existing:
                crypto_id, ohlc_table, existing_coin_id = existing

                # Обновляем coin_gecko_id если он был найден, но еще не сохранен
                if crypto.get('coin_id') and not existing_coin_id:
                    cursor.execute("""
                        UPDATE cryptocurrencies 
                        SET coin_gecko_id = %s 
                        WHERE id = %s
                    """, (crypto['coin_id'], crypto_id))

                updated_count += 1
            else:
                # Вставляем новую монету
                cursor.execute("""
                    INSERT INTO cryptocurrencies 
                    (name, symbol, chain, price, change_24h, market_cap, 
                     fdv, added_date, added_raw, coin_gecko_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, ohlc_table_name
                """, (
                    crypto['name'], crypto['symbol'], crypto['chain'],
                    crypto['price'], crypto['change_24h'], crypto['market_cap'],
                    crypto['fdv'], crypto['added'], crypto['added_raw'],
                    crypto.get('coin_id')
                ))
                crypto_id, ohlc_table = cursor.fetchone()
                new_count += 1

            # Сохраняем OHLC если есть
            if 'ohlc' in crypto and crypto['ohlc'] and ohlc_table:
                for candle in crypto['ohlc']:
                    try:
                        cursor.execute(f"""
                            INSERT INTO {ohlc_table} 
                            (timestamp, datetime, date, time, open, high, low, close)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (timestamp) DO NOTHING
                        """, (
                            candle['timestamp'], candle['datetime'],
                            candle['date'], candle['time'],
                            candle['open'], candle['high'],
                            candle['low'], candle['close']
                        ))
                        if cursor.rowcount > 0:
                            ohlc_count += 1
                    except:
                        pass

            conn.commit()

    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    print(f"✅ Новых монет: {new_count}")
    print(f"✅ Обновлено: {updated_count}")
    print(f"✅ OHLC записей: {ohlc_count}")


def main():
    print("=" * 60)
    print("🚀 ПАРСЕР НОВЫХ КРИПТОВАЛЮТ")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Минимальный возраст для OHLC: {MIN_AGE_DAYS} день")
    print("=" * 60)

    # Проверка БД
    conn = get_db_connection()
    if not conn:
        sys.exit(1)
    conn.close()

    # Загружаем страницу
    html = fetch_page()
    if not html:
        print("❌ Не удалось загрузить страницу")
        return

    # Парсим данные
    cryptos = parse_html(html)
    print(f"\n✅ Найдено {len(cryptos)} монет")

    # Получаем OHLC для монет старше 1 дня
    print(f"\n📊 Получение OHLC данных (для монет старше {MIN_AGE_DAYS} дня)...")

    for i, crypto in enumerate(cryptos):
        if i > 0:
            time.sleep(DELAYS['between_coins'])

        # Проверяем возраст монеты
        age_days = (datetime.now() - datetime.strptime(crypto['added'], '%Y-%m-%d')).days

        if age_days >= MIN_AGE_DAYS:
            print(f"\n🔍 {crypto['name']} ({crypto['symbol']}) - {age_days} дней")

            # Ищем ID
            coin_id = search_coin_id(crypto['name'], crypto['symbol'])
            if coin_id:
                crypto['coin_id'] = coin_id

                # Получаем OHLC с учетом возраста
                ohlc = fetch_ohlc(coin_id, age_days)
                if ohlc:
                    crypto['ohlc'] = ohlc
        else:
            print(f"⏭️  {crypto['name']} - слишком новая ({age_days} дней, нужно минимум {MIN_AGE_DAYS})")

    # Сохраняем в БД
    save_to_database(cryptos)

    print("\n✅ Парсер завершил работу")
    print("=" * 60)


if __name__ == "__main__":
    main()