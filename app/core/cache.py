
import hashlib
import time
from typing import Any, Optional
from collections import OrderedDict

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TTLCache:

    def __init__(
        self,
        max_size: int = settings.CACHE_MAX_SIZE,
        ttl_seconds: int = settings.CACHE_TTL_SECONDS,
        enabled: bool = settings.CACHE_ENABLED,
    ):
        self.max_size   = max_size
        self.ttl        = ttl_seconds
        self.enabled    = enabled
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._hits      = 0
        self._misses    = 0

        logger.info(
            f"TTLCache initialised — "
            f"enabled={enabled}, ttl={ttl_seconds}s, max_size={max_size}"
        )


    def get(self, key: str) -> Optional[Any]:

        if not self.enabled:
            return None

        if key not in self._store:
            self._misses += 1
            return None

        value, expiry = self._store[key]

        if self.ttl > 0 and time.time() > expiry:
            del self._store[key]
            self._misses += 1
            logger.debug(f"Cache EXPIRED for key={key[:12]}...")
            return None

        self._store.move_to_end(key)
        self._hits += 1
        logger.debug(f"Cache HIT for key={key[:12]}...")
        return value

    def set(self, key: str, value: Any) -> None:
        if not self.enabled:
            return

        if len(self._store) >= self.max_size:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]
            logger.debug(f"Cache EVICT (capacity) — removed key={oldest_key[:12]}...")

        expiry = time.time() + self.ttl if self.ttl > 0 else float("inf")
        self._store[key] = (value, expiry)
        logger.debug(f"Cache SET key={key[:12]}... (total={len(self._store)})")

    def invalidate(self, pattern: str) -> int:

        keys_to_remove = [k for k in self._store if pattern in k]
        for k in keys_to_remove:
            del self._store[k]
        if keys_to_remove:
            logger.info(
                f"Cache INVALIDATED {len(keys_to_remove)} entries "
                f"matching pattern='{pattern}'"
            )
        return len(keys_to_remove)

    def clear(self) -> None:
        count = len(self._store)
        self._store.clear()
        logger.info(f"Cache CLEARED — removed {count} entries")

    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = round(self._hits / total * 100, 1) if total > 0 else 0.0
        return {
            "enabled":       self.enabled,
            "size":          len(self._store),
            "max_size":      self.max_size,
            "ttl_seconds":   self.ttl,
            "hits":          self._hits,
            "misses":        self._misses,
            "hit_rate_pct":  hit_rate,
        }


    @staticmethod
    def make_key(repo_name: str, question: str, top_k: Optional[int] = None) -> str:

        raw = f"{repo_name}::{question.strip().lower()}::{top_k}"
        return hashlib.md5(raw.encode()).hexdigest()


rag_cache = TTLCache()