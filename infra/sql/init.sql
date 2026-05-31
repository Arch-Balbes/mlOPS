-- ETA ML system schema (feature store + raw tables)

CREATE DATABASE airflow;

CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(64) PRIMARY KEY,
    order_created TIMESTAMP NOT NULL,
    warehouse_id INTEGER NOT NULL,
    distance_km DOUBLE PRECISION NOT NULL,
    items_count INTEGER NOT NULL,
    payment_type VARCHAR(32) NOT NULL
);

CREATE TABLE IF NOT EXISTS routes (
    route_id VARCHAR(64) PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL REFERENCES orders(order_id),
    courier_id VARCHAR(64) NOT NULL,
    courier_load DOUBLE PRECISION NOT NULL,
    weather_code INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS delivery_events (
    event_id VARCHAR(64) PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL REFERENCES orders(order_id),
    delivered_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS features_eta (
    order_id VARCHAR(64) PRIMARY KEY,
    feature_set_id VARCHAR(32) NOT NULL DEFAULT 'v1',
    distance_km DOUBLE PRECISION NOT NULL,
    hour_of_day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    items_count INTEGER NOT NULL,
    payment_type INTEGER NOT NULL,
    courier_load DOUBLE PRECISION NOT NULL,
    weather_code INTEGER NOT NULL,
    delivery_minutes DOUBLE PRECISION,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions_log (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL,
    predicted_minutes DOUBLE PRECISION NOT NULL,
    model_uri VARCHAR(512) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_features_eta_updated ON features_eta(updated_at);
CREATE INDEX IF NOT EXISTS idx_predictions_log_created ON predictions_log(created_at);
