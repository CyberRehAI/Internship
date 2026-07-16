from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.stix.progress import log_phase, track

MAX_DEBUG_MESSAGES = 50


@dataclass(frozen=True)
class ValidationResult:
    object_id: str
    object_type: str
    is_valid: bool
    errors: list[str]
    warnings: list[str]


def _ensure_schemas_available(version: str = "2.1") -> str | None:
    try:
        import stix2validator
    except ImportError:
        return "stix2-validator package not installed"

    package_dir = Path(stix2validator.__file__).resolve().parent
    schema_dir = package_dir / f"schemas-{version}" / "schemas"
    if schema_dir.is_dir() and any(schema_dir.rglob("core.json")):
        return None
    return (
        f"stix2-validator {stix2validator.__version__} is missing bundled STIX {version} schemas. "
        "Install stix2-validator==3.2.0; versions 3.3.0 and 3.3.1 have a known packaging bug."
    )


def validate_object(obj: dict[str, Any], options: Any) -> ValidationResult:
    from stix2validator import validate_instance

    obj_id = str(obj.get("id") or "unknown")
    obj_type = str(obj.get("type") or "unknown")
    try:
        result = validate_instance(obj, options)
    except Exception as exc:
        return ValidationResult(obj_id, obj_type, False, [str(exc)], [])

    errors = [str(getattr(item, "message", item)) for item in getattr(result, "errors", []) or []]
    warnings = [str(getattr(item, "message", item)) for item in getattr(result, "warnings", []) or []]
    return ValidationResult(obj_id, obj_type, bool(getattr(result, "is_valid", False)), errors, warnings)


def validate_bundle(
    bundle: dict[str, Any],
    *,
    strict: bool = False,
    debug: bool = False,
    show_progress: bool | None = None,
) -> tuple[bool, list[str]]:
    schema_error = _ensure_schemas_available()
    if schema_error:
        return False, [schema_error]

    try:
        import stix2
        from stix2validator import ValidationOptions
    except ImportError as exc:
        return False, [f"STIX validation package not installed: {exc.name}"]

    objects = [
        obj
        for obj in bundle.get("objects") or []
        if isinstance(obj, dict) and obj.get("type") != "bundle"
    ]

    log_phase(f"Parsing bundle with stix2 ({len(objects)} objects)...", enabled=show_progress)
    try:
        stix2.parsing.parse(bundle, allow_custom=True)
    except Exception as exc:
        return False, [f"stix2 parse error: {exc}"]

    options = ValidationOptions(version="2.1", strict=strict)
    invalid_count = 0
    messages: list[str] = []
    omitted_messages = 0

    for obj in track(
        objects,
        total=len(objects),
        desc="Validating STIX",
        unit="obj",
        enabled=show_progress,
    ):
        result = validate_object(obj, options)
        if not result.is_valid:
            invalid_count += 1
            object_messages = result.errors or ["validation failed without an error message"]
            for error in object_messages:
                message = f"{result.object_type} {result.object_id}: {error}"
                if not debug or len(messages) < MAX_DEBUG_MESSAGES:
                    messages.append(message)
                else:
                    omitted_messages += 1

    if debug and omitted_messages:
        messages.append(f"Validation debug output omitted {omitted_messages} additional error(s).")
    if debug:
        messages.append(f"Validation debug summary: {invalid_count} invalid object(s).")
    return invalid_count == 0, messages
