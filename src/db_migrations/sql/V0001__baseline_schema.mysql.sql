-- baseline schema
CREATE TABLE analysis_history (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	query_id VARCHAR(64), 
	code VARCHAR(10) NOT NULL, 
	name VARCHAR(50), 
	report_type VARCHAR(16), 
	sentiment_score INTEGER, 
	operation_advice VARCHAR(20), 
	trend_prediction VARCHAR(50), 
	analysis_summary TEXT, 
	raw_result TEXT, 
	news_content TEXT, 
	context_snapshot TEXT, 
	ideal_buy FLOAT, 
	secondary_buy FLOAT, 
	stop_loss FLOAT, 
	take_profit FLOAT, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_analysis_code_time ON analysis_history (code, created_at);
CREATE INDEX ix_analysis_history_code ON analysis_history (code);
CREATE INDEX ix_analysis_history_created_at ON analysis_history (created_at);
CREATE INDEX ix_analysis_history_query_id ON analysis_history (query_id);
CREATE INDEX ix_analysis_history_report_type ON analysis_history (report_type);

CREATE TABLE backtest_summaries (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	scope VARCHAR(16) NOT NULL, 
	code VARCHAR(16), 
	eval_window_days INTEGER NOT NULL, 
	engine_version VARCHAR(16) NOT NULL, 
	computed_at DATETIME, 
	total_evaluations INTEGER, 
	completed_count INTEGER, 
	insufficient_count INTEGER, 
	long_count INTEGER, 
	cash_count INTEGER, 
	win_count INTEGER, 
	loss_count INTEGER, 
	neutral_count INTEGER, 
	direction_accuracy_pct FLOAT, 
	win_rate_pct FLOAT, 
	neutral_rate_pct FLOAT, 
	avg_stock_return_pct FLOAT, 
	avg_simulated_return_pct FLOAT, 
	stop_loss_trigger_rate FLOAT, 
	take_profit_trigger_rate FLOAT, 
	ambiguous_rate FLOAT, 
	avg_days_to_first_hit FLOAT, 
	advice_breakdown_json TEXT, 
	diagnostics_json TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_backtest_summary_scope_code_window_version UNIQUE (scope, code, eval_window_days, engine_version)
);
CREATE INDEX ix_backtest_summaries_code ON backtest_summaries (code);
CREATE INDEX ix_backtest_summaries_computed_at ON backtest_summaries (computed_at);
CREATE INDEX ix_backtest_summaries_scope ON backtest_summaries (scope);

CREATE TABLE conversation_messages (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	session_id VARCHAR(100) NOT NULL, 
	`role` VARCHAR(20) NOT NULL, 
	content TEXT NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_conversation_messages_created_at ON conversation_messages (created_at);
CREATE INDEX ix_conversation_messages_session_id ON conversation_messages (session_id);

CREATE TABLE fundamental_snapshot (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	query_id VARCHAR(64) NOT NULL, 
	code VARCHAR(10) NOT NULL, 
	payload TEXT NOT NULL, 
	source_chain TEXT, 
	coverage TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_fundamental_snapshot_code ON fundamental_snapshot (code);
CREATE INDEX ix_fundamental_snapshot_created ON fundamental_snapshot (created_at);
CREATE INDEX ix_fundamental_snapshot_created_at ON fundamental_snapshot (created_at);
CREATE INDEX ix_fundamental_snapshot_query_code ON fundamental_snapshot (query_id, code);
CREATE INDEX ix_fundamental_snapshot_query_id ON fundamental_snapshot (query_id);

CREATE TABLE llm_usage (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	call_type VARCHAR(32) NOT NULL, 
	model VARCHAR(128) NOT NULL, 
	stock_code VARCHAR(16), 
	prompt_tokens INTEGER NOT NULL, 
	completion_tokens INTEGER NOT NULL, 
	total_tokens INTEGER NOT NULL, 
	called_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_llm_usage_call_type ON llm_usage (call_type);
CREATE INDEX ix_llm_usage_called_at ON llm_usage (called_at);

CREATE TABLE news_intel (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	query_id VARCHAR(64), 
	code VARCHAR(10) NOT NULL, 
	name VARCHAR(50), 
	dimension VARCHAR(32), 
	query VARCHAR(255), 
	provider VARCHAR(32), 
	title VARCHAR(300) NOT NULL, 
	snippet TEXT, 
	url VARCHAR(1000) NOT NULL, 
	source VARCHAR(100), 
	published_date DATETIME, 
	fetched_at DATETIME, 
	query_source VARCHAR(32), 
	requester_platform VARCHAR(20), 
	requester_user_id VARCHAR(64), 
	requester_user_name VARCHAR(64), 
	requester_chat_id VARCHAR(64), 
	requester_message_id VARCHAR(64), 
	requester_query VARCHAR(255), 
	PRIMARY KEY (id), 
	CONSTRAINT uix_news_url UNIQUE (url)
);
CREATE INDEX ix_news_code_pub ON news_intel (code, published_date);
CREATE INDEX ix_news_intel_code ON news_intel (code);
CREATE INDEX ix_news_intel_dimension ON news_intel (dimension);
CREATE INDEX ix_news_intel_fetched_at ON news_intel (fetched_at);
CREATE INDEX ix_news_intel_provider ON news_intel (provider);
CREATE INDEX ix_news_intel_published_date ON news_intel (published_date);
CREATE INDEX ix_news_intel_query_id ON news_intel (query_id);
CREATE INDEX ix_news_intel_query_source ON news_intel (query_source);

CREATE TABLE portfolio_accounts (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	owner_id VARCHAR(64), 
	name VARCHAR(64) NOT NULL, 
	broker VARCHAR(64), 
	market VARCHAR(8) NOT NULL, 
	base_currency VARCHAR(8) NOT NULL, 
	is_active BOOL NOT NULL, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_portfolio_account_owner_active ON portfolio_accounts (owner_id, is_active);
CREATE INDEX ix_portfolio_accounts_created_at ON portfolio_accounts (created_at);
CREATE INDEX ix_portfolio_accounts_is_active ON portfolio_accounts (is_active);
CREATE INDEX ix_portfolio_accounts_market ON portfolio_accounts (market);
CREATE INDEX ix_portfolio_accounts_owner_id ON portfolio_accounts (owner_id);

CREATE TABLE portfolio_fx_rates (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	from_currency VARCHAR(8) NOT NULL, 
	to_currency VARCHAR(8) NOT NULL, 
	rate_date DATE NOT NULL, 
	rate FLOAT NOT NULL, 
	source VARCHAR(32) NOT NULL, 
	is_stale BOOL NOT NULL, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_portfolio_fx_pair_date UNIQUE (from_currency, to_currency, rate_date)
);
CREATE INDEX ix_portfolio_fx_rates_from_currency ON portfolio_fx_rates (from_currency);
CREATE INDEX ix_portfolio_fx_rates_rate_date ON portfolio_fx_rates (rate_date);
CREATE INDEX ix_portfolio_fx_rates_to_currency ON portfolio_fx_rates (to_currency);

CREATE TABLE stock_daily (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	code VARCHAR(10) NOT NULL, 
	date DATE NOT NULL, 
	open FLOAT, 
	high FLOAT, 
	low FLOAT, 
	close FLOAT, 
	volume FLOAT, 
	amount FLOAT, 
	pct_chg FLOAT, 
	ma5 FLOAT, 
	ma10 FLOAT, 
	ma20 FLOAT, 
	volume_ratio FLOAT, 
	data_source VARCHAR(50), 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_code_date UNIQUE (code, date)
);
CREATE INDEX ix_code_date ON stock_daily (code, date);
CREATE INDEX ix_stock_daily_code ON stock_daily (code);
CREATE INDEX ix_stock_daily_date ON stock_daily (date);

CREATE TABLE backtest_results (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	analysis_history_id INTEGER NOT NULL, 
	code VARCHAR(10) NOT NULL, 
	analysis_date DATE, 
	eval_window_days INTEGER NOT NULL, 
	engine_version VARCHAR(16) NOT NULL, 
	eval_status VARCHAR(16) NOT NULL, 
	evaluated_at DATETIME, 
	operation_advice VARCHAR(20), 
	position_recommendation VARCHAR(8), 
	start_price FLOAT, 
	end_close FLOAT, 
	max_high FLOAT, 
	min_low FLOAT, 
	stock_return_pct FLOAT, 
	direction_expected VARCHAR(16), 
	direction_correct BOOL, 
	outcome VARCHAR(16), 
	stop_loss FLOAT, 
	take_profit FLOAT, 
	hit_stop_loss BOOL, 
	hit_take_profit BOOL, 
	first_hit VARCHAR(16), 
	first_hit_date DATE, 
	first_hit_trading_days INTEGER, 
	simulated_entry_price FLOAT, 
	simulated_exit_price FLOAT, 
	simulated_exit_reason VARCHAR(24), 
	simulated_return_pct FLOAT, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_backtest_analysis_window_version UNIQUE (analysis_history_id, eval_window_days, engine_version), 
	FOREIGN KEY(analysis_history_id) REFERENCES analysis_history (id)
);
CREATE INDEX ix_backtest_code_date ON backtest_results (code, analysis_date);
CREATE INDEX ix_backtest_results_analysis_date ON backtest_results (analysis_date);
CREATE INDEX ix_backtest_results_analysis_history_id ON backtest_results (analysis_history_id);
CREATE INDEX ix_backtest_results_code ON backtest_results (code);
CREATE INDEX ix_backtest_results_evaluated_at ON backtest_results (evaluated_at);

CREATE TABLE portfolio_cash_ledger (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	account_id INTEGER NOT NULL, 
	event_date DATE NOT NULL, 
	direction VARCHAR(8) NOT NULL, 
	amount FLOAT NOT NULL, 
	currency VARCHAR(8) NOT NULL, 
	note VARCHAR(255), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id)
);
CREATE INDEX ix_portfolio_cash_account_date ON portfolio_cash_ledger (account_id, event_date);
CREATE INDEX ix_portfolio_cash_ledger_account_id ON portfolio_cash_ledger (account_id);
CREATE INDEX ix_portfolio_cash_ledger_created_at ON portfolio_cash_ledger (created_at);
CREATE INDEX ix_portfolio_cash_ledger_event_date ON portfolio_cash_ledger (event_date);

CREATE TABLE portfolio_corporate_actions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	account_id INTEGER NOT NULL, 
	symbol VARCHAR(16) NOT NULL, 
	market VARCHAR(8) NOT NULL, 
	currency VARCHAR(8) NOT NULL, 
	effective_date DATE NOT NULL, 
	action_type VARCHAR(24) NOT NULL, 
	cash_dividend_per_share FLOAT, 
	split_ratio FLOAT, 
	note VARCHAR(255), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id)
);
CREATE INDEX ix_portfolio_ca_account_date ON portfolio_corporate_actions (account_id, effective_date);
CREATE INDEX ix_portfolio_corporate_actions_account_id ON portfolio_corporate_actions (account_id);
CREATE INDEX ix_portfolio_corporate_actions_created_at ON portfolio_corporate_actions (created_at);
CREATE INDEX ix_portfolio_corporate_actions_effective_date ON portfolio_corporate_actions (effective_date);
CREATE INDEX ix_portfolio_corporate_actions_symbol ON portfolio_corporate_actions (symbol);

CREATE TABLE portfolio_daily_snapshots (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	account_id INTEGER NOT NULL, 
	snapshot_date DATE NOT NULL, 
	cost_method VARCHAR(8) NOT NULL, 
	base_currency VARCHAR(8) NOT NULL, 
	total_cash FLOAT NOT NULL, 
	total_market_value FLOAT NOT NULL, 
	total_equity FLOAT NOT NULL, 
	unrealized_pnl FLOAT NOT NULL, 
	realized_pnl FLOAT NOT NULL, 
	fee_total FLOAT NOT NULL, 
	tax_total FLOAT NOT NULL, 
	fx_stale BOOL NOT NULL, 
	payload TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_portfolio_snapshot_account_date_method UNIQUE (account_id, snapshot_date, cost_method), 
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id)
);
CREATE INDEX ix_portfolio_daily_snapshots_account_id ON portfolio_daily_snapshots (account_id);
CREATE INDEX ix_portfolio_daily_snapshots_created_at ON portfolio_daily_snapshots (created_at);
CREATE INDEX ix_portfolio_daily_snapshots_snapshot_date ON portfolio_daily_snapshots (snapshot_date);

CREATE TABLE portfolio_positions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	account_id INTEGER NOT NULL, 
	cost_method VARCHAR(8) NOT NULL, 
	symbol VARCHAR(16) NOT NULL, 
	market VARCHAR(8) NOT NULL, 
	currency VARCHAR(8) NOT NULL, 
	quantity FLOAT NOT NULL, 
	avg_cost FLOAT NOT NULL, 
	total_cost FLOAT NOT NULL, 
	last_price FLOAT NOT NULL, 
	market_value_base FLOAT NOT NULL, 
	unrealized_pnl_base FLOAT NOT NULL, 
	valuation_currency VARCHAR(8) NOT NULL, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_portfolio_position_account_symbol_market_currency UNIQUE (account_id, symbol, market, currency, cost_method), 
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id)
);
CREATE INDEX ix_portfolio_positions_account_id ON portfolio_positions (account_id);
CREATE INDEX ix_portfolio_positions_symbol ON portfolio_positions (symbol);
CREATE INDEX ix_portfolio_positions_updated_at ON portfolio_positions (updated_at);

CREATE TABLE portfolio_trades (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	account_id INTEGER NOT NULL, 
	trade_uid VARCHAR(128), 
	symbol VARCHAR(16) NOT NULL, 
	market VARCHAR(8) NOT NULL, 
	currency VARCHAR(8) NOT NULL, 
	trade_date DATE NOT NULL, 
	side VARCHAR(8) NOT NULL, 
	quantity FLOAT NOT NULL, 
	price FLOAT NOT NULL, 
	fee FLOAT, 
	tax FLOAT, 
	note VARCHAR(255), 
	dedup_hash VARCHAR(64), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_portfolio_trade_uid UNIQUE (account_id, trade_uid), 
	CONSTRAINT uix_portfolio_trade_dedup_hash UNIQUE (account_id, dedup_hash), 
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id)
);
CREATE INDEX ix_portfolio_trade_account_date ON portfolio_trades (account_id, trade_date);
CREATE INDEX ix_portfolio_trades_account_id ON portfolio_trades (account_id);
CREATE INDEX ix_portfolio_trades_created_at ON portfolio_trades (created_at);
CREATE INDEX ix_portfolio_trades_dedup_hash ON portfolio_trades (dedup_hash);
CREATE INDEX ix_portfolio_trades_symbol ON portfolio_trades (symbol);
CREATE INDEX ix_portfolio_trades_trade_date ON portfolio_trades (trade_date);

CREATE TABLE portfolio_position_lots (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	account_id INTEGER NOT NULL, 
	cost_method VARCHAR(8) NOT NULL, 
	symbol VARCHAR(16) NOT NULL, 
	market VARCHAR(8) NOT NULL, 
	currency VARCHAR(8) NOT NULL, 
	open_date DATE NOT NULL, 
	remaining_quantity FLOAT NOT NULL, 
	unit_cost FLOAT NOT NULL, 
	source_trade_id INTEGER, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(account_id) REFERENCES portfolio_accounts (id), 
	FOREIGN KEY(source_trade_id) REFERENCES portfolio_trades (id)
);
CREATE INDEX ix_portfolio_lot_account_symbol ON portfolio_position_lots (account_id, symbol);
CREATE INDEX ix_portfolio_position_lots_account_id ON portfolio_position_lots (account_id);
CREATE INDEX ix_portfolio_position_lots_open_date ON portfolio_position_lots (open_date);
CREATE INDEX ix_portfolio_position_lots_symbol ON portfolio_position_lots (symbol);
CREATE INDEX ix_portfolio_position_lots_updated_at ON portfolio_position_lots (updated_at);
