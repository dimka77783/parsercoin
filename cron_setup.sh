#!/bin/bash

# Настройка cron задач для парсера

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_FILE="/tmp/crypto_parser_cron"

echo "⚙️  Настройка cron задач..."

# Создаем временный файл с задачами
cat > "$CRON_FILE" << EOF
# Crypto Parser - запуск каждые 4 часа
0 */4 * * * $SCRIPT_DIR/run_parser_with_db.sh >> $SCRIPT_DIR/logs/cron.log 2>&1

# Резервное копирование БД - каждый день в 3:00
0 3 * * * $SCRIPT_DIR/backup_db.sh >> $SCRIPT_DIR/logs/backup.log 2>&1

# Очистка старых логов - раз в неделю
0 2 * * 0 find $SCRIPT_DIR/logs -name "parser_*.log" -mtime +30 -delete

EOF

# Показываем что будет добавлено
echo "📋 Будут добавлены следующие задачи:"
echo "-----------------------------------"
cat "$CRON_FILE"
echo "-----------------------------------"

# Спрашиваем подтверждение
read -p "Добавить эти задачи в cron? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Сохраняем текущий crontab
    crontab -l > /tmp/current_cron 2>/dev/null || true

    # Добавляем новые задачи
    cat /tmp/current_cron "$CRON_FILE" | crontab -

    echo "✅ Задачи добавлены в cron"
    echo ""
    echo "Проверить задачи: crontab -l"
    echo "Редактировать: crontab -e"
else
    echo "❌ Отменено"
fi

# Удаляем временный файл
rm -f "$CRON_FILE"