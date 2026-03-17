-- add chinese comments for existing columns while preserving current mysql column definitions
SET SESSION group_concat_max_len = 1024 * 1024;

CREATE TEMPORARY TABLE tmp_column_comments (
    table_name VARCHAR(64) NOT NULL,
    column_name VARCHAR(64) NOT NULL,
    column_comment VARCHAR(255) NOT NULL,
    PRIMARY KEY (table_name, column_name)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO tmp_column_comments (table_name, column_name, column_comment) VALUES
    ('analysis_history', 'id', '主键ID'),
    ('analysis_history', 'query_id', '查询链路ID'),
    ('analysis_history', 'code', '股票代码'),
    ('analysis_history', 'name', '股票名称'),
    ('analysis_history', 'report_type', '报告类型'),
    ('analysis_history', 'sentiment_score', '情绪评分'),
    ('analysis_history', 'operation_advice', '操作建议'),
    ('analysis_history', 'trend_prediction', '趋势预测'),
    ('analysis_history', 'analysis_summary', '分析摘要'),
    ('analysis_history', 'raw_result', '原始分析结果'),
    ('analysis_history', 'news_content', '新闻内容摘要'),
    ('analysis_history', 'context_snapshot', '上下文快照'),
    ('analysis_history', 'ideal_buy', '理想买点'),
    ('analysis_history', 'secondary_buy', '次级买点'),
    ('analysis_history', 'stop_loss', '止损价'),
    ('analysis_history', 'take_profit', '止盈价'),
    ('analysis_history', 'created_at', '创建时间'),
    ('backtest_summaries', 'id', '主键ID'),
    ('backtest_summaries', 'scope', '汇总范围'),
    ('backtest_summaries', 'code', '股票代码'),
    ('backtest_summaries', 'eval_window_days', '评估窗口天数'),
    ('backtest_summaries', 'engine_version', '回测引擎版本'),
    ('backtest_summaries', 'computed_at', '计算时间'),
    ('backtest_summaries', 'total_evaluations', '总评估次数'),
    ('backtest_summaries', 'completed_count', '已完成次数'),
    ('backtest_summaries', 'insufficient_count', '数据不足次数'),
    ('backtest_summaries', 'long_count', '做多建议次数'),
    ('backtest_summaries', 'cash_count', '持币建议次数'),
    ('backtest_summaries', 'win_count', '获胜次数'),
    ('backtest_summaries', 'loss_count', '亏损次数'),
    ('backtest_summaries', 'neutral_count', '中性次数'),
    ('backtest_summaries', 'direction_accuracy_pct', '方向准确率'),
    ('backtest_summaries', 'win_rate_pct', '胜率'),
    ('backtest_summaries', 'neutral_rate_pct', '中性占比'),
    ('backtest_summaries', 'avg_stock_return_pct', '平均股票收益率'),
    ('backtest_summaries', 'avg_simulated_return_pct', '平均模拟收益率'),
    ('backtest_summaries', 'stop_loss_trigger_rate', '止损触发率'),
    ('backtest_summaries', 'take_profit_trigger_rate', '止盈触发率'),
    ('backtest_summaries', 'ambiguous_rate', '模糊结果占比'),
    ('backtest_summaries', 'avg_days_to_first_hit', '平均首次命中天数'),
    ('backtest_summaries', 'advice_breakdown_json', '建议分布JSON'),
    ('backtest_summaries', 'diagnostics_json', '诊断信息JSON'),
    ('conversation_messages', 'id', '主键ID'),
    ('conversation_messages', 'session_id', '会话ID'),
    ('conversation_messages', 'role', '消息角色'),
    ('conversation_messages', 'content', '消息内容'),
    ('conversation_messages', 'created_at', '创建时间'),
    ('fundamental_snapshot', 'id', '主键ID'),
    ('fundamental_snapshot', 'query_id', '查询链路ID'),
    ('fundamental_snapshot', 'code', '股票代码'),
    ('fundamental_snapshot', 'payload', '基本面载荷'),
    ('fundamental_snapshot', 'source_chain', '数据来源链路'),
    ('fundamental_snapshot', 'coverage', '覆盖说明'),
    ('fundamental_snapshot', 'created_at', '创建时间'),
    ('llm_usage', 'id', '主键ID'),
    ('llm_usage', 'call_type', '调用类型'),
    ('llm_usage', 'model', '模型名称'),
    ('llm_usage', 'stock_code', '股票代码'),
    ('llm_usage', 'prompt_tokens', '提示词Token数'),
    ('llm_usage', 'completion_tokens', '回复Token数'),
    ('llm_usage', 'total_tokens', '总Token数'),
    ('llm_usage', 'called_at', '调用时间'),
    ('migration_demo_records', 'id', '主键ID'),
    ('migration_demo_records', 'title', '标题'),
    ('migration_demo_records', 'status', '状态'),
    ('migration_demo_records', 'notes', '备注'),
    ('migration_demo_records', 'created_at', '创建时间'),
    ('news_intel', 'id', '主键ID'),
    ('news_intel', 'query_id', '查询链路ID'),
    ('news_intel', 'code', '股票代码'),
    ('news_intel', 'name', '股票名称'),
    ('news_intel', 'dimension', '搜索维度'),
    ('news_intel', 'query', '搜索查询词'),
    ('news_intel', 'provider', '搜索提供方'),
    ('news_intel', 'title', '新闻标题'),
    ('news_intel', 'snippet', '摘要片段'),
    ('news_intel', 'url', '新闻链接'),
    ('news_intel', 'source', '新闻来源'),
    ('news_intel', 'published_date', '发布时间'),
    ('news_intel', 'fetched_at', '抓取时间'),
    ('news_intel', 'query_source', '请求来源'),
    ('news_intel', 'requester_platform', '请求平台'),
    ('news_intel', 'requester_user_id', '请求用户ID'),
    ('news_intel', 'requester_user_name', '请求用户名'),
    ('news_intel', 'requester_chat_id', '请求会话ID'),
    ('news_intel', 'requester_message_id', '请求消息ID'),
    ('news_intel', 'requester_query', '原始请求内容'),
    ('portfolio_accounts', 'id', '主键ID'),
    ('portfolio_accounts', 'owner_id', '所属用户ID'),
    ('portfolio_accounts', 'name', '账户名称'),
    ('portfolio_accounts', 'broker', '券商名称'),
    ('portfolio_accounts', 'market', '市场标识'),
    ('portfolio_accounts', 'base_currency', '基准币种'),
    ('portfolio_accounts', 'is_active', '是否启用'),
    ('portfolio_accounts', 'created_at', '创建时间'),
    ('portfolio_accounts', 'updated_at', '更新时间'),
    ('portfolio_fx_rates', 'id', '主键ID'),
    ('portfolio_fx_rates', 'from_currency', '源币种'),
    ('portfolio_fx_rates', 'to_currency', '目标币种'),
    ('portfolio_fx_rates', 'rate_date', '汇率日期'),
    ('portfolio_fx_rates', 'rate', '汇率值'),
    ('portfolio_fx_rates', 'source', '汇率来源'),
    ('portfolio_fx_rates', 'is_stale', '是否过期'),
    ('portfolio_fx_rates', 'updated_at', '更新时间'),
    ('stock_daily', 'id', '主键ID'),
    ('stock_daily', 'code', '股票代码'),
    ('stock_daily', 'date', '交易日期'),
    ('stock_daily', 'open', '开盘价'),
    ('stock_daily', 'high', '最高价'),
    ('stock_daily', 'low', '最低价'),
    ('stock_daily', 'close', '收盘价'),
    ('stock_daily', 'volume', '成交量'),
    ('stock_daily', 'amount', '成交额'),
    ('stock_daily', 'pct_chg', '涨跌幅'),
    ('stock_daily', 'ma5', '5日均线'),
    ('stock_daily', 'ma10', '10日均线'),
    ('stock_daily', 'ma20', '20日均线'),
    ('stock_daily', 'volume_ratio', '量比'),
    ('stock_daily', 'data_source', '数据来源'),
    ('stock_daily', 'created_at', '创建时间'),
    ('stock_daily', 'updated_at', '更新时间'),
    ('backtest_results', 'id', '主键ID'),
    ('backtest_results', 'analysis_history_id', '分析历史ID'),
    ('backtest_results', 'code', '股票代码'),
    ('backtest_results', 'analysis_date', '分析日期'),
    ('backtest_results', 'eval_window_days', '评估窗口天数'),
    ('backtest_results', 'engine_version', '回测引擎版本'),
    ('backtest_results', 'eval_status', '评估状态'),
    ('backtest_results', 'evaluated_at', '评估时间'),
    ('backtest_results', 'operation_advice', '操作建议'),
    ('backtest_results', 'position_recommendation', '仓位建议'),
    ('backtest_results', 'start_price', '起始价格'),
    ('backtest_results', 'end_close', '结束收盘价'),
    ('backtest_results', 'max_high', '期间最高价'),
    ('backtest_results', 'min_low', '期间最低价'),
    ('backtest_results', 'stock_return_pct', '股票收益率'),
    ('backtest_results', 'direction_expected', '预期方向'),
    ('backtest_results', 'direction_correct', '方向是否正确'),
    ('backtest_results', 'outcome', '结果分类'),
    ('backtest_results', 'stop_loss', '止损价'),
    ('backtest_results', 'take_profit', '止盈价'),
    ('backtest_results', 'hit_stop_loss', '是否触发止损'),
    ('backtest_results', 'hit_take_profit', '是否触发止盈'),
    ('backtest_results', 'first_hit', '首次命中类型'),
    ('backtest_results', 'first_hit_date', '首次命中日期'),
    ('backtest_results', 'first_hit_trading_days', '首次命中交易日数'),
    ('backtest_results', 'simulated_entry_price', '模拟入场价'),
    ('backtest_results', 'simulated_exit_price', '模拟离场价'),
    ('backtest_results', 'simulated_exit_reason', '模拟离场原因'),
    ('backtest_results', 'simulated_return_pct', '模拟收益率'),
    ('portfolio_cash_ledger', 'id', '主键ID'),
    ('portfolio_cash_ledger', 'account_id', '账户ID'),
    ('portfolio_cash_ledger', 'event_date', '发生日期'),
    ('portfolio_cash_ledger', 'direction', '资金方向'),
    ('portfolio_cash_ledger', 'amount', '金额'),
    ('portfolio_cash_ledger', 'currency', '币种'),
    ('portfolio_cash_ledger', 'note', '备注'),
    ('portfolio_cash_ledger', 'created_at', '创建时间'),
    ('portfolio_corporate_actions', 'id', '主键ID'),
    ('portfolio_corporate_actions', 'account_id', '账户ID'),
    ('portfolio_corporate_actions', 'symbol', '证券代码'),
    ('portfolio_corporate_actions', 'market', '市场标识'),
    ('portfolio_corporate_actions', 'currency', '币种'),
    ('portfolio_corporate_actions', 'effective_date', '生效日期'),
    ('portfolio_corporate_actions', 'action_type', '企业行为类型'),
    ('portfolio_corporate_actions', 'cash_dividend_per_share', '每股现金分红'),
    ('portfolio_corporate_actions', 'split_ratio', '拆分比例'),
    ('portfolio_corporate_actions', 'note', '备注'),
    ('portfolio_corporate_actions', 'created_at', '创建时间'),
    ('portfolio_daily_snapshots', 'id', '主键ID'),
    ('portfolio_daily_snapshots', 'account_id', '账户ID'),
    ('portfolio_daily_snapshots', 'snapshot_date', '快照日期'),
    ('portfolio_daily_snapshots', 'cost_method', '成本法'),
    ('portfolio_daily_snapshots', 'base_currency', '基准币种'),
    ('portfolio_daily_snapshots', 'total_cash', '总现金'),
    ('portfolio_daily_snapshots', 'total_market_value', '总市值'),
    ('portfolio_daily_snapshots', 'total_equity', '总权益'),
    ('portfolio_daily_snapshots', 'unrealized_pnl', '未实现盈亏'),
    ('portfolio_daily_snapshots', 'realized_pnl', '已实现盈亏'),
    ('portfolio_daily_snapshots', 'fee_total', '手续费合计'),
    ('portfolio_daily_snapshots', 'tax_total', '税费合计'),
    ('portfolio_daily_snapshots', 'fx_stale', '汇率是否过期'),
    ('portfolio_daily_snapshots', 'payload', '扩展载荷'),
    ('portfolio_daily_snapshots', 'created_at', '创建时间'),
    ('portfolio_daily_snapshots', 'updated_at', '更新时间'),
    ('portfolio_positions', 'id', '主键ID'),
    ('portfolio_positions', 'account_id', '账户ID'),
    ('portfolio_positions', 'cost_method', '成本法'),
    ('portfolio_positions', 'symbol', '证券代码'),
    ('portfolio_positions', 'market', '市场标识'),
    ('portfolio_positions', 'currency', '币种'),
    ('portfolio_positions', 'quantity', '持仓数量'),
    ('portfolio_positions', 'avg_cost', '平均成本'),
    ('portfolio_positions', 'total_cost', '总成本'),
    ('portfolio_positions', 'last_price', '最新价格'),
    ('portfolio_positions', 'market_value_base', '基准币种市值'),
    ('portfolio_positions', 'unrealized_pnl_base', '基准币种未实现盈亏'),
    ('portfolio_positions', 'valuation_currency', '估值币种'),
    ('portfolio_positions', 'updated_at', '更新时间'),
    ('portfolio_trades', 'id', '主键ID'),
    ('portfolio_trades', 'account_id', '账户ID'),
    ('portfolio_trades', 'trade_uid', '交易唯一标识'),
    ('portfolio_trades', 'symbol', '证券代码'),
    ('portfolio_trades', 'market', '市场标识'),
    ('portfolio_trades', 'currency', '币种'),
    ('portfolio_trades', 'trade_date', '交易日期'),
    ('portfolio_trades', 'side', '交易方向'),
    ('portfolio_trades', 'quantity', '成交数量'),
    ('portfolio_trades', 'price', '成交价格'),
    ('portfolio_trades', 'fee', '手续费'),
    ('portfolio_trades', 'tax', '税费'),
    ('portfolio_trades', 'note', '备注'),
    ('portfolio_trades', 'dedup_hash', '去重哈希'),
    ('portfolio_trades', 'created_at', '创建时间'),
    ('portfolio_position_lots', 'id', '主键ID'),
    ('portfolio_position_lots', 'account_id', '账户ID'),
    ('portfolio_position_lots', 'cost_method', '成本法'),
    ('portfolio_position_lots', 'symbol', '证券代码'),
    ('portfolio_position_lots', 'market', '市场标识'),
    ('portfolio_position_lots', 'currency', '币种'),
    ('portfolio_position_lots', 'open_date', '开仓日期'),
    ('portfolio_position_lots', 'remaining_quantity', '剩余数量'),
    ('portfolio_position_lots', 'unit_cost', '单位成本'),
    ('portfolio_position_lots', 'source_trade_id', '来源交易ID'),
    ('portfolio_position_lots', 'updated_at', '更新时间');

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `analysis_history` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('分析结果历史表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'analysis_history'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `backtest_summaries` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('回测汇总结果表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'backtest_summaries'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `conversation_messages` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('对话消息记录表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'conversation_messages'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `fundamental_snapshot` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('基本面快照表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'fundamental_snapshot'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `llm_usage` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('大模型调用用量表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'llm_usage'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `migration_demo_records` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('数据库迁移演示表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'migration_demo_records'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `news_intel` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('新闻情报表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'news_intel'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `portfolio_accounts` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('投资账户表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'portfolio_accounts'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `portfolio_fx_rates` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('汇率记录表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'portfolio_fx_rates'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `stock_daily` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('股票日线行情表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'stock_daily'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `backtest_results` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('回测明细结果表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'backtest_results'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `portfolio_cash_ledger` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('账户现金流水表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'portfolio_cash_ledger'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `portfolio_corporate_actions` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('企业行为记录表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'portfolio_corporate_actions'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `portfolio_daily_snapshots` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('每日资产快照表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'portfolio_daily_snapshots'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `portfolio_positions` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('当前持仓汇总表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'portfolio_positions'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `portfolio_trades` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('交易流水表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'portfolio_trades'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT CONCAT(
        'ALTER TABLE `portfolio_position_lots` ',
        GROUP_CONCAT(
            CONCAT(
                'MODIFY COLUMN `', c.COLUMN_NAME, '` ', c.COLUMN_TYPE,
                IF(c.CHARACTER_SET_NAME IS NOT NULL, CONCAT(' CHARACTER SET ', c.CHARACTER_SET_NAME), ''),
                IF(c.COLLATION_NAME IS NOT NULL, CONCAT(' COLLATE ', c.COLLATION_NAME), ''),
                IF(c.IS_NULLABLE = 'NO', ' NOT NULL', ' NULL'),
                IF(c.COLUMN_DEFAULT IS NOT NULL, CONCAT(' DEFAULT ', QUOTE(c.COLUMN_DEFAULT)), ''),
                IF(c.EXTRA <> '', CONCAT(' ', c.EXTRA), ''),
                ' COMMENT ', QUOTE(m.column_comment)
            )
            ORDER BY c.ORDINAL_POSITION SEPARATOR ', '
        ),
        ', COMMENT=', QUOTE('持仓批次表')
    )
    FROM information_schema.COLUMNS c
    JOIN tmp_column_comments m ON m.table_name = c.TABLE_NAME AND m.column_name = c.COLUMN_NAME
    WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME = 'portfolio_position_lots'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

DROP TEMPORARY TABLE tmp_column_comments;
