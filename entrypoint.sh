#!/bin/bash

echo "=== Запуск парсера криптовалют ==="
echo "Время: $(date)"

# Пытаемся установить пакеты при первом запуске
if [ ! -f /app/.packages_installed ]; then
    echo "=== Установка пакетов ==="
    /app/install_packages.sh && touch /app/.packages_installed
fi

# Проверяем наличие пакетов
echo "=== Проверка Python пакетов ==="
python -c "import requests; print('✅ requests установлен')" || echo "❌ requests отсутствует"
python -c "import bs4; print('✅ beautifulsoup4 установлен')" || echo "❌ beautifulsoup4 отсутствует"
python -c "import psycopg2; print('✅ psycopg2 установлен')" || echo "❌ psycopg2 отсутствует"

echo ""
echo "=== Версия Python ==="
python --version

# Экспортируем переменные окружения для cron
printenv | grep -E "^(DB_|PATH|PYTHONPATH)" > /etc/environment

# Запуск cron сервиса
service cron start

# Загрузка crontab из файла
crontab /etc/cron.d/parser-cron

# Вывод cron заданий
echo "=== Cron задания: ==="
crontab -l

# Создание лог файлов если не существуют
touch /var/log/parser.log
touch /var/log/cron.log
touch /app/logs/cron.log

# Тестовый запуск парсера
echo "=== Тестовый запуск парсера ==="
cd /app && python parser.py || {
    echo "❌ Ошибка при запуске парсера"
    echo "Попробуем установить пакеты еще раз..."
    pip install --index-url https://pypi.org/simple/ requests beautifulsoup4 psycopg2-binary fake-useragent lxml || true
}

echo "=== Мониторинг логов ==="
# Мониторинг логов (контейнер будет работать постоянно)
tail -f /var/log/parser.log /var/log/cron.log /app/logs/cron.log