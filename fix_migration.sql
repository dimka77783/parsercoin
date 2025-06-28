-- Скрипт для исправления существующей БД и добавления поддержки отдельных таблиц

-- 1. Добавляем недостающий столбец в таблицу cryptocurrencies
ALTER TABLE cryptocurrencies
ADD COLUMN IF NOT EXISTS ohlc_table_name VARCHAR(100);

-- 2. Создаем индекс для нового столбца
CREATE INDEX IF NOT EXISTS idx_crypto_ohlc_table ON cryptocurrencies(ohlc_table_name);

-- 3. Удаляем старое представление если есть
DROP VIEW IF EXISTS all_ohlc_data CASCADE;

-- 4. Создаем функцию для безопасного имени таблицы
CREATE OR REPLACE FUNCTION safe_table_name(p_symbol VARCHAR, p_added_date DATE)
RETURNS VARCHAR AS $$
DECLARE
    v_safe_name VARCHAR;
BEGIN
    -- Преобразуем символ в нижний регистр и заменяем небезопасные символы
    v_safe_name := LOWER(p_symbol);
    v_safe_name := REGEXP_REPLACE(v_safe_name, '[^a-z0-9]', '_', 'g');
    v_safe_name := REGEXP_REPLACE(v_safe_name, '_+', '_', 'g');
    v_safe_name := TRIM('_' FROM v_safe_name);

    -- Добавляем префикс и дату
    v_safe_name := 'ohlc_' || v_safe_name || '_' || TO_CHAR(p_added_date, 'YYYYMMDD');

    -- Ограничиваем длину до 63 символов (максимум для PostgreSQL)
    IF LENGTH(v_safe_name) > 63 THEN
        v_safe_name := SUBSTRING(v_safe_name, 1, 63);
    END IF;

    RETURN v_safe_name;
END;
$$ LANGUAGE plpgsql;

-- 5. Создаем функцию для создания OHLC таблицы
CREATE OR REPLACE FUNCTION create_ohlc_table(p_symbol VARCHAR, p_added_date DATE)
RETURNS VARCHAR AS $$
DECLARE
    v_table_name VARCHAR;
    v_sql TEXT;
BEGIN
    -- Получаем безопасное имя таблицы
    v_table_name := safe_table_name(p_symbol, p_added_date);

    -- Проверяем, существует ли уже таблица
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public'
                   AND table_name = v_table_name) THEN

        -- Создаем таблицу OHLC
        v_sql := format('
            CREATE TABLE %I (
                id SERIAL PRIMARY KEY,
                "timestamp" BIGINT NOT NULL UNIQUE,
                datetime TIMESTAMP NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                open DECIMAL(20, 8) NOT NULL,
                high DECIMAL(20, 8) NOT NULL,
                low DECIMAL(20, 8) NOT NULL,
                close DECIMAL(20, 8) NOT NULL,
                volume DECIMAL(20, 8) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )', v_table_name);

        EXECUTE v_sql;

        -- Создаем индексы
        EXECUTE format('CREATE INDEX idx_%I_timestamp ON %I("timestamp")', v_table_name, v_table_name);
        EXECUTE format('CREATE INDEX idx_%I_datetime ON %I(datetime)', v_table_name, v_table_name);
        EXECUTE format('CREATE INDEX idx_%I_date ON %I(date)', v_table_name, v_table_name);

        RAISE NOTICE 'Created OHLC table: %', v_table_name;
    END IF;

    RETURN v_table_name;
END;
$$ LANGUAGE plpgsql;

-- 6. Создаем триггер для автоматического создания OHLC таблицы
CREATE OR REPLACE FUNCTION create_ohlc_table_trigger()
RETURNS TRIGGER AS $$
DECLARE
    v_table_name VARCHAR;
BEGIN
    -- Создаем таблицу OHLC для новой монеты
    v_table_name := create_ohlc_table(NEW.symbol, NEW.added_date);

    -- Обновляем запись с именем таблицы
    NEW.ohlc_table_name := v_table_name;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 7. Удаляем старый триггер если есть
DROP TRIGGER IF EXISTS create_ohlc_table_on_insert ON cryptocurrencies;

-- 8. Создаем новый триггер
CREATE TRIGGER create_ohlc_table_on_insert
    BEFORE INSERT ON cryptocurrencies
    FOR EACH ROW
    EXECUTE FUNCTION create_ohlc_table_trigger();

-- 9. Создаем представление для удобного просмотра
CREATE OR REPLACE VIEW all_ohlc_data AS
SELECT
    c.id as crypto_id,
    c.name,
    c.symbol,
    c.added_date,
    c.ohlc_table_name,
    CASE
        WHEN c.ohlc_table_name IS NOT NULL THEN
            EXISTS (SELECT 1 FROM information_schema.tables
                    WHERE table_name = c.ohlc_table_name)
        ELSE false
    END as table_exists
FROM cryptocurrencies c;

-- 10. Создаем функцию для получения последних OHLC данных
CREATE OR REPLACE FUNCTION get_latest_ohlc(p_symbol VARCHAR, p_added_date DATE, p_limit INTEGER DEFAULT 10)
RETURNS TABLE (
    "timestamp" BIGINT,
    datetime TIMESTAMP,
    open DECIMAL,
    high DECIMAL,
    low DECIMAL,
    close DECIMAL
) AS $$
DECLARE
    v_table_name VARCHAR;
    v_sql TEXT;
BEGIN
    -- Получаем имя таблицы
    SELECT ohlc_table_name INTO v_table_name
    FROM cryptocurrencies
    WHERE symbol = p_symbol AND added_date = p_added_date;

    IF v_table_name IS NULL THEN
        RAISE EXCEPTION 'Crypto not found: % (%)', p_symbol, p_added_date;
    END IF;

    -- Выполняем запрос
    v_sql := format('
        SELECT "timestamp", datetime, open, high, low, close
        FROM %I
        ORDER BY "timestamp" DESC
        LIMIT %s
    ', v_table_name, p_limit);

    RETURN QUERY EXECUTE v_sql;
END;
$$ LANGUAGE plpgsql;

-- 11. Функция для миграции существующих данных
CREATE OR REPLACE FUNCTION migrate_existing_ohlc()
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
    -- Проходим по всем криптовалютам с OHLC данными
    FOR v_crypto IN
        SELECT DISTINCT c.id, c.name, c.symbol, c.added_date
        FROM cryptocurrencies c
        WHERE EXISTS (
            SELECT 1 FROM ohlc_data o WHERE o.crypto_id = c.id
        )
        AND c.ohlc_table_name IS NULL
        ORDER BY c.id
    LOOP
        -- Создаем таблицу OHLC для монеты
        v_table_name := create_ohlc_table(v_crypto.symbol, v_crypto.added_date);

        -- Мигрируем данные
        v_sql := format('
            INSERT INTO %I ("timestamp", datetime, date, time, open, high, low, close)
            SELECT timestamp, datetime, date, time, open, high, low, close
            FROM ohlc_data
            WHERE crypto_id = %s
            ON CONFLICT ("timestamp") DO NOTHING
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

-- 12. Выводим текущее состояние
DO $$
DECLARE
    v_total_cryptos INTEGER;
    v_cryptos_with_ohlc INTEGER;
    v_cryptos_with_tables INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_total_cryptos FROM cryptocurrencies;

    SELECT COUNT(DISTINCT crypto_id) INTO v_cryptos_with_ohlc
    FROM ohlc_data;

    SELECT COUNT(*) INTO v_cryptos_with_tables
    FROM cryptocurrencies
    WHERE ohlc_table_name IS NOT NULL;

    RAISE NOTICE '';
    RAISE NOTICE '📊 Текущее состояние БД:';
    RAISE NOTICE '   Всего монет: %', v_total_cryptos;
    RAISE NOTICE '   Монет с OHLC в старой таблице: %', v_cryptos_with_ohlc;
    RAISE NOTICE '   Монет с отдельными таблицами: %', v_cryptos_with_tables;
    RAISE NOTICE '';
    RAISE NOTICE 'Для миграции данных выполните:';
    RAISE NOTICE 'SELECT * FROM migrate_existing_ohlc();';
END $$;