"""Lazy-load LRU registry for model adapters.

Per Spark constraints (130 GB unified VRAM shared with MedGemma+DermApixel),
we keep only the most-recently-used model resident. After UNLOAD_AFTER_S of
idleness the registry unloads the model to free VRAM.

Single-process scope: Celery is configured with prefetch=1 so tasks for one
worker process never overlap. The reaper runs in a background thread.
"""

from __future__ import annotations

import threading
import time

import structlog

from app.workers.adapters import ModelAdapter, get_adapter

UNLOAD_AFTER_S = 600  # 10 minutes

log = structlog.get_logger(__name__)


class ModelRegistry:
    def __init__(self, unload_after_s: float = UNLOAD_AFTER_S) -> None:
        self._unload_after_s = unload_after_s
        self._lock = threading.RLock()
        self._adapter: ModelAdapter | None = None
        self._last_used: float = 0.0
        self._reaper_started = False

    def get(self, model: str) -> ModelAdapter:
        with self._lock:
            if self._adapter is not None and self._adapter.name != model:
                log.info("registry.evict", evicting=self._adapter.name, requesting=model)
                self._adapter.unload()
                self._adapter = None
            if self._adapter is None:
                log.info("registry.load", model=model)
                self._adapter = get_adapter(model)
                self._adapter.load()
            self._last_used = time.time()
            self._ensure_reaper()
            return self._adapter

    def touch(self) -> None:
        with self._lock:
            self._last_used = time.time()

    def evict_current(self) -> None:
        """Force-unload the cached adapter.

        Called by tasks.py on synthesis errors so a suspect adapter state
        (e.g. qwen3 subprocess hung) doesn't carry over into the next job.
        Best-effort unload — if unload itself raises, we still drop the ref
        so the next get() loads cleanly.
        """
        with self._lock:
            if self._adapter is None:
                return
            name = self._adapter.name
            try:
                self._adapter.unload()
            except Exception:
                log.warning("registry.evict.unload_failed", model=name, exc_info=True)
            self._adapter = None
            log.info("registry.evict.manual", model=name)

    def _ensure_reaper(self) -> None:
        if self._reaper_started:
            return
        t = threading.Thread(target=self._reaper_loop, name="vcapp-lru-reaper", daemon=True)
        t.start()
        self._reaper_started = True

    def _reaper_loop(self) -> None:
        while True:
            time.sleep(30)
            with self._lock:
                if self._adapter is None:
                    continue
                if time.time() - self._last_used > self._unload_after_s:
                    log.info("registry.idle_unload", model=self._adapter.name)
                    self._adapter.unload()
                    self._adapter = None


registry = ModelRegistry()
