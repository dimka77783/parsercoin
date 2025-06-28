#!/usr/bin/env python3
"""
Тестирование подключения к PostgreSQL
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Настройки БД
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', 'crypto_db'),
    'user': os.environ.get('DB_USER', 'crypto_user'),
    'password': os.environ.get('DB_PASSWORD', 'crypto_password')
}


def test_connection():
    """Проверяет подключение к БД"""
    print("🔍 Проверка подключения к PostgreSQL...")
    print(f"   Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"   Database: {DB_CONFIG['database']}")
    print(f"   User: {DB_CONFIG['user']}")

    try:
        # Подключение
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print("✅ Подключение успешно!")

        # Проверка таблиц
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()
        print(f"\n📊 Найдено таблиц: {len(tables)}")

        for table in tables:
            table_name = table['table_name']

            # Получаем количество записей
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            count = cursor.fetchone()['count']

            print(f"   - {table_name}: {count} записей")

        # Проверка последних монет
        cursor.execute("""
            SELECT name, symbol, added_date 
            FROM cryptocurrencies 
            ORDER BY first_seen_at DESC 
            LIMIT 5
        """)

        recent = cursor.fetchall()
        if recent:
            print(f"\n🆕 Последние добавленные монеты:")
            for coin in recent:
                print(f"   - {coin['name']} ({coin['symbol']}) - {coin['added_date']}")

        cursor.close()
        conn.close()

        print("\n✅ Все проверки пройдены успешно!")
        return True

    except psycopg2.OperationalError as e:
        print(f"\n❌ Ошибка подключения: {e}")
        print("\nВозможные причины:")
        print("1. PostgreSQL не запущен")
        print("2. Неверные параметры подключения")
        print("3. Проблемы с сетью")
        print("\nПроверьте:")
        print("- docker ps (должен быть контейнер crypto_postgres)")
        print("- docker logs crypto_postgres")
        return False

    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        return False


if __name__ == "__main__":
    # Можно передать параметры через командную строку
    if len(sys.argv) > 1:
        os.environ['DB_HOST'] = sys.argv[1]

    success = test_connection()
    sys.exit(0 if success else 1)