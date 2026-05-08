"""
Geocoding Cache Module
Caches geocoding results by address hash to avoid redundant API calls.
Identical addresses in the same file only geocode once.
"""

import hashlib
from typing import Dict, Optional
from threading import Lock


class GeoCache:
    """Thread-safe in-memory geocoding cache."""

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, address: str, country_code: str = '') -> str:
        """Create a cache key from address + country code."""
        raw = f"{address.strip().lower()}|{country_code.strip().lower()}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def get(self, address: str, country_code: str = '') -> Optional[Dict]:
        """Look up a cached result. Returns None if not cached."""
        key = self._make_key(address, country_code)
        with self._lock:
            result = self._cache.get(key)
            if result is not None:
                self._hits += 1
            else:
                self._misses += 1
            return result

    def put(self, address: str, country_code: str, result: Dict) -> None:
        """Store a geocoding result in the cache."""
        key = self._make_key(address, country_code)
        with self._lock:
            self._cache[key] = result

    def clear(self) -> None:
        """Clear all cached results."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> Dict[str, int]:
        """Return cache hit/miss statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                'hits': self._hits,
                'misses': self._misses,
                'total_lookups': total,
                'cached_entries': len(self._cache),
                'hit_rate': round(self._hits / total * 100, 1) if total > 0 else 0,
            }


# Global cache instance (shared across threads)
geocode_cache = GeoCache()
