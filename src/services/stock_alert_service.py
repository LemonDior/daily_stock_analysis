# -*- coding: utf-8 -*-
"""
股票告警监控服务。

职责：
1. 从 AGENT_EVENT_ALERT_RULES_JSON 加载监控规则
2. 定期检查实时行情与最近日线数据
3. 命中条件后主动推送到飞书应用机器人或现有通知渠道
4. 持久化规则状态，避免重启后重复告警
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from data_provider.base import DataFetcherManager, normalize_stock_code

from src.config import Config, get_config
from src.notification import NotificationService
from src.notification_sender import FeishuAppSender
from src.storage import DatabaseManager


logger = logging.getLogger(__name__)


SUPPORTED_STOCK_ALERT_TYPES = {"price_cross", "change_pct", "volume_ratio"}
STOCK_ALERT_TYPE_ALIASES = {
    "price_above": ("price_cross", "above"),
    "price_below": ("price_cross", "below"),
    "change_pct_above": ("change_pct", "above"),
    "change_pct_below": ("change_pct", "below"),
    "volume_ratio_above": ("volume_ratio", "above"),
    "volume_ratio_below": ("volume_ratio", "below"),
}
VALID_ALERT_DIRECTIONS = {"above", "below"}


@dataclass(frozen=True)
class StockAlertRule:
    """运行期标准化后的股票告警规则。"""

    rule_id: str
    stock_code: str
    alert_type: str
    threshold: float
    direction: str = "above"
    name: str = ""
    enabled: bool = True
    cooldown_seconds: int = 1800
    receive_id_type: Optional[str] = None
    receive_ids: Tuple[str, ...] = field(default_factory=tuple)

    def display_name(self) -> str:
        if self.name:
            return self.name
        metric = {
            "price_cross": "价格",
            "change_pct": "涨跌幅",
            "volume_ratio": "量比",
        }.get(self.alert_type, self.alert_type)
        direction_text = "上穿" if self.direction == "above" else "下穿"
        return f"{metric}{direction_text}{self.threshold:g}"


@dataclass(frozen=True)
class StockAlertEvent:
    """单次触发的告警事件。"""

    rule: StockAlertRule
    stock_name: str
    current_value: float
    current_price: Optional[float]
    change_pct: Optional[float]
    volume_ratio: Optional[float]
    triggered_at: datetime
    message: str


class StockAlertService:
    """规则加载、行情检查与通知发送入口。"""

    def __init__(
        self,
        *,
        config: Optional[Config] = None,
        db: Optional[DatabaseManager] = None,
        fetcher_manager: Optional[DataFetcherManager] = None,
        feishu_sender: Optional[FeishuAppSender] = None,
        notifier: Optional[NotificationService] = None,
    ) -> None:
        self._config = config or get_config()
        self._db = db or DatabaseManager.get_instance()
        self._fetcher_manager = fetcher_manager or DataFetcherManager()
        self._feishu_sender = feishu_sender or FeishuAppSender(self._config)
        self._notifier = notifier
        self._rules_cache: Optional[List[StockAlertRule]] = None

    def load_rules(self, *, force_reload: bool = False) -> List[StockAlertRule]:
        """Load and normalize stock alert rules from config JSON."""
        if self._rules_cache is not None and not force_reload:
            return list(self._rules_cache)

        raw_json = (getattr(self._config, "agent_event_alert_rules_json", "") or "").strip()
        if not raw_json:
            self._rules_cache = []
            return []

        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            logger.warning("AGENT_EVENT_ALERT_RULES_JSON 不是合法 JSON，已跳过股票告警监控: %s", exc)
            self._rules_cache = []
            return []

        if not isinstance(payload, list):
            logger.warning("AGENT_EVENT_ALERT_RULES_JSON 必须是 JSON 数组，已跳过股票告警监控")
            self._rules_cache = []
            return []

        rules: List[StockAlertRule] = []
        seen_ids = set()
        for index, raw_rule in enumerate(payload, start=1):
            rule = self._normalize_rule(raw_rule, index=index)
            if rule is None:
                continue
            if rule.rule_id in seen_ids:
                logger.warning("股票告警规则 rule_id 重复，已跳过: %s", rule.rule_id)
                continue
            seen_ids.add(rule.rule_id)
            rules.append(rule)

        self._rules_cache = rules
        return list(rules)

    def run_once(self) -> List[StockAlertEvent]:
        """Evaluate all loaded rules once and send triggered alerts."""
        rules = [rule for rule in self.load_rules() if rule.enabled]
        if not rules:
            return []

        states = self._db.get_stock_alert_states([rule.rule_id for rule in rules])
        snapshot_cache: Dict[str, Dict[str, Any]] = {}
        events: List[StockAlertEvent] = []

        for rule in rules:
            event = self._evaluate_rule(
                rule,
                snapshot=self._get_market_snapshot(rule.stock_code, snapshot_cache),
                previous_state=states.get(rule.rule_id) or {},
            )
            if event is None:
                continue
            events.append(event)
            self._dispatch_event(event)

        return events

    def _normalize_rule(self, raw_rule: Any, *, index: int) -> Optional[StockAlertRule]:
        if not isinstance(raw_rule, dict):
            logger.warning("股票告警规则 #%s 不是对象，已跳过", index)
            return None

        enabled = bool(raw_rule.get("enabled", True))
        if not enabled:
            return None

        stock_code = normalize_stock_code(str(raw_rule.get("stock_code") or raw_rule.get("code") or "").strip())
        if not stock_code:
            logger.warning("股票告警规则 #%s 缺少 stock_code/code，已跳过", index)
            return None

        raw_alert_type = str(raw_rule.get("alert_type") or "").strip().lower()
        if not raw_alert_type:
            logger.warning("股票告警规则 #%s 缺少 alert_type，已跳过", index)
            return None

        normalized_direction = str(raw_rule.get("direction") or "").strip().lower()
        if raw_alert_type in STOCK_ALERT_TYPE_ALIASES:
            raw_alert_type, alias_direction = STOCK_ALERT_TYPE_ALIASES[raw_alert_type]
            if not normalized_direction:
                normalized_direction = alias_direction

        if raw_alert_type not in SUPPORTED_STOCK_ALERT_TYPES:
            logger.warning(
                "股票告警规则 #%s 使用了不支持的 alert_type=%s，已跳过",
                index,
                raw_rule.get("alert_type"),
            )
            return None

        direction = normalized_direction or "above"
        direction_aliases = {
            "up": "above",
            "gt": "above",
            "gte": "above",
            "greater": "above",
            "greater_or_equal": "above",
            "down": "below",
            "lt": "below",
            "lte": "below",
            "less": "below",
            "less_or_equal": "below",
        }
        direction = direction_aliases.get(direction, direction)
        if direction not in VALID_ALERT_DIRECTIONS:
            logger.warning("股票告警规则 #%s 的 direction=%s 无效，已跳过", index, direction)
            return None

        threshold = self._resolve_threshold(raw_rule, alert_type=raw_alert_type, direction=direction)
        if threshold is None:
            logger.warning("股票告警规则 #%s 缺少有效阈值，已跳过", index)
            return None

        cooldown_seconds = self._resolve_cooldown_seconds(raw_rule)
        receive_ids = self._normalize_receive_ids(raw_rule.get("receive_ids"))
        receive_id_type = str(raw_rule.get("receive_id_type") or "").strip().lower() or None
        rule_id = str(raw_rule.get("rule_id") or "").strip() or self._build_rule_id(
            stock_code=stock_code,
            alert_type=raw_alert_type,
            direction=direction,
            threshold=threshold,
        )

        return StockAlertRule(
            rule_id=rule_id,
            stock_code=stock_code,
            alert_type=raw_alert_type,
            threshold=threshold,
            direction=direction,
            name=str(raw_rule.get("name") or "").strip(),
            enabled=enabled,
            cooldown_seconds=cooldown_seconds,
            receive_id_type=receive_id_type,
            receive_ids=receive_ids,
        )

    def _resolve_threshold(self, raw_rule: Dict[str, Any], *, alert_type: str, direction: str) -> Optional[float]:
        if alert_type == "price_cross":
            return self._safe_float(raw_rule.get("price", raw_rule.get("threshold")))

        if alert_type == "change_pct":
            value = self._safe_float(raw_rule.get("change_pct", raw_rule.get("threshold")))
            if value is None:
                return None
            if direction == "below" and value > 0:
                return -abs(value)
            if direction == "above" and value < 0:
                return abs(value)
            return value

        if alert_type == "volume_ratio":
            return self._safe_float(raw_rule.get("volume_ratio", raw_rule.get("threshold")))

        return None

    def _resolve_cooldown_seconds(self, raw_rule: Dict[str, Any]) -> int:
        seconds = self._safe_int(raw_rule.get("cooldown_seconds"))
        if seconds is not None:
            return max(0, seconds)

        minutes = self._safe_int(raw_rule.get("cooldown_minutes"))
        if minutes is not None:
            return max(0, minutes * 60)

        return 1800

    def _build_rule_id(self, *, stock_code: str, alert_type: str, direction: str, threshold: float) -> str:
        threshold_token = str(threshold).replace(".", "_").replace("-", "m")
        return f"{stock_code}:{alert_type}:{direction}:{threshold_token}"

    def _normalize_receive_ids(self, receive_ids: Any) -> Tuple[str, ...]:
        if receive_ids is None:
            return tuple()
        if isinstance(receive_ids, str):
            items = receive_ids.split(",")
        elif isinstance(receive_ids, Sequence):
            items = list(receive_ids)
        else:
            return tuple()

        normalized: List[str] = []
        seen = set()
        for item in items:
            value = str(item or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return tuple(normalized)

    def _get_market_snapshot(self, stock_code: str, cache: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        if stock_code in cache:
            return cache[stock_code]

        quote = None
        try:
            quote = self._fetcher_manager.get_realtime_quote(stock_code)
        except Exception as exc:
            logger.warning("获取 %s 实时行情失败，告警监控将回退到库内数据: %s", stock_code, exc)

        latest_data = []
        try:
            latest_data = self._db.get_latest_data(stock_code, days=2)
        except Exception as exc:
            logger.warning("获取 %s 最近日线失败: %s", stock_code, exc)

        stock_name = ""
        if quote is not None:
            stock_name = str(getattr(quote, "name", "") or "").strip()
        if not stock_name:
            try:
                stock_name = str(self._fetcher_manager.get_stock_name(stock_code, allow_realtime=False) or "").strip()
            except Exception:
                stock_name = ""

        cache[stock_code] = {
            "quote": quote,
            "latest_data": latest_data,
            "stock_name": stock_name or stock_code,
        }
        return cache[stock_code]

    def _evaluate_rule(
        self,
        rule: StockAlertRule,
        *,
        snapshot: Dict[str, Any],
        previous_state: Dict[str, Any],
    ) -> Optional[StockAlertEvent]:
        current_value = self._extract_current_value(rule, snapshot)
        if current_value is None:
            logger.debug("股票告警规则 %s 当前缺少可用数据，跳过本轮检查", rule.rule_id)
            return None

        condition_met = self._compare(current_value, rule.threshold, direction=rule.direction)
        previous_condition_met = bool(previous_state.get("last_condition_met", False))
        last_triggered_at = previous_state.get("last_triggered_at")
        cooldown_ok = self._is_cooldown_elapsed(last_triggered_at, rule.cooldown_seconds)

        current_price = self._extract_price(snapshot)
        change_pct = self._extract_change_pct(snapshot)
        volume_ratio = self._extract_volume_ratio(snapshot)
        stock_name = str(snapshot.get("stock_name") or rule.stock_code).strip() or rule.stock_code

        should_trigger = condition_met and not previous_condition_met and cooldown_ok
        message = self._build_alert_message(
            rule=rule,
            stock_name=stock_name,
            current_value=current_value,
            current_price=current_price,
            change_pct=change_pct,
            volume_ratio=volume_ratio,
        )

        self._db.upsert_stock_alert_state(
            rule_id=rule.rule_id,
            stock_code=rule.stock_code,
            alert_type=rule.alert_type,
            last_condition_met=condition_met,
            last_triggered_at=datetime.now() if should_trigger else last_triggered_at,
            last_trigger_value=current_value if should_trigger else previous_state.get("last_trigger_value"),
            last_message=message if should_trigger else previous_state.get("last_message"),
        )

        if not should_trigger:
            return None

        return StockAlertEvent(
            rule=rule,
            stock_name=stock_name,
            current_value=current_value,
            current_price=current_price,
            change_pct=change_pct,
            volume_ratio=volume_ratio,
            triggered_at=datetime.now(),
            message=message,
        )

    def _extract_current_value(self, rule: StockAlertRule, snapshot: Dict[str, Any]) -> Optional[float]:
        if rule.alert_type == "price_cross":
            return self._extract_price(snapshot)
        if rule.alert_type == "change_pct":
            return self._extract_change_pct(snapshot)
        if rule.alert_type == "volume_ratio":
            return self._extract_volume_ratio(snapshot)
        return None

    def _extract_price(self, snapshot: Dict[str, Any]) -> Optional[float]:
        quote = snapshot.get("quote")
        if quote is not None:
            price = self._safe_float(getattr(quote, "price", None))
            if price is not None:
                return price

        latest = snapshot.get("latest_data") or []
        if latest:
            return self._safe_float(getattr(latest[0], "close", None))
        return None

    def _extract_change_pct(self, snapshot: Dict[str, Any]) -> Optional[float]:
        quote = snapshot.get("quote")
        if quote is not None:
            change_pct = self._safe_float(getattr(quote, "change_pct", None))
            if change_pct is not None:
                return change_pct

        latest = snapshot.get("latest_data") or []
        if latest:
            return self._safe_float(getattr(latest[0], "pct_chg", None))
        return None

    def _extract_volume_ratio(self, snapshot: Dict[str, Any]) -> Optional[float]:
        quote = snapshot.get("quote")
        if quote is not None:
            volume_ratio = self._safe_float(getattr(quote, "volume_ratio", None))
            if volume_ratio is not None:
                return volume_ratio

        latest = snapshot.get("latest_data") or []
        if latest:
            return self._safe_float(getattr(latest[0], "volume_ratio", None))
        return None

    def _compare(self, current_value: float, threshold: float, *, direction: str) -> bool:
        if direction == "below":
            return current_value <= threshold
        return current_value >= threshold

    def _is_cooldown_elapsed(self, last_triggered_at: Optional[datetime], cooldown_seconds: int) -> bool:
        if cooldown_seconds <= 0 or last_triggered_at is None:
            return True
        return datetime.now() - last_triggered_at >= timedelta(seconds=cooldown_seconds)

    def _build_alert_message(
        self,
        *,
        rule: StockAlertRule,
        stock_name: str,
        current_value: float,
        current_price: Optional[float],
        change_pct: Optional[float],
        volume_ratio: Optional[float],
    ) -> str:
        direction_text = "上穿" if rule.direction == "above" else "下穿"
        metric_label = {
            "price_cross": "价格",
            "change_pct": "涨跌幅",
            "volume_ratio": "量比",
        }.get(rule.alert_type, rule.alert_type)
        threshold_text = self._format_metric_value(rule.alert_type, rule.threshold)
        current_text = self._format_metric_value(rule.alert_type, current_value)

        lines = [
            "🔔 **股票告警触发**",
            "",
            f"**股票**：{stock_name} ({rule.stock_code})",
            f"**规则**：{rule.display_name()}",
            f"**条件**：{metric_label}{direction_text} {threshold_text}",
            f"**当前值**：{current_text}",
        ]

        if current_price is not None:
            lines.append(f"**当前价**：{current_price:.2f}")
        if change_pct is not None:
            lines.append(f"**涨跌幅**：{change_pct:+.2f}%")
        if volume_ratio is not None:
            lines.append(f"**量比**：{volume_ratio:.2f}")

        lines.extend(
            [
                f"**触发时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "_提示：仅作监控提醒，不构成投资建议。_",
            ]
        )
        return "\n".join(lines)

    def _format_metric_value(self, alert_type: str, value: float) -> str:
        if alert_type == "change_pct":
            return f"{value:+.2f}%"
        return f"{value:.2f}"

    def _dispatch_event(self, event: StockAlertEvent) -> bool:
        if self._feishu_sender and self._feishu_sender.has_credentials():
            success = self._feishu_sender.send_markdown(
                event.message,
                receive_ids=event.rule.receive_ids or None,
                receive_id_type=event.rule.receive_id_type,
            )
            if success:
                return True
            logger.warning("飞书应用机器人主动推送失败，回退到现有通知渠道")

        notifier = self._notifier or NotificationService()
        if not notifier.is_available():
            logger.warning("股票告警已触发，但未配置可用通知渠道")
            return False
        return notifier.send(event.message)

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            return int(float(value))
        except (TypeError, ValueError):
            return None


class StockAlertMonitorRuntime:
    """后台轮询运行时。"""

    def __init__(
        self,
        *,
        config: Optional[Config] = None,
        service: Optional[StockAlertService] = None,
    ) -> None:
        self._config = config or get_config()
        self._service = service or StockAlertService(config=self._config)
        self._interval_seconds = max(
            60,
            int(getattr(self._config, "agent_event_monitor_interval_minutes", 5)) * 60,
        )
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Start the background monitor thread."""
        if self._thread and self._thread.is_alive():
            return True

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="stock-alert-monitor",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "股票告警监控线程已启动：每 %s 分钟检查一次",
            max(1, self._interval_seconds // 60),
        )
        return True

    def stop(self) -> None:
        """Stop the background monitor thread."""
        self._stop_event.set()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._service.run_once()
            except Exception:
                logger.exception("股票告警监控执行失败")

            if self._stop_event.wait(self._interval_seconds):
                break


_alert_runtime_lock = threading.Lock()
_alert_runtime: Optional[StockAlertMonitorRuntime] = None


def start_stock_alert_monitor_background(
    *,
    config: Optional[Config] = None,
) -> Optional[StockAlertMonitorRuntime]:
    """Start stock alert monitoring in the background when enabled."""
    cfg = config or get_config()
    if not getattr(cfg, "agent_event_monitor_enabled", False):
        return None

    service = StockAlertService(config=cfg)
    rules = service.load_rules()
    if not rules:
        logger.warning("已启用股票告警监控，但未配置有效规则，后台监控未启动")
        return None

    global _alert_runtime
    with _alert_runtime_lock:
        if _alert_runtime and _alert_runtime._thread and _alert_runtime._thread.is_alive():
            return _alert_runtime

        runtime = StockAlertMonitorRuntime(config=cfg, service=service)
        runtime.start()
        _alert_runtime = runtime
        return runtime
