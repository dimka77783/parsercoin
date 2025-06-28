#!/bin/bash

echo "🚀 Установка Crypto Parser с PostgreSQL"
echo "======================================"

# Проверка, что скрипт запущен с правами sudo
if [ "$EUID" -eq 0 ]; then
   echo "⚠️  Не запускайте этот скрипт как root. Используйте обычного пользователя."
   echo "   Скрипт сам запросит sudo когда нужно."
   exit 1
fi

# Обновление списка пакетов
echo "📦 Обновление списка пакетов..."
sudo apt-get update

# Установка системных зависимостей
echo "📦 Установка системных пакетов..."
sudo apt-get install -y \
    postgresql-client \
    python3-psycopg2 \
    python3-dotenv \
    python3-pip \
    git \
    cron

# Проверка установки
echo "✅ Проверка установленных пакетов..."
python3 -c "import psycopg2; print('✅ psycopg2 установлен успешно')" || echo "❌ Ошибка установки psycopg2"
python3 -c "import dotenv; print('✅ dotenv установлен успешно')" || echo "❌ Ошибка установки dotenv"

# Создание директорий
echo "📁 Создание директорий..."
mkdir -p logs
mkdir -p backups

# Настройка прав
echo "🔐 Настройка прав доступа..."
chmod +x run_parser.sh
chmod +x run_parser_with_db.sh
chmod +x backup_db.sh

# Проверка Docker
if command -v docker &> /dev/null; then
    echo "✅ Docker установлен"

    # Проверка запущен ли PostgreSQL
    if docker ps | grep -q crypto_postgres; then
        echo "✅ PostgreSQL контейнер запущен"
    else
        echo "⚠️  PostgreSQL контейнер не найден"
        echo "   Запустите: docker-compose -f docker-compose-db-only.yml up -d"
    fi
else
    echo "⚠️  Docker не установлен"
    echo "   Установите Docker или используйте локальный PostgreSQL"
fi

echo ""
echo "✅ Установка завершена!"
echo ""
echo "Следующие шаги:"
echo "1. Запустите PostgreSQL: docker-compose -f docker-compose-db-only.yml up -d"
echo "2. Проверьте подключение: ./test_db_connection.py"
echo "3. Запустите парсер: ./run_parser_with_db.sh"
echo "4. Настройте cron: crontab -e"
echo ""