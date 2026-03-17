# -*- coding: utf-8 -*-
"""
手动启动 `stock_daily` 回填/补齐任务的测试类入口。

用法示例：
    python3 tests/manual_stock_daily_sync_runner.py history-backfill
    python3 tests/manual_stock_daily_sync_runner.py history-backfill --max-codes 200
    python3 tests/manual_stock_daily_sync_runner.py daily-sync
    python3 tests/manual_stock_daily_sync_runner.py daily-sync --target-date 2026-03-18
"""

import argparse
import json
import logging
import os
import sys
import unittest
from datetime import date
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import setup_env

setup_env()

from src.services.stock_daily_sync_service import StockDailySyncService
from src.storage import DatabaseManager


logger = logging.getLogger(__name__)


class TestStockDailySyncManualRunner(unittest.TestCase):
    """手动执行 `stock_daily` 任务的测试类包装。"""

    @classmethod
    def setUpClass(cls) -> None:
        DatabaseManager.reset_instance()
        cls.service = StockDailySyncService()

    @classmethod
    def tearDownClass(cls) -> None:
        DatabaseManager.reset_instance()

    def run_history_backfill_job(self, *, max_codes: Optional[int] = None):
        result = self.service.backfill_history_from_master(max_codes=max_codes)
        self._print_result(result)
        return result

    def run_daily_sync_job(
        self,
        *,
        target_date: Optional[date] = None,
        max_codes: Optional[int] = None,
    ):
        result = self.service.sync_daily_if_trade_day(
            target_date=target_date,
            max_codes=max_codes,
        )
        self._print_result(result)
        return result

    @staticmethod
    def _print_result(result) -> None:
        logger.info("stock_daily 任务执行结果如下")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="手动执行 stock_daily 回填/补齐任务")
    subparsers = parser.add_subparsers(dest="command", required=True)

    history_backfill = subparsers.add_parser(
        "history-backfill",
        help="根据 cn_stock_master 全量回填 stock_daily 历史日线",
    )
    history_backfill.add_argument(
        "--max-codes",
        type=int,
        default=None,
        help="限制处理股票数量，便于小批量测试",
    )

    daily_sync = subparsers.add_parser(
        "daily-sync",
        help="按交易日规则补齐指定日期的 stock_daily 日线，默认当天",
    )
    daily_sync.add_argument(
        "--target-date",
        type=str,
        default=None,
        help="目标日期，格式 YYYY-MM-DD；不传时默认今天",
    )
    daily_sync.add_argument(
        "--max-codes",
        type=int,
        default=None,
        help="限制处理股票数量，便于小批量测试",
    )

    return parser.parse_args()


def _parse_target_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"非法日期格式: {value}，请使用 YYYY-MM-DD") from exc


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    )

    args = _parse_args()
    runner = TestStockDailySyncManualRunner()
    TestStockDailySyncManualRunner.setUpClass()
    try:
        if args.command == "history-backfill":
            runner.run_history_backfill_job(max_codes=args.max_codes)
        else:
            runner.run_daily_sync_job(
                target_date=_parse_target_date(args.target_date),
                max_codes=args.max_codes,
            )
    finally:
        TestStockDailySyncManualRunner.tearDownClass()
