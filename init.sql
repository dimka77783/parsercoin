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
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, added_date)
);

-- Создание таблицы для OHLC данных
CREATE TABLE IF NOT EXISTS ohlc_data (
    id SERIAL PRIMARY KEY,
    crypto_id INTEGER REFERENCES cryptocurrencies(id) ON DELETE CASCADE,
    timestamp BIGINT NOT NULL,
    datetime TIMESTAMP NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(crypto_id, timestamp)
);

-- Индексы для улучшения производительности
CREATE INDEX idx_crypto_symbol ON cryptocurrencies(symbol);
CREATE INDEX idx_crypto_added_date ON cryptocurrencies(added_date);
CREATE INDEX idx_crypto_gecko_id ON cryptocurrencies(coin_gecko_id);
CREATE INDEX idx_ohlc_crypto_id ON ohlc_data(crypto_id);
CREATE INDEX idx_ohlc_timestamp ON ohlc_data(timestamp);
CREATE INDEX idx_ohlc_datetime ON ohlc_data(datetime);

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