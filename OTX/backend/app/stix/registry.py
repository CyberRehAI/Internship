from __future__ import annotations

from typing import Any


class EntityRegistry:
    """Cross-pulse deduplication store for STIX objects."""

    def __init__(self) -> None:
        self._objects: dict[str, dict[str, Any]] = {}
        self._keys: dict[str, str] = {}

    def get_by_key(self, key: str) -> dict[str, Any] | None:
        obj_id = self._keys.get(key)
        if not obj_id:
            return None
        return self._objects.get(obj_id)

    def register(self, key: str, obj: dict[str, Any]) -> dict[str, Any]:
        obj_id = obj["id"]
        existing_key = self._keys.get(key)
        if existing_key and existing_key in self._objects:
            return self._objects[existing_key]
        self._keys[key] = obj_id
        self._objects[obj_id] = obj
        return obj

    def merge_labels(self, obj_id: str, labels: list[str]) -> None:
        obj = self._objects.get(obj_id)
        if not obj:
            return
        current = set(obj.get("labels") or [])
        current.update(label for label in labels if label)
        if current:
            obj["labels"] = sorted(current)

    def all_objects(self) -> list[dict[str, Any]]:
        return list(self._objects.values())

    def count(self) -> int:
        return len(self._objects)
