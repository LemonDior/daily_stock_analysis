# -*- coding: utf-8 -*-
import os
import sys
import unittest
from datetime import date

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.cn_stock_master_sync_service import CNStockMasterSyncService


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

    def test_records_from_bj_keeps_area(self):
        df = pd.DataFrame(
            [
                {
                    "证券代码": "430047",
                    "证券简称": "诺思兰德",
                    "上市日期": "2021-11-15",
                    "所属行业": "生物制药",
                    "地区": "北京",
                }
            ]
        )

        records = self.service._records_from_bj(
            df,
            source="test",
            source_updated_at=pd.Timestamp("2026-03-17 12:00:00").to_pydatetime(),
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["exchange"], "BSE")
        self.assertEqual(records[0]["market"], "beijing")
        self.assertEqual(records[0]["area"], "北京")


if __name__ == "__main__":
    unittest.main()
