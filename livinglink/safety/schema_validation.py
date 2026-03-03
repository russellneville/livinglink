from __future__ import annotations

from typing import Any


def validate_object_schema(schema: dict[str, Any], data: dict[str, Any]) -> tuple[bool, str]:
    """Minimal JSON-schema-like validation for object arguments.

    Supports: type=object, properties, required, additionalProperties.
    """
    if schema.get("type") != "object":
        return False, "UNSUPPORTED_SCHEMA"

    properties = schema.get("properties", {})
    required = schema.get("required", [])
    additional = schema.get("additionalProperties", True)

    if not isinstance(data, dict):
        return False, "ARGS_NOT_OBJECT"

    for field in required:
        if field not in data:
            return False, "MISSING_REQUIRED"

    if additional is False:
        unknown_keys = set(data.keys()) - set(properties.keys())
        if unknown_keys:
            return False, "UNKNOWN_ARGUMENT"

    for field_name, expected in properties.items():
        if field_name not in data:
            continue

        expected_type = expected.get("type")
        value = data[field_name]
        if expected_type == "string" and not isinstance(value, str):
            return False, "TYPE_MISMATCH"
        if expected_type == "integer" and not isinstance(value, int):
            return False, "TYPE_MISMATCH"
        if expected_type == "number" and not isinstance(value, (int, float)):
            return False, "TYPE_MISMATCH"
        if expected_type == "boolean" and not isinstance(value, bool):
            return False, "TYPE_MISMATCH"
        if expected_type == "object" and not isinstance(value, dict):
            return False, "TYPE_MISMATCH"
        if expected_type == "array" and not isinstance(value, list):
            return False, "TYPE_MISMATCH"

    return True, "VALID"
