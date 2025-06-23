from selenium import webdriver
from bs4 import BeautifulSoup
import csv
import time
import os
from datetime import datetime, timedelta

# Заголовки (для имитации браузера)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36',
}

BASE_URL = "https://www.coingecko.com/ru"


def setup_browser():
    """Создаёт драйвер браузера"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # фоновый режим
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('blink-settings=imagesEnabled=false')

    driver = webdriver.Chrome(options=options)
    return driver


def parse_added_date(added_text):
    """Преобразует относительные временные метки в формат ГГГГ-ММ-ДД"""
    now = datetime.now()
    if "около 1 часа" in added_text:
        added_date = now - timedelta(hours=1)
    elif "около 1 дня" in added_text:
        added_date = now - timedelta(days=1)
    elif "около 2 дней" in added_text:
        added_date = now - timedelta(days=2)
    elif "недавно" in added_text:
        added_date = now - timedelta(minutes=30)
    else:
        # Попытка парсинга стандартной даты
        try:
            added_date = datetime.strptime(added_text, '%Y-%m-%d')
        except ValueError:
            added_date = now - timedelta(hours=1)  # По умолчанию — около 1 часа назад

    return added_date.strftime('%Y-%m-%d')


def fetch_new_cryptos(limit=3):
    url = "https://www.coingecko.com/ru/new-cryptocurrencies"
    print(f"🌐 Загрузка главной страницы: {url}")

    driver = setup_browser()
    driver.get(url)
    time.sleep(5)  # Ждём загрузки JS
    html = driver.page_source
    driver.quit()

    with open("selenium_debug.html", "w", encoding="utf-8") as f:
        f.write(html)

    soup = BeautifulSoup(html, 'html.parser')

    # Ищем таблицу с новыми монетами
    table = soup.find('table', {'class': lambda c: c and 'tw-border-y' in c and 'tw-border-gray-200' in c and 'dark:tw-border-moon-700' in c and 'tw-divide-y' in c and 'tw-divide-gray-200' in c and 'dark:tw-divide-moon-700' in c and '[&>tbody:first-of-type]:!tw-border-t-0' in c and 'tw-w-full' in c and 'sortable' in c})
    if not table:
        print("❌ Не найдена таблица с новыми монетами")
        return []

    # Ищем все строки с нужным классом
    rows = table.find_all('tr', {'class': lambda c: c and 'hover:tw-bg' in c})

    if not rows:
        print("❌ Не найдены строки с новыми монетами")
        return []

    cryptos = []
    count = 0

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 10:
            print(f"⚠️ Строка пропущена — недостаточно колонок: {len(cols)}")
            continue

        name_tag = cols[2].find('a')
        name = name_tag.get_text(strip=True) if name_tag else "Без имени"

        chain = cols[5].get_text(strip=True) if len(cols) > 5 else "–"

        fdv = cols[9].get_text(strip=True) if len(cols) > 9 else "N/A"

        added_text = cols[10].get_text(strip=True) if len(cols) > 10 else "–"
        added_date = parse_added_date(added_text)

        cryptos.append({
            'name': name,
            'chain': chain,
            'fdv': fdv,
            'added': added_date
        })

        print(f"✅ Найдена монета: {name} → FDV: {fdv}, Добавлен: {added_date}")
        count += 1

        if count >= limit:
            break

        time.sleep(2)

    save_crypto_data_to_csv(cryptos)
    return cryptos


def save_crypto_data_to_csv(data, filename="new_cryptocurrencies_full.csv"):
    """Сохраняет все данные о монетах в CSV"""
    fieldnames = ['name', 'chain', 'fdv', 'added']

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"\n✅ Полные данные сохранены в {os.path.abspath(filename)}")
    except Exception as e:
        print(f"❌ Ошибка при сохранении full CSV: {e}")


if __name__ == "__main__":
    print("🔄 Запуск парсера новых криптовалют...\n")
    new_cryptos = fetch_new_cryptos(limit=3)

    if new_cryptos:
        print(f"\n📊 Найдено монет: {len(new_cryptos)}")
    else:
        print("\n❌ Новых монет не найдено.")