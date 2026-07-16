from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def normalize_timestamp(value: str | None, fallback: str | None = None) -> str:
    if value:
        text = value.strip()
        if text.endswith("Z"):
            return text if "." in text else text.replace("Z", ".000Z")
        if "+" in text or text.endswith("000"):
            try:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
                return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            except ValueError:
                pass
        return text + (".000Z" if "T" in text else "T00:00:00.000Z")
    return fallback or utc_now()


def is_valid_uri(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    parsed = urlparse(text)
    return parsed.scheme in {"http", "https", "ftp"} and bool(parsed.netloc)


def external_reference(source_name: str, url: str, external_id: str | None = None) -> dict[str, Any]:
    ref: dict[str, Any] = {"source_name": source_name, "url": url}
    if external_id:
        ref["external_id"] = external_id
    return ref


def base_object(
    stix_type: str,
    obj_id: str,
    created: str,
    modified: str,
    *,
    labels: list[str] | None = None,
    marking_refs: list[str] | None = None,
) -> dict[str, Any]:
    obj: dict[str, Any] = {
        "type": stix_type,
        "spec_version": "2.1",
        "id": obj_id,
        "created": created,
        "modified": modified,
    }
    if labels:
        obj["labels"] = sorted(set(labels))
    if marking_refs:
        obj["object_marking_refs"] = marking_refs
    return obj
