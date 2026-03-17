# -*- coding: utf-8 -*-
"""
`stock_daily` 补齐服务。

职责：
1. 根据 `cn_stock_master` 中的 code 一次性回填历史日线
2. 每日检查 A 股是否为交易日；若是，则补齐当天缺失的日线数据
3. 使用 `stock_daily(code, date)` 唯一约束 + save_daily_data 的 UPSERT 语义，保证数据唯一
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from data_provider.base import DataFetcherManager
from src.storage import DatabaseManager, get_db


logger = logging.getLogger(__name__)


class StockDailySyncService:
    """基于 `cn_stock_master` 的 `stock_daily` 回填与日常补齐服务。"""

    DEFAULT_HISTORY_START = date(1990, 12, 19)
    DAILY_SYNC_TIME = "18:00"

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        fetcher_manager: Optional[DataFetcherManager] = None,
    ) -> None:
        self.db = db or get_db()
        self.fetcher_manager = fetcher_manager or DataFetcherManager()

    def backfill_history_from_master(self, *, max_codes: Optional[int] = None) -> Dict[str, Any]:
        """
        按 `cn_stock_master` 全量补齐历史日线。

        Args:
            max_codes: 可选，限制回填股票数量，便于分批执行/测试
        """
        target_date = date.today()
        targets = self._load_targets(max_codes=max_codes)
        if not targets:
            return self._empty_stats(mode="history_backfill", target_date=target_date)

        latest_dates = self.db.get_stock_daily_latest_dates([item["code"] for item in targets])
        return self._sync_targets(
            targets=targets,
            latest_dates=latest_dates,
            target_date=target_date,
            full_backfill=True,
            mode="history_backfill",
        )

    def sync_daily_if_trade_day(
        self,
        *,
        target_date: Optional[date] = None,
        max_codes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        若 target_date 为 A 股交易日，则补齐当天缺失的日线数据。

        Args:
            target_date: 目标日期，默认今天
            max_codes: 可选，限制处理股票数量
        """
        actual_date = target_date or date.today()
        if not self.is_cn_trade_day(actual_date):
            stats = self._empty_stats(mode="daily_sync", target_date=actual_date)
            stats["trade_day"] = False
            logger.info("A股 %s 为非交易日，跳过 stock_daily 日线补齐", actual_date)
            return stats

        targets = self._load_targets(max_codes=max_codes)
        if not targets:
            stats = self._empty_stats(mode="daily_sync", target_date=actual_date)
            stats["trade_day"] = True
            return stats

        latest_dates = self.db.get_stock_daily_latest_dates([item["code"] for item in targets])
        result = self._sync_targets(
            targets=targets,
            latest_dates=latest_dates,
            target_date=actual_date,
            full_backfill=False,
            mode="daily_sync",
        )
        result["trade_day"] = True
        return result

    def is_cn_trade_day(self, target_date: date) -> bool:
        """
        使用 AkShare 交易日历接口判断 A 股是否开市。

        当前使用：`ak.tool_trade_date_hist_sina()`
        """
        try:
            import akshare as ak
        except ImportError as exc:
            raise RuntimeError("AkShare 未安装，无法判断 A 股交易日") from exc

        df = ak.tool_trade_date_hist_sina()
        if df is None or df.empty:
            raise RuntimeError("AkShare 交易日历返回为空")

        column = "trade_date" if "trade_date" in df.columns else df.columns[0]
        trade_dates = {
            item.date()
            for item in pd.to_datetime(df[column], errors="coerce")
            if not pd.isna(item)
        }
        return target_date in trade_dates

    def _sync_targets(
        self,
        *,
        targets: List[Dict[str, Any]],
        latest_dates: Dict[str, date],
        target_date: date,
        full_backfill: bool,
        mode: str,
    ) -> Dict[str, Any]:
        stats = self._empty_stats(mode=mode, target_date=target_date)
        stats["codes_total"] = len(targets)

        for item in targets:
            code = str(item.get("code") or "").strip()
            if not code:
                continue

            latest_date = latest_dates.get(code)
            start_date = self._resolve_start_date(
                target_date=target_date,
                latest_date=latest_date,
                list_date=item.get("list_date"),
                full_backfill=full_backfill,
            )

            if start_date is None or start_date > target_date:
                stats["codes_skipped"] += 1
                continue

            stats["codes_processed"] += 1
            try:
                df, source = self.fetcher_manager.get_daily_data(
                    stock_code=code,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=target_date.strftime("%Y-%m-%d"),
                    days=max(30, (target_date - start_date).days + 10),
                )
            except Exception as exc:
                stats["errors"] += 1
                logger.warning("补齐 stock_daily 失败(%s): %s", code, exc)
                continue

            filtered_df = self._filter_df(df, start_date=start_date, target_date=target_date)
            if filtered_df is None or filtered_df.empty:
                stats["codes_skipped"] += 1
                continue

            saved_rows = self.db.save_daily_data(filtered_df, code=code, data_source=source)
            stats["rows_saved"] += int(saved_rows)
            stats["codes_synced"] += 1

        logger.info(
            "stock_daily 同步完成: mode=%s target_date=%s total=%s processed=%s synced=%s skipped=%s rows_saved=%s errors=%s",
            stats["mode"],
            stats["target_date"],
            stats["codes_total"],
            stats["codes_processed"],
            stats["codes_synced"],
            stats["codes_skipped"],
            stats["rows_saved"],
            stats["errors"],
        )
        return stats

    def _load_targets(self, *, max_codes: Optional[int] = None) -> List[Dict[str, Any]]:
        targets = self.db.list_cn_stock_master_sync_targets()
        if max_codes is not None and max_codes > 0:
            return targets[:max_codes]
        return targets

    def _resolve_start_date(
        self,
        *,
        target_date: date,
        latest_date: Optional[date],
        list_date: Optional[date],
        full_backfill: bool,
    ) -> Optional[date]:
        if latest_date is not None:
            candidate = latest_date + timedelta(days=1)
            return candidate if candidate <= target_date else None

        if full_backfill:
            if isinstance(list_date, date):
                return list_date if list_date <= target_date else None
            return self.DEFAULT_HISTORY_START if self.DEFAULT_HISTORY_START <= target_date else None

        return target_date

    def _filter_df(
        self,
        df: Optional[pd.DataFrame],
        *,
        start_date: date,
        target_date: date,
    ) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        if "date" not in df.columns:
            return df

        filtered = df.copy()
        filtered["date"] = pd.to_datetime(filtered["date"], errors="coerce").dt.date
        filtered = filtered[
            filtered["date"].notna()
            & (filtered["date"] >= start_date)
            & (filtered["date"] <= target_date)
        ]
        return filtered

    @staticmethod
    def _empty_stats(*, mode: str, target_date: date) -> Dict[str, Any]:
        return {
            "mode": mode,
            "target_date": target_date.isoformat(),
            "codes_total": 0,
            "codes_processed": 0,
            "codes_synced": 0,
            "codes_skipped": 0,
            "rows_saved": 0,
            "errors": 0,
        }
