# 🚀 Crypto Parser - Руководство по быстрому запуску

## 📋 Минимальные требования

- Linux (Ubuntu/Mint/Debian)
- Docker и Docker Compose
- Python 3.8+
- Интернет соединение

## 🎯 Быстрый запуск за 5 минут

### 1️⃣ Установка зависимостей

```bash
# Обновите систему и установите необходимые пакеты
sudo apt-get update
sudo apt-get install -y postgresql-client python3-psycopg2 python3-dotenv
```

### 2️⃣ Запуск PostgreSQL

```bash
# Запустите базу данных
docker-compose -f docker-compose-db-only.yml up -d

# Проверьте, что БД запущена
docker ps | grep crypto_postgres
```

### 3️⃣ Создание таблиц в БД

```bash
# Базовые таблицы
docker exec -i crypto_postgres psql -U crypto_user -d crypto_db < init.sql

# Таблицы с поддержкой отдельных OHLC
docker exec -i crypto_postgres psql -U crypto_user -d crypto_db < fix_migration.sql
```

### 4️⃣ Запуск парсера

```bash
# Сделайте скрипты исполняемыми
chmod +x run_parser_with_db.sh test_db_connection.py

# Проверьте подключение к БД
./test_db_connection.py

# Запустите парсер
./run_parser_with_db.sh
```

### 5️⃣ Проверка результатов

```bash
# Посмотрите сколько монет найдено
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c \
  "SELECT COUNT(*) as total FROM cryptocurrencies;"

# Последние добавленные монеты
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c \
  "SELECT name, symbol, added_date FROM cryptocurrencies 
   ORDER BY first_seen_at DESC LIMIT 5;"
```

## 📊 Структура файлов

```
parsercoin/
├── docker-compose-db-only.yml  # Конфигурация PostgreSQL
├── init.sql                    # Основные таблицы БД
├── fix_migration.sql           # Поддержка отдельных OHLC таблиц
├── parser_ohlcv.py            # Оригинальный парсер
├── parser_ohlcv_db.py         # Парсер с БД (копия parser_ohlcv_db_separate_tables.py)
├── load_json_to_db.py         # Загрузчик JSON в БД
├── test_db_connection.py      # Тест подключения
├── run_parser_with_db.sh      # Скрипт запуска
└── logs/                      # Директория для логов
```

## ⚙️ Настройка автоматического запуска

### Добавьте в crontab для запуска каждые 4 часа:

```bash
# Откройте редактор cron
crontab -e

# Добавьте строку (замените путь на ваш)
0 */4 * * * /home/user/parsercoin/run_parser_with_db.sh >> /home/user/parsercoin/logs/cron.log 2>&1
```

## 🔍 Полезные команды

### Мониторинг работы

```bash
# Статус PostgreSQL
docker logs crypto_postgres --tail 20

# Последние логи парсера
tail -f logs/parser_*.log

# Статистика БД
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
SELECT 
    (SELECT COUNT(*) FROM cryptocurrencies) as total_cryptos,
    (SELECT COUNT(*) FROM cryptocurrencies WHERE ohlc_table_name IS NOT NULL) as with_ohlc;
"
```

### Управление БД

```bash
# Резервная копия
docker exec crypto_postgres pg_dump -U crypto_user crypto_db > backup_$(date +%Y%m%d).sql

# Очистка старых данных (монеты старше 90 дней)
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c \
  "DELETE FROM cryptocurrencies WHERE added_date < CURRENT_DATE - INTERVAL '90 days';"
```

### Остановка и перезапуск

```bash
# Остановить PostgreSQL
docker-compose -f docker-compose-db-only.yml down

# Перезапустить PostgreSQL
docker-compose -f docker-compose-db-only.yml restart

# Полная очистка (УДАЛИТ ВСЕ ДАННЫЕ!)
docker-compose -f docker-compose-db-only.yml down -v
```

## ❗ Решение проблем

### PostgreSQL не запускается

```bash
# Проверьте порт 5432
sudo lsof -i :5432

# Удалите старый контейнер
docker rm -f crypto_postgres

# Запустите заново
docker-compose -f docker-compose-db-only.yml up -d
```

### Ошибка подключения к БД

```bash
# Проверьте переменные окружения
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=crypto_db
export DB_USER=crypto_user
export DB_PASSWORD=crypto_password

# Проверьте подключение
./test_db_connection.py
```

### Парсер не находит монеты

1. Проверьте доступность CoinGecko
2. Проверьте логи: `tail logs/parser_*.log`
3. Попробуйте VPN если CoinGecko блокирует

## 📈 Что дальше?

1. **Настройте мониторинг**: используйте `monitor_separate_tables.sh`
2. **Автоматизируйте бэкапы**: добавьте `backup_db.sh` в cron
3. **Анализируйте данные**: подключитесь к БД через pgAdmin или DBeaver
4. **Масштабируйте**: увеличьте MAX_COINS в парсере для большего охвата

## 💡 Советы

- Запускайте парсер не чаще чем раз в 4 часа (лимиты API)
- Регулярно делайте резервные копии БД
- Мониторьте размер БД и очищайте старые данные
- Используйте VPN при блокировках CoinGecko

---

**Нужна помощь?** Проверьте полную документацию в `INSTALLATION_GUIDE.md`