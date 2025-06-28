-- Скрипт миграции существующих данных в отдельные таблицы OHLC

-- Функция для миграции данных из общей таблицы в отдельные
CREATE OR REPLACE FUNCTION migrate_ohlc_to_separate_tables()
RETURNS TABLE (
    crypto_name VARCHAR,
    symbol VARCHAR,
    table_name VARCHAR,
    records_migrated INTEGER
) AS $$
DECLARE
    v_crypto RECORD;
    v_table_name VARCHAR;
    v_count INTEGER;
    v_sql TEXT;
BEGIN
    -- Проходим по всем криптовалютам
    FOR v_crypto IN
        SELECT DISTINCT c.id, c.name, c.symbol, c.added_date
        FROM cryptocurrencies c
        WHERE EXISTS (
            SELECT 1 FROM ohlc_data o WHERE o.crypto_id = c.id
        )
        ORDER BY c.id
    LOOP
        -- Создаем таблицу OHLC для монеты
        v_table_name := create_ohlc_table(v_crypto.symbol, v_crypto.added_date);

        -- Мигрируем данные
        v_sql := format('
            INSERT INTO %I (timestamp, datetime, date, time, open, high, low, close)
            SELECT timestamp, datetime, date, time, open, high, low, close
            FROM ohlc_data
            WHERE crypto_id = %s
            ON CONFLICT (timestamp) DO NOTHING
        ', v_table_name, v_crypto.id);

        EXECUTE v_sql;

        -- Получаем количество перенесенных записей
        EXECUTE format('SELECT COUNT(*) FROM %I', v_table_name) INTO v_count;

        -- Обновляем запись криптовалюты
        UPDATE cryptocurrencies
        SET ohlc_table_name = v_table_name
        WHERE id = v_crypto.id;

        -- Возвращаем результат
        crypto_name := v_crypto.name;
        symbol := v_crypto.symbol;
        table_name := v_table_name;
        records_migrated := v_count;

        RETURN NEXT;
    END LOOP;

    RETURN;
END;
$$ LANGUAGE plpgsql;

-- Выполнение миграции
DO $$
DECLARE
    v_migration_needed BOOLEAN;
BEGIN
    -- Проверяем, нужна ли миграция
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'ohlc_data'
    ) INTO v_migration_needed;

    IF v_migration_needed THEN
        RAISE NOTICE 'Начинаем миграцию OHLC данных...';

        -- Выполняем миграцию
        CREATE TEMP TABLE migration_results AS
        SELECT * FROM migrate_ohlc_to_separate_tables();

        -- Показываем результаты
        RAISE NOTICE 'Результаты миграции:';
        FOR r IN SELECT * FROM migration_results LOOP
            RAISE NOTICE '  % (%) -> % : % записей',
                r.crypto_name, r.symbol, r.table_name, r.records_migrated;
        END LOOP;

        -- Переименовываем старую таблицу
        ALTER TABLE ohlc_data RENAME TO ohlc_data_old;

        RAISE NOTICE 'Миграция завершена. Старая таблица переименована в ohlc_data_old';
        RAISE NOTICE 'Для удаления старой таблицы выполните: DROP TABLE ohlc_data_old CASCADE;';
    ELSE
        RAISE NOTICE 'Миграция не требуется - таблица ohlc_data не найдена';
    END IF;
END $$;