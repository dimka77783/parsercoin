# Crypto Parser - Руководство по развертыванию на VPS

## Содержание
1. [Требования](#требования)
2. [Подготовка сервера](#подготовка-сервера)
3. [Установка зависимостей](#установка-зависимостей)
4. [Клонирование проекта](#клонирование-проекта)
5. [Настройка базы данных](#настройка-базы-данных)
6. [Настройка приложения](#настройка-приложения)
7. [Первый запуск](#первый-запуск)
8. [Автоматизация через Cron](#автоматизация-через-cron)
9. [Мониторинг и обслуживание](#мониторинг-и-обслуживание)
10. [Решение проблем](#решение-проблем)

## Требования

### Минимальные требования к серверу:
- **ОС**: Ubuntu 20.04/22.04 или Debian 10/11
- **CPU**: 1 ядро
- **RAM**: 2 GB
- **Диск**: 10 GB свободного места
- **Сеть**: Стабильное интернет-соединение

### Необходимое ПО:
- Python 3.8+
- Docker и Docker Compose
- PostgreSQL (через Docker)
- Git

## Подготовка сервера

### 1. Подключение к серверу
```bash
ssh user@your-server-ip
```

### 2. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

### 3. Установка базовых утилит
```bash
sudo apt install -y curl wget git nano htop
```

## Установка зависимостей

### 1. Установка Python и pip
```bash
# Установка Python 3 и необходимых пакетов
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Проверка версии
python3 --version
```

### 2. Установка Docker
```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Выйти и зайти снова для применения изменений
exit
# Подключиться заново
ssh user@your-server-ip

# Проверка Docker
docker --version
```

### 3. Установка Docker Compose
```bash
# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка
docker-compose --version
```

### 4. Установка PostgreSQL клиента (опционально)
```bash
sudo apt install -y postgresql-client
```

## Клонирование проекта

### 1. Создание рабочей директории
```bash
# Создание директории для проектов
mkdir -p ~/projects
cd ~/projects
```

### 2. Клонирование репозитория
```bash
# Если есть Git репозиторий
git clone https://github.com/yourusername/crypto-parser.git
cd crypto-parser

# Или создайте директорию и скопируйте файлы
mkdir crypto-parser
cd crypto-parser
```

### 3. Создание структуры проекта
```bash
# Создание необходимых директорий
mkdir -p logs backups

# Проверка структуры
ls -la
```

### 4. Копирование файлов проекта
Скопируйте следующие файлы в директорию проекта:
- `docker-compose.yml`
- `init_db.sql`
- `parser.py`
- `updater.py`
- `run.sh`
- `requirements.txt`

## Настройка базы данных

### 1. Проверка docker-compose.yml
```bash
nano docker-compose.yml
```

Убедитесь, что настройки корректны:
```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: crypto_db
    environment:
      POSTGRES_DB: crypto_db
      POSTGRES_USER: crypto_user
      POSTGRES_PASSWORD: crypto_password  # Измените на безопасный пароль!
```

### 2. Запуск базы данных
```bash
# Запуск PostgreSQL в фоновом режиме
docker-compose up -d

# Проверка статуса
docker ps

# Просмотр логов
docker-compose logs -f postgres
```

### 3. Проверка подключения
```bash
# Тест подключения
docker exec -it crypto_db psql -U crypto_user -d crypto_db -c "SELECT version();"
```

## Настройка приложения

### 1. Создание виртуального окружения (рекомендуется)
```bash
# Создание venv
python3 -m venv venv

# Активация
source venv/bin/activate
```

### 2. Установка Python зависимостей
```bash
# Установка зависимостей
pip install -r requirements.txt

# Или установка вручную
pip install psycopg2-binary==2.9.9
```

### 3. Создание файла конфигурации окружения
```bash
# Создание .env файла (опционально)
nano .env
```

Содержимое .env:
```bash
# Database settings
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crypto_db
DB_USER=crypto_user
DB_PASSWORD=crypto_password

# Parser settings
MAX_COINS=30
PARSER_MODE=safe
```

### 4. Настройка прав на выполнение
```bash
# Сделать скрипты исполняемыми
chmod +x parser.py updater.py run.sh
```

## Первый запуск

### 1. Тестовый запуск парсера
```bash
# Активировать venv если не активирован
source venv/bin/activate

# Запуск парсера
python3 parser.py
```

### 2. Проверка результатов
```bash
# Проверка данных в БД
docker exec -it crypto_db psql -U crypto_user -d crypto_db -c "
SELECT COUNT(*) as total_coins FROM cryptocurrencies;
"
```

### 3. Запуск обновления OHLC
```bash
python3 updater.py
```

### 4. Полный цикл через run.sh
```bash
./run.sh
```

## Автоматизация через Cron

### 1. Создание wrapper скрипта
```bash
nano cron_wrapper.sh
```

Содержимое:
```bash
#!/bin/bash
# Crypto Parser Cron Wrapper

PROJECT_DIR="/home/$USER/projects/crypto-parser"
cd "$PROJECT_DIR" || exit 1

# Настройка окружения
export PATH="/usr/local/bin:/usr/bin:/bin"
source "$PROJECT_DIR/venv/bin/activate"

# Настройки БД
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="crypto_db"
export DB_USER="crypto_user"
export DB_PASSWORD="crypto_password"

# Создание директорий
mkdir -p logs backups

# Запуск команды
case "$1" in
    "parser")
        python3 parser.py
        ;;
    "updater")
        python3 updater.py
        ;;
    "full")
        ./run.sh
        ;;
    *)
        echo "Usage: $0 {parser|updater|full}"
        exit 1
        ;;
esac
```

### 2. Настройка прав
```bash
chmod +x cron_wrapper.sh
```

### 3. Настройка crontab
```bash
crontab -e
```

Добавьте:
```bash
# Crypto Parser Schedule
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

# Переменные
PROJECT_DIR=/home/user/projects/crypto-parser

# Парсинг новых монет - каждые 6 часов
0 */6 * * * $PROJECT_DIR/cron_wrapper.sh parser >> $PROJECT_DIR/logs/parser.log 2>&1

# Обновление OHLC - каждые 4 часа
30 */4 * * * $PROJECT_DIR/cron_wrapper.sh updater >> $PROJECT_DIR/logs/updater.log 2>&1

# Полный цикл - раз в день в 3:00
0 3 * * * $PROJECT_DIR/cron_wrapper.sh full >> $PROJECT_DIR/logs/full.log 2>&1

# Резервное копирование БД - ежедневно в 4:00
0 4 * * * docker exec crypto_db pg_dump -U crypto_user crypto_db | gzip > $PROJECT_DIR/backups/crypto_db_$(date +\%Y\%m\%d).sql.gz

# Очистка старых логов - воскресенье
0 5 * * 0 find $PROJECT_DIR/logs -name "*.log" -mtime +30 -delete

# Статистика - дважды в день
0 9,21 * * * docker exec crypto_db psql -U crypto_user -d crypto_db -c "SELECT 'Time: ' || NOW(), 'Total: ' || COUNT(*) FROM cryptocurrencies;" >> $PROJECT_DIR/logs/stats.log
```

### 4. Проверка cron
```bash
# Список задач
crontab -l

# Проверка логов cron
sudo tail -f /var/log/syslog | grep CRON
```

## Мониторинг и обслуживание

### 1. Просмотр логов
```bash
# Логи приложения
tail -f logs/parser.log
tail -f logs/updater.log

# Логи Docker
docker-compose logs -f

# Системные логи
journalctl -u docker -f
```

### 2. Мониторинг ресурсов
```bash
# Использование CPU и памяти
htop

# Использование диска
df -h

# Размер БД
docker exec crypto_db psql -U crypto_user -d crypto_db -c "
SELECT pg_size_pretty(pg_database_size('crypto_db')) as db_size;
"

# Количество таблиц OHLC
docker exec crypto_db psql -U crypto_user -d crypto_db -c "
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_name LIKE 'ohlc_%';
"
```

### 3. Резервное копирование
```bash
# Ручное резервное копирование
docker exec crypto_db pg_dump -U crypto_user crypto_db | gzip > backups/manual_backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Восстановление из бэкапа
gunzip < backups/crypto_db_20240101.sql.gz | docker exec -i crypto_db psql -U crypto_user crypto_db
```

### 4. Обновление приложения
```bash
# Если используете Git
git pull origin main

# Обновление зависимостей
pip install -r requirements.txt --upgrade

# Перезапуск контейнеров
docker-compose restart
```

## Решение проблем

### 1. База данных не запускается
```bash
# Проверка логов
docker-compose logs postgres

# Пересоздание контейнера
docker-compose down
docker-compose up -d

# Проверка прав на volumes
sudo chown -R $USER:$USER ./
```

### 2. Ошибки подключения к БД
```bash
# Проверка доступности порта
netstat -tulpn | grep 5432

# Тест подключения
psql -h localhost -U crypto_user -d crypto_db -p 5432
```

### 3. Проблемы с Python модулями
```bash
# Переустановка в venv
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Нехватка места на диске
```bash
# Очистка Docker
docker system prune -a

# Очистка старых логов
find logs/ -name "*.log" -mtime +7 -delete

# Очистка старых бэкапов
find backups/ -name "*.sql.gz" -mtime +30 -delete
```

### 5. API лимиты CoinGecko
```bash
# Проверка текущих задержек в parser.py
grep "DELAYS" parser.py

# Увеличение задержек если нужно
# Отредактируйте DELAYS в parser.py и updater.py
```

## Безопасность

### 1. Настройка firewall
```bash
# Установка ufw
sudo apt install ufw

# Базовые правила
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 22/tcp

# Включение firewall
sudo ufw enable
```

### 2. Защита БД
- Измените пароль по умолчанию в docker-compose.yml
- Не открывайте порт 5432 наружу без необходимости
- Используйте сложные пароли

### 3. Регулярные обновления
```bash
# Обновление системы
sudo apt update && sudo apt upgrade

# Обновление Docker образов
docker-compose pull
docker-compose up -d
```

## Полезные команды

```bash
# Статус всех сервисов
docker-compose ps

# Перезапуск всего
docker-compose restart

# Остановка
docker-compose stop

# Полная остановка и удаление
docker-compose down

# Просмотр процессов Python
ps aux | grep python

# Kill зависшего процесса
pkill -f parser.py

# Проверка cron задач
grep CRON /var/log/syslog | tail -20

# Быстрая статистика
docker exec crypto_db psql -U crypto_user -d crypto_db -c "SELECT COUNT(*) FROM cryptocurrencies;"
```

## Контакты и поддержка

При возникновении проблем:
1. Проверьте логи в директории `logs/`
2. Проверьте статус Docker контейнеров
3. Убедитесь, что все зависимости установлены
4. Проверьте доступность API CoinGecko

---

**Версия**: 1.0  
**Дата обновления**: 2024  
**Автор**: Crypto Parser Team