# -*- coding: utf-8 -*-
import os
import sys
import unittest
from datetime import date

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.cn_stock_master_sync_service import (
    ALLOWED_CN_STOCK_MASTER_CODE_PREFIXES,
    CNStockMasterSyncService,
)


class TestCNStockMasterSyncService(unittest.TestCase):
    def setUp(self):
        self.service = CNStockMasterSyncService(db=object())

    def test_records_from_sh_marks_star_board(self):
        df = pd.DataFrame(
            [
                {"证券代码": "688001", "证券简称": "*ST华测", "上市日期": date(2020, 1, 1)},
            ]
        )

        records = self.service._records_from_sh(
            df,
            market="star",
            source="test",
            source_updated_at=pd.Timestamp("2026-03-17 12:00:00").to_pydatetime(),
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["exchange"], "SSE")
        self.assertEqual(records[0]["market"], "star")
        self.assertTrue(records[0]["is_risk_warning"])

    def test_records_from_sz_normalizes_market_and_industry(self):
        df = pd.DataFrame(
            [
                {
                    "板块": "创业板",
                    "A股代码": "300750",
                    "A股简称": "宁德时代",
                    "A股上市日期": "2018-06-11",
                    "所属行业": "电池",
                }
            ]
        )

        records = self.service._records_from_sz(
            df,
            source="test",
            source_updated_at=pd.Timestamp("2026-03-17 12:00:00").to_pydatetime(),
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["exchange"], "SZSE")
        self.assertEqual(records[0]["market"], "gem")
        self.assertEqual(records[0]["industry"], "电池")

    def test_allowed_prefixes_are_limited_to_sse_and_szse_boards(self):
        self.assertEqual(ALLOWED_CN_STOCK_MASTER_CODE_PREFIXES, ("6", "0", "3"))

    def test_fetch_records_filters_out_non_target_prefixes(self):
        self.service._records_from_sh = lambda *args, **kwargs: [
            {"code": "600000", "name": "浦发银行"},
            {"code": "688001", "name": "华兴源创"},
        ]
        self.service._records_from_sz = lambda *args, **kwargs: [
            {"code": "000001", "name": "平安银行"},
            {"code": "300750", "name": "宁德时代"},
            {"code": "830000", "name": "应被过滤"},
        ]

        class _AkStub:
            @staticmethod
            def stock_info_sh_name_code(symbol):
                return pd.DataFrame()

            @staticmethod
            def stock_info_sz_name_code(symbol):
                return pd.DataFrame()

        import sys as _sys

        original = _sys.modules.get("akshare")
        _sys.modules["akshare"] = _AkStub()
        try:
            records = self.service.fetch_records()
        finally:
            if original is None:
                _sys.modules.pop("akshare", None)
            else:
                _sys.modules["akshare"] = original

        self.assertEqual([item["code"] for item in records], ["000001", "300750", "600000", "688001"])


if __name__ == "__main__":
    unittest.main()
