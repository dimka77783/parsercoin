# Crypto Parser с PostgreSQL

Автоматический парсер новых криптовалют с CoinGecko, который сохраняет данные в PostgreSQL и запускается каждые 4 часа.

## Структура проекта

```
crypto-parser/
├── docker-compose.yml      # Docker Compose конфигурация
├── Dockerfile             # Docker образ для парсера
├── init.sql              # SQL скрипт инициализации БД
├── parser_ohlcv_db.py    # Модифицированный парсер с поддержкой БД
├── run_parser.sh         # Скрипт запуска парсера
├── crontab              # Расписание cron
├── .env.example         # Пример файла с переменными окружения
└── logs/                # Директория для логов
```

## Возможности

- **Автоматический парсинг**: Запускается каждые 4 часа через cron
- **PostgreSQL база данных**: Две таблицы для криптовалют и OHLC данных
- **Предотвращение дублирования**: Уникальные ограничения на уровне БД
- **OHLC данные**: 4-часовые свечи для монет старше 2 дней
- **Логирование**: Все операции логируются в файлы
- **Health checks**: Проверка готовности БД перед запуском парсера

## Установка и запуск

1. **Клонируйте репозиторий или создайте файлы**:
```bash
mkdir crypto-parser
cd crypto-parser
```

2. **Создайте все необходимые файлы из артефактов выше**

3. **Скопируйте ваш оригинальный parser_ohlcv.py и переименуйте**:
```bash
cp parser_ohlcv.py parser_ohlcv_db.py
```
Или используйте модифицированную версию из артефакта выше.

4. **Создайте файл окружения**:
```bash
cp .env .env
# Отредактируйте .env при необходимости
```

5. **Запустите Docker Compose**:
```bash
docker-compose up -d
```

6. **Проверьте логи**:
```bash
# Логи PostgreSQL
docker-compose logs postgres

# Логи парсера
docker-compose logs parser

# Логи cron задач
docker exec crypto_parser tail -f /var/log/cron.log

# Логи парсера
tail -f logs/last_50_cryptos_report.txt
```

## Структура базы данных

### Таблица `cryptocurrencies`
- Хранит информацию о криптовалютах
- Уникальное ограничение по `(symbol, added_date)` предотвращает дубликаты
- Автоматическое обновление `last_updated_at` через триггер

### Таблица `ohlc_data`
- Хранит 4-часовые OHLC свечи
- Связана с `cryptocurrencies` через внешний ключ
- Уникальное ограничение по `(crypto_id, timestamp)` предотвращает дубликаты

## Управление

### Остановка сервисов:
```bash
docker-compose down
```

### Остановка с удалением данных:
```bash
docker-compose down -v
```

### Ручной запуск парсера:
```bash
docker exec crypto_parser /app/run_parser.sh
```

### Просмотр данных в БД:
```bash
# Подключение к PostgreSQL
docker exec -it crypto_postgres psql -U crypto_user -d crypto_db

# Примеры запросов:
SELECT COUNT(*) FROM cryptocurrencies;
SELECT name, symbol, added_date FROM cryptocurrencies ORDER BY first_seen_at DESC LIMIT 10;
SELECT COUNT(*) FROM ohlc_data;
```

### Изменение расписания:
Отредактируйте файл `crontab`. Формат:
- `0 */4 * * *` - каждые 4 часа
- `0 */2 * * *` - каждые 2 часа
- `0 6,12,18,0 * * *` - в 6:00, 12:00, 18:00 и 00:00

После изменения пересоздайте контейнер:
```bash
docker-compose up -d --build parser
```

## Мониторинг

### Проверка последнего запуска:
```bash
docker exec crypto_parser tail -20 /var/log/cron.log
```

### Статистика БД:
```bash
docker exec crypto_postgres psql -U crypto_user -d crypto_db -c "
SELECT 
    (SELECT COUNT(*) FROM cryptocurrencies) as total_cryptos,
    (SELECT COUNT(DISTINCT crypto_id) FROM ohlc_data) as cryptos_with_ohlc,
    (SELECT COUNT(*) FROM ohlc_data) as total_ohlc_records;
"
```

## Troubleshooting

### Парсер не запускается:
1. Проверьте логи: `docker-compose logs parser`
2. Проверьте подключение к БД: `docker exec crypto_parser pg_isready -h postgres -U crypto_user`

### Нет данных в БД:
1. Проверьте, что CoinGecko доступен
2. Проверьте логи парсера: `tail -f logs/last_50_cryptos_report.txt`
3. Попробуйте запустить вручную: `docker exec crypto_parser python3 /app/parser_ohlcv.py`

### Rate limiting:
Парсер автоматически обрабатывает rate limiting с повторными попытками и задержками.

## Безопасность

- Измените пароли в production окружении
- Используйте Docker secrets для чувствительных данных
- Ограничьте доступ к порту PostgreSQL (5432) файрволом