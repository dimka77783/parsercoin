from selenium import webdriver
from bs4 import BeautifulSoup
import csv
import time
import os

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


def fetch_new_cryptos(limit=10):
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

    # Ищем все строки с нужным классом
    rows = soup.find_all('tr', {'class': lambda c: c and 'hover:tw-bg' in c})

    if not rows:
        print("❌ Не найдены строки с новыми монетами")
        return []

    cryptos = []
    count = 0

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 6:
            continue

        name_tag = cols[2].find('a')
        name = name_tag.get_text(strip=True) if name_tag else None

        symbol = cols[3].get_text(strip=True).lower() if len(cols) > 3 else None

        added = cols[5].get_text(strip=True) if len(cols) > 5 else None

        link_tag = cols[2].find('a', href=True)
        coin_page_url = BASE_URL + link_tag['href'].replace('/ru/', '/', 1).replace('//', '/') if link_tag else None

        cryptos.append({
            'name': name,
            'symbol': symbol,
            'added': added,
            'url': coin_page_url
        })

        print(f"✅ Найдена монета: {name} ({symbol})")
        count += 1

        if count >= limit:
            break

    save_crypto_data_to_csv(cryptos)
    save_coin_names_to_file(cryptos)

    return cryptos


def save_crypto_data_to_csv(data, filename="new_cryptocurrencies.csv"):
    fieldnames = ['name', 'symbol', 'added', 'url']

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"\n✅ Данные сохранены в {os.path.abspath(filename)}")
    except Exception as e:
        print(f"❌ Ошибка при сохранении full CSV: {e}")


def save_coin_names_to_file(data, filename="newcoin.csv"):
    if not data:
        print("❌ Нет данных для сохранения в newcoin.csv")
        return []

    fieldnames = ['name', 'symbol']

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for crypto in data:
                writer.writerow({'name': crypto['name'], 'symbol': crypto['symbol']})
        print(f"✅ Список монет сохранён в {os.path.abspath(filename)}")
    except Exception as e:
        print(f"❌ Ошибка при сохранении newcoin.csv: {e}")


if __name__ == "__main__":
    print("🔄 Запуск парсера новых криптовалют...\n")
    new_cryptos = fetch_new_cryptos(limit=10)

    if new_cryptos:
        print(f"\n📊 Найдено монет: {len(new_cryptos)}")
    else:
        print("\n❌ Новых монет не найдено.")