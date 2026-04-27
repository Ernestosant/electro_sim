from __future__ import annotations

from collections import OrderedDict
from typing import Any


class LRUCache:
    """LRU cache simple con capacity fija. Thread-safe no garantizado (uso desde un solo thread)."""

    def __init__(self, maxsize: int = 256) -> None:
        self._maxsize = maxsize
        self._data: OrderedDict[Any, Any] = OrderedDict()
        self._hits = 0
        self._total = 0

    def get(self, key: Any) -> Any:
        self._total += 1
        if key in self._data:
            self._hits += 1
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key: Any, value: Any) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    @property
    def hit_ratio(self) -> float:
        return self._hits / self._total if self._total else 0.0

    def clear(self) -> None:
        self._data.clear()
        self._hits = 0
        self._total = 0
