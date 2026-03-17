CREATE TABLE IF NOT EXISTS stock_alert_state (
    rule_id VARCHAR(128) PRIMARY KEY NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    alert_type VARCHAR(32) NOT NULL,
    last_condition_met BOOLEAN NOT NULL DEFAULT 0,
    last_triggered_at DATETIME,
    last_trigger_value FLOAT,
    last_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_alert_state_stock_code
    ON stock_alert_state (stock_code);

CREATE INDEX IF NOT EXISTS idx_stock_alert_state_alert_type
    ON stock_alert_state (alert_type);
