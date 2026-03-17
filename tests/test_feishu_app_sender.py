# -*- coding: utf-8 -*-
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import Config
from src.notification_sender.feishu_app_sender import FeishuAppSender


class TestFeishuAppSender(unittest.TestCase):
    def test_send_markdown_supports_explicit_receive_ids(self):
        config = Config(
            stock_list=["600519"],
            feishu_app_id="cli_xxx",
            feishu_app_secret="secret_xxx",
            feishu_app_alert_enabled=True,
            feishu_app_receive_ids=[],
        )
        sender = FeishuAppSender(config)

        token_response = MagicMock(status_code=200)
        token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "tenant-token",
            "expire": 7200,
        }
        message_response = MagicMock(status_code=200)
        message_response.json.return_value = {"code": 0, "msg": "success"}

        with patch(
            "src.notification_sender.feishu_app_sender.requests.post",
            side_effect=[token_response, message_response],
        ) as mock_post:
            success = sender.send_markdown(
                "hello",
                receive_ids=["oc_123"],
                receive_id_type="open_id",
            )

        self.assertTrue(success)
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(mock_post.call_args_list[0].args[0], sender.TOKEN_URL)
        self.assertIn("receive_id_type=open_id", mock_post.call_args_list[1].args[0])


if __name__ == "__main__":
    unittest.main()
