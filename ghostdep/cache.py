"""Local caching mechanism for registry lookups."""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "ghostdep"
CACHE_FILE_NAME = "registry_cache.json"
DEFAULT_TTL_SECONDS = 86400  # 24 hours


class RegistryCache:
    def __init__(self, cache_dir: Optional[Path] = None, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_file = self.cache_dir / CACHE_FILE_NAME
        self.ttl = ttl_seconds
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    now = time.time()
                    # Filter out expired entries
                    self._memory_cache = {
                        k: v for k, v in data.items()
                        if isinstance(v, dict) and now - v.get("_cached_at", 0) < self.ttl
                    }
        except Exception:
            self._memory_cache = {}

    def get(self, ecosystem: str, name: str) -> Optional[Dict[str, Any]]:
        key = f"{ecosystem}:{name.lower()}"
        entry = self._memory_cache.get(key)
        if not entry:
            return None
        if time.time() - entry.get("_cached_at", 0) > self.ttl:
            del self._memory_cache[key]
            return None
        return entry.get("data")

    def set(self, ecosystem: str, name: str, data: Dict[str, Any]) -> None:
        key = f"{ecosystem}:{name.lower()}"
        self._memory_cache[key] = {
            "_cached_at": time.time(),
            "data": data
        }
        self._save()

    def _save(self) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            temp_file = self.cache_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._memory_cache, f, indent=2)
            temp_file.replace(self.cache_file)
        except Exception:
            pass  # Non-fatal if cache cannot be written to disk

    def clear(self) -> None:
        self._memory_cache.clear()
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
        except Exception:
            pass
