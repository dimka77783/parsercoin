-- Создание таблицы для криптовалют
CREATE TABLE IF NOT EXISTS cryptocurrencies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    chain VARCHAR(100),
    price VARCHAR(100),
    change_24h VARCHAR(50),
    market_cap VARCHAR(100),
    fdv VARCHAR(100),
    added_date DATE,
    added_raw VARCHAR(100),
    coin_gecko_id VARCHAR(255),
    ohlc_table_name VARCHAR(100), -- Имя таблицы с OHLC данными
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, added_date)
);

-- Индексы для улучшения производительности
CREATE INDEX idx_crypto_symbol ON cryptocurrencies(symbol);
CREATE INDEX idx_crypto_added_date ON cryptocurrencies(added_date);
CREATE INDEX idx_crypto_gecko_id ON cryptocurrencies(coin_gecko_id);
CREATE INDEX idx_crypto_ohlc_table ON cryptocurrencies(ohlc_table_name);

-- Функция для обновления last_updated_at
CREATE OR REPLACE FUNCTION update_last_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для автоматического обновления last_updated_at
CREATE TRIGGER update_crypto_last_updated
    BEFORE UPDATE ON cryptocurrencies
    FOR EACH ROW
    EXECUTE FUNCTION update_last_updated_at();

-- Функция для создания безопасного имени таблицы
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

-- Функция для создания OHLC таблицы для конкретной монеты
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
                timestamp BIGINT NOT NULL UNIQUE,
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
        EXECUTE format('CREATE INDEX idx_%I_timestamp ON %I(timestamp)', v_table_name, v_table_name);
        EXECUTE format('CREATE INDEX idx_%I_datetime ON %I(datetime)', v_table_name, v_table_name);
        EXECUTE format('CREATE INDEX idx_%I_date ON %I(date)', v_table_name, v_table_name);

        RAISE NOTICE 'Created OHLC table: %', v_table_name;
    END IF;

    RETURN v_table_name;
END;
$$ LANGUAGE plpgsql;

-- Триггер для автоматического создания OHLC таблицы при добавлении новой криптовалюты
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

-- Создаем триггер
CREATE TRIGGER create_ohlc_table_on_insert
    BEFORE INSERT ON cryptocurrencies
    FOR EACH ROW
    EXECUTE FUNCTION create_ohlc_table_trigger();

-- Представление для удобного просмотра всех OHLC данных
CREATE OR REPLACE VIEW all_ohlc_data AS
SELECT
    c.id as crypto_id,
    c.name,
    c.symbol,
    c.added_date,
    c.ohlc_table_name,
    (SELECT COUNT(*) FROM information_schema.tables
     WHERE table_name = c.ohlc_table_name) as table_exists,
    (SELECT COUNT(*) FROM pg_class
     WHERE relname = c.ohlc_table_name AND relkind = 'r') as record_count_estimate
FROM cryptocurrencies c;

-- Функция для получения последних OHLC данных монеты
CREATE OR REPLACE FUNCTION get_latest_ohlc(p_symbol VARCHAR, p_added_date DATE, p_limit INTEGER DEFAULT 10)
RETURNS TABLE (
    timestamp BIGINT,
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
        SELECT timestamp, datetime, open, high, low, close
        FROM %I
        ORDER BY timestamp DESC
        LIMIT %s
    ', v_table_name, p_limit);

    RETURN QUERY EXECUTE v_sql;
END;
$$ LANGUAGE plpgsql;

-- Функция для очистки старых OHLC таблиц
CREATE OR REPLACE FUNCTION cleanup_old_ohlc_tables(p_days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    v_table_name VARCHAR;
    v_count INTEGER := 0;
    v_cutoff_date DATE;
BEGIN
    v_cutoff_date := CURRENT_DATE - p_days_to_keep;

    FOR v_table_name IN
        SELECT ohlc_table_name
        FROM cryptocurrencies
        WHERE added_date < v_cutoff_date
        AND ohlc_table_name IS NOT NULL
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', v_table_name);
        v_count := v_count + 1;
    END LOOP;

    -- Удаляем записи о старых криптовалютах
    DELETE FROM cryptocurrencies WHERE added_date < v_cutoff_date;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql;