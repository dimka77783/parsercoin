#!/bin/bash

# Запуск cron сервиса
service cron start

# Загрузка crontab из файла
crontab /etc/cron.d/parser-cron

# Запуск парсера один раз при старте (опционально)
# python /app/parser.py

# Вывод логов cron для отладки
echo "Cron jobs:"
crontab -l

# Создание лог файла если не существует
touch /var/log/parser.log
touch /var/log/cron.log

# Мониторинг логов (контейнер будет работать постоянно)
tail -f /var/log/parser.log /var/log/cron.log