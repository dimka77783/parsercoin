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


def parse_html(html):
    """Парсит HTML и извлекает данные о монетах"""
    print("🔍 Парсинг HTML...", flush=True)

    cryptos = []

    try:
        # Сохраняем HTML для отладки
        save_html_debug(html)

        # Ищем таблицу с данными
        # Паттерн для поиска строк таблицы
        table_pattern = r'<tr[^>]*class="[^"]*hover:tw-bg[^"]*"[^>]*>(.*?)</tr>'
        rows = re.findall(table_pattern, html, re.DOTALL)

        print(f"📊 Найдено строк в таблице: {len(rows)}", flush=True)

        # Для отладки - выводим первую строку
        if rows and len(rows) > 0:
            print("🔍 Анализ первой строки для отладки...", flush=True)
            analyze_first_row(rows[0])

        for i, row in enumerate(rows):
            try:
                crypto = parse_row(row)
                if crypto:
                    cryptos.append(crypto)
                    print(f"✅ [{i + 1}] Найдена монета: {crypto['name']} ({crypto['symbol']})", flush=True)
            except Exception as e:
                print(f"⚠️ Ошибка при парсинге строки {i + 1}: {e}", flush=True)
                continue

        return cryptos

    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}", flush=True)
        return []


def analyze_first_row(row_html):
    """Анализирует первую строку для отладки"""
    print("\n--- АНАЛИЗ ПЕРВОЙ СТРОКИ ---", flush=True)

    # Извлекаем все ячейки
    td_pattern = r'<td[^>]*>(.*?)</td>'
    cells = re.findall(td_pattern, row_html, re.DOTALL)

    print(f"Найдено ячеек: {len(cells)}", flush=True)

    if len(cells) > 2:
        print(f"\nЯчейка с названием (индекс 2):", flush=True)
        name_cell = cells[2]
        # Выводим первые 500 символов
        print(name_cell[:500] + "..." if len(name_cell) > 500 else name_cell, flush=True)

        # Ищем все ссылки
        links = re.findall(r'<a[^>]*>([^<]+)</a>', name_cell)
        print(f"\nНайдено ссылок: {len(links)}", flush=True)
        for i, link in enumerate(links):
            print(f"  Ссылка {i + 1}: {link.strip()}", flush=True)

        # Ищем все span
        spans = re.findall(r'<span[^>]*>([^<]+)</span>', name_cell)
        print(f"\nНайдено span: {len(spans)}", flush=True)
        for i, span in enumerate(spans[:5]):  # Первые 5
            print(f"  Span {i + 1}: {span.strip()}", flush=True)

    print("--- КОНЕЦ АНАЛИЗА ---\n", flush=True)


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

    # Отладка - выводим содержимое ячейки для первой монеты
    if 'debug_shown' not in globals():
        globals()['debug_shown'] = True
        print("\n=== ОТЛАДКА ЯЧЕЙКИ С НАЗВАНИЕМ ===")
        print(name_cell[:1000])
        print("=== КОНЕЦ ОТЛАДКИ ===\n")

    # Ищем все текстовое содержимое между тегами
    # Паттерн для извлечения текста из различных тегов
    text_pattern = r'>([^<>]+)<'
    all_texts = re.findall(text_pattern, name_cell)

    # Фильтруем и ищем название
    crypto['name'] = "Unknown"
    crypto['symbol'] = ""

    # Отладка - показываем все найденные тексты для первой монеты
    if len(all_texts) > 0 and 'texts_shown' not in globals():
        globals()['texts_shown'] = True
        print("\n=== ВСЕ НАЙДЕННЫЕ ТЕКСТЫ ===")
        for i, text in enumerate(all_texts):
            clean = text.strip()
            if clean:
                print(f"{i}: '{clean}'")
        print("=== КОНЕЦ ТЕКСТОВ ===\n")

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

    # Проверяем данные data- атрибуты
    if crypto['name'] == "Unknown":
        data_pattern = r'data-[^=]+=["\'"]([^"\']+)["\'"]'
        data_matches = re.findall(data_pattern, name_cell)
        for data in data_matches:
            if data and len(data) > 2 and any(c.isalpha() for c in data) and not data.startswith('/'):
                crypto['name'] = data
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


def save_html_debug(html):
    """Сохраняет HTML для отладки"""
    try:
        log_dir = get_log_dir()
        debug_file = os.path.join(log_dir, 'last_page.html')
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"🔍 HTML сохранен для отладки: {debug_file}", flush=True)
    except Exception as e:
        print(f"⚠️ Не удалось сохранить HTML: {e}", flush=True)


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
        'cryptos': cryptos
    }

    # Сохраняем основной файл
    data_file = os.path.join(log_dir, 'new_cryptos.json')
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Данные сохранены: {data_file}", flush=True)
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}", flush=True)

    # Сохраняем историю
    history_file = os.path.join(log_dir, f'cryptos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"📄 История сохранена: {history_file}", flush=True)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения истории: {e}", flush=True)


def generate_report(cryptos):
    """Генерирует текстовый отчет"""
    log_dir = get_log_dir()
    report_file = os.path.join(log_dir, 'new_cryptos_report.txt')

    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("НОВЫЕ КРИПТОВАЛЮТЫ НА COINGECKO\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Источник: {BASE_URL}\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Всего найдено: {len(cryptos)} монет\n\n")

            # Группировка по платформам
            platforms = {}
            for crypto in cryptos:
                platform = crypto.get('chain', 'Unknown')
                if platform not in platforms:
                    platforms[platform] = []
                platforms[platform].append(crypto)

            f.write("РАСПРЕДЕЛЕНИЕ ПО ПЛАТФОРМАМ:\n")
            for platform, coins in sorted(platforms.items(), key=lambda x: len(x[1]), reverse=True):
                f.write(f"  {platform}: {len(coins)} монет\n")

            f.write("\n" + "-" * 60 + "\n")
            f.write("СПИСОК МОНЕТ:\n\n")

            for i, crypto in enumerate(cryptos, 1):
                f.write(f"{i}. {crypto['name']} ({crypto['symbol']})\n")
                f.write(f"   Платформа: {crypto['chain']}\n")
                f.write(f"   Цена: {crypto['price']}\n")
                f.write(f"   Изменение 24ч: {crypto['change_24h']}\n")
                f.write(f"   Market Cap: {crypto['market_cap']}\n")
                f.write(f"   FDV: {crypto['fdv']}\n")
                f.write(f"   Добавлено: {crypto['added_raw']} ({crypto['added']})\n")
                f.write("\n")

        print(f"📊 Отчет создан: {report_file}", flush=True)
    except Exception as e:
        print(f"❌ Ошибка создания отчета: {e}", flush=True)


def main():
    print("=" * 60, flush=True)
    print("🚀 ПАРСЕР НОВЫХ КРИПТОВАЛЮТ COINGECKO", flush=True)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 60 + "\n", flush=True)

    # Загружаем страницу
    html = fetch_page()

    if not html:
        print("❌ Не удалось загрузить страницу", flush=True)
        # Сохраняем пустой результат
        save_data([])
        return

    # Парсим данные
    cryptos = parse_html(html)

    if cryptos:
        print(f"\n✅ Успешно распарсено {len(cryptos)} монет", flush=True)

        # Сохраняем данные
        save_data(cryptos)

        # Генерируем отчет
        generate_report(cryptos)

        # Выводим краткую сводку
        print("\n📈 КРАТКАЯ СВОДКА:", flush=True)
        for crypto in cryptos[:5]:
            print(f"  • {crypto['name']} ({crypto['symbol']}) - {crypto['chain']} - {crypto['price']}", flush=True)
        if len(cryptos) > 5:
            print(f"  ... и еще {len(cryptos) - 5} монет", flush=True)
    else:
        print("\n❌ Не удалось найти данные о монетах", flush=True)
        save_data([])

    print("\n✅ Парсер завершил работу", flush=True)
    print("=" * 60 + "\n", flush=True)


if __name__ == "__main__":
    main()