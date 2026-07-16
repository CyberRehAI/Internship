from __future__ import annotations

import uuid

# Fixed project namespace for deterministic STIX IDs across runs.
OTX_STIX_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def stix_id(stix_type: str, key: str) -> str:
    """Generate a deterministic STIX 2.1 ID using UUIDv5."""
    normalized = f"{stix_type}:{key.strip().lower()}"
    uid = uuid.uuid5(OTX_STIX_NAMESPACE, normalized)
    return f"{stix_type}--{uid}"


def relationship_id(source_id: str, relationship_type: str, target_id: str) -> str:
    return stix_id("relationship", f"{source_id}|{relationship_type}|{target_id}")
