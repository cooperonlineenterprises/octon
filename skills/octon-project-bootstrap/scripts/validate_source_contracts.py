#!/usr/bin/env python3
"""Validate source-only pattern, semantic, Context Pack, and proof contracts."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]


def octon_mini_source_root() -> Path:
    candidates = (
        Path(__file__).resolve().parents[3],
        SKILL_ROOT / "assets" / "octon-source",
    )
    for candidate in candidates:
        if (
            (candidate / "VERSION").is_file()
            and (candidate / "patterns/catalog.json").is_file()
            and (candidate / "shared/optional-schemas").is_dir()
        ):
            return candidate
    return candidates[0]


ROOT = octon_mini_source_root()
LIFECYCLE_STATES = (
    "candidate",
    "reviewed",
    "experimental",
    "recommended",
    "stable",
    "deprecated",
    "rejected",
)
ALLOWED_TRANSITIONS: dict[str | None, set[str]] = {
    None: {"candidate"},
    "candidate": {"reviewed", "rejected"},
    "reviewed": {"experimental", "deprecated", "rejected"},
    "experimental": {"reviewed", "recommended", "deprecated", "rejected"},
    "recommended": {"experimental", "stable", "deprecated", "rejected"},
    "stable": {"deprecated"},
    "deprecated": set(),
    "rejected": set(),
}
INFORMATION_ROLES = {
    "authoritative",
    "observed",
    "inferred",
    "proposed",
    "derived",
    "historical",
    "superseded",
    "stale",
    "unknown",
    "intentionally_omitted",
}
SOURCE_ONLY_MARKERS = {
    "patterns/",
    "PAT-0001",
    "PAT-0002",
    "PAT-0003",
    "lifecycle-disposition",
    "governed-change-and-effects",
    "patterns/architecture-proof",
}
SENTINELS = {
    "",
    "unknown",
    "not_assessed",
    "not_recorded",
    "latest",
    "current",
    "replace",
    "replace_me",
}
SUPPORTED_SCHEMA_KEYWORDS = {
    "$defs",
    "$id",
    "$ref",
    "$schema",
    "additionalProperties",
    "allOf",
    "const",
    "description",
    "enum",
    "else",
    "format",
    "if",
    "items",
    "maxItems",
    "maximum",
    "minItems",
    "minLength",
    "minimum",
    "pattern",
    "properties",
    "required",
    "title",
    "then",
    "type",
    "uniqueItems",
}


class DuplicateKeyError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is prohibited: {value}")


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=strict_object,
        parse_constant=reject_json_constant,
    )


def schema_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def resolve_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ValueError(f"unsupported non-local schema reference: {reference}")
    current: Any = root_schema
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"unresolved schema reference: {reference}")
        current = current[part]
    if not isinstance(current, dict):
        raise ValueError(f"schema reference is not an object: {reference}")
    return current


def validate_schema(
    value: Any,
    schema: dict[str, Any],
    path: str = "$",
    *,
    root_schema: dict[str, Any] | None = None,
) -> list[str]:
    root_schema = root_schema or schema
    if "$ref" in schema:
        try:
            resolved = resolve_ref(root_schema, schema["$ref"])
        except ValueError as error:
            return [f"{path}: {error}"]
        return validate_schema(value, resolved, path, root_schema=root_schema)

    errors: list[str] = []
    all_of = schema.get("allOf", [])
    if isinstance(all_of, list):
        for item in all_of:
            if isinstance(item, dict):
                errors.extend(
                    validate_schema(value, item, path, root_schema=root_schema)
                )
    condition = schema.get("if")
    if isinstance(condition, dict):
        condition_matches = not validate_schema(
            value,
            condition,
            path,
            root_schema=root_schema,
        )
        branch = schema.get("then" if condition_matches else "else")
        if isinstance(branch, dict):
            errors.extend(
                validate_schema(value, branch, path, root_schema=root_schema)
            )
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value is outside the allowed vocabulary")

    expected = schema.get("type")
    if expected is not None:
        types = expected if isinstance(expected, list) else [expected]
        if not any(schema_type_matches(value, item) for item in types):
            return [f"{path}: expected type {expected!r}"]

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is too short")
        pattern = schema.get("pattern")
        if pattern and not re.fullmatch(pattern, value):
            errors.append(f"{path}: string does not match required pattern")
        if schema.get("format") == "date":
            try:
                date.fromisoformat(value)
            except ValueError:
                errors.append(f"{path}: expected ISO date")
        if schema.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError("timezone required")
            except ValueError:
                errors.append(f"{path}: expected timezone-aware ISO date-time")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: number is below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: number is above maximum")

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: array has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: array has too many items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True) for item in value]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{path}: array items must be unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(
                    validate_schema(
                        item,
                        item_schema,
                        f"{path}[{index}]",
                        root_schema=root_schema,
                    )
                )

    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: missing required property {required!r}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, child in properties.items():
                if key in value and isinstance(child, dict):
                    errors.extend(
                        validate_schema(
                            value[key],
                            child,
                            f"{path}.{key}",
                            root_schema=root_schema,
                        )
                    )
            if schema.get("additionalProperties") is False:
                for key in value:
                    if key not in properties:
                        errors.append(f"{path}: unknown property {key!r}")
    return errors


def lint_schema(schema: Any, path: str = "$", *, root: Any | None = None) -> list[str]:
    if not isinstance(schema, dict):
        return [f"{path}: schema node must be an object"]
    root = root or schema
    errors = [
        f"{path}: unsupported schema keyword {key!r}"
        for key in schema
        if key not in SUPPORTED_SCHEMA_KEYWORDS
    ]
    reference = schema.get("$ref")
    if isinstance(reference, str):
        try:
            resolve_ref(root, reference)
        except ValueError as error:
            errors.append(f"{path}: {error}")
    for key in ("properties", "$defs"):
        children = schema.get(key)
        if isinstance(children, dict):
            for name, child in children.items():
                errors.extend(lint_schema(child, f"{path}.{key}.{name}", root=root))
    if isinstance(schema.get("items"), dict):
        errors.extend(lint_schema(schema["items"], f"{path}.items", root=root))
    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        for index, child in enumerate(all_of):
            errors.extend(lint_schema(child, f"{path}.allOf[{index}]", root=root))
    for key in ("if", "then", "else"):
        child = schema.get(key)
        if isinstance(child, dict):
            errors.extend(lint_schema(child, f"{path}.{key}", root=root))
    return errors


def schema_issues(value: Any, schema: dict[str, Any], label: str) -> list[str]:
    return [f"{label}: {error}" for error in validate_schema(value, schema)]


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def is_sentinel(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    normalized = value.strip().casefold()
    return normalized in SENTINELS or normalized.startswith("replace with")


def safe_source_path(root: Path, reference: str) -> Path | None:
    if not reference.startswith("repo:"):
        return None
    raw = reference[5:].split("#", 1)[0]
    candidate = PurePosixPath(raw)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        return None
    path = root.joinpath(*candidate.parts)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    return path


def load_catalog_values(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    catalog = load_json(root / "patterns/catalog.json")
    records: dict[str, dict[str, Any]] = {}
    if isinstance(catalog, dict):
        for allocation in catalog.get("allocations", []):
            if not isinstance(allocation, dict):
                continue
            record_path = allocation.get("record_path")
            if allocation.get("allocation_status") == "allocated" and isinstance(
                record_path, str
            ):
                value = load_json(root / record_path)
                if isinstance(value, dict):
                    records[record_path] = value
    return catalog, records


def validate_catalog_values(
    root: Path,
    catalog: dict[str, Any],
    records: dict[str, dict[str, Any]],
) -> list[str]:
    catalog_schema = load_json(root / "patterns/schemas/pattern-catalog.schema.json")
    record_schema = load_json(root / "patterns/schemas/pattern-record.schema.json")
    errors = schema_issues(catalog, catalog_schema, "patterns/catalog.json")
    if errors:
        return errors
    if catalog.get("lifecycle_states") != list(LIFECYCLE_STATES):
        errors.append("patterns/catalog.json: lifecycle state order or vocabulary differs")

    decisions = (root / "ARCHITECTURE_DECISIONS.md").read_text(encoding="utf-8")
    allocations = catalog.get("allocations", [])
    ids: set[str] = set()
    slugs: set[str] = set()
    paths: set[str] = set()
    numeric_ids: list[int] = []
    active_records: dict[str, dict[str, Any]] = {}
    for index, allocation in enumerate(allocations):
        if not isinstance(allocation, dict):
            continue
        pattern_id = allocation.get("id")
        slug = allocation.get("slug")
        record_path = allocation.get("record_path")
        if pattern_id in ids:
            errors.append(f"patterns/catalog.json: duplicate stable ID {pattern_id}")
        if slug in slugs:
            errors.append(f"patterns/catalog.json: duplicate slug {slug}")
        if isinstance(record_path, str) and record_path in paths:
            errors.append(f"patterns/catalog.json: duplicate record path {record_path}")
        if isinstance(pattern_id, str):
            ids.add(pattern_id)
            numeric_ids.append(int(pattern_id.rsplit("-", 1)[1]))
        if isinstance(slug, str):
            slugs.add(slug)
        if isinstance(record_path, str):
            paths.add(record_path)
        if allocation.get("allocation_status") == "retired":
            if record_path is not None:
                errors.append(
                    f"patterns/catalog.json: retired allocation {pattern_id} retains a record path"
                )
            continue
        if not isinstance(record_path, str):
            errors.append(
                f"patterns/catalog.json: allocated ID {pattern_id} lacks a record path"
            )
            continue
        record = records.get(record_path)
        if record is None:
            errors.append(f"patterns/catalog.json: unresolved record path {record_path}")
            continue
        active_records[str(pattern_id)] = record
        errors.extend(schema_issues(record, record_schema, record_path))
        if record.get("id") != pattern_id or record.get("slug") != slug:
            errors.append(f"{record_path}: allocation identity or slug mismatch")
        expected_name = f"{pattern_id}-{slug}.json"
        if PurePosixPath(record_path).name != expected_name:
            errors.append(f"{record_path}: filename does not preserve allocated identity")

    if numeric_ids != sorted(numeric_ids):
        errors.append("patterns/catalog.json: stable ID allocations are not ordered")

    for pattern_id, record in active_records.items():
        label = next(
            path for path, value in records.items() if value is record
        )
        history = record.get("status_history", [])
        previous: str | None = None
        previous_date: date | None = None
        seen_statuses: list[str] = []
        for index, transition in enumerate(history):
            if not isinstance(transition, dict):
                continue
            from_status = transition.get("from_status")
            to_status = transition.get("to_status")
            if from_status != previous:
                errors.append(f"{label}: status history is not contiguous at item {index}")
            if to_status not in ALLOWED_TRANSITIONS.get(from_status, set()):
                errors.append(
                    f"{label}: illegal lifecycle transition {from_status!r} -> {to_status!r}"
                )
            try:
                changed = date.fromisoformat(str(transition.get("changed_on")))
            except ValueError:
                changed = None
            if changed is not None and previous_date is not None and changed < previous_date:
                errors.append(f"{label}: status history dates decrease")
            if changed is not None:
                previous_date = changed
            decision_ref = transition.get("decision_ref")
            if not isinstance(decision_ref, str) or f"## {decision_ref} —" not in decisions:
                errors.append(f"{label}: transition decision does not resolve: {decision_ref}")
            if isinstance(to_status, str):
                seen_statuses.append(to_status)
                previous = to_status
        if previous != record.get("status"):
            errors.append(f"{label}: current status differs from status history")
        if history and record.get("status_changed_on") != history[-1].get("changed_on"):
            errors.append(f"{label}: status_changed_on differs from final transition")

        for decision_ref in record.get("decision_refs", []):
            if f"## {decision_ref} —" not in decisions:
                errors.append(f"{label}: decision reference does not resolve: {decision_ref}")
        for evidence_group in ("evidence", "contrary_evidence"):
            for evidence in record.get(evidence_group, []):
                if not isinstance(evidence, dict):
                    continue
                source_ref = evidence.get("source_ref")
                if isinstance(source_ref, str) and source_ref.startswith("repo:"):
                    path = safe_source_path(root, source_ref)
                    if path is None or not path.is_file():
                        errors.append(f"{label}: evidence source does not resolve: {source_ref}")
        for asset in record.get("optional_assets", []):
            if not isinstance(asset, str) or not (root / asset).is_file():
                errors.append(f"{label}: optional asset does not resolve: {asset}")

        status = record.get("status")
        qualifying = [
            item
            for item in record.get("evidence", [])
            if isinstance(item, dict)
            and item.get("evidence_kind")
            in {"architecture_proof", "project_observation"}
            and not is_sentinel(item.get("project_ref"))
            and not is_sentinel(item.get("exact_subject"))
        ]
        if status == "experimental" and not qualifying:
            errors.append(f"{label}: experimental status lacks an exact adopter proof")
        if status in {"recommended", "stable"}:
            independent_projects = {
                str(item.get("project_ref"))
                for item in qualifying
                if item.get("independent_project") is True
            }
            if len(independent_projects) < 2:
                errors.append(
                    f"{label}: {status} status lacks two independent project proofs"
                )
        if status == "stable":
            if "recommended" not in seen_statuses:
                errors.append(f"{label}: stable status did not pass through recommended")
            compatibility = record.get("compatibility", {})
            if not isinstance(compatibility, dict) or compatibility.get(
                "stable_support_commitment"
            ) is not True:
                errors.append(f"{label}: stable status lacks support commitment")
        successor = record.get("successor")
        if successor is not None and successor not in active_records:
            errors.append(f"{label}: successor does not resolve: {successor}")
        if successor == pattern_id:
            errors.append(f"{label}: pattern cannot succeed itself")
        if status == "deprecated" and (
            successor is None or not record.get("deprecation_reason")
        ):
            errors.append(f"{label}: deprecated status lacks reason or successor")
        if status == "rejected" and (
            not record.get("rejection_reason")
            or not record.get("contrary_evidence")
        ):
            errors.append(f"{label}: rejected status lacks retained contrary rationale")

    governed = active_records.get("PAT-0002", {})
    if governed.get("status") not in {"candidate", "reviewed"}:
        errors.append("PAT-0002: catalog admission may not exceed reviewed")
    if governed.get("modules") != [
        "impact",
        "action",
        "mutation_effect",
        "recovery_incident",
    ]:
        errors.append("PAT-0002: governed-change module inventory differs")
    lifecycle = active_records.get("PAT-0001", {})
    if lifecycle.get("status") not in {"candidate", "reviewed"}:
        errors.append("PAT-0001: catalog admission may not exceed reviewed")
    return errors


def validate_pattern_catalog(root: Path = ROOT) -> list[str]:
    try:
        catalog, records = load_catalog_values(root)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"pattern catalog cannot be loaded: {error}"]
    return validate_catalog_values(root, catalog, records)


def validate_information_state_value(root: Path, value: dict[str, Any]) -> list[str]:
    schema = load_json(
        root / "shared/source-contracts/information-state-semantics.schema.json"
    )
    errors = schema_issues(
        value,
        schema,
        "shared/source-contracts/information-state-semantics.json",
    )
    roles = value.get("roles", [])
    names = {
        item.get("name") for item in roles if isinstance(item, dict)
    }
    if names != INFORMATION_ROLES:
        errors.append("information-state semantics: role set is incomplete or expanded")
    for item in roles:
        if not isinstance(item, dict):
            continue
        if item.get("may_grant_action_authority") is not False:
            errors.append(
                f"information-state semantics: {item.get('name')} grants action authority"
            )
        if item.get("may_establish_readiness_by_itself") is not False:
            errors.append(
                f"information-state semantics: {item.get('name')} infers readiness"
            )
        if (
            item.get("information_effect") == "declared_scope_authority_only"
            and item.get("name") != "authoritative"
        ):
            errors.append(
                f"information-state semantics: {item.get('name')} launders information authority"
            )
    return errors


def validate_information_state_contract(root: Path = ROOT) -> list[str]:
    try:
        value = load_json(
            root / "shared/source-contracts/information-state-semantics.json"
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"information-state semantics cannot be loaded: {error}"]
    if not isinstance(value, dict):
        return ["information-state semantics must be an object"]
    errors = validate_information_state_value(root, value)
    dossier = (root / "dossier/SPECIFICATION.md").read_text(encoding="utf-8")
    harness = (root / "harness/SPECIFICATION.md").read_text(encoding="utf-8")
    for role in sorted(INFORMATION_ROLES):
        if f"`{role}`" not in dossier and f"`{role}`" not in harness:
            errors.append(f"canonical documentation lacks semantic role `{role}`")
    if "universal status enum" not in (dossier + harness).casefold():
        errors.append("canonical documentation lacks universal-status-enum exclusion")
    return errors


def validate_context_pack(
    value: dict[str, Any],
    *,
    root: Path = ROOT,
    as_of: datetime,
    intended_consumer: str,
    requested_resources: set[str],
    requested_purpose: str,
    permitted_sensitivities: set[str],
) -> list[str]:
    schema = load_json(
        root / "shared/optional-schemas/context-pack-manifest.schema.json"
    )
    errors = schema_issues(value, schema, "context-pack manifest")
    if errors:
        return errors
    as_of = as_of.astimezone(timezone.utc)
    if value.get("status") != "active":
        errors.append("context-pack manifest: pack is not active")
    consumer = value.get("consumer", {})
    if not isinstance(consumer, dict) or consumer.get("id") != intended_consumer:
        errors.append("context-pack manifest: intended consumer does not match")
    scope = value.get("scope", {})
    if isinstance(scope, dict):
        included = set(scope.get("included_resources", []))
        excluded = set(scope.get("excluded_resources", []))
        if not requested_resources <= included or requested_resources & excluded:
            errors.append("context-pack manifest: requested resources exceed scope")
        maximum_items = scope.get("maximum_items")
        if isinstance(maximum_items, int) and len(requested_resources) > maximum_items:
            errors.append("context-pack manifest: requested resource count exceeds scope")
    sensitivity = value.get("sensitivity")
    if sensitivity not in permitted_sensitivities:
        errors.append("context-pack manifest: sensitivity is not permitted for consumer")
    allowed_use = value.get("allowed_use", {})
    if not isinstance(allowed_use, dict) or requested_purpose not in allowed_use.get(
        "purposes", []
    ):
        errors.append("context-pack manifest: requested purpose is not allowed")

    freshness = value.get("freshness", {})
    retention = value.get("retention", {})
    try:
        created_at = parse_datetime(freshness["created_at"])
        valid_until = parse_datetime(freshness["valid_until"])
        revalidate_after = parse_datetime(freshness["revalidate_after"])
        retain_until = parse_datetime(retention["retain_until"])
    except (KeyError, TypeError, ValueError) as error:
        errors.append(f"context-pack manifest: invalid temporal envelope: {error}")
    else:
        if created_at > as_of or valid_until < as_of:
            errors.append("context-pack manifest: pack is expired or not yet valid")
        if revalidate_after < as_of:
            errors.append("context-pack manifest: pack requires revalidation")
        if not created_at <= revalidate_after <= valid_until:
            errors.append("context-pack manifest: freshness dates are incoherent")
        if retain_until < valid_until or retain_until < as_of:
            errors.append("context-pack manifest: retention ends before valid use")

    revocation = value.get("revocation", {})
    if not isinstance(revocation, dict) or revocation.get("status") != "active":
        errors.append("context-pack manifest: pack is revoked")
    elif any(revocation.get(field) is not None for field in ("revoked_at", "reason")):
        errors.append("context-pack manifest: active revocation envelope is inconsistent")

    seen_source_refs: set[str] = set()
    for index, source in enumerate(value.get("sources", [])):
        if not isinstance(source, dict):
            continue
        source_ref = source.get("source_ref")
        if source_ref in seen_source_refs:
            errors.append(f"context-pack manifest: duplicate source at index {index}")
        if isinstance(source_ref, str):
            seen_source_refs.add(source_ref)
        if is_sentinel(source.get("exact_version_or_digest")):
            errors.append(f"context-pack manifest: source {index} lacks an exact version")
        if source.get("authority_status") in {"stale", "superseded", "unknown"}:
            errors.append(f"context-pack manifest: source {index} is not current enough")
        try:
            observed = parse_datetime(source["observed_at"])
            fresh_until = parse_datetime(source["fresh_until"])
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"context-pack manifest: source {index} time invalid: {error}")
        else:
            if observed > as_of or fresh_until < as_of:
                errors.append(f"context-pack manifest: source {index} is stale")

    budget = value.get("size_budget", {})
    if isinstance(budget, dict) and budget.get("measured", 0) > budget.get("maximum", 0):
        errors.append("context-pack manifest: measured size exceeds budget")
    for field in ("invalidation_triggers", "limitations", "non_proven_implications"):
        if not value.get(field):
            errors.append(f"context-pack manifest: {field} must be explicit")
    if is_sentinel(retention.get("deletion_method") if isinstance(retention, dict) else None):
        errors.append("context-pack manifest: deletion method is unresolved")
    return errors


def validate_architecture_proof(
    value: dict[str, Any], *, root: Path = ROOT
) -> list[str]:
    schema = load_json(root / "patterns/architecture-proof/schema.json")
    errors = schema_issues(value, schema, "architecture proof")
    if errors:
        return errors
    status = value.get("status")
    if status == "template":
        if value.get("conclusion") != "not_assessed":
            errors.append("architecture proof: template cannot contain a conclusion")
        return errors
    if status == "completed":
        if value.get("conclusion") not in {"supported", "unsupported", "inconclusive"}:
            errors.append("architecture proof: completed proof lacks a bounded conclusion")
        for field, item in value.get("subject", {}).items():
            if is_sentinel(item):
                errors.append(f"architecture proof: completed subject {field} is inexact")
        environment = value.get("environment", {})
        for field in ("description", "source_revision"):
            if is_sentinel(environment.get(field)):
                errors.append(f"architecture proof: completed environment {field} is inexact")
        if not environment.get("toolchain_versions") or any(
            is_sentinel(item) for item in environment.get("toolchain_versions", [])
        ):
            errors.append("architecture proof: exact toolchain versions are required")
        for field in ("acceptance_criteria", "stop_criteria", "method", "evidence_refs"):
            if not value.get(field) or any(is_sentinel(item) for item in value.get(field, [])):
                errors.append(f"architecture proof: completed {field} is unresolved")
        cases = value.get("adversarial_cases", [])
        if not cases or any(
            isinstance(item, dict) and item.get("result") == "not_run"
            for item in cases
        ):
            errors.append("architecture proof: completed adversarial cases were not run")
        for item in cases:
            if isinstance(item, dict) and not item.get("evidence_refs"):
                errors.append(
                    "architecture proof: completed adversarial case lacks evidence"
                )
        cleanup = value.get("cleanup_or_rollback", {})
        cleanup_status = cleanup.get("status") if isinstance(cleanup, dict) else None
        if cleanup_status in {"not_assessed", "planned"}:
            errors.append("architecture proof: cleanup or rollback is incomplete")
        if cleanup_status == "completed" and not cleanup.get("evidence_refs"):
            errors.append("architecture proof: completed cleanup lacks evidence")
        if cleanup_status == "failed" and not cleanup.get("residual_effects"):
            errors.append("architecture proof: failed cleanup lacks residual effects")
        if value.get("conclusion") == "supported" and cleanup_status == "failed":
            errors.append("architecture proof: supported conclusion conflicts with failed cleanup")
        for field in ("limitations", "non_proven_implications"):
            if not value.get(field) or any(is_sentinel(item) for item in value.get(field, [])):
                errors.append(f"architecture proof: completed {field} is missing")
        try:
            created = date.fromisoformat(value["created_on"])
            completed = date.fromisoformat(value["completed_on"])
        except (KeyError, TypeError, ValueError):
            errors.append("architecture proof: completion dates are required")
        else:
            if completed < created:
                errors.append("architecture proof: completion precedes creation")
    return errors


def load_scaffolder(root: Path) -> Any:
    path = (
        root / "skills/octon-project-bootstrap/scripts/scaffold_project.py"
        if (root / "skills/octon-project-bootstrap/scripts/scaffold_project.py").is_file()
        else SKILL_ROOT / "scripts/scaffold_project.py"
    )
    spec = importlib.util.spec_from_file_location("source_contract_scaffolder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load scaffolder: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_generated_inventory_boundaries(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        scaffolder = load_scaffolder(root)
    except RuntimeError as error:
        return [str(error)]
    try:
        policy = scaffolder.load_generation_policy()
    except ValueError as error:
        return [f"generation policy cannot be loaded: {error}"]
    try:
        profiles = tuple(scaffolder.profile_layers(policy))
        diagnostics = scaffolder.generation_policy_diagnostics(policy, profiles)
    except ValueError as error:
        return [f"generation policy diagnostics failed: {error}"]
    for finding in diagnostics.get("findings", []):
        if not isinstance(finding, dict):
            continue
        errors.append(
            "generation inventory drift "
            f"[{finding.get('failure_class')}] {finding.get('rule_id')}: "
            + ", ".join(str(path) for path in finding.get("paths", []))
        )
    for rule in policy.get("rules", []):
        if not isinstance(rule, dict) or rule.get("disposition") != "source_only":
            continue
        try:
            source_only_path = scaffolder.policy_source_path(
                rule.get("source"), f"source-only rule {rule.get('id')}"
            )
        except ValueError as error:
            errors.append(str(error))
            continue
        if not source_only_path.exists():
            errors.append(
                f"source-only rule {rule.get('id')}: source path is missing"
            )
        elif source_only_path.is_symlink():
            errors.append(
                f"source-only rule {rule.get('id')}: source path is a symlink"
            )
    for profile in profiles:
        try:
            templates = scaffolder.collect_templates(profile, policy)
            schemas = scaffolder.schema_outputs(profile, policy)
            scaffolder.validate_generation_boundary(
                profile, templates, schemas, policy
            )
        except ValueError as error:
            errors.append(f"{profile}: {error}")
            continue
        output_paths = {path.as_posix() for path in set(templates) | set(schemas)}
        for output in output_paths:
            if output.startswith("patterns/") or any(
                marker in output for marker in ("architecture-proof", "PAT-000")
            ):
                errors.append(f"{profile}: source-only pattern path entered inventory: {output}")
        for template in templates.values():
            text = template.read_text(encoding="utf-8")
            for marker in SOURCE_ONLY_MARKERS - {"patterns/"}:
                if marker in text:
                    errors.append(
                        f"{profile}: source-only pattern marker {marker!r} entered {template}"
                    )
    artifact_source = load_json(root / "dossier/artifact-types.json")
    for representation in artifact_source.get("representations", []):
        path = representation.get("path") if isinstance(representation, dict) else None
        if isinstance(path, str) and path.startswith("patterns/"):
            errors.append(f"dossier artifact taxonomy generates source pattern path {path}")
    return errors


def validate_decision_governance_fixtures(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    schema_path = root / "shared/schemas/harness-decision-governance.schema.json"
    positive_path = (
        SKILL_ROOT
        / "fixtures/decision-governance/valid/empty-register.json"
    )
    mutations_path = (
        SKILL_ROOT
        / "fixtures/decision-governance/invalid/mutations.json"
    )
    generated_mutations_path = (
        SKILL_ROOT
        / "assets/templates/core/.agent/tests/fixtures/invalid/decision-governance-mutations.json.tmpl"
    )
    try:
        schema = load_json(schema_path)
        positive = load_json(positive_path)
        mutations = load_json(mutations_path)
        generated_mutations = load_json(generated_mutations_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"decision-governance fixtures cannot be loaded: {error}"]

    errors.extend(
        schema_issues(
            positive,
            schema,
            "fixtures/decision-governance/valid/empty-register.json",
        )
    )
    source_entries = mutations.get("mutations") if isinstance(mutations, dict) else None
    generated_entries = (
        generated_mutations.get("mutations")
        if isinstance(generated_mutations, dict)
        else None
    )
    if not isinstance(source_entries, list) or not source_entries:
        errors.append("decision-governance mutation catalog is empty or malformed")
        return errors
    ids: list[str] = []
    expectations: dict[str, str] = {}
    for index, item in enumerate(source_entries):
        if not isinstance(item, dict) or set(item) != {
            "id",
            "operation",
            "expected_diagnostic",
        }:
            errors.append(
                f"decision-governance mutation {index} requires exactly id, operation, and expected_diagnostic"
            )
            continue
        fixture_id = item.get("id")
        operation = item.get("operation")
        expected = item.get("expected_diagnostic")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (fixture_id, operation, expected)
        ):
            errors.append(
                f"decision-governance mutation {index} contains an empty field"
            )
            continue
        ids.append(fixture_id)
        expectations[fixture_id] = expected
    if len(ids) != len(set(ids)):
        errors.append("decision-governance mutation IDs must be unique")
    generated_expectations = {
        item.get("id"): item.get("expected_diagnostic")
        for item in generated_entries or []
        if isinstance(item, dict)
    }
    if generated_expectations != expectations:
        errors.append(
            "source and generated decision-governance mutation inventories differ"
        )
    return errors


def validate_guided_setup_contracts(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    catalog_path = root / "shared/source-contracts/setup-questions.json"
    catalog_schema_path = root / "shared/source-contracts/setup-questions.schema.json"
    answers_schema_path = root / "shared/schemas/octon-mini-bootstrap-setup-answers.schema.json"
    session_schema_path = root / "shared/schemas/octon-mini-bootstrap-setup-session-v2.schema.json"
    try:
        catalog = load_json(catalog_path)
        catalog_schema = load_json(catalog_schema_path)
        answers_schema = load_json(answers_schema_path)
        session_schema = load_json(session_schema_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"guided setup contracts cannot be loaded: {error}"]
    errors.extend(schema_issues(catalog, catalog_schema, "shared/source-contracts/setup-questions.json"))
    try:
        spec = importlib.util.spec_from_file_location(
            "source_contract_guided_setup",
            SKILL_ROOT / "scripts/setup_session.py",
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load guided setup engine")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.validate_catalog(catalog)
        with tempfile.TemporaryDirectory(prefix="octon-mini-setup-schema-") as temporary:
            target = Path(temporary) / "target"
            target.mkdir()
            session = module.create_session("initialization", target)
            errors.extend(
                schema_issues(
                    session,
                    session_schema,
                    "generated initialization setup session",
                )
            )
    except (OSError, RuntimeError, ValueError) as error:
        errors.append(f"guided setup catalog semantics failed: {error}")
    for path in sorted((SKILL_ROOT / "fixtures/guided-setup/valid").glob("*.json")):
        try:
            value = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{path.relative_to(SKILL_ROOT)} cannot be loaded: {error}")
            continue
        errors.extend(schema_issues(value, answers_schema, str(path.relative_to(SKILL_ROOT))))
    mutation_path = SKILL_ROOT / "fixtures/guided-setup/invalid/mutations.json"
    try:
        mutations = load_json(mutation_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors.append(f"guided setup mutation inventory cannot be loaded: {error}")
        return errors
    if (
        not isinstance(mutations, dict)
        or set(mutations) != {"schema_version", "permission_grant", "mutations", "limitations"}
        or mutations.get("schema_version") != "octon-mini.bootstrap.setup-mutations.v1"
        or mutations.get("permission_grant") is not False
        or not isinstance(mutations.get("mutations"), list)
        or not mutations["mutations"]
    ):
        errors.append("guided setup mutation inventory uses an invalid closed contract")
        return errors
    identifiers: list[str] = []
    for index, item in enumerate(mutations["mutations"]):
        if not isinstance(item, dict) or set(item) != {"id", "operation", "expected_diagnostic"}:
            errors.append(f"guided setup mutation {index} uses an invalid closed contract")
            continue
        if any(not isinstance(item[key], str) or not item[key] for key in item):
            errors.append(f"guided setup mutation {index} has an empty field")
        identifiers.append(item["id"])
    if len(identifiers) != len(set(identifiers)):
        errors.append("guided setup mutation IDs must be unique")
    return errors


def validate_command_capability_catalog(root: Path = ROOT) -> list[str]:
    """Enforce the one authoritative command-to-capability taxonomy."""
    errors: list[str] = []
    try:
        manifest = load_json(root / "shared/source-contracts/commands.json")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"command capability catalog cannot be loaded: {error}"]
    if not isinstance(manifest, dict):
        return ["command capability catalog must be an object"]
    capabilities = manifest.get("capabilities")
    commands = manifest.get("commands")
    if not isinstance(capabilities, list) or not isinstance(commands, list):
        return ["command capability catalog lacks capability or command arrays"]

    capability_ids = [item.get("id") for item in capabilities if isinstance(item, dict)]
    command_names = [item.get("name") for item in commands if isinstance(item, dict)]
    if len(capability_ids) != len(capabilities) or len(capability_ids) != len(set(capability_ids)):
        errors.append("capability IDs must be present and unique")
    if len(command_names) != len(commands) or len(command_names) != len(set(command_names)):
        errors.append("command names must be present and unique")
    capability_index = {
        item["id"]: item
        for item in capabilities
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    references: dict[str, list[dict[str, Any]]] = {identifier: [] for identifier in capability_index}
    for command in commands:
        if not isinstance(command, dict):
            continue
        capability_id = command.get("capability_id")
        if capability_id not in capability_index:
            errors.append(
                f"command {command.get('name')!r} references missing capability {capability_id!r}"
            )
            continue
        references[capability_id].append(command)

    forbidden_names = {
        "Octon Skill",
        "Octon Engine",
        "Octon Manager",
        "Octon Tool",
        "Octon Service",
    }
    for capability_id, capability in capability_index.items():
        if capability.get("display_name") in forbidden_names:
            errors.append(f"capability {capability_id} has a vague brand-only display name")
        if not references.get(capability_id):
            errors.append(f"capability {capability_id} has no command reference")
            continue
        expected_availability = sorted(
            {
                availability
                for command in references[capability_id]
                for availability in command.get("availability", [])
                if isinstance(availability, str)
            }
        )
        if sorted(capability.get("availability", [])) != expected_availability:
            errors.append(
                f"capability {capability_id} availability differs from its commands"
            )
        entries = capability.get("command_entry_points", [])
        for command in references[capability_id]:
            words = str(command.get("name", "")).split(".")
            if not any(
                isinstance(entry, str)
                and entry.split()[1 : 1 + len(words)] == words
                for entry in entries
            ):
                errors.append(
                    f"capability {capability_id} does not expose command {command.get('name')}"
                )
        for implementation in capability.get("implementation_entry_points", []):
            if not isinstance(implementation, str):
                continue
            if implementation.startswith("skills/"):
                source_path = root / implementation
                if not source_path.is_file():
                    skill_prefix = Path("skills/octon-project-bootstrap")
                    try:
                        source_path = SKILL_ROOT / Path(implementation).relative_to(
                            skill_prefix
                        )
                    except ValueError:
                        pass
                if not source_path.is_file():
                    errors.append(
                        f"capability {capability_id} implementation is absent: {implementation}"
                    )
            elif implementation.startswith(".agent/"):
                template = (
                    SKILL_ROOT
                    / "assets/templates/core"
                    / f"{implementation}.tmpl"
                )
                package_templates = sorted(
                    (SKILL_ROOT / "assets/packages").glob(
                        f"*/templates/{implementation}.tmpl"
                    )
                )
                if not template.is_file() and len(package_templates) != 1:
                    errors.append(
                        f"capability {capability_id} generated implementation template is absent: {implementation}"
                    )
            else:
                errors.append(
                    f"capability {capability_id} implementation has an unknown availability boundary: {implementation}"
                )
    return errors


def validate_repository(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    schema_paths = (
        root / "patterns/schemas/pattern-catalog.schema.json",
        root / "patterns/schemas/pattern-record.schema.json",
        root / "patterns/architecture-proof/schema.json",
        root / "shared/source-contracts/information-state-semantics.schema.json",
        root / "shared/source-contracts/profile-manifest.schema.json",
        root / "shared/source-contracts/long-running-work-benchmark-report.schema.json",
        root / "shared/source-contracts/commands.schema.json",
        root / "shared/source-contracts/diagnostic-catalog.schema.json",
        root / "shared/source-contracts/hook-detector-protocol.schema.json",
        root / "shared/source-contracts/setup-questions.schema.json",
        root / "shared/source-contracts/legacy-reference-allowlist.schema.json",
        root / "shared/source-contracts/validation-benchmark-report.schema.json",
        root / "shared/optional-schemas/context-pack-manifest.schema.json",
        root / "shared/schemas/octon-mini-bootstrap-setup-answers.schema.json",
        root / "shared/schemas/octon-mini-bootstrap-setup-session.schema.json",
        root / "shared/schemas/octon-mini-bootstrap-setup-session-v2.schema.json",
        root / "shared/schemas/harness-continuation.schema.json",
        root / "shared/schemas/harness-plan-summary.schema.json",
        root / "shared/schemas/harness-decision-reuse.schema.json",
        root / "shared/schemas/harness-validation-proof.schema.json",
        root / "shared/schemas/harness-transaction-v3.schema.json",
        root / "shared/schemas/harness-diagnostics-v2.schema.json",
        root / "shared/schemas/harness-project-check-evidence-v3.schema.json",
    )
    for path in schema_paths:
        try:
            schema = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{path.relative_to(root)}: cannot load schema: {error}")
            continue
        errors.extend(
            f"{path.relative_to(root)}: {item}" for item in lint_schema(schema)
        )
    errors.extend(validate_pattern_catalog(root))
    errors.extend(validate_information_state_contract(root))
    try:
        generation_policy = load_json(
            root / "shared/source-contracts/profile-manifest.json"
        )
        generation_policy_schema = load_json(
            root / "shared/source-contracts/profile-manifest.schema.json"
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors.append(f"generation policy cannot be loaded: {error}")
    else:
        errors.extend(
            schema_issues(
                generation_policy,
                generation_policy_schema,
                "shared/source-contracts/profile-manifest.json",
            )
        )
    for name in (
        "commands",
        "diagnostic-catalog",
        "hook-detector-protocol",
        "setup-questions",
        "legacy-reference-allowlist",
    ):
        try:
            contract = load_json(root / f"shared/source-contracts/{name}.json")
            schema = load_json(root / f"shared/source-contracts/{name}.schema.json")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"shared/source-contracts/{name}: cannot load contract: {error}")
            continue
        errors.extend(
            schema_issues(
                contract,
                schema,
                f"shared/source-contracts/{name}.json",
            )
        )
    context_fixture = load_json(
        root / "patterns/fixtures/context-pack/valid/active.json"
    )
    errors.extend(
        validate_context_pack(
            context_fixture,
            root=root,
            as_of=datetime(2030, 1, 5, tzinfo=timezone.utc),
            intended_consumer="agent-role:architecture-reviewer",
            requested_resources={
                "project-dossier/canonical/architecture-or-outcome-model.md",
                "project-dossier/provenance/README.md",
            },
            requested_purpose="architecture_review",
            permitted_sensitivities={"internal"},
        )
    )
    proof_paths = sorted(
        (root / "patterns/fixtures/architecture-proof/valid").glob("*.json")
    )
    for path in proof_paths:
        value = load_json(path)
        errors.extend(
            f"{path.relative_to(root)}: {item}"
            for item in validate_architecture_proof(value, root=root)
        )
    template_paths = sorted(
        (root / "patterns/architecture-proof/templates").glob("*.json")
    )
    expected_kinds = {
        "spike",
        "reference_slice",
        "provider_qualification",
        "adversarial_fixture_pack",
        "readiness_evidence",
    }
    observed_kinds: set[str] = set()
    for path in template_paths:
        value = load_json(path)
        observed_kinds.add(value.get("proof_kind"))
        errors.extend(
            f"{path.relative_to(root)}: {item}"
            for item in validate_architecture_proof(value, root=root)
        )
    if observed_kinds != expected_kinds:
        errors.append("architecture-proof templates do not cover the five accepted kinds")
    errors.extend(validate_generated_inventory_boundaries(root))
    errors.extend(validate_decision_governance_fixtures(root))
    errors.extend(validate_guided_setup_contracts(root))
    errors.extend(validate_command_capability_catalog(root))
    return errors


def main() -> int:
    if sys.version_info < (3, 11):
        print("FAIL: Python 3.11+ is required")
        return 2
    errors = validate_repository(ROOT)
    if errors:
        print(f"FAIL: {len(errors)} source-contract issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: source-only architectural contracts are valid")
    print("- pattern records: 3 reviewed, 0 generated or automatically adopted")
    print("- semantic roles: 10 cross-walked without a universal status enum")
    print("- optional contracts: Context Pack v1 and Architecture Proof v1")
    mutation_count = len(
        load_json(
            SKILL_ROOT
            / "fixtures/decision-governance/invalid/mutations.json"
        )["mutations"]
    )
    print(
        f"- decision governance: valid baseline plus {mutation_count} fail-closed mutations"
    )
    print(
        "- profile manifest: v2 source contract with retained explicit allowlists, derived profile projections, "
        "capability-scoped degradation, and strict repository drift validation"
    )
    guided_mutation_count = len(
        load_json(SKILL_ROOT / "fixtures/guided-setup/invalid/mutations.json")["mutations"]
    )
    print(
        f"- guided setup: one catalog, strict session/answer contracts, and {guided_mutation_count} fail-closed mutations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
