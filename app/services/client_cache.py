from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import time
from typing import Any


@dataclass
class _CacheEntry:
    expires_at: float
    value: Any


class ClientCache:
    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        now = time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            if entry.expires_at <= now:
                self._store.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            self._store[key] = _CacheEntry(
                expires_at=time() + max(1, ttl_seconds),
                value=value,
            )

    def invalidate_prefix(self, prefix: str) -> int:
        removed = 0
        with self._lock:
            for key in list(self._store.keys()):
                if key.startswith(prefix):
                    self._store.pop(key, None)
                    removed += 1
        return removed


client_cache = ClientCache()


def orders_cache_key(user_id: str, include_items: bool) -> str:
    return f"client:orders:{user_id}:include_items:{int(include_items)}"


def home_cache_key(user_id: str, *, variant: str = "default") -> str:
    return f"client:home:{user_id}:variant:{variant}"


def bootstrap_cache_key(user_id: str) -> str:
    return f"client:bootstrap:{user_id}"


def bootstrap_home_cache_key(user_id: str, images_mode: str) -> str:
    return f"client:bootstrap:home:{user_id}:images:{images_mode}"


def bootstrap_cart_cache_key(user_id: str) -> str:
    return f"client:bootstrap:cart:{user_id}"


def bootstrap_orders_cache_key(user_id: str) -> str:
    return f"client:bootstrap:orders:{user_id}"


def bootstrap_locks_cache_key(user_id: str) -> str:
    return f"client:bootstrap:locks:{user_id}"


def invalidate_user_orders_cache(user_id: str) -> int:
    return client_cache.invalidate_prefix(f"client:orders:{user_id}:")


def invalidate_user_home_cache(user_id: str) -> int:
    return client_cache.invalidate_prefix(f"client:home:{user_id}:")


def invalidate_user_bootstrap_cache(user_id: str) -> int:
    removed = 0
    removed += client_cache.invalidate_prefix(f"client:bootstrap:home:{user_id}:")
    removed += client_cache.invalidate_prefix(f"client:bootstrap:cart:{user_id}")
    removed += client_cache.invalidate_prefix(f"client:bootstrap:orders:{user_id}")
    removed += client_cache.invalidate_prefix(f"client:bootstrap:locks:{user_id}")
    return removed


def invalidate_user_bootstrap_home_cache(user_id: str) -> int:
    return client_cache.invalidate_prefix(f"client:bootstrap:home:{user_id}:")


def invalidate_user_bootstrap_cart_cache(user_id: str) -> int:
    return client_cache.invalidate_prefix(f"client:bootstrap:cart:{user_id}")


def invalidate_user_bootstrap_orders_cache(user_id: str) -> int:
    return client_cache.invalidate_prefix(f"client:bootstrap:orders:{user_id}")


def invalidate_user_bootstrap_locks_cache(user_id: str) -> int:
    return client_cache.invalidate_prefix(f"client:bootstrap:locks:{user_id}")


def invalidate_all_home_cache() -> int:
    return client_cache.invalidate_prefix("client:home:")


def invalidate_all_bootstrap_cache() -> int:
    return client_cache.invalidate_prefix("client:bootstrap:")


def invalidate_all_bootstrap_home_cache() -> int:
    return client_cache.invalidate_prefix("client:bootstrap:home:")
