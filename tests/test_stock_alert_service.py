# -*- coding: utf-8 -*-
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import Config
from src.storage import DatabaseManager
from src.services.stock_alert_service import StockAlertService


class _FakeFeishuSender:
    def __init__(self):
        self.messages = []

    def has_credentials(self):
        return True

    def send_markdown(self, content, **kwargs):
        self.messages.append({"content": content, "kwargs": kwargs})
        return True


class _FakeNotifier:
    def is_available(self):
        return False

    def send(self, _content):
        return False


class TestStockAlertService(unittest.TestCase):
    def setUp(self):
        DatabaseManager.reset_instance()
        self.db = DatabaseManager(db_url="sqlite:///:memory:")

    def tearDown(self):
        DatabaseManager.reset_instance()

    def test_price_cross_triggers_once_until_reset(self):
        config = Config(
            stock_list=["600519"],
            agent_event_alert_rules_json=json.dumps(
                [
                    {
                        "rule_id": "moutai-break-1800",
                        "stock_code": "600519",
                        "alert_type": "price_cross",
                        "direction": "above",
                        "price": 1800,
                        "cooldown_seconds": 0,
                    }
                ]
            ),
        )

        fetcher = MagicMock()
        fetcher.get_realtime_quote.side_effect = [
            SimpleNamespace(price=1801, name="贵州茅台", change_pct=1.2, volume_ratio=1.4),
            SimpleNamespace(price=1802, name="贵州茅台", change_pct=1.5, volume_ratio=1.5),
            SimpleNamespace(price=1795, name="贵州茅台", change_pct=-0.2, volume_ratio=0.9),
            SimpleNamespace(price=1805, name="贵州茅台", change_pct=2.1, volume_ratio=1.8),
        ]
        fetcher.get_stock_name.return_value = "贵州茅台"

        sender = _FakeFeishuSender()
        service = StockAlertService(
            config=config,
            db=self.db,
            fetcher_manager=fetcher,
            feishu_sender=sender,
            notifier=_FakeNotifier(),
        )

        first_events = service.run_once()
        second_events = service.run_once()
        third_events = service.run_once()
        fourth_events = service.run_once()

        self.assertEqual(len(first_events), 1)
        self.assertEqual(len(second_events), 0)
        self.assertEqual(len(third_events), 0)
        self.assertEqual(len(fourth_events), 1)
        self.assertEqual(len(sender.messages), 2)

        states = self.db.get_stock_alert_states(["moutai-break-1800"])
        self.assertTrue(states["moutai-break-1800"]["last_condition_met"])

    def test_load_rules_skips_unsupported_alert_type(self):
        config = Config(
            stock_list=["600519"],
            agent_event_alert_rules_json=json.dumps(
                [
                    {
                        "rule_id": "unsupported",
                        "stock_code": "600519",
                        "alert_type": "sentiment_alert",
                        "threshold": 1,
                    }
                ]
            ),
        )

        service = StockAlertService(
            config=config,
            db=self.db,
            fetcher_manager=MagicMock(),
            feishu_sender=_FakeFeishuSender(),
            notifier=_FakeNotifier(),
        )

        self.assertEqual(service.load_rules(), [])


if __name__ == "__main__":
    unittest.main()
