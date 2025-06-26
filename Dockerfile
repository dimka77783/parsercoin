# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем необходимые зависимости
RUN apt-get update && apt-get install -y cron procps && rm -rf /var/lib/apt/lists/*

# Устанавливаем необходимые Python библиотеки
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Копируем код приложения
COPY . /app

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем crontab файл в правильное место для Debian/Ubuntu
COPY crontab /etc/cron.d/parser-cron

# Устанавливаем правильные права на crontab файл
RUN chmod 0644 /etc/cron.d/parser-cron

# Применяем crontab (загружаем в систему)
RUN crontab /etc/cron.d/parser-cron

# Создаем директорию для логов
RUN mkdir -p /app/logs

# Делаем start.sh исполняемым
RUN chmod +x /app/start.sh

# Создаем entrypoint скрипт для правильного запуска
RUN cat > /entrypoint.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Запуск парсера криптовалют ==="

# Создаем необходимые директории и файлы
mkdir -p /app/logs
touch /app/logs/start.log
touch /app/logs/cron.log
touch /var/log/cron.log

# Экспортируем переменные окружения Docker в файл для cron
echo "# Переменные окружения для cron" > /etc/environment
printenv | grep -E "^(DB_|PATH|PYTHONPATH)" >> /etc/environment

echo "=== Переменные окружения ==="
cat /etc/environment

# Запускаем cron демон
echo "=== Запуск cron демона ==="
cron

# Показываем активные cron задачи
echo "=== Активные cron задачи ==="
crontab -l

# Запускаем парсер один раз при старте контейнера для проверки
echo "=== Тестовый запуск парсера ==="
cd /app && ./start.sh

# Показываем статус cron
echo "=== Статус cron процесса ==="
ps aux | grep cron

echo "=== Начинаем мониторинг логов ==="
echo "Логи будут отображаться в реальном времени..."
echo "Для остановки используйте Ctrl+C"

# Мониторинг логов (держим контейнер живым)
tail -f /app/logs/start.log /app/logs/cron.log /var/log/cron.log
EOF

# Делаем entrypoint исполняемым
RUN chmod +x /entrypoint.sh

# Запускаем через entrypoint
CMD ["/entrypoint.sh"]