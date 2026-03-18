# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
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

    def test_save_daily_data_uses_batch_upsert_and_counts_only_new_rows(self):
        self._seed_master()

        first_saved = self.db.save_daily_data(
            pd.DataFrame(
                [
                    {"date": "2026-03-17", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 10, "amount": 20},
                    {"date": "2026-03-18", "open": 10.5, "high": 11.2, "low": 10.1, "close": 11, "volume": 12, "amount": 22},
                ]
            ),
            code="600519",
            data_source="seed",
        )
        second_saved = self.db.save_daily_data(
            pd.DataFrame(
                [
                    {"date": "2026-03-18", "open": 20, "high": 21, "low": 19, "close": 20.5, "volume": 99, "amount": 199},
                    {"date": "2026-03-19", "open": 11, "high": 12, "low": 10, "close": 11.5, "volume": 13, "amount": 23},
                    {"date": "2026-03-19", "open": 11.1, "high": 12.1, "low": 10.1, "close": 11.6, "volume": 14, "amount": 24},
                ]
            ),
            code="600519",
            data_source="sync",
        )

        latest = self.db.get_latest_data("600519", days=5)
        latest_by_date = {item.date.isoformat(): item for item in latest}

        self.assertEqual(first_saved, 2)
        self.assertEqual(second_saved, 1)
        self.assertEqual(len(latest), 3)
        self.assertEqual(latest_by_date["2026-03-18"].close, 20.5)
        self.assertEqual(latest_by_date["2026-03-19"].close, 11.6)
        self.assertEqual(latest_by_date["2026-03-19"].data_source, "sync")

    def test_backfill_history_respects_start_date_floor(self):
        self._seed_master(list_date=date(2024, 1, 2))
        fake_fetcher = MagicMock()
        fake_fetcher.get_daily_data.return_value = (
            pd.DataFrame(
                [
                    {"date": "2026-02-02", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10, "amount": 20},
                    {"date": "2026-02-03", "open": 2, "high": 3, "low": 2, "close": 3, "volume": 11, "amount": 21},
                ]
            ),
            "fake",
        )

        service = StockDailySyncService(db=self.db, fetcher_manager=fake_fetcher)
        result = service.backfill_history_from_master(
            start_date_floor=date(2026, 2, 2),
            target_date=date(2026, 3, 18),
        )

        kwargs = fake_fetcher.get_daily_data.call_args.kwargs
        self.assertEqual(kwargs["start_date"], "2026-02-02")
        self.assertEqual(kwargs["end_date"], "2026-03-18")
        self.assertEqual(result["codes_synced"], 1)

    def test_get_recent_trade_day_floor_returns_earliest_day_in_window(self):
        fake_fetcher = MagicMock()
        service = StockDailySyncService(db=self.db, fetcher_manager=fake_fetcher)

        class _AkStub:
            @staticmethod
            def tool_trade_date_hist_sina():
                return pd.DataFrame(
                    {
                        "trade_date": [
                            "2026-03-13",
                            "2026-03-16",
                            "2026-03-17",
                            "2026-03-18",
                        ]
                    }
                )

        original = sys.modules.get("akshare")
        sys.modules["akshare"] = _AkStub()
        try:
            floor = service.get_recent_trade_day_floor(limit=3, target_date=date(2026, 3, 18))
            self.assertEqual(floor, date(2026, 3, 16))
        finally:
            if original is None:
                sys.modules.pop("akshare", None)
            else:
                sys.modules["akshare"] = original

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

    def test_resolve_worker_count_auto_falls_back_to_serial_for_small_batch(self):
        service = StockDailySyncService(db=self.db, fetcher_manager=MagicMock())
        self.assertEqual(
            service._resolve_worker_count(
                total_targets=3,
                requested_max_workers=8,
                mode="history_backfill",
            ),
            1,
        )

    def test_resolve_worker_count_uses_parallel_for_large_daily_sync_batch(self):
        service = StockDailySyncService(db=self.db, fetcher_manager=MagicMock())
        self.assertEqual(
            service._resolve_worker_count(
                total_targets=10,
                requested_max_workers=None,
                mode="daily_sync",
            ),
            service.DEFAULT_DAILY_SYNC_MAX_WORKERS,
        )

    def test_backfill_history_parallel_resume_from_checkpoint(self):
        DatabaseManager.reset_instance()
        with tempfile.TemporaryDirectory() as temp_dir:
            db = DatabaseManager(db_url=f"sqlite:///{os.path.join(temp_dir, 'stock_daily_resume.db')}")
            db.upsert_cn_stock_master_records([
                {
                    "code": "000001",
                    "name": "平安银行",
                    "exchange": "SZSE",
                    "market": "main",
                    "industry": "银行",
                    "area": "深圳",
                    "list_status": "listed",
                    "is_risk_warning": False,
                    "list_date": date(2024, 1, 2),
                    "delist_date": None,
                    "is_active": True,
                    "source": "test",
                    "source_updated_at": None,
                },
                {
                    "code": "000002",
                    "name": "万科A",
                    "exchange": "SZSE",
                    "market": "main",
                    "industry": "地产",
                    "area": "深圳",
                    "list_status": "listed",
                    "is_risk_warning": False,
                    "list_date": date(2024, 1, 2),
                    "delist_date": None,
                    "is_active": True,
                    "source": "test",
                    "source_updated_at": None,
                },
                {
                    "code": "000004",
                    "name": "国华网安",
                    "exchange": "SZSE",
                    "market": "main",
                    "industry": "软件",
                    "area": "深圳",
                    "list_status": "listed",
                    "is_risk_warning": False,
                    "list_date": date(2024, 1, 2),
                    "delist_date": None,
                    "is_active": True,
                    "source": "test",
                    "source_updated_at": None,
                },
            ])

            call_codes = []
            failure_once = {"000002": True}

            class FakeFetcher:
                def get_daily_data(self, *, stock_code, start_date, end_date, days):
                    call_codes.append(stock_code)
                    if failure_once.get(stock_code):
                        failure_once[stock_code] = False
                        raise RuntimeError("temporary db disconnect")
                    return (
                        pd.DataFrame(
                            [
                                {
                                    "date": start_date,
                                    "open": 1,
                                    "high": 2,
                                    "low": 1,
                                    "close": 2,
                                    "volume": 10,
                                    "amount": 20,
                                }
                            ]
                        ),
                        "fake",
                    )

            checkpoint_path = os.path.join(temp_dir, "history_checkpoint.json")
            service = StockDailySyncService(
                db=db,
                fetcher_manager=FakeFetcher(),
                fetcher_factory=FakeFetcher,
            )
            first = service.backfill_history_from_master(
                start_date_floor=date(2026, 2, 2),
                target_date=date(2026, 3, 18),
                max_workers=2,
                checkpoint_path=Path(checkpoint_path),
                resume=False,
            )

            self.assertEqual(first["errors"], 1)
            self.assertTrue(os.path.exists(checkpoint_path))

            second = service.backfill_history_from_master(
                start_date_floor=date(2026, 2, 2),
                target_date=date(2026, 3, 18),
                max_workers=2,
                checkpoint_path=Path(checkpoint_path),
                resume=True,
            )

            self.assertEqual(second["errors"], 0)
            self.assertEqual(second["codes_total"], 1)
            self.assertEqual(second["resumed_completed_codes"], 2)
            self.assertFalse(os.path.exists(checkpoint_path))
            self.assertEqual(len(db.get_latest_data("000001", days=5)), 1)
            self.assertEqual(len(db.get_latest_data("000002", days=5)), 1)
            self.assertEqual(len(db.get_latest_data("000004", days=5)), 1)


if __name__ == "__main__":
    unittest.main()
