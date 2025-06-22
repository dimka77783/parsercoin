import requests
from bs4 import BeautifulSoup
import time
import csv

# Заголовки для имитации браузера
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}

# Базовый URL по ТВОЕМУ запросу
BASE_URL = "https://www.coingecko.com/ru/new-cryptocurrencies/"


def slugify(name):
    """Преобразует имя монеты в URL-friendly строку"""
    return name.strip().lower().replace(' ', '-')


def get_market_cap_from_coin_page(url, max_retries=3):
    """Получает Market Cap с внутренней страницы монеты"""
    if not url or url == "Нет ссылки":
        print("🚫 Пропущена монета: отсутствует ссылка")
        return "Нет данных"

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Ищем блоки с классом no-wrap и пытаемся найти Market Cap
                no_wrap_blocks = soup.find_all('div', {'class': 'no-wrap'})

                for block in no_wrap_blocks:
                    text = block.get_text(strip=True)
                    if 'market cap' in text.lower():
                        return text

                # Если не нашли точное совпадение — возьмём первый
                if no_wrap_blocks:
                    return no_wrap_blocks[0].get_text(strip=True)

                return "Не найдено"
            elif response.status_code == 403:
                print(f"❌ Ошибка 403 при открытии {url}")
                time.sleep(10)
            else:
                print(f"Ошибка {response.status_code} при открытии {url}")
                time.sleep(3 * attempt)
        except Exception as e:
            print(f"Исключение ({attempt} попытка): {e}")
            time.sleep(3 * attempt)

    return "Ошибка загрузки"


def save_market_caps_to_csv(data, filename="market_caps.csv"):
    """Сохраняет данные в CSV"""
    fieldnames = ['name', 'symbol', 'url', 'market_cap']

    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"\n✅ Данные сохранены в {filename}")


def read_coins_from_csv(filename="newcoin.csv"):
    """Читает список монет из CSV"""
    coins = []

    try:
        with open(filename, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                coins.append({
                    'name': row.get('name', 'Без имени'),
                    'symbol': row.get('symbol', '—')
                })
    except FileNotFoundError:
        print(f"❌ Файл {filename} не найден")
        return []

    return coins


def main():
    print("🔄 Запуск получения данных о капитализации...\n")

    # Читаем список монет из файла newcoin.csv
    cryptos = read_coins_from_csv()

    if not cryptos:
        print("❌ Нет данных для обработки")
        return

    results = []

    for crypto in cryptos:
        name = crypto.get('name', 'Без имени')
        symbol = crypto.get('symbol', '—')

        # Формируем именно ТАКОЙ URL
        coin_url = BASE_URL + slugify(name)

        print(f"🔍 Получение данных для: {name} ({symbol})")
        market_cap = get_market_cap_from_coin_page(coin_url)
        print(f"📈 Капитализация: {market_cap}\n")

        results.append({
            'name': name,
            'symbol': symbol,
            'url': coin_url,
            'market_cap': market_cap
        })

        time.sleep(3)  # Защита от блокировки

    # Сохраняем результаты в CSV
    save_market_caps_to_csv(results)


if __name__ == "__main__":
    main()