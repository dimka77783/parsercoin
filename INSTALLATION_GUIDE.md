### 9. Проверка подключения и первый запуск

```bash
# Проверьте подключение к БД
./test_db_connection.py

# Вы должны увидеть:
# ✅ Подключение успешно!
# 📊 Найдено таблиц: 1-2

# Запустите парсер
./run_parser_with_db.sh

# Мониторьте процесс в реальном времени
tail -f logs/parser_*.log

# Парсер будет:
# 1. Загружать страницу CoinGecko
# 2. Парсить данные о 50 новых монетах
# 3. Для монет старше 2 дней получать OHLC данные
# 4. Создавать отдельные таблицы для каждой монеты
# 5. Сохранять данные в PostgreSQL
```# 🚀 Crypto Parser - Полное руководство по установке и запуску

Парсер для сбора информации о новых криптовалютах с CoinGecko и сохранения данных в PostgreSQL с отдельными таблицами OHLC для каждой монеты.

## 📋 Требования

- Ubuntu/Linux Mint/Debian (или другой Linux дистрибутив)
- Python 3.8+
- Docker и Docker Compose
- Минимум 2GB RAM
- 10GB свободного места на диске
- Доступ к интернету для загрузки данных с CoinGecko

## 🛠️ Детальная установка

### 1. Проверка системы и установка Docker

```bash
# Проверьте версию системы
lsb_release -a

# Проверьте Python
python3 --version

# Установите Docker (если не установлен)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Установите Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверьте установку
docker --version
docker-compose --version
```

### 2. Клонирование проекта и создание структуры

```bash
# Создайте директорию проекта
mkdir -p ~/PycharmProjects/parsercoin
cd ~/PycharmProjects/parsercoin

# Создайте необходимые поддиректории
mkdir -p logs backups

# Проверьте структуру
ls -la
```

### 3. Установка системных зависимостей

```bash
# Обновите список пакетов
sudo apt-get update

# Установите необходимые пакеты одной командой
sudo apt-get install -y \
    postgresql-client \
    python3-psycopg2 \
    python3-dotenv \
    python3-pip \
    git \
    cron \
    curl \
    wget

# Проверьте установку Python библиотек
python3 -c "import psycopg2; print('✅ psycopg2 версия:', psycopg2.__version__)"
python3 -c "import dotenv; print('✅ dotenv установлен')"

# Если psycopg2 не установился через apt, используйте pip
# pip3 install psycopg2-binary python-dotenv
```

### 4. Создание всех необходимых файлов

#### 4.1. docker-compose-db-only.yml
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: crypto_postgres
    environment:
      POSTGRES_DB: crypto_db
      POSTGRES_USER: crypto_user
      POSTGRES_PASSWORD: crypto_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U crypto_user -d crypto_db"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

#### 4.2. Создайте остальные файлы из артефактов:
- `init.sql` - основные таблицы БД
- `fix_migration.sql` - поддержка отдельных OHLC таблиц
- `parser_ohlcv_db_separate_tables.py` - парсер с отдельными таблицами
- `test_db_connection.py` - скрипт проверки подключения
- `load_json_to_db.py` - загрузчик данных в БД
- `run_parser_with_db.sh` - основной скрипт запуска
- `monitor_separate_tables.sh` - мониторинг системы
- `backup_db.sh` - резервное копирование

### 5. Настройка прав доступа

```bash
# Сделайте все скрипты исполняемыми
chmod +x *.sh *.py

# Или по отдельности
chmod +x run_parser_with_db.sh
chmod +x test_db_connection.py
chmod +x load_json_to_db.py
chmod +x parser_ohlcv.py
chmod +x parser_ohlcv_db_separate_tables.py
chmod +x monitor_separate_tables.sh
chmod +x backup_db.sh
chmod +x setup.sh
chmod +x cron_setup.sh

# Проверьте права
ls -la *.sh *.py
```

### 6. Запуск PostgreSQL с проверками

```bash
# Убедитесь, что порт 5432 свободен
sudo lsof -i :5432
# Если занят, остановите процесс или измените порт в docker-compose.yml

# Запустите контейнер с PostgreSQL
docker-compose -f docker-compose-db-only.yml up -d

# Подождите инициализации
sleep 10

# Проверьте статус контейнера
docker ps | grep crypto_postgres

# Проверьте логи на наличие ошибок
docker logs crypto_postgres --tail 30

# Проверьте готовность БД
docker exec crypto_postgres pg_isready

# Проверьте, что можете подключиться
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "SELECT 1;"
```

### 7. Инициализация базы данных

```bash
# Создайте основные таблицы
docker exec -i crypto_postgres psql -U crypto_user -d crypto_db < init.sql

# Добавьте поддержку отдельных OHLC таблиц
docker exec -i crypto_postgres psql -U crypto_user -d crypto_db < fix_migration.sql

# Проверьте, что таблицы созданы
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "\dt"

# Должны увидеть:
# - cryptocurrencies
# - all_ohlc_data (view)

# Проверьте структуру главной таблицы
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "\d cryptocurrencies"
```

### 8. Настройка парсера

```bash
# Копируйте парсер с поддержкой отдельных таблиц
cp parser_ohlcv_db_separate_tables.py parser_ohlcv_db.py

# Или если у вас есть оригинальный parser_ohlcv.py и вы хотите использовать его
# оставьте как есть, скрипт run_parser_with_db.sh автоматически определит что использовать

# Создайте файл переменных окружения (опционально)
cat > .env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crypto_db
DB_USER=crypto_user
DB_PASSWORD=crypto_password
MAX_COINS=50
EOF
```

## 📊 Проверка результатов

### Основные запросы к БД

```bash
# Общая статистика
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
SELECT 
    COUNT(*) as total_cryptos,
    COUNT(ohlc_table_name) as with_ohlc_tables
FROM cryptocurrencies;
"

# Последние добавленные монеты
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
SELECT name, symbol, added_date, chain, price 
FROM cryptocurrencies 
ORDER BY first_seen_at DESC 
LIMIT 10;
"

# Монеты с OHLC таблицами
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
SELECT 
    c.name, 
    c.symbol, 
    c.ohlc_table_name,
    c.added_date
FROM cryptocurrencies c
WHERE c.ohlc_table_name IS NOT NULL
ORDER BY c.first_seen_at DESC
LIMIT 10;
"

# Проверка OHLC данных конкретной монеты
# Замените SYMBOL и DATE на реальные значения
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
SELECT * FROM get_latest_ohlc('SYMBOL', 'YYYY-MM-DD', 5);
"
```

## ⏰ Настройка автоматического запуска

### Вариант 1: Ручная настройка crontab

```bash
# Откройте crontab
crontab -e

# Добавьте следующие строки (замените /path/to на ваш путь):

# Парсер - каждые 4 часа
0 */4 * * * /path/to/parsercoin/run_parser_with_db.sh >> /path/to/parsercoin/logs/cron.log 2>&1

# Резервное копирование БД - каждый день в 3:00
0 3 * * * /path/to/parsercoin/backup_db.sh >> /path/to/parsercoin/logs/backup.log 2>&1

# Очистка старых логов - каждое воскресенье в 2:00
0 2 * * 0 find /path/to/parsercoin/logs -name "parser_*.log" -mtime +30 -delete
```

### Вариант 2: Автоматическая настройка

```bash
# Используйте скрипт автоматической настройки
./cron_setup.sh

# Проверьте установленные задачи
crontab -l
```

## 🔧 Решение распространенных проблем

### PostgreSQL не запускается

```bash
# Проверьте логи детально
docker logs crypto_postgres --tail 50

# Проверьте, не занят ли порт
sudo lsof -i :5432
# Если занят, убейте процесс: sudo kill -9 <PID>

# Удалите старые контейнеры и volumes
docker rm -f crypto_postgres
docker volume rm parsercoin_postgres_data

# Запустите заново
docker-compose -f docker-compose-db-only.yml up -d
```

### Ошибка подключения к БД

```bash
# Установите переменные окружения
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=crypto_db
export DB_USER=crypto_user
export DB_PASSWORD=crypto_password

# Проверьте сеть Docker
docker network ls
docker network inspect parsercoin_default

# Проверьте из контейнера
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "SELECT 1;"
```

### Парсер не находит данные / CoinGecko блокирует

```bash
# Проверьте доступность CoinGecko
curl -I https://www.coingecko.com/ru/new-cryptocurrencies

# Если 403 Forbidden - используйте VPN или измените User-Agent
# Отредактируйте parser_ohlcv_db.py и добавьте задержки между запросами

# Альтернативные решения:
# 1. Увеличьте задержки в парсере (time.sleep)
# 2. Уменьшите MAX_COINS
# 3. Используйте прокси
# 4. Запускайте в разное время суток
```

### Ошибки при установке psycopg2

```bash
# Вариант 1: Системный пакет (рекомендуется)
sudo apt-get install python3-psycopg2

# Вариант 2: Установка зависимостей для сборки
sudo apt-get install libpq-dev python3-dev
pip3 install psycopg2

# Вариант 3: Бинарная версия
pip3 install psycopg2-binary

# Вариант 4: Использование виртуального окружения
python3 -m venv venv
source venv/bin/activate
pip install psycopg2-binary python-dotenv
```

### Проблемы с правами доступа

```bash
# Для логов
chmod -R 755 logs/
chown -R $USER:$USER logs/

# Для скриптов
chmod +x *.sh *.py

# Для Docker
sudo usermod -aG docker $USER
newgrp docker
```

## 📁 Полная структура проекта

```
parsercoin/
├── docker-compose-db-only.yml    # Конфигурация PostgreSQL
├── init.sql                      # Основные таблицы БД
├── fix_migration.sql             # Миграция на отдельные OHLC таблицы
├── init_separate_tables.sql      # Альтернативная схема БД (опционально)
├── parser_ohlcv.py              # Оригинальный парсер (без БД)
├── parser_ohlcv_db.py           # Парсер с БД (копия _separate_tables)
├── parser_ohlcv_db_separate_tables.py  # Парсер с отдельными таблицами
├── load_json_to_db.py           # Загрузчик JSON → PostgreSQL
├── test_db_connection.py        # Тест подключения к БД
├── run_parser_with_db.sh        # Основной скрипт запуска
├── setup.sh                     # Скрипт установки зависимостей
├── backup_db.sh                 # Резервное копирование БД
├── monitor_separate_tables.sh   # Мониторинг системы
├── cron_setup.sh               # Автоматическая настройка cron
├── .env                        # Переменные окружения (создать из .env.example)
├── .env.example                # Пример переменных окружения
├── logs/                       # Директория с логами
│   ├── parser_*.log           # Логи парсера
│   ├── cron.log              # Логи cron задач
│   └── backup.log            # Логи резервного копирования
├── backups/                    # Резервные копии БД
│   └── crypto_db_backup_*.sql
├── INSTALLATION_GUIDE.md       # Это руководство
├── QUICK_START_GUIDE.md       # Краткое руководство
└── README.md                  # Описание проекта
```

## 🔍 Мониторинг и обслуживание

### Мониторинг в реальном времени

```bash
# Запустите скрипт мониторинга
./monitor_separate_tables.sh

# Или используйте отдельные команды:

# Просмотр логов парсера
tail -f logs/parser_*.log

# Мониторинг PostgreSQL
docker logs -f crypto_postgres

# Статистика БД в реальном времени
watch -n 10 'docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
SELECT 
    (SELECT COUNT(*) FROM cryptocurrencies) as cryptos,
    (SELECT COUNT(*) FROM cryptocurrencies WHERE ohlc_table_name IS NOT NULL) as with_ohlc,
    pg_size_pretty(pg_database_size('"'"'crypto_db'"'"')) as db_size;"'
```

### Резервное копирование

```bash
# Ручное резервное копирование
./backup_db.sh

# Или команда напрямую
docker exec crypto_postgres pg_dump -U crypto_user crypto_db > backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление из резервной копии
docker exec -i crypto_postgres psql -U crypto_user -d crypto_db < backups/backup_20240115.sql

# Экспорт конкретной таблицы в CSV
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c \
  "\COPY cryptocurrencies TO '/tmp/cryptos.csv' CSV HEADER;"
docker cp crypto_postgres:/tmp/cryptos.csv ./
```

### Обслуживание БД

```bash
# Очистка старых данных (монеты старше 90 дней)
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
SELECT cleanup_old_ohlc_tables(90);
"

# Анализ размера таблиц
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
SELECT 
    c.symbol,
    c.ohlc_table_name,
    pg_size_pretty(pg_relation_size(c.ohlc_table_name::regclass)) as size
FROM cryptocurrencies c
WHERE c.ohlc_table_name IS NOT NULL
ORDER BY pg_relation_size(c.ohlc_table_name::regclass) DESC
LIMIT 20;
"

# Оптимизация БД
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "VACUUM ANALYZE;"
```

## 🛑 Остановка и управление

### Остановка сервисов

```bash
# Остановить PostgreSQL (данные сохраняются)
docker-compose -f docker-compose-db-only.yml stop

# Полная остановка с удалением контейнера (данные сохраняются)
docker-compose -f docker-compose-db-only.yml down

# Полное удаление включая данные (ОСТОРОЖНО!)
docker-compose -f docker-compose-db-only.yml down -v

# Остановить конкретную cron задачу
crontab -e  # и закомментируйте нужную строку
```

### Перезапуск сервисов

```bash
# Перезапуск PostgreSQL
docker-compose -f docker-compose-db-only.yml restart

# Перезапуск с обновлением образа
docker-compose -f docker-compose-db-only.yml pull
docker-compose -f docker-compose-db-only.yml up -d
```

### Очистка системы

```bash
# Удаление старых логов (старше 30 дней)
find logs/ -name "*.log" -mtime +30 -delete

# Удаление старых бэкапов (оставить последние 7)
cd backups/ && ls -t *.sql | tail -n +8 | xargs rm -f

# Очистка Docker
docker system prune -a  # Удалит неиспользуемые образы
docker volume prune     # Удалит неиспользуемые volumes
```

## 💡 Полезные команды и советы

### Работа с БД

```bash
# Интерактивный вход в PostgreSQL
docker exec -it crypto_postgres psql -U crypto_user -d crypto_db

# Полезные SQL команды внутри psql:
\dt                    # Список таблиц
\d+ cryptocurrencies   # Структура таблицы
\dv                    # Список views
\df                    # Список функций
\l                     # Список баз данных
\q                     # Выход

# Экспорт данных для анализа
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c \
  "SELECT * FROM cryptocurrencies ORDER BY first_seen_at DESC" \
  --csv > export_cryptos.csv

# Поиск конкретной монеты
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c \
  "SELECT * FROM cryptocurrencies WHERE symbol = 'BTC';"
```

### Отладка парсера

```bash
# Запуск парсера в режиме отладки
python3 -u parser_ohlcv_db.py 2>&1 | tee debug.log

# Проверка только парсинга без сохранения
python3 parser_ohlcv.py

# Тестирование конкретной функции
python3 -c "
from parser_ohlcv_db import search_coin_id
result = search_coin_id('Bitcoin', 'BTC')
print(result)
"
```

### Производительность и оптимизация

```bash
# Анализ медленных запросов
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# Размер индексов
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
SELECT schemaname, tablename, indexname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;
"
```

### Безопасность

```bash
# Изменить пароль PostgreSQL
docker exec crypto_postgres psql -U postgres -c \
  "ALTER USER crypto_user PASSWORD 'new_secure_password';"

# Создать read-only пользователя для аналитики
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
CREATE USER analyst WITH PASSWORD 'analyst_password';
GRANT CONNECT ON DATABASE crypto_db TO analyst;
GRANT USAGE ON SCHEMA public TO analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analyst;
"
```

## 📞 Часто задаваемые вопросы (FAQ)

### Q: Как часто можно запускать парсер?
**A:** Рекомендуется не чаще чем раз в 4 часа из-за лимитов API CoinGecko. Более частые запросы могут привести к блокировке.

### Q: Сколько места занимает БД?
**A:** Примерно 1-2 MB на монету с полными OHLC данными за 30 дней. Для 1000 монет потребуется около 1-2 GB.

### Q: Можно ли парсить больше 50 монет?
**A:** Да, измените `MAX_COINS` в парсере, но учитывайте лимиты API и увеличьте задержки между запросами.

### Q: Как перенести БД на другой сервер?
**A:** 
```bash
# На старом сервере
docker exec crypto_postgres pg_dump -U crypto_user crypto_db > full_backup.sql

# На новом сервере
docker exec -i crypto_postgres psql -U crypto_user -d crypto_db < full_backup.sql
```

### Q: Парсер работает медленно
**A:** Это нормально. Парсер специально делает паузы между запросами к API. Полный цикл для 50 монет занимает 5-10 минут.

### Q: Ошибка "Rate limit exceeded"
**A:** CoinGecko ограничивает количество запросов. Решения:
- Увеличьте задержки в коде (time.sleep)
- Используйте VPN
- Запускайте в разное время суток

### Q: Как добавить новые поля в БД?
**A:** Используйте ALTER TABLE:
```sql
ALTER TABLE cryptocurrencies ADD COLUMN new_field VARCHAR(100);
```

## 🚀 Дальнейшее развитие

1. **Веб-интерфейс**: Добавьте Grafana для визуализации данных
2. **API**: Создайте REST API для доступа к данным
3. **Аналитика**: Используйте Jupyter Notebook для анализа
4. **Уведомления**: Настройте алерты через Telegram при находке интересных монет
5. **Масштабирование**: Переход на TimescaleDB для больших объемов данных

## 📚 Полезные ресурсы

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [CoinGecko API](https://www.coingecko.com/en/api)
- [Python psycopg2](https://www.psycopg.org/docs/)

---

**Версия:** 2.0 (с отдельными OHLC таблицами)  
**Последнее обновление:** 2024-01-15  
**Автор:** Crypto Parser Team