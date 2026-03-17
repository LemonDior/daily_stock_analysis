# -*- coding: utf-8 -*-
"""
A 股股票主数据同步服务
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.storage import DatabaseManager, get_db

logger = logging.getLogger(__name__)


class CNStockMasterSyncService:
    """同步 `cn_stock_master` 表的周更服务。"""

    def __init__(self, db: Optional[DatabaseManager] = None) -> None:
        self.db = db or get_db()

    def sync(self) -> Dict[str, int]:
        """拉取 A 股股票主数据并写入数据库。"""
        records = self.fetch_records()
        stats = self.db.upsert_cn_stock_master_records(records)
        result = {
            "fetched": len(records),
            "inserted": int(stats.get("inserted", 0)),
            "updated": int(stats.get("updated", 0)),
        }
        logger.info(
            "A股主数据同步完成: fetched=%s inserted=%s updated=%s",
            result["fetched"],
            result["inserted"],
            result["updated"],
        )
        return result

    def fetch_records(self) -> List[Dict[str, Any]]:
        """从 AkShare 拉取并标准化 A 股股票主数据。"""
        import akshare as ak

        now = datetime.now()
        records: List[Dict[str, Any]] = []
        records.extend(
            self._records_from_sh(
                ak.stock_info_sh_name_code(symbol="主板A股"),
                market="main",
                source="akshare.stock_info_sh_name_code",
                source_updated_at=now,
            )
        )
        records.extend(
            self._records_from_sh(
                ak.stock_info_sh_name_code(symbol="科创板"),
                market="star",
                source="akshare.stock_info_sh_name_code",
                source_updated_at=now,
            )
        )
        records.extend(
            self._records_from_sz(
                ak.stock_info_sz_name_code(symbol="A股列表"),
                source="akshare.stock_info_sz_name_code",
                source_updated_at=now,
            )
        )
        records.extend(
            self._records_from_bj(
                ak.stock_info_bj_name_code(),
                source="akshare.stock_info_bj_name_code",
                source_updated_at=now,
            )
        )

        deduped: Dict[str, Dict[str, Any]] = {}
        for item in records:
            code = str(item.get("code") or "").strip()
            name = str(item.get("name") or "").strip()
            if not code or not name:
                continue
            deduped[code] = item

        final_records = [deduped[code] for code in sorted(deduped)]
        if len(final_records) < 3000:
            raise RuntimeError(f"A股主数据拉取结果异常，数量过少: {len(final_records)}")
        return final_records

    def _records_from_sh(
        self,
        df: pd.DataFrame,
        *,
        market: str,
        source: str,
        source_updated_at: datetime,
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            code = self._normalize_code(row.get("证券代码"))
            name = self._normalize_name(row.get("证券简称"))
            if not code or not name:
                continue
            rows.append(
                self._build_record(
                    code=code,
                    name=name,
                    exchange="SSE",
                    market=market,
                    industry=None,
                    area=None,
                    list_date=row.get("上市日期"),
                    source=source,
                    source_updated_at=source_updated_at,
                )
            )
        return rows

    def _records_from_sz(
        self,
        df: pd.DataFrame,
        *,
        source: str,
        source_updated_at: datetime,
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            code = self._normalize_code(row.get("A股代码"))
            name = self._normalize_name(row.get("A股简称"))
            if not code or not name:
                continue
            board = str(row.get("板块") or "").strip()
            rows.append(
                self._build_record(
                    code=code,
                    name=name,
                    exchange="SZSE",
                    market=self._resolve_sz_market(code=code, board=board),
                    industry=self._normalize_nullable_text(row.get("所属行业")),
                    area=None,
                    list_date=row.get("A股上市日期"),
                    source=source,
                    source_updated_at=source_updated_at,
                )
            )
        return rows

    def _records_from_bj(
        self,
        df: pd.DataFrame,
        *,
        source: str,
        source_updated_at: datetime,
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            code = self._normalize_code(row.get("证券代码"))
            name = self._normalize_name(row.get("证券简称"))
            if not code or not name:
                continue
            rows.append(
                self._build_record(
                    code=code,
                    name=name,
                    exchange="BSE",
                    market="beijing",
                    industry=self._normalize_nullable_text(row.get("所属行业")),
                    area=self._normalize_nullable_text(row.get("地区")),
                    list_date=row.get("上市日期"),
                    source=source,
                    source_updated_at=source_updated_at,
                )
            )
        return rows

    def _build_record(
        self,
        *,
        code: str,
        name: str,
        exchange: str,
        market: str,
        industry: Optional[str],
        area: Optional[str],
        list_date: Any,
        source: str,
        source_updated_at: datetime,
    ) -> Dict[str, Any]:
        return {
            "code": code,
            "name": name,
            "exchange": exchange,
            "market": market,
            "industry": industry,
            "area": area,
            "list_status": "listed",
            "is_risk_warning": self._is_risk_warning_stock(name),
            "list_date": self._normalize_date(list_date),
            "delist_date": None,
            "is_active": True,
            "source": source,
            "source_updated_at": source_updated_at,
        }

    @staticmethod
    def _normalize_code(value: Any) -> str:
        text = str(value or "").strip()
        digits = re.sub(r"\D", "", text)
        return digits.zfill(6) if digits else ""

    @staticmethod
    def _normalize_name(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _normalize_nullable_text(value: Any) -> Optional[str]:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _normalize_date(value: Any):
        if value is None or value == "":
            return None
        if hasattr(value, "to_pydatetime"):
            return value.to_pydatetime().date()
        if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
            try:
                return value if value.__class__.__name__ == "date" else value.date()
            except Exception:
                pass
        text = str(value).strip()
        if not text:
            return None
        return pd.to_datetime(text, errors="coerce").date() if pd.notna(pd.to_datetime(text, errors="coerce")) else None

    @staticmethod
    def _resolve_sz_market(*, code: str, board: str) -> str:
        board_text = (board or "").strip()
        if "创业" in board_text:
            return "gem"
        if "主板" in board_text:
            return "main"
        if code.startswith("300"):
            return "gem"
        return "main"

    @staticmethod
    def _is_risk_warning_stock(name: str) -> bool:
        normalized = str(name or "").strip().upper().replace(" ", "")
        return (
            normalized.startswith("ST")
            or normalized.startswith("*ST")
            or normalized.startswith("S*ST")
        )
