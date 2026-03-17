# -*- coding: utf-8 -*-
import unittest
import sys
import os
import tempfile
from pathlib import Path
from sqlalchemy import text

# Ensure src module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.storage import DatabaseManager

class TestStorage(unittest.TestCase):
    
    def test_parse_sniper_value(self):
        """测试解析狙击点位数值"""
        
        # 1. 正常数值
        self.assertEqual(DatabaseManager._parse_sniper_value(100), 100.0)
        self.assertEqual(DatabaseManager._parse_sniper_value(100.5), 100.5)
        self.assertEqual(DatabaseManager._parse_sniper_value("100"), 100.0)
        self.assertEqual(DatabaseManager._parse_sniper_value("100.5"), 100.5)
        
        # 2. 包含中文描述和"元"
        self.assertEqual(DatabaseManager._parse_sniper_value("建议在 100 元附近买入"), 100.0)
        self.assertEqual(DatabaseManager._parse_sniper_value("价格：100.5元"), 100.5)
        
        # 3. 包含干扰数字（修复的Bug场景）
        # 之前 "MA5" 会被错误提取为 5.0，现在应该提取 "元" 前面的 100
        text_bug = "无法给出。需等待MA5数据恢复，在股价回踩MA5且乖离率<2%时考虑100元"
        self.assertEqual(DatabaseManager._parse_sniper_value(text_bug), 100.0)
        
        # 4. 更多干扰场景
        text_complex = "MA10为20.5，建议在30元买入"
        self.assertEqual(DatabaseManager._parse_sniper_value(text_complex), 30.0)
        
        text_multiple = "支撑位10元，阻力位20元" # 应该提取最后一个"元"前面的数字，即20，或者更复杂的逻辑？
        # 当前逻辑是找最后一个冒号，然后找之后的第一个"元"，提取中间的数字。
        # 测试没有冒号的情况
        self.assertEqual(DatabaseManager._parse_sniper_value("30元"), 30.0)
        
        # 测试多个数字在"元"之前
        self.assertEqual(DatabaseManager._parse_sniper_value("MA5 10 20元"), 20.0)
        
        # 5. Fallback: no "元" character — extracts last non-MA number
        self.assertEqual(DatabaseManager._parse_sniper_value("102.10-103.00（MA5附近）"), 103.0)
        self.assertEqual(DatabaseManager._parse_sniper_value("97.62-98.50（MA10附近）"), 98.5)
        self.assertEqual(DatabaseManager._parse_sniper_value("93.40下方（MA20支撑）"), 93.4)
        self.assertEqual(DatabaseManager._parse_sniper_value("108.00-110.00（前期高点阻力）"), 110.0)

        # 6. 无效输入
        self.assertIsNone(DatabaseManager._parse_sniper_value(None))
        self.assertIsNone(DatabaseManager._parse_sniper_value(""))
        self.assertIsNone(DatabaseManager._parse_sniper_value("没有数字"))
        self.assertIsNone(DatabaseManager._parse_sniper_value("MA5但没有元"))

        # 7. 回归：括号内技术指标数字不应被提取
        self.assertNotEqual(DatabaseManager._parse_sniper_value("1.52-1.53 (回踩MA5/10附近)"), 10.0)
        self.assertNotEqual(DatabaseManager._parse_sniper_value("1.55-1.56(MA5/M20支撑)"), 20.0)
        self.assertNotEqual(DatabaseManager._parse_sniper_value("1.49-1.50(MA60附近企稳)"), 60.0)
        # 验证正确值在区间内
        self.assertIn(DatabaseManager._parse_sniper_value("1.52-1.53 (回踩MA5/10附近)"), [1.52, 1.53])
        self.assertIn(DatabaseManager._parse_sniper_value("1.55-1.56(MA5/M20支撑)"), [1.55, 1.56])
        self.assertIn(DatabaseManager._parse_sniper_value("1.49-1.50(MA60附近企稳)"), [1.49, 1.50])

    def test_get_chat_sessions_prefix_is_scoped_by_colon_boundary(self):
        DatabaseManager.reset_instance()
        db = DatabaseManager(db_url="sqlite:///:memory:")

        db.save_conversation_message("telegram_12345:chat", "user", "first user")
        db.save_conversation_message("telegram_123456:chat", "user", "second user")

        sessions = db.get_chat_sessions(session_prefix="telegram_12345")

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], "telegram_12345:chat")

        DatabaseManager.reset_instance()

    def test_get_chat_sessions_can_include_legacy_exact_session_id(self):
        DatabaseManager.reset_instance()
        db = DatabaseManager(db_url="sqlite:///:memory:")

        db.save_conversation_message("feishu_u1", "user", "legacy chat")
        db.save_conversation_message("feishu_u1:ask_600519", "user", "ask session")

        sessions = db.get_chat_sessions(
            session_prefix="feishu_u1:",
            extra_session_ids=["feishu_u1"],
        )

        self.assertEqual({item["session_id"] for item in sessions}, {"feishu_u1", "feishu_u1:ask_600519"})

        DatabaseManager.reset_instance()

    def test_config_database_url_mysql_is_normalized(self):
        from src.config import Config

        cfg = Config(
            stock_list=["600519"],
            database_url="mysql://user:pass@127.0.0.1:3306/dsa?charset=utf8mb4",
        )

        self.assertEqual(
            cfg.get_db_url(),
            "mysql+pymysql://user:pass@127.0.0.1:3306/dsa?charset=utf8mb4",
        )

    def test_config_database_url_takes_precedence_over_database_path(self):
        from src.config import Config

        cfg = Config(
            stock_list=["600519"],
            database_url="mysql+pymysql://user:pass@127.0.0.1:3306/dsa",
            database_path="./data/should_not_be_used.db",
        )

        self.assertEqual(
            cfg.get_db_url(),
            "mysql+pymysql://user:pass@127.0.0.1:3306/dsa",
        )

    def test_config_database_path_fallback_creates_parent_dir(self):
        from src.config import Config

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "nested" / "stock_analysis.db"
            cfg = Config(
                stock_list=["600519"],
                database_path=str(db_path),
            )

            db_url = cfg.get_db_url()

            self.assertTrue(db_path.parent.exists())
            self.assertTrue(db_url.startswith("sqlite:///"))
            self.assertTrue(db_url.endswith("stock_analysis.db"))

    def test_upsert_cn_stock_master_records(self):
        DatabaseManager.reset_instance()
        db = DatabaseManager(db_url="sqlite:///:memory:")

        first = db.upsert_cn_stock_master_records([
            {
                "code": "600519",
                "name": "贵州茅台",
                "exchange": "SSE",
                "market": "main",
                "industry": "酿酒行业",
                "area": "贵州",
                "list_status": "listed",
                "is_risk_warning": False,
                "list_date": None,
                "delist_date": None,
                "is_active": True,
                "source": "test",
                "source_updated_at": None,
            }
        ])
        second = db.upsert_cn_stock_master_records([
            {
                "code": "600519",
                "name": "贵州茅台股份",
                "exchange": "SSE",
                "market": "main",
                "industry": "白酒",
                "area": "贵州",
                "list_status": "listed",
                "is_risk_warning": False,
                "list_date": None,
                "delist_date": None,
                "is_active": True,
                "source": "test2",
                "source_updated_at": None,
            }
        ])

        with db.get_session() as session:
            row = session.execute(
                text("SELECT code, name, industry, source FROM cn_stock_master WHERE code='600519'")
            ).fetchone()

        self.assertEqual(first, {"inserted": 1, "updated": 0})
        self.assertEqual(second, {"inserted": 0, "updated": 1})
        self.assertEqual(tuple(row), ("600519", "贵州茅台股份", "白酒", "test2"))

        DatabaseManager.reset_instance()

    def test_upsert_cn_stock_master_records_dedupes_same_code_in_batch(self):
        DatabaseManager.reset_instance()
        db = DatabaseManager(db_url="sqlite:///:memory:")

        stats = db.upsert_cn_stock_master_records([
            {
                "code": "600519",
                "name": "贵州茅台",
                "exchange": "SSE",
                "market": "main",
                "industry": "酿酒行业",
                "area": "贵州",
                "list_status": "listed",
                "is_risk_warning": False,
                "list_date": None,
                "delist_date": None,
                "is_active": True,
                "source": "test",
                "source_updated_at": None,
            },
            {
                "code": "600519",
                "name": "贵州茅台股份有限公司",
                "exchange": "SSE",
                "market": "main",
                "industry": "白酒",
                "area": "贵州",
                "list_status": "listed",
                "is_risk_warning": False,
                "list_date": None,
                "delist_date": None,
                "is_active": True,
                "source": "test-latest",
                "source_updated_at": None,
            },
        ])

        with db.get_session() as session:
            rows = session.execute(
                text("SELECT code, name, industry, source FROM cn_stock_master WHERE code='600519'")
            ).fetchall()

        self.assertEqual(stats, {"inserted": 1, "updated": 0})
        self.assertEqual(len(rows), 1)
        self.assertEqual(tuple(rows[0]), ("600519", "贵州茅台股份有限公司", "白酒", "test-latest"))

        DatabaseManager.reset_instance()

    def test_delete_cn_stock_master_records_not_matching_prefixes(self):
        DatabaseManager.reset_instance()
        db = DatabaseManager(db_url="sqlite:///:memory:")

        db.upsert_cn_stock_master_records([
            {
                "code": "600519",
                "name": "贵州茅台",
                "exchange": "SSE",
                "market": "main",
                "industry": None,
                "area": None,
                "list_status": "listed",
                "is_risk_warning": False,
                "list_date": None,
                "delist_date": None,
                "is_active": True,
                "source": "test",
                "source_updated_at": None,
            },
            {
                "code": "430047",
                "name": "诺思兰德",
                "exchange": "BSE",
                "market": "beijing",
                "industry": None,
                "area": None,
                "list_status": "listed",
                "is_risk_warning": False,
                "list_date": None,
                "delist_date": None,
                "is_active": True,
                "source": "test",
                "source_updated_at": None,
            },
        ])

        deleted = db.delete_cn_stock_master_records_not_matching_prefixes(("6", "0", "3"))

        with db.get_session() as session:
            rows = session.execute(
                text("SELECT code FROM cn_stock_master ORDER BY code")
            ).fetchall()

        self.assertEqual(deleted, 1)
        self.assertEqual([row[0] for row in rows], ["600519"])

        DatabaseManager.reset_instance()

    def test_schema_migration_row_created_on_init(self):
        DatabaseManager.reset_instance()
        db = DatabaseManager(db_url="sqlite:///:memory:")

        with db.get_session() as session:
            rows = session.execute(
                text("SELECT version, script, checksum FROM schema_migrations ORDER BY version")
            ).fetchall()

        self.assertEqual([row[0] for row in rows], ["0001", "0002", "0003", "0004", "0005", "0006", "0007"])
        self.assertEqual(
            [row[1] for row in rows],
            [
                "V0001__baseline_schema.sqlite.sql",
                "V0002__create_migration_demo_records.sqlite.sql",
                "V0003__add_chinese_table_comments.sqlite.sql",
                "V0004__add_chinese_column_comments.sqlite.sql",
                "V0005__create_cn_stock_master.sqlite.sql",
                "V0006__fix_cn_stock_master_charset.sqlite.sql",
                "V0007__create_stock_alert_state.sqlite.sql",
            ],
        )
        self.assertTrue(all(len(row[2]) == 32 for row in rows))

        DatabaseManager.reset_instance()

    def test_fresh_database_creates_all_declared_tables(self):
        from src.storage import Base

        DatabaseManager.reset_instance()
        db = DatabaseManager(db_url="sqlite:///:memory:")

        with db.get_session() as session:
            tables = {
                row[0]
                for row in session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                ).fetchall()
            }

        expected_tables = set(Base.metadata.tables.keys())
        self.assertTrue(expected_tables.issubset(tables))
        self.assertIn("schema_migrations", tables)

        DatabaseManager.reset_instance()

    def test_existing_table_missing_columns_requires_explicit_migration(self):
        DatabaseManager.reset_instance()

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "schema_patch_test.db"
            bootstrap_db = DatabaseManager(db_url=f"sqlite:///{db_path}")
            with bootstrap_db.get_session() as session:
                session.execute(text("DROP TABLE IF EXISTS analysis_history"))
                session.execute(
                    text(
                        """
                        CREATE TABLE analysis_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            code VARCHAR(10) NOT NULL,
                            created_at DATETIME
                        )
                        """
                    )
                )
                session.commit()
            DatabaseManager.reset_instance()

            patched_db = DatabaseManager(db_url=f"sqlite:///{db_path}")
            with patched_db.get_session() as session:
                columns = session.execute(text("PRAGMA table_info('analysis_history')")).fetchall()
                migrations = session.execute(
                    text("SELECT version FROM schema_migrations ORDER BY version")
                ).fetchall()

            column_names = {row[1] for row in columns}
            self.assertNotIn("query_id", column_names)
            self.assertNotIn("analysis_summary", column_names)
            self.assertEqual([row[0] for row in migrations], ["0001", "0002", "0003", "0004", "0005", "0006", "0007"])

            DatabaseManager.reset_instance()

    def test_upsert_and_get_stock_alert_state(self):
        DatabaseManager.reset_instance()
        db = DatabaseManager(db_url="sqlite:///:memory:")

        db.upsert_stock_alert_state(
            rule_id="rule-1",
            stock_code="600519",
            alert_type="price_cross",
            last_condition_met=True,
            last_trigger_value=1800.0,
            last_message="first",
        )
        db.upsert_stock_alert_state(
            rule_id="rule-1",
            stock_code="600519",
            alert_type="price_cross",
            last_condition_met=False,
            last_trigger_value=1799.5,
            last_message="second",
        )

        states = db.get_stock_alert_states(["rule-1"])

        self.assertIn("rule-1", states)
        self.assertEqual(states["rule-1"]["stock_code"], "600519")
        self.assertEqual(states["rule-1"]["alert_type"], "price_cross")
        self.assertFalse(states["rule-1"]["last_condition_met"])
        self.assertEqual(states["rule-1"]["last_trigger_value"], 1799.5)
        self.assertEqual(states["rule-1"]["last_message"], "second")

        DatabaseManager.reset_instance()

if __name__ == '__main__':
    unittest.main()
