-- add chinese comments for existing tables
ALTER TABLE analysis_history COMMENT='分析结果历史表';
ALTER TABLE backtest_summaries COMMENT='回测汇总结果表';
ALTER TABLE conversation_messages COMMENT='对话消息记录表';
ALTER TABLE fundamental_snapshot COMMENT='基本面快照表';
ALTER TABLE llm_usage COMMENT='大模型调用用量表';
ALTER TABLE news_intel COMMENT='新闻情报表';
ALTER TABLE portfolio_accounts COMMENT='投资账户表';
ALTER TABLE portfolio_fx_rates COMMENT='汇率记录表';
ALTER TABLE stock_daily COMMENT='股票日线行情表';
ALTER TABLE backtest_results COMMENT='回测明细结果表';
ALTER TABLE portfolio_cash_ledger COMMENT='账户现金流水表';
ALTER TABLE portfolio_corporate_actions COMMENT='企业行为记录表';
ALTER TABLE portfolio_daily_snapshots COMMENT='每日资产快照表';
ALTER TABLE portfolio_positions COMMENT='当前持仓汇总表';
ALTER TABLE portfolio_trades COMMENT='交易流水表';
ALTER TABLE portfolio_position_lots COMMENT='持仓批次表';
ALTER TABLE migration_demo_records COMMENT='数据库迁移演示表';
