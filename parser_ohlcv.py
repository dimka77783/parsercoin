#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json
import os
import re
from datetime import datetime, timedelta
import time
import ssl

# URL страницы с новыми криптовалютами
BASE_URL = "https://www.coingecko.com/ru/new-cryptocurrencies"
API_BASE = "https://api.coingecko.com/api/v3"

# Количество монет для парсинга
MAX_COINS = 50


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
        # Создаем запрос с заголовками
        req = urllib.request.Request(BASE_URL)
        req.add_header('User-Agent',
                       'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
        req.add_header('Accept',
                       'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8')
        req.add_header('Accept-Language', 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7')
        req.add_header('Accept-Encoding', 'gzip, deflate')
        req.add_header('Connection', 'keep-alive')
        req.add_header('Upgrade-Insecure-Requests', '1')

        # Выполняем запрос
        context = create_ssl_context()
        response = urllib.request.urlopen(req, context=context, timeout=30)

        # Читаем ответ
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
    """Ищет ID монеты в CoinGecko API с обработкой rate limit"""
    print(f"  🔍 Поиск ID для {coin_name} ({coin_symbol})...", flush=True)

    # Преобразуем символ в нижний регистр для поиска
    search_query = coin_symbol.lower()
    url = f"{API_BASE}/search?query={urllib.parse.quote(search_query)}"

    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')

        context = create_ssl_context()
        response = urllib.request.urlopen(req, context=context, timeout=15)
        data = json.loads(response.read().decode('utf-8'))

        # Ищем точное совпадение по символу
        if 'coins' in data:
            for coin in data['coins']:
                if coin.get('symbol', '').upper() == coin_symbol.upper():
                    found_id = coin['id']
                    found_name = coin.get('name', '')
                    found_symbol = coin.get('symbol', '').upper()

                    # Проверка соответствия
                    print(f"    📌 Найден кандидат: {found_name} ({found_symbol}) - ID: {found_id}", flush=True)

                    # Проверяем соответствие названия
                    if coin_name.lower() in found_name.lower() or found_name.lower() in coin_name.lower():
                        print(f"    ✅ Подтверждено совпадение по названию и символу", flush=True)
                        return found_id
                    else:
                        print(f"    ⚠️ Название не совпадает: ожидалось '{coin_name}', найдено '{found_name}'",
                              flush=True)
                        # Продолжаем поиск

        # Если не нашли по символу, пробуем по названию
        search_query = coin_name.lower()
        url = f"{API_BASE}/search?query={urllib.parse.quote(search_query)}"

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')

        response = urllib.request.urlopen(req, context=context, timeout=15)
        data = json.loads(response.read().decode('utf-8'))

        if 'coins' in data and len(data['coins']) > 0:
            # Проверяем результаты поиска по названию
            best_match = None
            for coin in data['coins'][:5]:  # Проверяем первые 5 результатов
                found_id = coin['id']
                found_name = coin.get('name', '')
                found_symbol = coin.get('symbol', '').upper()

                print(f"    📌 Кандидат по названию: {found_name} ({found_symbol}) - ID: {found_id}", flush=True)

                # Проверяем точное совпадение символа
                if found_symbol == coin_symbol.upper():
                    print(f"    ✅ Найдено точное совпадение по символу: {found_name} ({found_symbol})", flush=True)
                    return found_id

                # Проверяем перевернутое совпадение (например, "3D (MAN)" vs "MAN (3D)")
                if (coin_name.upper() == found_symbol and coin_symbol.upper() == found_name.upper()) or \
                        (f"{coin_symbol} ({coin_name})" == f"{found_name} ({found_symbol})") or \
                        (f"{coin_name} ({coin_symbol})" == f"{found_symbol} ({found_name})"):
                    print(f"    ✅ Найдено перевернутое совпадение: {found_name} ({found_symbol})", flush=True)
                    return found_id

                # Сохраняем первый результат как запасной
                if not best_match:
                    best_match = coin

            # Если точного совпадения нет, используем лучший найденный результат
            if best_match:
                print(
                    f"    ⚠️ Точное совпадение не найдено. Используется: {best_match.get('name', '')} ({best_match.get('symbol', '')})",
                    flush=True)
                return best_match['id']

    except urllib.error.HTTPError as e:
        if e.code == 429 and retry_count < 3:
            wait_time = 60 * (retry_count + 1)  # 60, 120, 180 секунд
            print(f"    ⚠️ Rate limit превышен. Ожидание {wait_time} секунд...", flush=True)
            time.sleep(wait_time)
            return search_coin_id(coin_name, coin_symbol, retry_count + 1)
        else:
            print(f"    ❌ Ошибка поиска: {e}", flush=True)
    except Exception as e:
        print(f"    ❌ Ошибка поиска: {e}", flush=True)

    return None


def fetch_ohlc_data(coin_id, days=30, retry_count=0):
    """Получает OHLCV данные для монеты с 4-часовым таймфреймом"""
    url = f"{API_BASE}/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"

    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')

        context = create_ssl_context()
        response = urllib.request.urlopen(req, context=context, timeout=15)

        data = json.loads(response.read().decode('utf-8'))

        # Обрабатываем OHLC данные (4-часовые свечи)
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


def search_alternative_coin_id(coin_name, coin_symbol, exclude_ids, retry_count=0):
    """Ищет альтернативный ID монеты, исключая уже проверенные"""
    if isinstance(exclude_ids, str):
        exclude_ids = [exclude_ids]

    print(f"    🔎 Поиск альтернативных ID для {coin_name} ({coin_symbol}), исключая {', '.join(exclude_ids)}...",
          flush=True)

    # Пробуем различные варианты поиска
    search_queries = [
        f"{coin_symbol} new",
        f"{coin_name} 2025",
        f"{coin_symbol} v2",
        f"new {coin_symbol}",
        coin_name.lower(),
        coin_symbol.lower()
    ]

    found_alternatives = []

    for query in search_queries:
        url = f"{API_BASE}/search?query={urllib.parse.quote(query)}"

        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Accept', 'application/json')

            context = create_ssl_context()
            response = urllib.request.urlopen(req, context=context, timeout=15)
            data = json.loads(response.read().decode('utf-8'))

            if 'coins' in data:
                for coin in data['coins']:
                    found_id = coin['id']
                    found_symbol = coin.get('symbol', '').upper()

                    # Если символ совпадает и ID не в списке исключений
                    if found_symbol == coin_symbol.upper() and found_id not in exclude_ids:
                        if found_id not in [alt['id'] for alt in found_alternatives]:
                            found_alternatives.append({
                                'id': found_id,
                                'name': coin.get('name', ''),
                                'symbol': found_symbol
                            })
                            print(
                                f"    📍 Найдена альтернатива: {coin.get('name', '')} ({found_symbol}) - ID: {found_id}",
                                flush=True)

            # Небольшая задержка между запросами
            if query != search_queries[-1]:
                time.sleep(1)

        except urllib.error.HTTPError as e:
            if e.code == 429 and retry_count < 1:
                print(f"    ⚠️ Rate limit при поиске альтернатив. Ожидание 30 секунд...", flush=True)
                time.sleep(30)
                return search_alternative_coin_id(coin_name, coin_symbol, exclude_ids, retry_count + 1)
        except Exception:
            continue

    return found_alternatives


def get_coin_age_days(added_date_str):
    """Получает возраст монеты в днях"""
    try:
        added_date = datetime.strptime(added_date_str, '%Y-%m-%d')
        now = datetime.now()
        days_diff = (now - added_date).days
        return days_diff
    except:
        return 0


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
    """Парсит HTML и извлекает данные только о первых N монетах"""
    print(f"🔍 Парсинг HTML (ограничение: {limit} монет)...", flush=True)

    cryptos = []

    try:
        # Ищем таблицу с данными
        table_pattern = r'<tr[^>]*class="[^"]*hover:tw-bg[^"]*"[^>]*>(.*?)</tr>'
        rows = re.findall(table_pattern, html, re.DOTALL)

        print(f"📊 Найдено строк в таблице: {len(rows)}", flush=True)
        print(f"🎯 Будут обработаны первые {limit} строк", flush=True)

        # Обрабатываем только первые N строк
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

    # Извлекаем все ячейки <td>
    td_pattern = r'<td[^>]*>(.*?)</td>'
    cells = re.findall(td_pattern, row_html, re.DOTALL)

    if len(cells) < 11:
        return None

    # Индекс 2 - название и символ
    name_cell = cells[2]

    # Ищем все текстовое содержимое между тегами
    text_pattern = r'>([^<>]+)<'
    all_texts = re.findall(text_pattern, name_cell)

    # Фильтруем и ищем название
    crypto['name'] = "Unknown"
    crypto['symbol'] = ""

    # Ищем название среди всех текстов
    for text in all_texts:
        clean = text.strip()
        if clean and len(clean) > 1:
            # Пропускаем числа и специальные символы
            if not clean.startswith('$') and not clean.startswith('%') and not clean.replace(',', '').replace('.',
                                                                                                              '').isdigit():
                # Если текст содержит буквы, это может быть название
                if any(c.isalpha() for c in clean):
                    # Проверяем, не является ли это символом (обычно короткий и в верхнем регистре)
                    if len(clean) > 5 or not clean.isupper():
                        crypto['name'] = clean
                        break
                    elif crypto['symbol'] == "":
                        crypto['symbol'] = clean

    # Альтернативный метод - ищем в img alt атрибутах
    if crypto['name'] == "Unknown":
        img_pattern = r'<img[^>]*alt="([^"]+)"[^>]*>'
        img_match = re.search(img_pattern, name_cell)
        if img_match:
            crypto['name'] = img_match.group(1).strip()

    # Еще один метод - ищем в title атрибутах
    if crypto['name'] == "Unknown":
        title_pattern = r'title="([^"]+)"'
        title_matches = re.findall(title_pattern, name_cell)
        for title in title_matches:
            if title and len(title) > 2 and not title.startswith('$'):
                crypto['name'] = title
                break

    # Извлекаем символ если еще не нашли
    if not crypto['symbol']:
        # Ищем короткие тексты в верхнем регистре
        for text in all_texts:
            clean = text.strip()
            if clean and 2 <= len(clean) <= 10 and clean.isupper() and clean.isalpha():
                crypto['symbol'] = clean
                break

    # Остальные поля парсим как раньше
    # Индекс 3 - цена
    price_text = clean_text(cells[3]) if len(cells) > 3 else ""
    crypto['price'] = price_text if price_text else "N/A"

    # Индекс 4 - изменение за 24ч
    change_text = clean_text(cells[4]) if len(cells) > 4 else ""
    percent_match = re.search(r'([-+]?\d+[,.]?\d*%)', change_text)
    if percent_match:
        crypto['change_24h'] = percent_match.group(1)
    else:
        crypto['change_24h'] = change_text if change_text else "N/A"

    # Индекс 5 - блокчейн/платформа
    crypto['chain'] = clean_text(cells[5]) if len(cells) > 5 else "Unknown"

    # Индекс 7 - Market Cap
    crypto['market_cap'] = clean_text(cells[7]) if len(cells) > 7 else "N/A"

    # Индекс 9 - FDV
    crypto['fdv'] = clean_text(cells[9]) if len(cells) > 9 else "N/A"

    # Индекс 10 - дата добавления
    added_text = clean_text(cells[10]) if len(cells) > 10 else "недавно"
    crypto['added'] = parse_added_date(added_text)
    crypto['added_raw'] = added_text

    # Добавляем метаданные
    crypto['parsed_at'] = datetime.now().isoformat()

    return crypto


def clean_text(html):
    """Очищает HTML от тегов и лишних пробелов"""
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', html)
    # Удаляем лишние пробелы
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
        # Извлекаем количество часов
        hours_match = re.search(r'около (\d+) час', added_text)
        if hours_match:
            hours = int(hours_match.group(1))
            return (now - timedelta(hours=hours)).strftime('%Y-%m-%d')
    elif "около 1 дня" in added_text or "около дня" in added_text:
        return (now - timedelta(days=1)).strftime('%Y-%m-%d')
    elif "около" in added_text and "дн" in added_text:
        # Извлекаем количество дней
        days_match = re.search(r'около (\d+) дн', added_text)
        if days_match:
            days = int(days_match.group(1))
            return (now - timedelta(days=days)).strftime('%Y-%m-%d')
    elif "дн" in added_text:
        # Простой формат "1 день", "2 дня"
        days_match = re.search(r'(\d+)\s*дн', added_text)
        if days_match:
            days = int(days_match.group(1))
            return (now - timedelta(days=days)).strftime('%Y-%m-%d')

    # По умолчанию - сегодня
    return now.strftime('%Y-%m-%d')


def get_log_dir():
    """Возвращает директорию для логов"""
    for path in ['/app/logs', './logs', '.']:
        if os.path.exists(path) and os.access(path, os.W_OK):
            return path
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except:
            continue
    return '.'


def save_data(cryptos):
    """Сохраняет данные в JSON"""
    log_dir = get_log_dir()

    # Основной файл данных
    data = {
        'timestamp': datetime.now().isoformat(),
        'source': BASE_URL,
        'count': len(cryptos),
        'limit': MAX_COINS,
        'cryptos': cryptos
    }

    # Сохраняем основной файл
    data_file = os.path.join(log_dir, 'last_50_cryptos.json')
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Данные сохранены: {data_file}", flush=True)
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}", flush=True)

    # Сохраняем историю
    history_file = os.path.join(log_dir, f'last_50_cryptos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"📄 История сохранена: {history_file}", flush=True)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения истории: {e}", flush=True)


def generate_report(cryptos):
    """Генерирует отчет с OHLCV данными"""
    log_dir = get_log_dir()
    report_file = os.path.join(log_dir, 'last_50_cryptos_report.txt')

    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ПОСЛЕДНИЕ 50 НОВЫХ КРИПТОВАЛЮТ НА COINGECKO\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Источник: {BASE_URL}\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Всего найдено: {len(cryptos)} монет\n")

            # Считаем монеты с OHLCV
            coins_with_ohlcv = sum(1 for c in cryptos if 'ohlcv' in c and c['ohlcv'])
            f.write(f"Монет с OHLCV данными (старше 2 дней): {coins_with_ohlcv}\n\n")

            f.write("СПИСОК МОНЕТ:\n")
            f.write("-" * 80 + "\n")

            for i, crypto in enumerate(cryptos, 1):
                f.write(f"\n{i}. {crypto['name']} ({crypto['symbol']})\n")
                f.write(f"   Платформа: {crypto['chain']}\n")
                f.write(f"   Цена: {crypto['price']}\n")
                f.write(f"   Изменение 24ч: {crypto['change_24h']}\n")
                f.write(f"   Market Cap: {crypto['market_cap']}\n")
                f.write(f"   FDV: {crypto['fdv']}\n")
                f.write(f"   Добавлено: {crypto['added_raw']} ({crypto['added']})\n")

                # Если есть OHLCV данные
                if 'ohlcv' in crypto and crypto['ohlcv']:
                    f.write(f"   📊 OHLCV данные (последние 10 свечей, 4-часовой таймфрейм):\n")
                    for j, candle in enumerate(crypto['ohlcv'][-10:]):
                        # Форматируем полную дату и время
                        full_datetime = datetime.fromisoformat(candle['datetime']).strftime('%Y-%m-%d %H:%M:%S')
                        f.write(
                            f"      {j + 1}. {full_datetime} - O: {candle['open']:.8f}, H: {candle['high']:.8f}, L: {candle['low']:.8f}, C: {candle['close']:.8f}\n")

        print(f"📊 Отчет создан: {report_file}", flush=True)
    except Exception as e:
        print(f"❌ Ошибка создания отчета: {e}", flush=True)


def main():
    print("=" * 80, flush=True)
    print("🚀 ПАРСЕР ПОСЛЕДНИХ 50 НОВЫХ КРИПТОВАЛЮТ COINGECKO С OHLCV", flush=True)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 80 + "\n", flush=True)

    # Загружаем страницу
    html = fetch_page()

    if not html:
        print("❌ Не удалось загрузить страницу", flush=True)
        save_data([])
        return

    # Парсим данные с ограничением
    cryptos = parse_html_limited(html, limit=MAX_COINS)

    if cryptos:
        print(f"\n✅ Успешно распарсено {len(cryptos)} монет", flush=True)

        # Проверяем какие монеты старше 2 дней и получаем для них OHLCV
        print(f"\n📊 Получение 4-часовых OHLCV данных для монет старше 2 дней...\n", flush=True)

        ohlcv_count = 0
        for crypto in cryptos:
            if is_older_than_two_days(crypto['added']):
                print(f"🔍 {crypto['name']} ({crypto['symbol']}) - монета старше 2 дней", flush=True)

                # Ищем ID монеты
                coin_id = search_coin_id(crypto['name'], crypto['symbol'])

                if coin_id:
                    # Увеличенная задержка для соблюдения лимитов API
                    time.sleep(3)  # Увеличено с 1.5 до 3 секунд

                    # Получаем OHLCV данные с 4-часовым таймфреймом
                    ohlcv = fetch_ohlc_data(coin_id, days=30)  # За последние 30 дней

                    if ohlcv:
                        # Проверяем соответствие количества свечей возрасту монеты
                        coin_age_days = get_coin_age_days(crypto['added'])
                        max_expected_candles = (coin_age_days * 24) // 4 + 6  # +6 для погрешности
                        actual_candles = len(ohlcv)

                        print(
                            f"    📊 Проверка данных: возраст монеты {coin_age_days} дней, ожидается макс. {max_expected_candles} свечей",
                            flush=True)
                        print(f"    📊 Получено свечей: {actual_candles}", flush=True)

                        if actual_candles > max_expected_candles * 2:  # Если свечей в 2 раза больше ожидаемого
                            print(
                                f"    ⚠️ ВНИМАНИЕ: Количество свечей ({actual_candles}) не соответствует возрасту монеты ({coin_age_days} дней)",
                                flush=True)
                            print(f"    ⚠️ Возможно, найдена другая монета с похожим названием!", flush=True)

                            # Проверяем первую свечу
                            if ohlcv:
                                first_candle_date = datetime.fromisoformat(ohlcv[0]['datetime'])
                                days_since_first_candle = (datetime.now() - first_candle_date).days
                                print(
                                    f"    📅 Первая свеча датирована: {first_candle_date.strftime('%Y-%m-%d')} ({days_since_first_candle} дней назад)",
                                    flush=True)

                            # Пробуем найти другую монету с таким же символом
                            print(f"    🔄 Продолжаем поиск более новой монеты {crypto['name']} ({crypto['symbol']})...",
                                  flush=True)

                            # Список уже проверенных ID
                            checked_ids = [coin_id]
                            found_suitable = False

                            # Поиск альтернативных ID
                            alternatives = search_alternative_coin_id(crypto['name'], crypto['symbol'], checked_ids)

                            # Проверяем все найденные альтернативы
                            for alt in alternatives:
                                if found_suitable:
                                    break

                                alternative_id = alt['id']
                                print(f"    🔍 Проверяем альтернативную монету: {alt['name']} - ID: {alternative_id}",
                                      flush=True)
                                time.sleep(3)

                                # Получаем OHLCV для альтернативной монеты
                                alt_ohlcv = fetch_ohlc_data(alternative_id, days=30)

                                if alt_ohlcv:
                                    alt_candles_count = len(alt_ohlcv)
                                    print(f"    📊 Альтернативная монета: получено {alt_candles_count} свечей",
                                          flush=True)

                                    # Проверяем первую свечу альтернативной монеты
                                    alt_first_candle_date = datetime.fromisoformat(alt_ohlcv[0]['datetime'])
                                    alt_days_since_first = (datetime.now() - alt_first_candle_date).days
                                    print(
                                        f"    📅 Первая свеча: {alt_first_candle_date.strftime('%Y-%m-%d')} ({alt_days_since_first} дней назад)",
                                        flush=True)

                                    # Если альтернативная монета подходит по возрасту
                                    if alt_candles_count <= max_expected_candles * 1.5:
                                        print(f"    ✅ Найдена подходящая монета! Используем ID: {alternative_id}",
                                              flush=True)
                                        crypto['ohlcv'] = alt_ohlcv
                                        crypto['coin_id'] = alternative_id
                                        crypto['candles_count'] = alt_candles_count
                                        crypto['expected_max_candles'] = max_expected_candles
                                        ohlcv_count += 1
                                        found_suitable = True
                                        break
                                    else:
                                        print(
                                            f"    ❌ Монета {alternative_id} тоже слишком старая ({alt_candles_count} свечей)",
                                            flush=True)
                                        checked_ids.append(alternative_id)

                            # Если не нашли подходящую монету среди альтернатив
                            if not found_suitable:
                                print(f"    ❌ Не найдено подходящих альтернатив среди {len(alternatives)} кандидатов",
                                      flush=True)
                                # Сохраняем первоначальные данные с предупреждением
                                crypto['ohlcv'] = ohlcv
                                crypto['coin_id'] = coin_id
                                crypto['candles_count'] = actual_candles
                                crypto['expected_max_candles'] = max_expected_candles
                                crypto[
                                    'warning'] = f"Возможно неверная монета: ожидалось {max_expected_candles} свечей, получено {actual_candles}"
                                ohlcv_count += 1
                        else:
                            # Если количество свечей соответствует ожиданиям
                            crypto['ohlcv'] = ohlcv
                            crypto['coin_id'] = coin_id
                            crypto['candles_count'] = actual_candles
                            crypto['expected_max_candles'] = max_expected_candles
                            ohlcv_count += 1
                else:
                    print(f"    ⚠️ Не удалось найти ID монеты\n", flush=True)
            else:
                print(f"ℹ️ {crypto['name']} ({crypto['symbol']}) - монета младше 2 дней, OHLCV не требуется",
                      flush=True)

        print(f"\n✅ Получено OHLCV для {ohlcv_count} монет", flush=True)

        # Сохраняем данные
        save_data(cryptos)

        # Генерируем отчет
        generate_report(cryptos)

        # Выводим краткую сводку в консоль
        print("\n📈 ПОСЛЕДНИЕ 50 МОНЕТ:", flush=True)
        print("-" * 100, flush=True)
        for i, crypto in enumerate(cryptos, 1):
            has_ohlcv = "✓" if 'ohlcv' in crypto and crypto['ohlcv'] else " "
            print(
                f"{i:2d}. [{has_ohlcv}] {crypto['name']:<25} ({crypto['symbol']:<10}) - {crypto['chain']:<15} - {crypto['added_raw']}",
                flush=True)
        print("-" * 100, flush=True)
        print(f"[✓] - монеты с OHLCV данными ({ohlcv_count} шт.)", flush=True)

    else:
        print("\n❌ Не удалось найти данные о монетах", flush=True)
        save_data([])

    print("\n✅ Парсер завершил работу", flush=True)
    print("=" * 80 + "\n", flush=True)


if __name__ == "__main__":
    main()