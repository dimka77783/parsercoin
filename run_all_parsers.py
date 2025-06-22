import subprocess
import time


def run_parser(script_name):
    """Запускает указанный скрипт через subprocess"""
    print(f"\n🔄 Запуск {script_name}...")
    result = subprocess.run(['python', script_name], capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✅ {script_name} успешно завершён")
    else:
        print(f"❌ Ошибка при выполнении {script_name}:")
        print(result.stderr)


def main():
    print("🚀 Запуск полного цикла парсинга...\n")

    # Шаг 1: Получаем список новых криптовалют
    run_parser('coingecko_new_parser_2025.py')

    # Делаем паузу на случай медленной загрузки файла
    time.sleep(2)

    # Шаг 2: Парсим капитализацию с внутренних страниц
    run_parser('get_market_caps.py')

    print("\n🎉 Полный цикл парсинга завершён!")


if __name__ == "__main__":
    main()