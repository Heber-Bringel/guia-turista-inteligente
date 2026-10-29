"""Cache em memória thread-safe com TTL (Time-To-Live) e expiração automática."""

import threading
import time
from typing import Any


class InMemoryCache:
    """Cache thread-safe baseado em dicionário com suporte a expiração por TTL."""

    def __init__(self, default_ttl_seconds: float = 3600.0) -> None:
        self._default_ttl = default_ttl_seconds
        self._storage: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        """Armazena um valor com chave e TTL em segundos."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expire_at = time.time() + ttl
        with self._lock:
            self._storage[key] = (value, expire_at)

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém um valor se ainda válido. Remove se expirado."""
        now = time.time()
        with self._lock:
            item = self._storage.get(key)
            if item is None:
                return default
            value, expire_at = item
            if now > expire_at:
                del self._storage[key]
                return default
            return value

    def delete(self, key: str) -> bool:
        """Remove explicitamente uma chave."""
        with self._lock:
            return bool(self._storage.pop(key, None))

    def clear(self) -> None:
        """Esvazia todo o cache."""
        with self._lock:
            self._storage.clear()

    def cleanup(self) -> int:
        """Varre e expurga todas as chaves expiradas. Retorna quantidade removida."""
        now = time.time()
        removidos = 0
        with self._lock:
            expirados = [k for k, (_, exp) in self._storage.items() if now > exp]
            for k in expirados:
                del self._storage[k]
                removidos += 1
        return removidos

    def __len__(self) -> int:
        with self._lock:
            return len(self._storage)


cache = InMemoryCache(default_ttl_seconds=7200.0)

