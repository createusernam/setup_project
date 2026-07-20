#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Validate setup artifacts against the JSON Schema subset used by repository contracts.
# SCOPE: Draft 2020-12 structural keywords, local references, conditionals, and date-time format.
# DEPENDS: Python standard library only.
# END_MODULE_CONTRACT
"""Small fail-closed JSON Schema validator for setup's committed schema vocabulary."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any


class SchemaError(ValueError):
    """Raised when a schema uses a keyword this portable validator cannot resolve."""


def _pointer(document: Any, pointer: str) -> Any:
    value = document
    for raw in pointer.lstrip("/").split("/") if pointer else []:
        token = raw.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def _type_matches(instance: Any, expected: str) -> bool:
    if expected == "null":
        return instance is None
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "object":
        return isinstance(instance, dict)
    raise SchemaError(f"unsupported JSON Schema type {expected!r}")


def _format_valid(value: str, format_name: str) -> bool:
    if format_name != "date-time":
        raise SchemaError(f"unsupported JSON Schema format {format_name!r}")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return "T" in value


def validate(instance: Any, schema: dict[str, Any], *, root_schema: dict[str, Any] | None = None, path: str = "$") -> list[str]:
    """Return stable human-readable errors for the supported Draft 2020-12 subset."""
    root = root_schema or schema
    errors: list[str] = []

    if "$ref" in schema:
        reference = schema["$ref"]
        if not isinstance(reference, str) or not reference.startswith("#/"):
            raise SchemaError(f"only local JSON Schema references are supported, got {reference!r}")
        try:
            target = _pointer(root, reference[1:])
        except (KeyError, IndexError, ValueError, TypeError) as error:
            raise SchemaError(f"cannot resolve schema reference {reference!r}: {error}") from error
        return validate(instance, target, root_schema=root, path=path)

    expected_types = schema.get("type")
    if expected_types is not None:
        candidates = [expected_types] if isinstance(expected_types, str) else expected_types
        if not isinstance(candidates, list) or not all(isinstance(item, str) for item in candidates):
            raise SchemaError(f"invalid type declaration at {path}")
        if not any(_type_matches(instance, item) for item in candidates):
            errors.append(f"{path}: expected type {candidates}, got {type(instance).__name__}")
            return errors

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: must be one of {schema['enum']!r}")

    for keyword in ("allOf", "anyOf", "oneOf"):
        if keyword not in schema:
            continue
        branches = schema[keyword]
        results = [validate(instance, branch, root_schema=root, path=path) for branch in branches]
        successes = sum(not result for result in results)
        if keyword == "allOf":
            for result in results:
                errors.extend(result)
        elif keyword == "anyOf" and successes == 0:
            errors.append(f"{path}: does not match any allowed schema")
        elif keyword == "oneOf" and successes != 1:
            errors.append(f"{path}: must match exactly one allowed schema, matched {successes}")

    if "if" in schema:
        condition_errors = validate(instance, schema["if"], root_schema=root, path=path)
        branch = schema.get("then") if not condition_errors else schema.get("else")
        if branch is not None:
            errors.extend(validate(instance, branch, root_schema=root, path=path))

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: string is longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: does not match pattern {schema['pattern']!r}")
        if "format" in schema and not _format_valid(instance, schema["format"]):
            errors.append(f"{path}: is not a valid {schema['format']}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: must be >= {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: must be <= {schema['maximum']}")

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: array has fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: array has more than {schema['maxItems']} items")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in instance}) != len(instance):
            errors.append(f"{path}: array items must be unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(validate(item, item_schema, root_schema=root, path=f"{path}[{index}]"))

    if isinstance(instance, dict):
        if len(instance) < schema.get("minProperties", 0):
            errors.append(f"{path}: object has fewer than {schema['minProperties']} properties")
        required = schema.get("required", [])
        for name in required:
            if name not in instance:
                errors.append(f"{path}: missing required property {name!r}")
        properties = schema.get("properties", {})
        pattern_properties = schema.get("patternProperties", {})
        additional = schema.get("additionalProperties", True)
        for name, value in instance.items():
            child_path = f"{path}.{name}"
            matched = False
            if name in properties:
                matched = True
                errors.extend(validate(value, properties[name], root_schema=root, path=child_path))
            for pattern, child_schema in pattern_properties.items():
                if re.search(pattern, name):
                    matched = True
                    errors.extend(validate(value, child_schema, root_schema=root, path=child_path))
            if not matched and additional is False:
                errors.append(f"{path}: additional property {name!r} is not allowed")
            elif not matched and isinstance(additional, dict):
                errors.extend(validate(value, additional, root_schema=root, path=child_path))
        property_names = schema.get("propertyNames")
        if isinstance(property_names, dict):
            for name in instance:
                errors.extend(validate(name, property_names, root_schema=root, path=f"{path}.<property:{name}>"))

    return errors


def validate_file(instance_path: Path, schema_path: Path) -> list[str]:
    """Load JSON files and validate the instance against the schema."""
    try:
        instance = json.loads(instance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot read JSON artifact {instance_path}: {error}"]
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot read JSON schema {schema_path}: {error}"]
    try:
        return validate(instance, schema)
    except SchemaError as error:
        return [f"schema contract error: {error}"]
