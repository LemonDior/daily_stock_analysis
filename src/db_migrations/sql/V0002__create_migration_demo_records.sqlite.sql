-- demo migration: create migration_demo_records
CREATE TABLE migration_demo_records (
	id INTEGER NOT NULL, 
	title VARCHAR(128) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	notes TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_migration_demo_records_created_at ON migration_demo_records (created_at);
CREATE INDEX ix_migration_demo_records_status ON migration_demo_records (status);
CREATE INDEX ix_migration_demo_records_title ON migration_demo_records (title);
