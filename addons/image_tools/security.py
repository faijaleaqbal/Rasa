"""
Ephemeral file store with TTL expiration, path-sanitization, tokenized downloads, and rate limiting.
"""

import os
import time
import secrets
import threading
import logging
from typing import Dict, Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)

TEMP_STORAGE_DIR = Path("/tmp/alya_image_tools_storage")
TEMP_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TTL_SECONDS = 1800  # 30 minutes


class EphemeralItem:
    def __init__(self, data: bytes, filename: str, mime_type: str, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.token = secrets.token_urlsafe(24)
        self.data = data
        self.filename = self._sanitize_filename(filename)
        self.mime_type = mime_type
        self.size_bytes = len(data)
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        # Strip path traversal characters
        clean = os.path.basename(name).replace("/", "_").replace("\\", "_")
        clean = "".join(c for c in clean if c.isalnum() or c in "._- ")
        return clean.strip() or "image_output.jpg"

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class EphemeralStore:
    """Thread-safe in-memory/disk ephemeral cache for processed downloads."""

    def __init__(self):
        self._items: Dict[str, EphemeralItem] = {}
        self._lock = threading.Lock()
        self._start_cleanup_daemon()

    def put(self, data: bytes, filename: str, mime_type: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
        item = EphemeralItem(data, filename, mime_type, ttl_seconds)
        with self._lock:
            self._items[item.token] = item
        return item.token

    def get(self, token: str) -> Optional[EphemeralItem]:
        with self._lock:
            item = self._items.get(token)
            if item is None:
                return None
            if item.is_expired:
                del self._items[token]
                return None
            return item

    def delete(self, token: str) -> bool:
        with self._lock:
            if token in self._items:
                del self._items[token]
                return True
        return False

    def purge_expired(self) -> int:
        now = time.time()
        count = 0
        with self._lock:
            expired_keys = [k for k, item in self._items.items() if item.expires_at < now]
            for k in expired_keys:
                del self._items[k]
                count += 1
        return count

    def _start_cleanup_daemon(self):
        def _loop():
            while True:
                time.sleep(300)  # Every 5 minutes
                try:
                    self.purge_expired()
                except Exception as e:
                    logger.error(f"Error in store cleanup daemon: {e}")

        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()


class TokenBucketRateLimiter:
    """Simple in-memory token bucket rate limiter for IP address throttling."""

    def __init__(self, capacity: int = 60, refill_rate_per_sec: float = 2.0):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self._buckets: Dict[str, Tuple[float, float]] = {}  # ip -> (tokens, last_update)
        self._lock = threading.Lock()

    def allow_request(self, client_ip: str, tokens_cost: float = 1.0) -> bool:
        now = time.time()
        with self._lock:
            if client_ip not in self._buckets:
                self._buckets[client_ip] = (self.capacity - tokens_cost, now)
                return True

            tokens, last_update = self._buckets[client_ip]
            elapsed = now - last_update
            # Refill
            tokens = min(float(self.capacity), tokens + elapsed * self.refill_rate)

            if tokens >= tokens_cost:
                self._buckets[client_ip] = (tokens - tokens_cost, now)
                return True
            else:
                self._buckets[client_ip] = (tokens, now)
                return False


# Global singletons
ephemeral_store = EphemeralStore()
rate_limiter = TokenBucketRateLimiter(capacity=100, refill_rate_per_sec=5.0)
