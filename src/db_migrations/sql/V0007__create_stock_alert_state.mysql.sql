CREATE TABLE IF NOT EXISTS stock_alert_state (
    rule_id VARCHAR(128) NOT NULL COMMENT '告警规则 ID',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    alert_type VARCHAR(32) NOT NULL COMMENT '告警类型',
    last_condition_met TINYINT(1) NOT NULL DEFAULT 0 COMMENT '最近一次检查是否命中条件',
    last_triggered_at DATETIME NULL COMMENT '最近一次触发时间',
    last_trigger_value DOUBLE NULL COMMENT '最近一次触发值',
    last_message TEXT NULL COMMENT '最近一次推送消息',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (rule_id),
    KEY idx_stock_alert_state_stock_code (stock_code),
    KEY idx_stock_alert_state_alert_type (alert_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='股票告警状态表';
