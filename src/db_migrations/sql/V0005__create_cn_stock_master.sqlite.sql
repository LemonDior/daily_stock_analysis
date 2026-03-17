CREATE TABLE cn_stock_master (
    id INTEGER NOT NULL,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(64) NOT NULL,
    exchange VARCHAR(8) NOT NULL,
    market VARCHAR(16) NOT NULL,
    industry VARCHAR(128),
    area VARCHAR(64),
    list_status VARCHAR(16) NOT NULL,
    is_risk_warning BOOLEAN NOT NULL,
    list_date DATE,
    delist_date DATE,
    is_active BOOLEAN NOT NULL,
    source VARCHAR(32) NOT NULL,
    source_updated_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uk_cn_stock_master_code UNIQUE (code)
);
CREATE INDEX idx_cn_stock_master_name ON cn_stock_master (name);
CREATE INDEX idx_cn_stock_master_exchange_market ON cn_stock_master (exchange, market);
CREATE INDEX idx_cn_stock_master_industry ON cn_stock_master (industry);
CREATE INDEX idx_cn_stock_master_list_status ON cn_stock_master (list_status);
CREATE INDEX idx_cn_stock_master_is_risk_warning ON cn_stock_master (is_risk_warning);
CREATE INDEX idx_cn_stock_master_is_active ON cn_stock_master (is_active);
