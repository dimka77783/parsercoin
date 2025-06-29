-- Crypto Parser Database Schema
-- Объединенный файл инициализации БД

-- Основная таблица криптовалют
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
    ohlc_table_name VARCHAR(100),
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, added_date)
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_crypto_symbol ON cryptocurrencies(symbol);
CREATE INDEX IF NOT EXISTS idx_crypto_added_date ON cryptocurrencies(added_date);
CREATE INDEX IF NOT EXISTS idx_crypto_gecko_id ON cryptocurrencies(coin_gecko_id);
CREATE INDEX IF NOT EXISTS idx_crypto_ohlc_table ON cryptocurrencies(ohlc_table_name);

-- Функция для обновления last_updated_at
CREATE OR REPLACE FUNCTION update_last_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер обновления
DROP TRIGGER IF EXISTS update_crypto_last_updated ON cryptocurrencies;
CREATE TRIGGER update_crypto_last_updated
    BEFORE UPDATE ON cryptocurrencies
    FOR EACH ROW
    EXECUTE FUNCTION update_last_updated_at();

-- Функция для безопасного имени таблицы
CREATE OR REPLACE FUNCTION safe_table_name(p_symbol VARCHAR, p_added_date DATE)
RETURNS VARCHAR AS $$
DECLARE
    v_safe_name VARCHAR;
BEGIN
    v_safe_name := LOWER(p_symbol);
    v_safe_name := REGEXP_REPLACE(v_safe_name, '[^a-z0-9]', '_', 'g');
    v_safe_name := REGEXP_REPLACE(v_safe_name, '_+', '_', 'g');
    v_safe_name := TRIM('_' FROM v_safe_name);
    v_safe_name := 'ohlc_' || v_safe_name || '_' || TO_CHAR(p_added_date, 'YYYYMMDD');

    IF LENGTH(v_safe_name) > 63 THEN
        v_safe_name := SUBSTRING(v_safe_name, 1, 63);
    END IF;

    RETURN v_safe_name;
END;
$$ LANGUAGE plpgsql;

-- Функция создания OHLC таблицы
CREATE OR REPLACE FUNCTION create_ohlc_table(p_symbol VARCHAR, p_added_date DATE)
RETURNS VARCHAR AS $$
DECLARE
    v_table_name VARCHAR;
    v_sql TEXT;
BEGIN
    v_table_name := safe_table_name(p_symbol, p_added_date);

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public'
                   AND table_name = v_table_name) THEN

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

-- Триггер для автоматического создания OHLC таблицы
CREATE OR REPLACE FUNCTION create_ohlc_table_trigger()
RETURNS TRIGGER AS $$
DECLARE
    v_table_name VARCHAR;
BEGIN
    v_table_name := create_ohlc_table(NEW.symbol, NEW.added_date);
    NEW.ohlc_table_name := v_table_name;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS create_ohlc_table_on_insert ON cryptocurrencies;
CREATE TRIGGER create_ohlc_table_on_insert
    BEFORE INSERT ON cryptocurrencies
    FOR EACH ROW
    EXECUTE FUNCTION create_ohlc_table_trigger();

-- Представление для удобного просмотра
CREATE OR REPLACE VIEW crypto_stats AS
SELECT
    c.id,
    c.name,
    c.symbol,
    c.added_date,
    CURRENT_DATE - c.added_date as age_days,
    c.ohlc_table_name,
    c.last_updated_at,
    CASE
        WHEN c.ohlc_table_name IS NOT NULL THEN
            (SELECT COUNT(*) FROM pg_class WHERE relname = c.ohlc_table_name)
        ELSE 0
    END as ohlc_count
FROM cryptocurrencies c
ORDER BY c.first_seen_at DESC;