from __future__ import annotations

import copy
import os
import time
from dataclasses import dataclass
from threading import Lock
from typing import Protocol


DEFAULT_CACHE_TTL_SECONDS = 900
CACHEABLE_MODES = {"macro", "sectors", "sectors_all", "sector", "company", "risk", "overheat", "conclusion"}
SHORT_TTL_MODES = {"company", "risk", "overheat"}


class AnalysisCache(Protocol):
    def get(self, key: str) -> dict[str, object] | None:
        ...

    def set(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        ...


@dataclass
class CacheEntry:
    value: dict[str, object]
    expires_at: float


class InMemoryAnalysisCache:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._lock = Lock()

    def get(self, key: str) -> dict[str, object] | None:
        now = time.time()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                return None
            return copy.deepcopy(entry.value)

    def set(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        with self._lock:
            self._entries[key] = CacheEntry(copy.deepcopy(value), time.time() + ttl_seconds)


def bool_from_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def int_from_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def cache_enabled() -> bool:
    return bool_from_env("CACHE_ENABLED", True)


def ttl_for_mode(mode: str) -> int:
    if mode in SHORT_TTL_MODES:
        return int_from_env("COMPANY_CACHE_TTL_SECONDS", int_from_env("CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS))
    return int_from_env("CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS)


def cache_key(mode: str, normalized_input: str) -> str:
    return f"{mode}_{normalized_input}" if normalized_input else mode


analysis_cache: AnalysisCache = InMemoryAnalysisCache()

# Future hook: replace analysis_cache with a Redis-backed implementation without changing api.main.
