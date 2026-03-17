# -*- coding: utf-8 -*-
"""
飞书应用机器人主动推送发送器。

职责：
1. 使用 FEISHU_APP_ID / FEISHU_APP_SECRET 获取 tenant_access_token
2. 主动向 chat_id / open_id / user_id 发送消息
3. 支持 Markdown 卡片与长消息分片
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Dict, Iterable, List, Optional

import requests

from src.config import Config
from src.formatters import chunk_content_by_max_bytes, format_feishu_markdown


logger = logging.getLogger(__name__)


class FeishuAppSender:
    """基于飞书应用机器人 API 的主动推送发送器。"""

    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
    VALID_RECEIVE_ID_TYPES = {"chat_id", "open_id", "user_id"}

    def __init__(self, config: Config):
        self._app_id = getattr(config, "feishu_app_id", None)
        self._app_secret = getattr(config, "feishu_app_secret", None)
        self._enabled = bool(getattr(config, "feishu_app_alert_enabled", False))
        self._default_receive_id_type = getattr(config, "feishu_app_receive_id_type", "chat_id")
        self._default_receive_ids = list(getattr(config, "feishu_app_receive_ids", []) or [])
        self._verify_ssl = getattr(config, "webhook_verify_ssl", True)
        self._max_bytes = getattr(config, "feishu_max_bytes", 20000)

        self._tenant_access_token: str = ""
        self._tenant_access_token_expire_at: float = 0.0
        self._token_lock = threading.Lock()

    def is_configured(self) -> bool:
        """Return True when proactive Feishu app alerts are fully configured."""
        return bool(
            self._enabled
            and self._app_id
            and self._app_secret
            and self._default_receive_ids
        )

    def has_credentials(self) -> bool:
        """Return True when proactive send can run if explicit targets are provided."""
        return bool(self._enabled and self._app_id and self._app_secret)

    def send_markdown(
        self,
        content: str,
        *,
        receive_ids: Optional[Iterable[str]] = None,
        receive_id_type: Optional[str] = None,
    ) -> bool:
        """
        主动发送 Markdown 告警到飞书。

        Args:
            content: Markdown 文本
            receive_ids: 目标 chat_id/open_id/user_id 列表；为空时使用默认配置
            receive_id_type: 目标 ID 类型；为空时使用默认配置
        """
        if not self._enabled:
            logger.info("飞书应用机器人主动推送未启用，跳过发送")
            return False

        if not self._app_id or not self._app_secret:
            logger.warning("飞书应用机器人凭证未配置完整，跳过发送")
            return False

        targets = self._normalize_receive_ids(receive_ids or self._default_receive_ids)
        if not targets:
            logger.warning("飞书应用机器人未配置接收者 ID，跳过发送")
            return False

        id_type = (receive_id_type or self._default_receive_id_type or "chat_id").strip().lower()
        if id_type not in self.VALID_RECEIVE_ID_TYPES:
            logger.warning("飞书接收者 ID 类型无效: %s，已回退为 chat_id", id_type)
            id_type = "chat_id"

        formatted_content = format_feishu_markdown(content)
        chunks = chunk_content_by_max_bytes(
            formatted_content,
            self._max_bytes,
            add_page_marker=True,
        )

        success_count = 0
        for target in targets:
            target_ok = True
            for chunk in chunks:
                if self._send_interactive_card(chunk, receive_id=target, receive_id_type=id_type):
                    continue
                if not self._send_text_message(chunk, receive_id=target, receive_id_type=id_type):
                    target_ok = False
                    break
                time.sleep(0.5)

            if target_ok:
                success_count += 1

        logger.info(
            "飞书应用机器人主动推送完成：成功 %s/%s 个接收者",
            success_count,
            len(targets),
        )
        return success_count > 0

    def _normalize_receive_ids(self, receive_ids: Iterable[str]) -> List[str]:
        """Normalize receive ids and drop blanks while preserving order."""
        normalized: List[str] = []
        seen = set()
        for item in receive_ids or []:
            value = str(item or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    def _get_tenant_access_token(self) -> Optional[str]:
        """Fetch or reuse a cached tenant access token."""
        with self._token_lock:
            now = time.time()
            if self._tenant_access_token and now < self._tenant_access_token_expire_at:
                return self._tenant_access_token

            response = requests.post(
                self.TOKEN_URL,
                json={
                    "app_id": self._app_id,
                    "app_secret": self._app_secret,
                },
                timeout=30,
                verify=self._verify_ssl,
            )

            if response.status_code != 200:
                logger.error("获取飞书 tenant_access_token 失败: HTTP %s %s", response.status_code, response.text)
                return None

            try:
                payload = response.json()
            except ValueError:
                logger.error("获取飞书 tenant_access_token 失败：响应不是合法 JSON")
                return None

            if payload.get("code", 0) != 0:
                logger.error(
                    "获取飞书 tenant_access_token 失败: code=%s msg=%s",
                    payload.get("code"),
                    payload.get("msg"),
                )
                return None

            token = str(payload.get("tenant_access_token") or "").strip()
            expire_seconds = int(payload.get("expire", 7200) or 7200)
            if not token:
                logger.error("获取飞书 tenant_access_token 失败：响应缺少 token")
                return None

            self._tenant_access_token = token
            self._tenant_access_token_expire_at = now + max(60, expire_seconds - 120)
            return token

    def _send_interactive_card(self, content: str, *, receive_id: str, receive_id_type: str) -> bool:
        """Send a single interactive card message."""
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "股票告警通知",
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content,
                    },
                }
            ],
        }
        return self._send_message_payload(
            receive_id=receive_id,
            receive_id_type=receive_id_type,
            payload={
                "receive_id": receive_id,
                "msg_type": "interactive",
                "content": json.dumps(card, ensure_ascii=False),
            },
        )

    def _send_text_message(self, content: str, *, receive_id: str, receive_id_type: str) -> bool:
        """Fallback to plain text when interactive cards fail."""
        return self._send_message_payload(
            receive_id=receive_id,
            receive_id_type=receive_id_type,
            payload={
                "receive_id": receive_id,
                "msg_type": "text",
                "content": json.dumps({"text": content}, ensure_ascii=False),
            },
        )

    def _send_message_payload(
        self,
        *,
        receive_id: str,
        receive_id_type: str,
        payload: Dict[str, Any],
    ) -> bool:
        token = self._get_tenant_access_token()
        if not token:
            return False

        try:
            response = requests.post(
                f"{self.MESSAGE_URL}?receive_id_type={receive_id_type}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=payload,
                timeout=30,
                verify=self._verify_ssl,
            )
        except Exception as exc:
            logger.error("发送飞书应用机器人消息异常: %s", exc)
            return False

        if response.status_code != 200:
            logger.error(
                "飞书应用机器人消息发送失败: target=%s HTTP %s %s",
                receive_id,
                response.status_code,
                response.text,
            )
            return False

        try:
            result = response.json()
        except ValueError:
            logger.error("飞书应用机器人消息发送失败：响应不是合法 JSON")
            return False

        if result.get("code", 0) != 0:
            logger.error(
                "飞书应用机器人消息发送失败: target=%s code=%s msg=%s",
                receive_id,
                result.get("code"),
                result.get("msg"),
            )
            return False

        return True
