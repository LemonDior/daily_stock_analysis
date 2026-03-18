# -*- coding: utf-8 -*-
"""
`stock_daily` 补齐服务。

职责：
1. 根据 `cn_stock_master` 中的 code 一次性回填历史日线
2. 每日检查 A 股是否为交易日；若是，则补齐当天缺失的日线数据
3. 使用 `stock_daily(code, date)` 唯一约束 + save_daily_data 的 UPSERT 语义，保证数据唯一
"""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from data_provider.base import DataFetcherManager
from src.storage import DatabaseManager, get_db
from src.utils.thread_pool import get_shared_thread_pool_registry


logger = logging.getLogger(__name__)


class StockDailySyncService:
    """基于 `cn_stock_master` 的 `stock_daily` 回填与日常补齐服务。"""

    DEFAULT_HISTORY_START = date(2024, 12, 31)
    DAILY_SYNC_TIME = "18:00"
    MANUAL_HISTORY_BACKFILL_TRADE_DAYS = 30
    DEFAULT_HISTORY_BACKFILL_MAX_WORKERS = 8
    DEFAULT_DAILY_SYNC_MAX_WORKERS = 4
    PARALLEL_MIN_CODES = 4
    DEFAULT_HISTORY_BACKFILL_CHECKPOINT = (
        Path(__file__).resolve().parents[2] / "data" / "runtime" / "stock_daily_history_backfill_checkpoint.json"
    )

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        fetcher_manager: Optional[DataFetcherManager] = None,
        fetcher_factory: Optional[Any] = None,
    ) -> None:
        self.db = db or get_db()
        self.fetcher_manager = fetcher_manager or DataFetcherManager()
        self.fetcher_factory = fetcher_factory or (lambda: DataFetcherManager())
        self._thread_local = threading.local()
        self._thread_pool_registry = get_shared_thread_pool_registry()

    def backfill_history_from_master(
        self,
        *,
        max_codes: Optional[int] = None,
        start_date_floor: Optional[date] = None,
        target_date: Optional[date] = None,
        max_workers: int = 1,
        checkpoint_path: Optional[Path] = None,
        resume: bool = False,
    ) -> Dict[str, Any]:
        """
        按 `cn_stock_master` 全量补齐历史日线。

        Args:
            max_codes: 可选，限制回填股票数量，便于分批执行/测试
            start_date_floor: 可选，限制最早回填日期；早于该日期的历史数据不会补齐
            target_date: 可选，回填截止日期，默认今天
            max_workers: 可选，回填并发线程数；1 表示串行执行
            checkpoint_path: 可选，断点续跑 checkpoint 文件路径
            resume: 是否从 checkpoint 继续执行
        """
        actual_target_date = target_date or date.today()
        targets = self._load_targets(max_codes=max_codes)
        if not targets:
            return self._empty_stats(mode="history_backfill", target_date=actual_target_date)

        checkpoint = self._prepare_checkpoint(
            checkpoint_path=checkpoint_path,
            mode="history_backfill",
            target_date=actual_target_date,
            start_date_floor=start_date_floor,
            resume=resume,
        )
        if checkpoint and checkpoint["completed_codes"]:
            completed_codes = set(checkpoint["completed_codes"])
            targets = [item for item in targets if item.get("code") not in completed_codes]

        latest_dates = self.db.get_stock_daily_latest_dates([item["code"] for item in targets])
        result = self._sync_targets(
            targets=targets,
            latest_dates=latest_dates,
            target_date=actual_target_date,
            full_backfill=True,
            mode="history_backfill",
            start_date_floor=start_date_floor,
            max_workers=max_workers,
            checkpoint=checkpoint,
        )
        result["checkpoint_path"] = str(checkpoint["path"]) if checkpoint and checkpoint["path"] else None
        result["resumed_completed_codes"] = checkpoint["initial_completed_count"] if checkpoint else 0
        return result

    def sync_daily_if_trade_day(
        self,
        *,
        target_date: Optional[date] = None,
        max_codes: Optional[int] = None,
        max_workers: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        若 target_date 为 A 股交易日，则补齐当天缺失的日线数据。

        Args:
            target_date: 目标日期，默认今天
            max_codes: 可选，限制处理股票数量
            max_workers: 可选，并发上限；是否并发由数据量自动判断
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
            max_workers=max_workers,
            checkpoint=None,
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
        start_date_floor: Optional[date] = None,
        max_workers: int = 1,
        checkpoint: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        stats = self._empty_stats(mode=mode, target_date=target_date)
        stats["codes_total"] = len(targets)
        if not targets:
            self._finalize_checkpoint(checkpoint=checkpoint, has_errors=False)
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

        worker_count = self._resolve_worker_count(
            total_targets=len(targets),
            requested_max_workers=max_workers,
            mode=mode,
        )
        if worker_count == 1:
            for item in targets:
                self._merge_result_into_stats(
                    stats=stats,
                    result=self._process_single_target(
                        item=item,
                        latest_date=latest_dates.get(str(item.get("code") or "").strip()),
                        target_date=target_date,
                        full_backfill=full_backfill,
                        start_date_floor=start_date_floor,
                        use_thread_local_fetcher=False,
                    ),
                    checkpoint=checkpoint,
                )
        else:
            executor = self._thread_pool_registry.get_executor(
                name="stock_daily_sync",
                max_workers=worker_count,
                thread_name_prefix="stock_daily_sync",
            )
            future_map = {
                executor.submit(
                    self._process_single_target,
                    item=item,
                    latest_date=latest_dates.get(str(item.get("code") or "").strip()),
                    target_date=target_date,
                    full_backfill=full_backfill,
                    start_date_floor=start_date_floor,
                    use_thread_local_fetcher=True,
                ): item
                for item in targets
            }
            for future in as_completed(future_map):
                try:
                    result = future.result()
                except Exception as exc:
                    code = str(future_map[future].get("code") or "").strip()
                    result = {
                        "code": code,
                        "processed": 0,
                        "synced": 0,
                        "skipped": 0,
                        "rows_saved": 0,
                        "errors": 1,
                        "status": "error",
                        "error_message": str(exc),
                    }
                self._merge_result_into_stats(stats=stats, result=result, checkpoint=checkpoint)

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
        self._finalize_checkpoint(checkpoint=checkpoint, has_errors=stats["errors"] > 0)
        return stats

    def _process_single_target(
        self,
        *,
        item: Dict[str, Any],
        latest_date: Optional[date],
        target_date: date,
        full_backfill: bool,
        start_date_floor: Optional[date],
        use_thread_local_fetcher: bool,
    ) -> Dict[str, Any]:
        code = str(item.get("code") or "").strip()
        if not code:
            return {
                "code": code,
                "processed": 0,
                "synced": 0,
                "skipped": 1,
                "rows_saved": 0,
                "errors": 0,
                "status": "skipped",
            }

        start_date = self._resolve_start_date(
            target_date=target_date,
            latest_date=latest_date,
            list_date=item.get("list_date"),
            full_backfill=full_backfill,
            start_date_floor=start_date_floor,
        )
        if start_date is None or start_date > target_date:
            return {
                "code": code,
                "processed": 0,
                "synced": 0,
                "skipped": 1,
                "rows_saved": 0,
                "errors": 0,
                "status": "skipped",
            }

        fetcher_manager = self._get_fetcher_manager(use_thread_local=use_thread_local_fetcher)
        try:
            df, source = fetcher_manager.get_daily_data(
                stock_code=code,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=target_date.strftime("%Y-%m-%d"),
                days=max(30, (target_date - start_date).days + 10),
            )
            filtered_df = self._filter_df(df, start_date=start_date, target_date=target_date)
            if filtered_df is None or filtered_df.empty:
                return {
                    "code": code,
                    "processed": 1,
                    "synced": 0,
                    "skipped": 1,
                    "rows_saved": 0,
                    "errors": 0,
                    "status": "skipped",
                }

            saved_rows = self.db.save_daily_data(filtered_df, code=code, data_source=source)
            return {
                "code": code,
                "processed": 1,
                "synced": 1,
                "skipped": 0,
                "rows_saved": int(saved_rows),
                "errors": 0,
                "status": "synced",
            }
        except Exception as exc:
            logger.warning("补齐 stock_daily 失败(%s): %s", code, exc)
            return {
                "code": code,
                "processed": 1,
                "synced": 0,
                "skipped": 0,
                "rows_saved": 0,
                "errors": 1,
                "status": "error",
                "error_message": str(exc),
            }

    def _merge_result_into_stats(
        self,
        *,
        stats: Dict[str, Any],
        result: Dict[str, Any],
        checkpoint: Optional[Dict[str, Any]],
    ) -> None:
        stats["codes_processed"] += int(result.get("processed", 0))
        stats["codes_synced"] += int(result.get("synced", 0))
        stats["codes_skipped"] += int(result.get("skipped", 0))
        stats["rows_saved"] += int(result.get("rows_saved", 0))
        stats["errors"] += int(result.get("errors", 0))

        code = str(result.get("code") or "").strip()
        if not checkpoint or not code:
            return
        if result.get("status") == "error":
            self._checkpoint_mark_failed(checkpoint, code=code, error_message=str(result.get("error_message") or ""))
        else:
            self._checkpoint_mark_completed(checkpoint, code=code)

    def _get_fetcher_manager(self, *, use_thread_local: bool) -> DataFetcherManager:
        if not use_thread_local:
            return self.fetcher_manager
        fetcher_manager = getattr(self._thread_local, "fetcher_manager", None)
        if fetcher_manager is None:
            fetcher_manager = self.fetcher_factory()
            self._thread_local.fetcher_manager = fetcher_manager
        return fetcher_manager

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
        start_date_floor: Optional[date] = None,
    ) -> Optional[date]:
        if latest_date is not None:
            candidate = latest_date + timedelta(days=1)
            if start_date_floor is not None and candidate < start_date_floor:
                candidate = start_date_floor
            return candidate if candidate <= target_date else None

        if full_backfill:
            if isinstance(list_date, date):
                candidate = list_date
            else:
                candidate = self.DEFAULT_HISTORY_START

            if start_date_floor is not None and candidate < start_date_floor:
                candidate = start_date_floor
            return candidate if candidate <= target_date else None

        candidate = target_date
        if start_date_floor is not None and candidate < start_date_floor:
            candidate = start_date_floor
        return candidate if candidate <= target_date else None

    def get_recent_trade_day_floor(
        self,
        *,
        limit: int,
        target_date: Optional[date] = None,
    ) -> date:
        """
        获取截至目标日期的最近 N 个交易日中的最早日期。

        Args:
            limit: 需要覆盖的交易日数量，必须大于 0
            target_date: 目标日期，默认今天

        Returns:
            最近 N 个交易日窗口中的起始交易日
        """
        if limit <= 0:
            raise ValueError("limit 必须大于 0")

        actual_date = target_date or date.today()

        try:
            import akshare as ak
        except ImportError as exc:
            raise RuntimeError("AkShare 未安装，无法计算最近交易日窗口") from exc

        df = ak.tool_trade_date_hist_sina()
        if df is None or df.empty:
            raise RuntimeError("AkShare 交易日历返回为空")

        column = "trade_date" if "trade_date" in df.columns else df.columns[0]
        trade_days = sorted(
            {
                item.date()
                for item in pd.to_datetime(df[column], errors="coerce")
                if not pd.isna(item) and item.date() <= actual_date
            }
        )
        if not trade_days:
            raise RuntimeError(f"未找到截至 {actual_date} 的 A 股交易日")

        return trade_days[max(0, len(trade_days) - limit)]

    def _resolve_worker_count(
        self,
        *,
        total_targets: int,
        requested_max_workers: Optional[int],
        mode: str,
    ) -> int:
        if total_targets < self.PARALLEL_MIN_CODES:
            return 1

        default_cap = (
            self.DEFAULT_HISTORY_BACKFILL_MAX_WORKERS
            if mode == "history_backfill"
            else self.DEFAULT_DAILY_SYNC_MAX_WORKERS
        )
        worker_cap = requested_max_workers if requested_max_workers is not None else default_cap
        worker_cap = max(1, int(worker_cap))
        return min(worker_cap, total_targets)

    def _prepare_checkpoint(
        self,
        *,
        checkpoint_path: Optional[Path],
        mode: str,
        target_date: date,
        start_date_floor: Optional[date],
        resume: bool,
    ) -> Dict[str, Any]:
        normalized_path = Path(checkpoint_path) if checkpoint_path else None
        initial_state = {
            "path": normalized_path,
            "mode": mode,
            "target_date": target_date.isoformat(),
            "start_date_floor": start_date_floor.isoformat() if start_date_floor else None,
            "completed_codes": [],
            "failed_codes": {},
            "initial_completed_count": 0,
            "lock": threading.Lock(),
        }
        if normalized_path is None:
            return None

        if resume and normalized_path.exists():
            try:
                payload = json.loads(normalized_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("读取 stock_daily checkpoint 失败(%s): %s，改为重新开始", normalized_path, exc)
                self._write_checkpoint_payload(normalized_path, initial_state)
                return initial_state

            if (
                payload.get("mode") == mode
                and payload.get("target_date") == initial_state["target_date"]
                and payload.get("start_date_floor") == initial_state["start_date_floor"]
            ):
                initial_state["completed_codes"] = list(payload.get("completed_codes") or [])
                initial_state["failed_codes"] = dict(payload.get("failed_codes") or {})
                initial_state["initial_completed_count"] = len(initial_state["completed_codes"])
                logger.info(
                    "载入 stock_daily checkpoint: path=%s completed=%s failed=%s",
                    normalized_path,
                    len(initial_state["completed_codes"]),
                    len(initial_state["failed_codes"]),
                )
                return initial_state

            logger.info("stock_daily checkpoint 参数已变化，忽略旧 checkpoint: %s", normalized_path)

        self._write_checkpoint_payload(normalized_path, initial_state)
        return initial_state

    def _checkpoint_mark_completed(self, checkpoint: Dict[str, Any], *, code: str) -> None:
        if checkpoint["path"] is None:
            return
        with checkpoint["lock"]:
            completed_codes = checkpoint["completed_codes"]
            if code not in completed_codes:
                completed_codes.append(code)
            checkpoint["failed_codes"].pop(code, None)
            self._write_checkpoint_payload(checkpoint["path"], checkpoint)

    def _checkpoint_mark_failed(self, checkpoint: Dict[str, Any], *, code: str, error_message: str) -> None:
        if checkpoint["path"] is None:
            return
        with checkpoint["lock"]:
            checkpoint["failed_codes"][code] = error_message
            self._write_checkpoint_payload(checkpoint["path"], checkpoint)

    def _finalize_checkpoint(self, *, checkpoint: Optional[Dict[str, Any]], has_errors: bool) -> None:
        if not checkpoint or checkpoint["path"] is None:
            return
        with checkpoint["lock"]:
            if has_errors:
                self._write_checkpoint_payload(checkpoint["path"], checkpoint)
                logger.info("stock_daily checkpoint 已保留，便于后续断点续跑: %s", checkpoint["path"])
                return
            try:
                checkpoint["path"].unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("删除 stock_daily checkpoint 失败(%s): %s", checkpoint["path"], exc)

    @staticmethod
    def _write_checkpoint_payload(path: Path, checkpoint: Dict[str, Any]) -> None:
        payload = {
            "mode": checkpoint["mode"],
            "target_date": checkpoint["target_date"],
            "start_date_floor": checkpoint["start_date_floor"],
            "completed_codes": sorted(set(checkpoint["completed_codes"])),
            "failed_codes": checkpoint["failed_codes"],
            "updated_at": datetime.now().isoformat(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

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
