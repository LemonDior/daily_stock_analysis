# -*- coding: utf-8 -*-
"""
共享线程池工具。

职责：
1. 提供按名称复用的线程池
2. 避免业务代码散落创建 ThreadPoolExecutor
3. 在进程退出时统一关闭线程池
"""

from __future__ import annotations

import atexit
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Tuple


class SharedThreadPoolRegistry:
    """按 `(name, max_workers)` 复用线程池。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._executors: Dict[Tuple[str, int], ThreadPoolExecutor] = {}
        self._registered_shutdown = False

    def get_executor(
        self,
        *,
        name: str,
        max_workers: int,
        thread_name_prefix: Optional[str] = None,
    ) -> ThreadPoolExecutor:
        normalized_workers = max(1, int(max_workers))
        key = (str(name).strip() or "default", normalized_workers)

        with self._lock:
            executor = self._executors.get(key)
            if executor is None:
                executor = ThreadPoolExecutor(
                    max_workers=normalized_workers,
                    thread_name_prefix=thread_name_prefix or key[0],
                )
                self._executors[key] = executor

            if not self._registered_shutdown:
                atexit.register(self.shutdown_all)
                self._registered_shutdown = True

            return executor

    def shutdown_all(self, *, wait: bool = True) -> None:
        with self._lock:
            executors = list(self._executors.values())
            self._executors.clear()

        for executor in executors:
            executor.shutdown(wait=wait)


_registry = SharedThreadPoolRegistry()


def get_shared_thread_pool_registry() -> SharedThreadPoolRegistry:
    """获取全局共享线程池注册器。"""
    return _registry
