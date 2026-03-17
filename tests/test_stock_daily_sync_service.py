# -*- coding: utf-8 -*-
import os
import sys
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.stock_daily_sync_service import StockDailySyncService
from src.storage import DatabaseManager


class TestStockDailySyncService(unittest.TestCase):
    def setUp(self):
        DatabaseManager.reset_instance()
        self.db = DatabaseManager(db_url="sqlite:///:memory:")

    def tearDown(self):
        DatabaseManager.reset_instance()

    def _seed_master(self, code: str = "600519", list_date: date = date(2024, 1, 2)):
        self.db.upsert_cn_stock_master_records([
            {
                "code": code,
                "name": "贵州茅台",
                "exchange": "SSE",
                "market": "main",
                "industry": "白酒",
                "area": "贵州",
                "list_status": "listed",
                "is_risk_warning": False,
                "list_date": list_date,
                "delist_date": None,
                "is_active": True,
                "source": "test",
                "source_updated_at": None,
            }
        ])

    def test_backfill_history_uses_list_date_when_no_existing_daily_data(self):
        self._seed_master()
        fake_fetcher = MagicMock()
        fake_fetcher.get_daily_data.return_value = (
            pd.DataFrame(
                [
                    {"date": "2024-01-02", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10, "amount": 20},
                    {"date": "2024-01-03", "open": 2, "high": 3, "low": 2, "close": 3, "volume": 11, "amount": 21},
                ]
            ),
            "fake",
        )

        service = StockDailySyncService(db=self.db, fetcher_manager=fake_fetcher)
        result = service.backfill_history_from_master()

        kwargs = fake_fetcher.get_daily_data.call_args.kwargs
        self.assertEqual(kwargs["stock_code"], "600519")
        self.assertEqual(kwargs["start_date"], "2024-01-02")
        self.assertEqual(result["codes_synced"], 1)
        self.assertEqual(len(self.db.get_latest_data("600519", days=5)), 2)

    def test_sync_daily_skips_when_not_trade_day(self):
        self._seed_master()
        fake_fetcher = MagicMock()
        service = StockDailySyncService(db=self.db, fetcher_manager=fake_fetcher)

        with patch.object(service, "is_cn_trade_day", return_value=False):
            result = service.sync_daily_if_trade_day(target_date=date(2026, 3, 14))

        self.assertFalse(result["trade_day"])
        self.assertEqual(result["codes_processed"], 0)
        fake_fetcher.get_daily_data.assert_not_called()

    def test_sync_daily_uses_latest_date_plus_one_for_incremental_fill(self):
        self._seed_master()
        self.db.save_daily_data(
            pd.DataFrame(
                [
                    {"date": "2026-03-17", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 10, "amount": 20}
                ]
            ),
            code="600519",
            data_source="seed",
        )

        fake_fetcher = MagicMock()
        fake_fetcher.get_daily_data.return_value = (
            pd.DataFrame(
                [
                    {"date": "2026-03-18", "open": 10.5, "high": 11.2, "low": 10.1, "close": 11, "volume": 12, "amount": 22}
                ]
            ),
            "fake",
        )

        service = StockDailySyncService(db=self.db, fetcher_manager=fake_fetcher)
        with patch.object(service, "is_cn_trade_day", return_value=True):
            result = service.sync_daily_if_trade_day(target_date=date(2026, 3, 18))

        kwargs = fake_fetcher.get_daily_data.call_args.kwargs
        self.assertEqual(kwargs["start_date"], "2026-03-18")
        self.assertEqual(kwargs["end_date"], "2026-03-18")
        self.assertTrue(result["trade_day"])
        self.assertEqual(result["codes_synced"], 1)

    def test_sync_daily_is_idempotent_for_same_code_and_date(self):
        self._seed_master()
        fake_fetcher = MagicMock()
        fake_fetcher.get_daily_data.return_value = (
            pd.DataFrame(
                [
                    {"date": "2026-03-18", "open": 10.5, "high": 11.2, "low": 10.1, "close": 11, "volume": 12, "amount": 22}
                ]
            ),
            "fake",
        )

        service = StockDailySyncService(db=self.db, fetcher_manager=fake_fetcher)
        with patch.object(service, "is_cn_trade_day", return_value=True):
            first = service.sync_daily_if_trade_day(target_date=date(2026, 3, 18))
            second = service.sync_daily_if_trade_day(target_date=date(2026, 3, 18))

        self.assertEqual(first["rows_saved"], 1)
        self.assertEqual(second["rows_saved"], 0)
        self.assertEqual(len(self.db.get_latest_data("600519", days=5)), 1)

    def test_is_cn_trade_day_uses_akshare_trade_calendar(self):
        fake_fetcher = MagicMock()
        service = StockDailySyncService(db=self.db, fetcher_manager=fake_fetcher)

        class _AkStub:
            @staticmethod
            def tool_trade_date_hist_sina():
                return pd.DataFrame({"trade_date": ["2026-03-18", "2026-03-19"]})

        original = sys.modules.get("akshare")
        sys.modules["akshare"] = _AkStub()
        try:
            self.assertTrue(service.is_cn_trade_day(date(2026, 3, 18)))
            self.assertFalse(service.is_cn_trade_day(date(2026, 3, 20)))
        finally:
            if original is None:
                sys.modules.pop("akshare", None)
            else:
                sys.modules["akshare"] = original


if __name__ == "__main__":
    unittest.main()
