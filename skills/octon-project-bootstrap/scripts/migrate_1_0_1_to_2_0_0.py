#!/usr/bin/env python3
"""Deterministic reference migration for Project Blueprint 1.0.1 to 2.0.0.

This tool migrates a closed fixture bundle containing the live v1 task, plan,
lifecycle, project-command, validator, and origin records that changed in v2.
It is deliberately not an in-place target-project upgrader. A real project
must reconcile every legacy relationship and command assessment and supply an
externally grounded migration event before using this transform as part of
its authorized upgrade.

The result keeps v1 bytes and parsed live state as explicitly noncurrent
rollback evidence. Reapplying the migration to a validated result is an exact
no-op. Schema conformance remains distinct from project adoption, authority,
and readiness.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any


FROM_VERSION = "1.0.1"
TO_VERSION = "2.0.0"
GENERATOR_VERSION = "2.0.0"
KERNEL_VERSION = "2.0.0"
INPUT_SCHEMA = "project-blueprint.migration-input.1.0.1-to-2.0.0.v1"
RESULT_SCHEMA = "project-blueprint.migration-result.1.0.1-to-2.0.0.v1"
ROLLBACK_SCHEMA = "project-blueprint.rollback-evidence.1.0.1-to-2.0.0.v1"
CHECK_SCHEMA = "project-blueprint.migration-check.1.0.1-to-2.0.0.v1"
MIGRATION_GUIDE = "migrations/1.0.1-to-2.0.0.md"

AUTHORITY_TEXT = (
    "Generation provenance only; does not grant permission or establish "
    "project facts, decisions, implementation, or readiness."
)
ID4 = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{4}$")
TASK_ID = re.compile(r"^TASK-[0-9]{4}$")
PLAN_ID = re.compile(r"^PLAN-[0-9]{4}$")
GATE_ID = re.compile(r"^GATE-[0-9]{4}$")
EVIDENCE_ID = re.compile(r"^EVD-[0-9]{4}$")
MIGRATION_ID = re.compile(r"^MIG-[0-9]{4}$")
GENERAL_REF = re.compile(
    r"^(?:[A-Z][A-Z0-9]*-[0-9]{4}|(?:authority|external|project-blueprint|repo|url):.+)$"
)
BLOCKING_REF = re.compile(
    r"^(?:TASK|PLAN|GATE|DEC|RISK|ASM|ISSUE|DEP|OQ)-[0-9]{4}$"
)
HEX32 = re.compile(r"^[a-f0-9]{32}$")

TASK_STATUSES = {
    "proposed",
    "ready",
    "in_progress",
    "validating",
    "review",
    "blocked",
    "completed",
    "cancelled",
    "reopened",
}
PLAN_STATUSES = {
    "planned",
    "in_progress",
    "blocked",
    "completed",
    "deferred",
    "cancelled",
}
EXTERNAL_EFFECTS = {
    "not_assessed",
    "none",
    "repository_local",
    "external_reversible",
    "external_irreversible",
}
PROFILE_VALUES = {"minimal", "standard", "high-assurance"}
PLAN_STATUS_VOCABULARY = [
    "planned",
    "in_progress",
    "blocked",
    "completed",
    "deferred",
    "cancelled",
]

TASK_DEPENDENCY_KINDS = {
    "hard_task_dependency",
    "plan_item_ref",
    "gate_ref",
    "blocking_ref",
    "advisory",
}
PLAN_DEPENDENCY_KINDS = {
    "hard_plan_dependency",
    "task_ref",
    "gate_ref",
    "blocking_ref",
    "advisory",
}

V1_LIFECYCLE: dict[str, Any] = {
    "schema_version": "harness.lifecycle.v1",
    "task": {
        "initial": "proposed",
        "terminal": ["completed", "cancelled"],
        "transitions": {
            "proposed": ["ready", "cancelled"],
            "ready": ["in_progress", "cancelled"],
            "in_progress": ["validating", "blocked", "cancelled"],
            "validating": ["in_progress", "review", "blocked"],
            "review": ["in_progress", "completed", "blocked"],
            "blocked": ["in_progress", "cancelled"],
            "completed": ["reopened"],
            "reopened": ["in_progress", "cancelled"],
            "cancelled": [],
        },
        "gates": {
            "ready": [
                "scope",
                "authority_basis",
                "acceptance_criteria",
                "validation_plan",
            ],
            "completed": [
                "acceptance_criteria_met",
                "closure_evidence",
                "limitations_recorded",
                "external_effects_disclosed",
            ],
        },
    },
    "decision": {
        "initial": "proposed",
        "terminal": ["rejected", "superseded", "deprecated"],
        "transitions": {
            "proposed": ["accepted", "rejected"],
            "accepted": ["superseded", "deprecated"],
            "rejected": [],
            "superseded": [],
            "deprecated": [],
        },
        "immutable_meaning_after": "accepted",
        "successor_required_for": [
            "superseded",
            "materially_changed_accepted_decision",
        ],
    },
    "artifact": {
        "initial": "scratch",
        "terminal": ["archived"],
        "transitions": {
            "scratch": ["draft", "archived"],
            "draft": ["reviewed", "archived"],
            "reviewed": ["draft", "approved", "archived"],
            "approved": ["final", "archived"],
            "final": ["archived"],
            "archived": [],
        },
    },
}

V2_LIFECYCLE: dict[str, Any] = copy.deepcopy(V1_LIFECYCLE)
V2_LIFECYCLE["schema_version"] = "harness.lifecycle.v2"
V2_LIFECYCLE["task"]["transitions"] = {
    "proposed": ["ready", "cancelled"],
    "ready": ["in_progress", "blocked", "cancelled"],
    "in_progress": ["validating", "blocked", "cancelled"],
    "validating": ["in_progress", "review", "blocked"],
    "review": ["in_progress", "completed", "blocked"],
    "blocked": ["ready", "cancelled"],
    "completed": ["reopened"],
    "reopened": ["ready", "cancelled"],
    "cancelled": [],
}
V2_LIFECYCLE["task"]["gates"]["ready"] = [
    "scope",
    "authority_basis",
    "acceptance_criteria",
    "validation_plan",
    "dependencies_satisfied",
    "gates_satisfied",
    "blocking_refs_resolved",
    "plan_links_consistent",
]

TASK_V1_KEYS = {
    "schema_version",
    "id",
    "status",
    "previous_status",
    "title",
    "authority_basis",
    "owner",
    "created_at",
    "updated_at",
    "dependencies",
    "scope",
    "acceptance_criteria",
    "validation_plan",
    "implementation_result",
    "review_evidence",
    "blocked_by",
    "reopened_by",
    "acceptance_criteria_met",
    "closure_evidence",
    "external_effects",
    "limitations",
}
PLAN_ITEM_V1_KEYS = {
    "id",
    "title",
    "objective",
    "status",
    "owner_role",
    "depends_on",
    "requirement_refs",
    "finding_refs",
    "gate_refs",
    "acceptance_criteria",
    "evidence_expected",
    "evidence_refs",
    "blocked_by",
    "limitations",
}
PLAN_STORE_KEYS = {
    "schema_version",
    "document_role",
    "permission_grant",
    "project_slug",
    "scaffold_generated_on",
    "review",
    "status_vocabulary",
    "plan_items",
}
ORIGIN_KEYS = {
    "schema_version",
    "blueprint",
    "blueprint_version",
    "generator_version",
    "generation_id",
    "profile",
    "generated_on",
    "project_name",
    "project_slug",
    "harness_kernel_version",
    "authority",
    "initial_generation",
    "migration_history",
    "generated_paths",
}
MIGRATION_KEYS = {
    "schema_version",
    "id",
    "from_blueprint_version",
    "to_blueprint_version",
    "generator_version",
    "migrated_on",
    "from_profile",
    "to_profile",
    "migration_guide",
    "authority_source",
    "evidence_refs",
    "limitations",
}
TASK_MAPPING_KEYS = {
    "dependencies",
    "additional_plan_item_refs",
    "additional_gate_refs",
    "additional_blocking_refs",
}
PLAN_MAPPING_KEYS = {
    "depends_on",
    "additional_task_refs",
    "additional_gate_refs",
    "additional_blocking_refs",
}
PROJECT_HOOKS = (
    "project_test",
    "project_lint",
    "project_build",
    "project_closure",
)
PROJECT_V1_KEYS = {
    "schema_version",
    "project",
    "paths",
    "commands",
    "extensions",
    "mutable_work_status",
}
PROJECT_IDENTITY_KEYS = {
    "id",
    "name",
    "repository_root",
    "profile",
    "blueprint_version",
    "adoption_status",
    "adoption_decision_ref",
}
PROJECT_PATH_KEYS = {
    "source",
    "tests",
    "generated",
    "instruction_roots",
    "fingerprint_exclusions",
}
PROJECT_COMMAND_V2_KEYS = {
    "status",
    "owner",
    "rationale",
    "tool_name",
    "argv",
    "version_argv",
    "timeout_seconds",
    "evidence_freshness_days",
    "side_effects",
}
PROJECT_COMMAND_MAPPING_KEYS = {"action", "assessment"}
VALIDATORS_KEYS = {
    "schema_version",
    "validator_version",
    "runtime",
    "commands",
    "required_core_checks",
    "limitations",
}
V1_VALIDATOR_COMMANDS = {
    "bootstrap": {"run": "python --version", "writes": []},
    "check": {
        "run": "python -B .agent/scripts/validate.py --check",
        "writes": [],
    },
    "test": {
        "run": (
            "python -B -m unittest discover -s .agent/tests -p \"test_*.py\""
        ),
        "writes": [],
    },
    "closure": {
        "run": "configure_during_project_adoption",
        "writes": "not_assessed",
    },
}
V2_FIXED_VALIDATOR_COMMANDS = {
    "bootstrap": copy.deepcopy(V1_VALIDATOR_COMMANDS["bootstrap"]),
    "check": copy.deepcopy(V1_VALIDATOR_COMMANDS["check"]),
    "ready_frontier": {
        "run": "python -B .agent/scripts/validate.py --ready-frontier",
        "writes": [],
    },
    "test": copy.deepcopy(V1_VALIDATOR_COMMANDS["test"]),
    "project_checks": {
        "run": (
            "python -B .agent/scripts/run_project_checks.py "
            "--write-evidence"
        ),
        "writes": [".agent/project-checks/evidence.json"],
    },
    "adoption_verify": {
        "run": (
            "python -B .agent/scripts/run_project_checks.py "
            "--write-evidence --verify-adoption"
        ),
        "writes": "project_check_evidence_and_profile_refresh_outputs",
    },
    "closure": copy.deepcopy(V1_VALIDATOR_COMMANDS["closure"]),
}
V1_REQUIRED_CORE_CHECKS = [
    "python_runtime_floor",
    "strict_json_and_duplicate_keys",
    "schemas_and_versions",
    "authority_and_nested_instruction_invariants",
    "identifiers_references_and_lifecycles",
    "dossier_catalog_path_authority_and_traceability",
    "extension_compatibility_confinement_and_validator_protocol",
    "unresolved_generation_placeholders",
    "redacted_secret_detection",
    "repository_symlinks_and_host_metadata",
    "generated_integrity_freshness_when_present",
]
V2_REQUIRED_CORE_CHECKS = [
    "python_runtime_floor",
    "strict_json_and_duplicate_keys",
    "schemas_and_versions",
    "authority_and_nested_instruction_invariants",
    "identifiers_references_and_lifecycles",
    "dependency_readiness_and_ready_frontier",
    "project_command_assessment_and_current_evidence",
    "dossier_catalog_path_authority_and_traceability",
    "extension_compatibility_confinement_and_validator_protocol",
    "unresolved_generation_placeholders",
    "redacted_secret_detection",
    "repository_symlinks_and_host_metadata",
    "generated_integrity_freshness_when_present",
]
VALIDATOR_LIMITATIONS = [
    "structural_checks_do_not_prove_project_readiness",
    "repository_policy_is_not_runtime_sandbox_enforcement",
]
PROJECT_CHECKS_CONTRACT = {
    "evidence_schema": ".agent/schemas/harness-project-check-evidence.schema.json",
    "evidence_store": ".agent/project-checks/evidence.json",
    "writer_argv": [
        "python",
        "-B",
        ".agent/scripts/run_project_checks.py",
        "--write-evidence",
    ],
    "adoption_verification_argv": [
        "python",
        "-B",
        ".agent/scripts/run_project_checks.py",
        "--write-evidence",
        "--verify-adoption",
    ],
    "execution": "explicit_writer_only",
    "shell_interpretation": False,
}
SHELL_EXECUTABLES = {
    "bash",
    "cmd",
    "cmd.exe",
    "dash",
    "fish",
    "ksh",
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
    "sh",
    "zsh",
}
INLINE_SHELL_FLAGS = {"-c", "/c", "-command", "-encodedcommand"}

MIGRATION_CONTRACT = {
    "from_blueprint_version": FROM_VERSION,
    "to_blueprint_version": TO_VERSION,
    "live_authority_version": TO_VERSION,
    "rollback_state_role": "noncurrent_evidence_only",
    "authority_effect": "none",
    "readiness_claim": False,
    "in_place_mutation_supported": False,
    "advisory_relationships_affect_readiness": False,
    "legacy_project_command_strings_interpreted": False,
    "project_checks_executed": False,
}
RESULT_LIMITATIONS = [
    (
        "This reference transform covers task, plan, lifecycle, project, "
        "validator, and origin records only; full target-project "
        "reconciliation and validation remain project-owned."
    ),
    (
        "Schema-valid migrated records do not establish project adoption, "
        "authority, approval, or readiness."
    ),
    (
        "Rollback output contains an exact copy of the input bytes and must "
        "inherit the input's access and retention controls."
    ),
    (
        "Legacy command strings are never parsed or executed; configured "
        "hooks require a complete explicit v2 assessment."
    ),
    "Rollback evidence is noncurrent evidence and does not itself authorize restoration.",
]


class MigrationError(ValueError):
    """Raised when migration input is invalid, ambiguous, or unsafe."""


class DuplicateKeyError(MigrationError):
    """Raised when strict JSON contains a duplicate object key."""


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_json_constant(value: str) -> None:
    raise MigrationError(f"non-finite JSON number is prohibited: {value}")


def parse_json_bytes(raw: bytes, location: str) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise MigrationError(f"{location}: expected UTF-8: {error}") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=strict_object,
            parse_constant=reject_json_constant,
        )
    except (json.JSONDecodeError, DuplicateKeyError, MigrationError) as error:
        raise MigrationError(f"{location}: invalid strict JSON: {error}") from error
    if not isinstance(value, dict):
        raise MigrationError(f"{location}: top-level value must be an object")
    return value


def load_json_document(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise MigrationError(f"cannot read {path}: {error}") from error
    return parse_json_bytes(raw, str(path)), raw


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise MigrationError(f"value is not strict JSON: {error}") from error


def pretty_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
    except (TypeError, ValueError) as error:
        raise MigrationError(f"value is not strict JSON: {error}") from error
    return (text + "\n").encode("utf-8")


def digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def expect_object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MigrationError(f"{location}: expected an object")
    return value


def require_exact_keys(
    value: dict[str, Any], expected: set[str], location: str
) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unknown:
            details.append("unknown " + ", ".join(unknown))
        raise MigrationError(f"{location}: closed shape violation ({'; '.join(details)})")


def expect_nonempty_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MigrationError(f"{location}: expected a nonempty string")
    return value


def expect_nullable_string(value: Any, location: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise MigrationError(f"{location}: expected string or null")
    return value


def expect_date(value: Any, location: str) -> str:
    text = expect_nonempty_string(value, location)
    try:
        date.fromisoformat(text)
    except ValueError as error:
        raise MigrationError(f"{location}: expected an ISO date") from error
    return text


def expect_string_array(
    value: Any,
    location: str,
    *,
    pattern: re.Pattern[str] | None = None,
    nonempty_items: bool = True,
) -> list[str]:
    if not isinstance(value, list):
        raise MigrationError(f"{location}: expected an array")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or (nonempty_items and not item):
            raise MigrationError(f"{location}[{index}]: expected a nonempty string")
        if pattern is not None and not pattern.fullmatch(item):
            raise MigrationError(
                f"{location}[{index}]: value does not match {pattern.pattern}"
            )
        result.append(item)
    if len(result) != len(set(result)):
        raise MigrationError(f"{location}: array entries must be unique")
    return result


def validate_task_transition(
    task: dict[str, Any], lifecycle: dict[str, Any], location: str
) -> None:
    graph = lifecycle["task"]["transitions"]
    initial = lifecycle["task"]["initial"]
    status = task["status"]
    previous = task["previous_status"]
    if previous is None:
        if status != initial:
            raise MigrationError(
                f"{location}: noninitial status requires previous_status"
            )
        return
    if previous not in graph or status not in graph[previous]:
        raise MigrationError(
            f"{location}: illegal task transition {previous!r} -> {status!r}"
        )


def blueprint_root() -> Path:
    skill_root = Path(__file__).resolve().parents[1]
    candidates = (
        Path(__file__).resolve().parents[3],
        skill_root / "assets" / "octon-source",
    )
    for candidate in candidates:
        if (candidate / "VERSION").is_file() and (
            candidate / "shared" / "schemas"
        ).is_dir():
            return candidate
    raise MigrationError("cannot locate the Project Blueprint schema bundle")


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
        raise MigrationError(f"unsupported non-local schema reference: {reference}")
    current: Any = root_schema
    for part in reference[2:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or key not in current:
            raise MigrationError(f"unresolved schema reference: {reference}")
        current = current[key]
    if not isinstance(current, dict):
        raise MigrationError(
            f"schema reference does not resolve to an object: {reference}"
        )
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
        except MigrationError as error:
            return [f"{path}: {error}"]
        return validate_schema(value, resolved, path, root_schema=root_schema)

    errors: list[str] = []
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
        if len(value) < schema.get("minProperties", 0):
            errors.append(f"{path}: object has too few properties")
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


def load_current_schema(filename: str) -> dict[str, Any]:
    path = blueprint_root() / "shared" / "schemas" / filename
    value, _ = load_json_document(path)
    return value


def validate_v1_task(task: Any, location: str) -> dict[str, Any]:
    value = expect_object(task, location)
    require_exact_keys(value, TASK_V1_KEYS, location)
    if value["schema_version"] != "harness.task.v1":
        if value["schema_version"] == "harness.task.v2":
            raise MigrationError(
                f"{location}: mixed live v1/v2 authority is prohibited"
            )
        raise MigrationError(f"{location}.schema_version: expected harness.task.v1")
    if not isinstance(value["id"], str) or not TASK_ID.fullmatch(value["id"]):
        raise MigrationError(f"{location}.id: invalid task ID")
    if value["status"] not in TASK_STATUSES:
        raise MigrationError(f"{location}.status: unknown task status")
    previous = expect_nullable_string(value["previous_status"], f"{location}.previous_status")
    if previous is not None and previous not in TASK_STATUSES:
        raise MigrationError(f"{location}.previous_status: unknown task status")
    for field in ("title", "authority_basis", "owner", "scope"):
        expect_nonempty_string(value[field], f"{location}.{field}")
    expect_date(value["created_at"], f"{location}.created_at")
    expect_date(value["updated_at"], f"{location}.updated_at")
    expect_string_array(
        value["dependencies"], f"{location}.dependencies", pattern=GENERAL_REF
    )
    for field in (
        "acceptance_criteria",
        "validation_plan",
        "blocked_by",
        "limitations",
    ):
        expect_string_array(value[field], f"{location}.{field}")
    for field in ("review_evidence", "closure_evidence"):
        expect_string_array(value[field], f"{location}.{field}", pattern=GENERAL_REF)
    expect_nullable_string(value["implementation_result"], f"{location}.implementation_result")
    reopened = expect_nullable_string(value["reopened_by"], f"{location}.reopened_by")
    if reopened is not None and not EVIDENCE_ID.fullmatch(reopened):
        raise MigrationError(f"{location}.reopened_by: expected EVD-#### or null")
    if not isinstance(value["acceptance_criteria_met"], bool):
        raise MigrationError(f"{location}.acceptance_criteria_met: expected boolean")
    if value["external_effects"] not in EXTERNAL_EFFECTS:
        raise MigrationError(f"{location}.external_effects: unknown value")
    validate_task_transition(value, V1_LIFECYCLE, location)
    return value


def validate_review(value: Any, location: str) -> None:
    review = expect_object(value, location)
    require_exact_keys(review, {"status", "last_reviewed_on", "basis"}, location)
    if review["status"] not in {
        "not_reviewed",
        "reviewed",
        "stale",
        "not_applicable",
    }:
        raise MigrationError(f"{location}.status: unknown review status")
    if review["last_reviewed_on"] is not None:
        expect_date(review["last_reviewed_on"], f"{location}.last_reviewed_on")
    expect_nullable_string(review["basis"], f"{location}.basis")


def validate_v1_plan_item(item: Any, location: str) -> dict[str, Any]:
    value = expect_object(item, location)
    require_exact_keys(value, PLAN_ITEM_V1_KEYS, location)
    if not isinstance(value["id"], str) or not PLAN_ID.fullmatch(value["id"]):
        raise MigrationError(f"{location}.id: invalid plan ID")
    for field in ("title", "objective", "owner_role"):
        expect_nonempty_string(value[field], f"{location}.{field}")
    if value["status"] not in PLAN_STATUSES:
        raise MigrationError(f"{location}.status: unknown plan status")
    for field in (
        "depends_on",
        "requirement_refs",
        "finding_refs",
        "evidence_refs",
    ):
        expect_string_array(value[field], f"{location}.{field}", pattern=GENERAL_REF)
    expect_string_array(value["gate_refs"], f"{location}.gate_refs", pattern=GATE_ID)
    for field in (
        "acceptance_criteria",
        "evidence_expected",
        "blocked_by",
        "limitations",
    ):
        expect_string_array(value[field], f"{location}.{field}")
    return value


def validate_v1_plan_store(plan: Any) -> dict[str, Any]:
    value = expect_object(plan, "$.live.plan")
    require_exact_keys(value, PLAN_STORE_KEYS, "$.live.plan")
    if value["schema_version"] != "project.dossier.plan.v1":
        if value["schema_version"] == "project.dossier.plan.v2":
            raise MigrationError(
                "$.live.plan: mixed live v1/v2 authority is prohibited"
            )
        raise MigrationError(
            "$.live.plan.schema_version: expected project.dossier.plan.v1"
        )
    expect_nonempty_string(value["document_role"], "$.live.plan.document_role")
    if value["permission_grant"] is not False:
        raise MigrationError("$.live.plan.permission_grant: must be false")
    expect_nonempty_string(value["project_slug"], "$.live.plan.project_slug")
    expect_date(value["scaffold_generated_on"], "$.live.plan.scaffold_generated_on")
    validate_review(value["review"], "$.live.plan.review")
    if value["status_vocabulary"] != PLAN_STATUS_VOCABULARY:
        raise MigrationError(
            "$.live.plan.status_vocabulary: v1 vocabulary differs from the 1.0.1 contract"
        )
    if not isinstance(value["plan_items"], list):
        raise MigrationError("$.live.plan.plan_items: expected an array")
    ids: list[str] = []
    for index, item in enumerate(value["plan_items"]):
        record = validate_v1_plan_item(item, f"$.live.plan.plan_items[{index}]")
        ids.append(record["id"])
    if len(ids) != len(set(ids)):
        raise MigrationError("$.live.plan.plan_items: duplicate plan ID")
    return value


def validate_portable_relative_path(value: Any, location: str) -> str:
    text = expect_nonempty_string(value, location)
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or "\\" in text
        or text in {".", ".."}
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise MigrationError(f"{location}: expected a confined relative path")
    return path.as_posix()


def validate_v1_project(project: Any) -> dict[str, Any]:
    value = expect_object(project, "$.live.project")
    require_exact_keys(value, PROJECT_V1_KEYS, "$.live.project")
    if value["schema_version"] != "harness.project.v1":
        if value["schema_version"] == "harness.project.v2":
            raise MigrationError(
                "$.live.project: mixed live v1/v2 authority is prohibited"
            )
        raise MigrationError(
            "$.live.project.schema_version: expected harness.project.v1"
        )
    identity = expect_object(value["project"], "$.live.project.project")
    require_exact_keys(identity, PROJECT_IDENTITY_KEYS, "$.live.project.project")
    for field in ("id", "name"):
        expect_nonempty_string(identity[field], f"$.live.project.project.{field}")
    if identity["repository_root"] != ".":
        raise MigrationError("$.live.project.project.repository_root: must be '.'")
    if identity["profile"] not in PROFILE_VALUES:
        raise MigrationError("$.live.project.project.profile: invalid profile")
    if identity["blueprint_version"] != FROM_VERSION:
        if identity["blueprint_version"] == TO_VERSION:
            raise MigrationError(
                "$.live.project: mixed live v1/v2 authority is prohibited"
            )
        raise MigrationError(
            f"$.live.project.project.blueprint_version: expected {FROM_VERSION}"
        )
    if identity["adoption_status"] not in {
        "not_assessed",
        "in_progress",
        "adopted",
        "superseded",
    }:
        raise MigrationError("$.live.project.project.adoption_status: invalid")
    decision = identity["adoption_decision_ref"]
    if decision is not None and (
        not isinstance(decision, str)
        or not re.fullmatch(r"^DEC-[0-9]{4}$", decision)
    ):
        raise MigrationError(
            "$.live.project.project.adoption_decision_ref: invalid"
        )
    if identity["adoption_status"] in {"not_assessed", "in_progress"}:
        if decision is not None:
            raise MigrationError(
                "$.live.project.project: pre-adoption status requires a null "
                "adoption decision"
            )
    elif decision is None:
        raise MigrationError(
            "$.live.project.project: adopted/superseded status requires a decision"
        )

    paths = expect_object(value["paths"], "$.live.project.paths")
    require_exact_keys(paths, PROJECT_PATH_KEYS, "$.live.project.paths")
    for field in ("source", "tests", "generated", "instruction_roots"):
        entries = expect_string_array(
            paths[field], f"$.live.project.paths.{field}"
        )
        for index, entry in enumerate(entries):
            validate_portable_relative_path(
                entry, f"$.live.project.paths.{field}[{index}]"
            )
    exclusions = paths["fingerprint_exclusions"]
    if not isinstance(exclusions, list):
        raise MigrationError(
            "$.live.project.paths.fingerprint_exclusions: expected an array"
        )
    for index, raw in enumerate(exclusions):
        location = f"$.live.project.paths.fingerprint_exclusions[{index}]"
        exclusion = expect_object(raw, location)
        require_exact_keys(exclusion, {"path", "reason"}, location)
        validate_portable_relative_path(exclusion["path"], f"{location}.path")
        expect_nonempty_string(exclusion["reason"], f"{location}.reason")

    commands = expect_object(value["commands"], "$.live.project.commands")
    require_exact_keys(commands, set(PROJECT_HOOKS), "$.live.project.commands")
    for hook in PROJECT_HOOKS:
        location = f"$.live.project.commands.{hook}"
        command = expect_object(commands[hook], location)
        require_exact_keys(command, {"status", "run"}, location)
        if command["status"] not in {"not_assessed", "configured"}:
            raise MigrationError(f"{location}.status: invalid v1 command status")
        run = command["run"]
        if command["status"] == "not_assessed":
            if run is not None:
                raise MigrationError(
                    f"{location}: not_assessed v1 hook requires run=null"
                )
        else:
            expect_nonempty_string(run, f"{location}.run")

    extensions = expect_object(value["extensions"], "$.live.project.extensions")
    require_exact_keys(
        extensions,
        {"registry", "registry_required_in_profile"},
        "$.live.project.extensions",
    )
    if extensions != {
        "registry": ".agent/extensions/registry.json",
        "registry_required_in_profile": "standard_or_higher",
    }:
        raise MigrationError("$.live.project.extensions: v1 contract changed")
    if value["mutable_work_status"] != "prohibited_here":
        raise MigrationError("$.live.project.mutable_work_status: invalid")
    return value


def validate_validator_command(value: Any, location: str) -> dict[str, Any]:
    command = expect_object(value, location)
    require_exact_keys(command, {"run", "writes"}, location)
    expect_nonempty_string(command["run"], f"{location}.run")
    writes = command["writes"]
    if isinstance(writes, str):
        expect_nonempty_string(writes, f"{location}.writes")
    else:
        expect_string_array(writes, f"{location}.writes")
    return command


def validate_v1_validators(validators: Any) -> dict[str, Any]:
    value = expect_object(validators, "$.live.validators")
    require_exact_keys(value, VALIDATORS_KEYS, "$.live.validators")
    if value["schema_version"] != "harness.validators.v1":
        if value["schema_version"] == "harness.validators.v2":
            raise MigrationError(
                "$.live.validators: mixed live v1/v2 authority is prohibited"
            )
        raise MigrationError(
            "$.live.validators.schema_version: expected harness.validators.v1"
        )
    if value["validator_version"] != FROM_VERSION:
        raise MigrationError(
            f"$.live.validators.validator_version: expected {FROM_VERSION}"
        )
    runtime = expect_object(value["runtime"], "$.live.validators.runtime")
    expected_runtime = {
        "executable": "python",
        "minimum_version": "3.11",
        "dependencies": "standard_library_only",
        "bytecode_and_cache_writes": "prohibited_for_check",
    }
    if runtime != expected_runtime:
        raise MigrationError("$.live.validators.runtime: v1 runtime contract changed")
    commands = expect_object(value["commands"], "$.live.validators.commands")
    require_exact_keys(
        commands,
        {"bootstrap", "check", "test", "refresh", "closure"},
        "$.live.validators.commands",
    )
    for name, expected in V1_VALIDATOR_COMMANDS.items():
        actual = validate_validator_command(
            commands[name], f"$.live.validators.commands.{name}"
        )
        if actual != expected:
            raise MigrationError(
                f"$.live.validators.commands.{name}: v1 command changed"
            )
    refresh = validate_validator_command(
        commands["refresh"], "$.live.validators.commands.refresh"
    )
    if refresh["run"] != "python -B .agent/scripts/refresh.py --refresh":
        raise MigrationError(
            "$.live.validators.commands.refresh.run: v1 command changed"
        )
    if not isinstance(refresh["writes"], list):
        raise MigrationError(
            "$.live.validators.commands.refresh.writes: expected a path array"
        )
    for index, item in enumerate(refresh["writes"]):
        validate_portable_relative_path(
            item, f"$.live.validators.commands.refresh.writes[{index}]"
        )
    if value["required_core_checks"] != V1_REQUIRED_CORE_CHECKS:
        raise MigrationError(
            "$.live.validators.required_core_checks: v1 contract changed"
        )
    if value["limitations"] != VALIDATOR_LIMITATIONS:
        raise MigrationError("$.live.validators.limitations: v1 contract changed")
    return value


def project_argv_is_safe(value: Any) -> bool:
    return (
        isinstance(value, list)
        and 1 <= len(value) <= 128
        and all(
            isinstance(item, str)
            and bool(item.strip())
            and not any(
                ord(character) < 32 or ord(character) == 127
                for character in item
            )
            for item in value
        )
    )


def project_argv_uses_inline_shell(value: list[str]) -> bool:
    executable = PurePosixPath(value[0].replace("\\", "/")).name.lower()
    return executable in SHELL_EXECUTABLES and any(
        item.lower() in INLINE_SHELL_FLAGS for item in value[1:]
    )


def validate_v2_project_command(value: Any, location: str) -> dict[str, Any]:
    command = expect_object(value, location)
    require_exact_keys(command, PROJECT_COMMAND_V2_KEYS, location)
    side_effects = expect_object(command["side_effects"], f"{location}.side_effects")
    require_exact_keys(
        side_effects,
        {"classification", "repository_write_paths", "external_effects"},
        f"{location}.side_effects",
    )
    writes = expect_string_array(
        side_effects["repository_write_paths"],
        f"{location}.side_effects.repository_write_paths",
    )
    external = expect_string_array(
        side_effects["external_effects"],
        f"{location}.side_effects.external_effects",
    )
    for index, item in enumerate(writes):
        normalized = validate_portable_relative_path(
            item, f"{location}.side_effects.repository_write_paths[{index}]"
        )
        if normalized in {
            ".git",
            ".agent",
            ".agents",
            "project-dossier",
            "AGENTS.md",
            ".project-blueprint-origin.json",
        } or normalized.startswith(
            (".git/", ".agent/", ".agents/", "project-dossier/")
        ):
            raise MigrationError(
                f"{location}: project checks may not declare governance writes"
            )

    status = command["status"]
    classification = side_effects["classification"]
    if status == "configured":
        for field in ("owner", "tool_name"):
            expect_nonempty_string(command[field], f"{location}.{field}")
        rationale = command["rationale"]
        if rationale is not None:
            expect_nonempty_string(rationale, f"{location}.rationale")
        for field in ("argv", "version_argv"):
            argv = command[field]
            if not project_argv_is_safe(argv):
                raise MigrationError(
                    f"{location}.{field}: configured hook requires safe argv"
                )
            if project_argv_uses_inline_shell(argv):
                raise MigrationError(
                    f"{location}.{field}: inline shell interpretation is prohibited"
                )
        if command["argv"][0] != command["version_argv"][0]:
            raise MigrationError(
                f"{location}: version probe must use the configured executable"
            )
        for field, lower, upper in (
            ("timeout_seconds", 1, 86400),
            ("evidence_freshness_days", 1, 365),
        ):
            number = command[field]
            if (
                not isinstance(number, int)
                or isinstance(number, bool)
                or not lower <= number <= upper
            ):
                raise MigrationError(f"{location}.{field}: out of bounds")
        if classification == "read_only" and (writes or external):
            raise MigrationError(
                f"{location}: read_only hook cannot declare writes/effects"
            )
        if classification == "repository_writes" and (not writes or external):
            raise MigrationError(
                f"{location}: repository_writes requires paths and no external effects"
            )
        if classification == "external_effects_possible" and not external:
            raise MigrationError(
                f"{location}: external_effects_possible requires declarations"
            )
        if classification not in {
            "read_only",
            "repository_writes",
            "external_effects_possible",
        }:
            raise MigrationError(f"{location}: invalid configured side-effect class")
    elif status == "not_applicable":
        expect_nonempty_string(command["owner"], f"{location}.owner")
        expect_nonempty_string(command["rationale"], f"{location}.rationale")
        for field in (
            "tool_name",
            "argv",
            "version_argv",
            "timeout_seconds",
            "evidence_freshness_days",
        ):
            if command[field] is not None:
                raise MigrationError(
                    f"{location}: not_applicable requires {field}=null"
                )
        if classification != "not_applicable" or writes or external:
            raise MigrationError(f"{location}: not_applicable side effects incoherent")
    elif status == "not_assessed":
        for field in (
            "owner",
            "rationale",
            "tool_name",
            "argv",
            "version_argv",
            "timeout_seconds",
            "evidence_freshness_days",
        ):
            if command[field] is not None:
                raise MigrationError(
                    f"{location}: not_assessed requires {field}=null"
                )
        if classification != "not_assessed" or writes or external:
            raise MigrationError(f"{location}: not_assessed side effects incoherent")
    else:
        raise MigrationError(f"{location}.status: unknown assessment status")
    return command


def validate_v2_project_output(project: Any) -> dict[str, Any]:
    """Validate the historical v2 project contract without mutable v3 schemas."""
    value = expect_object(project, "$.live.project")
    require_exact_keys(
        value,
        PROJECT_V1_KEYS | {"project_checks"},
        "$.live.project",
    )
    if value["schema_version"] != "harness.project.v2":
        raise MigrationError(
            "$.live.project.schema_version: expected harness.project.v2"
        )
    identity = expect_object(value["project"], "$.live.project.project")
    require_exact_keys(identity, PROJECT_IDENTITY_KEYS, "$.live.project.project")
    for field in ("id", "name"):
        expect_nonempty_string(identity[field], f"$.live.project.project.{field}")
    if identity["repository_root"] != ".":
        raise MigrationError("$.live.project.project.repository_root: must be '.'")
    if identity["profile"] not in PROFILE_VALUES:
        raise MigrationError("$.live.project.project.profile: invalid profile")
    if identity["blueprint_version"] != TO_VERSION:
        raise MigrationError(
            f"$.live.project.project.blueprint_version: expected {TO_VERSION}"
        )
    if identity["adoption_status"] not in {
        "not_assessed",
        "in_progress",
        "adopted",
        "superseded",
    }:
        raise MigrationError("$.live.project.project.adoption_status: invalid")
    decision = identity["adoption_decision_ref"]
    if decision is not None and (
        not isinstance(decision, str)
        or not re.fullmatch(r"^DEC-[0-9]{4}$", decision)
    ):
        raise MigrationError(
            "$.live.project.project.adoption_decision_ref: invalid"
        )
    if identity["adoption_status"] in {"not_assessed", "in_progress"}:
        if decision is not None:
            raise MigrationError(
                "$.live.project.project: pre-adoption status requires a null "
                "adoption decision"
            )
    elif decision is None:
        raise MigrationError(
            "$.live.project.project: adopted/superseded status requires a decision"
        )

    paths = expect_object(value["paths"], "$.live.project.paths")
    require_exact_keys(paths, PROJECT_PATH_KEYS, "$.live.project.paths")
    for field in ("source", "tests", "generated", "instruction_roots"):
        entries = expect_string_array(paths[field], f"$.live.project.paths.{field}")
        for index, entry in enumerate(entries):
            validate_portable_relative_path(
                entry,
                f"$.live.project.paths.{field}[{index}]",
            )
    exclusions = paths["fingerprint_exclusions"]
    if not isinstance(exclusions, list):
        raise MigrationError(
            "$.live.project.paths.fingerprint_exclusions: expected an array"
        )
    for index, raw in enumerate(exclusions):
        location = f"$.live.project.paths.fingerprint_exclusions[{index}]"
        exclusion = expect_object(raw, location)
        require_exact_keys(exclusion, {"path", "reason"}, location)
        validate_portable_relative_path(exclusion["path"], f"{location}.path")
        expect_nonempty_string(exclusion["reason"], f"{location}.reason")

    commands = expect_object(value["commands"], "$.live.project.commands")
    require_exact_keys(commands, set(PROJECT_HOOKS), "$.live.project.commands")
    for hook in PROJECT_HOOKS:
        validate_v2_project_command(
            commands[hook],
            f"$.live.project.commands.{hook}",
        )
    if value["project_checks"] != PROJECT_CHECKS_CONTRACT:
        raise MigrationError("$.live.project.project_checks: v2 contract changed")
    extensions = expect_object(value["extensions"], "$.live.project.extensions")
    require_exact_keys(
        extensions,
        {"registry", "registry_required_in_profile"},
        "$.live.project.extensions",
    )
    if extensions != {
        "registry": ".agent/extensions/registry.json",
        "registry_required_in_profile": "standard_or_higher",
    }:
        raise MigrationError("$.live.project.extensions: v2 contract changed")
    if value["mutable_work_status"] != "prohibited_here":
        raise MigrationError("$.live.project.mutable_work_status: invalid")
    return value


def validate_v2_validators_output(validators: Any) -> dict[str, Any]:
    """Validate the historical v2 validator contract without mutable v3 schemas."""
    value = expect_object(validators, "$.live.validators")
    require_exact_keys(value, VALIDATORS_KEYS, "$.live.validators")
    if (
        value["schema_version"] != "harness.validators.v2"
        or value["validator_version"] != TO_VERSION
    ):
        raise MigrationError(
            "$.live.validators: expected the frozen 2.0.0 validator contract"
        )
    runtime = expect_object(value["runtime"], "$.live.validators.runtime")
    if runtime != {
        "executable": "python",
        "minimum_version": "3.11",
        "dependencies": "standard_library_only",
        "bytecode_and_cache_writes": "prohibited_for_check",
    }:
        raise MigrationError("$.live.validators.runtime: v2 runtime contract changed")
    commands = expect_object(value["commands"], "$.live.validators.commands")
    require_exact_keys(
        commands,
        set(V2_FIXED_VALIDATOR_COMMANDS) | {"refresh"},
        "$.live.validators.commands",
    )
    for name, expected in V2_FIXED_VALIDATOR_COMMANDS.items():
        actual = validate_validator_command(
            commands[name],
            f"$.live.validators.commands.{name}",
        )
        if actual != expected:
            raise MigrationError(
                f"$.live.validators.commands.{name}: v2 command changed"
            )
    refresh = validate_validator_command(
        commands["refresh"],
        "$.live.validators.commands.refresh",
    )
    if refresh["run"] != "python -B .agent/scripts/refresh.py --refresh":
        raise MigrationError(
            "$.live.validators.commands.refresh.run: v2 command changed"
        )
    if not isinstance(refresh["writes"], list):
        raise MigrationError(
            "$.live.validators.commands.refresh.writes: expected a path array"
        )
    for index, item in enumerate(refresh["writes"]):
        validate_portable_relative_path(
            item,
            f"$.live.validators.commands.refresh.writes[{index}]",
        )
    if value["required_core_checks"] != V2_REQUIRED_CORE_CHECKS:
        raise MigrationError(
            "$.live.validators.required_core_checks: v2 contract changed"
        )
    if value["limitations"] != VALIDATOR_LIMITATIONS:
        raise MigrationError("$.live.validators.limitations: v2 contract changed")
    return value


def validate_migration_event(event: Any, origin_profile: str) -> dict[str, Any]:
    value = expect_object(event, "$.migration")
    require_exact_keys(value, MIGRATION_KEYS, "$.migration")
    if value["schema_version"] != "project-blueprint.migration.v1":
        raise MigrationError("$.migration.schema_version: invalid migration schema")
    if not isinstance(value["id"], str) or not MIGRATION_ID.fullmatch(value["id"]):
        raise MigrationError("$.migration.id: invalid migration ID")
    expected_constants = {
        "from_blueprint_version": FROM_VERSION,
        "to_blueprint_version": TO_VERSION,
        "generator_version": GENERATOR_VERSION,
        "migration_guide": MIGRATION_GUIDE,
    }
    for field, expected in expected_constants.items():
        if value[field] != expected:
            raise MigrationError(f"$.migration.{field}: must equal {expected!r}")
    expect_date(value["migrated_on"], "$.migration.migrated_on")
    if value["from_profile"] != origin_profile or value["to_profile"] != origin_profile:
        raise MigrationError(
            "$.migration: profile changes are outside this core migration fixture"
        )
    authority = expect_nonempty_string(
        value["authority_source"], "$.migration.authority_source"
    )
    if not authority.startswith(("authority:", "external:")):
        raise MigrationError(
            "$.migration.authority_source: expected externally grounded "
            "authority: or external: reference"
        )
    evidence = expect_string_array(
        value["evidence_refs"], "$.migration.evidence_refs", pattern=EVIDENCE_ID
    )
    if not evidence:
        raise MigrationError("$.migration.evidence_refs: at least one reference is required")
    expect_string_array(value["limitations"], "$.migration.limitations")
    return value


def validate_origin_history(origin: dict[str, Any], location: str) -> None:
    initial = expect_object(origin["initial_generation"], f"{location}.initial_generation")
    require_exact_keys(
        initial,
        {
            "blueprint_version",
            "generator_version",
            "generation_id",
            "generated_on",
            "profile",
        },
        f"{location}.initial_generation",
    )
    expect_date(initial["generated_on"], f"{location}.initial_generation.generated_on")
    if not isinstance(initial["generation_id"], str) or not HEX32.fullmatch(
        initial["generation_id"]
    ):
        raise MigrationError(f"{location}.initial_generation.generation_id: invalid")
    if initial["profile"] not in PROFILE_VALUES:
        raise MigrationError(f"{location}.initial_generation.profile: invalid")

    history = origin["migration_history"]
    if not isinstance(history, list):
        raise MigrationError(f"{location}.migration_history: expected an array")
    expected_version = initial["blueprint_version"]
    expected_profile = initial["profile"]
    previous_date = initial["generated_on"]
    seen: set[str] = set()
    for index, raw in enumerate(history):
        item_location = f"{location}.migration_history[{index}]"
        item = expect_object(raw, item_location)
        require_exact_keys(item, MIGRATION_KEYS, item_location)
        migration_id = item.get("id")
        if not isinstance(migration_id, str) or not MIGRATION_ID.fullmatch(migration_id):
            raise MigrationError(f"{item_location}.id: invalid migration ID")
        if migration_id in seen:
            raise MigrationError(f"{item_location}.id: duplicate migration ID")
        seen.add(migration_id)
        if item.get("schema_version") != "project-blueprint.migration.v1":
            raise MigrationError(f"{item_location}.schema_version: invalid")
        if item.get("from_blueprint_version") != expected_version:
            raise MigrationError(f"{item_location}: migration version chain is broken")
        if item.get("from_profile") != expected_profile:
            raise MigrationError(f"{item_location}: migration profile chain is broken")
        migrated_on = expect_date(item.get("migrated_on"), f"{item_location}.migrated_on")
        if migrated_on < previous_date:
            raise MigrationError(f"{item_location}: migration dates are not chronological")
        authority = expect_nonempty_string(
            item.get("authority_source"), f"{item_location}.authority_source"
        )
        if not authority.startswith(("authority:", "external:")):
            raise MigrationError(f"{item_location}.authority_source: invalid")
        evidence = expect_string_array(
            item.get("evidence_refs"), f"{item_location}.evidence_refs", pattern=EVIDENCE_ID
        )
        if not evidence:
            raise MigrationError(f"{item_location}.evidence_refs: must not be empty")
        expect_string_array(item.get("limitations"), f"{item_location}.limitations")
        expected_version = item.get("to_blueprint_version")
        expected_profile = item.get("to_profile")
        previous_date = migrated_on
    if expected_version != origin["blueprint_version"]:
        raise MigrationError(f"{location}: migration history does not reach current version")
    if expected_profile != origin["profile"]:
        raise MigrationError(f"{location}: migration history does not reach current profile")
    if history and history[-1]["generator_version"] != origin["generator_version"]:
        raise MigrationError(
            f"{location}: latest migration generator differs from current provenance"
        )
    if not history:
        for field in (
            "blueprint_version",
            "generator_version",
            "generation_id",
            "generated_on",
            "profile",
        ):
            if initial[field] != origin[field]:
                raise MigrationError(
                    f"{location}: initial generation {field} differs without migration history"
                )


def validate_v1_origin(origin: Any) -> dict[str, Any]:
    value = expect_object(origin, "$.live.origin")
    require_exact_keys(value, ORIGIN_KEYS, "$.live.origin")
    # The v1 origin contract is frozen by the exact-key and semantic checks in
    # this migrator. Do not reinterpret historical input through a newer
    # current origin schema after a later Blueprint major release.
    if value["schema_version"] != "project-blueprint.origin.v1":
        raise MigrationError("$.live.origin.schema_version: invalid")
    if value["blueprint"] != "project-blueprint":
        raise MigrationError("$.live.origin.blueprint: invalid")
    if value["blueprint_version"] != FROM_VERSION:
        if value["blueprint_version"] == TO_VERSION:
            raise MigrationError(
                "$.live.origin: mixed live v1/v2 authority is prohibited"
            )
        raise MigrationError(
            f"$.live.origin.blueprint_version: expected {FROM_VERSION}"
        )
    if value["generator_version"] != FROM_VERSION:
        raise MigrationError(
            f"$.live.origin.generator_version: expected {FROM_VERSION}"
        )
    if value["harness_kernel_version"] != FROM_VERSION:
        raise MigrationError(
            f"$.live.origin.harness_kernel_version: expected {FROM_VERSION}"
        )
    if value["authority"] != AUTHORITY_TEXT:
        raise MigrationError("$.live.origin.authority: provenance boundary changed")
    validate_origin_history(value, "$.live.origin")
    return value


def validate_mapping_keys(
    mapping: Any,
    expected_ids: set[str],
    entry_keys: set[str],
    location: str,
) -> dict[str, Any]:
    value = expect_object(mapping, location)
    missing = sorted(expected_ids - set(value))
    unknown = sorted(set(value) - expected_ids)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("missing records " + ", ".join(missing))
        if unknown:
            details.append("unknown records " + ", ".join(unknown))
        raise MigrationError(f"{location}: classification coverage mismatch ({'; '.join(details)})")
    for record_id, raw in value.items():
        entry = expect_object(raw, f"{location}.{record_id}")
        require_exact_keys(entry, entry_keys, f"{location}.{record_id}")
    return value


def validate_dependency_classification(
    dependencies: list[str],
    raw: Any,
    allowed_kinds: set[str],
    location: str,
) -> dict[str, str]:
    value = expect_object(raw, location)
    missing = sorted(set(dependencies) - set(value))
    unknown = sorted(set(value) - set(dependencies))
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("unclassified " + ", ".join(missing))
        if unknown:
            details.append("not present in v1 record " + ", ".join(unknown))
        raise MigrationError(
            f"{location}: every legacy relationship requires one explicit "
            f"classification ({'; '.join(details)})"
        )
    result: dict[str, str] = {}
    for reference, kind in value.items():
        if kind not in allowed_kinds:
            raise MigrationError(f"{location}.{reference}: unknown classification {kind!r}")
        result[reference] = kind
    return result


def validate_additional_refs(
    entry: dict[str, Any], location: str, fields: dict[str, re.Pattern[str]]
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for field, pattern in fields.items():
        result[field] = expect_string_array(
            entry[field], f"{location}.{field}", pattern=pattern
        )
    return result


def validate_v1_bundle(bundle: dict[str, Any]) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    require_exact_keys(
        bundle,
        {"schema_version", "migration", "classification", "live"},
        "$",
    )
    if bundle["schema_version"] != INPUT_SCHEMA:
        raise MigrationError(f"$.schema_version: expected {INPUT_SCHEMA}")
    live = expect_object(bundle["live"], "$.live")
    require_exact_keys(
        live,
        {"lifecycle", "origin", "plan", "project", "tasks", "validators"},
        "$.live",
    )
    if live["lifecycle"] != V1_LIFECYCLE:
        version = (
            live["lifecycle"].get("schema_version")
            if isinstance(live["lifecycle"], dict)
            else None
        )
        if version == "harness.lifecycle.v2":
            raise MigrationError("$.live.lifecycle: mixed live v1/v2 authority is prohibited")
        raise MigrationError(
            "$.live.lifecycle: source differs from the closed 1.0.1 "
            "lifecycle; project-specific reconciliation is required"
        )
    origin = validate_v1_origin(live["origin"])
    plan = validate_v1_plan_store(live["plan"])
    project = validate_v1_project(live["project"])
    validators = validate_v1_validators(live["validators"])
    if plan["project_slug"] != origin["project_slug"]:
        raise MigrationError("$.live: plan and origin project identities differ")
    if (
        project["project"]["id"] != origin["project_slug"]
        or project["project"]["profile"] != origin["profile"]
    ):
        raise MigrationError("$.live: project and origin identity/profile differ")
    if not isinstance(live["tasks"], list):
        raise MigrationError("$.live.tasks: expected an array")
    tasks = [
        validate_v1_task(task, f"$.live.tasks[{index}]")
        for index, task in enumerate(live["tasks"])
    ]
    task_ids = [task["id"] for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise MigrationError("$.live.tasks: duplicate task ID")
    plan_ids = [item["id"] for item in plan["plan_items"]]

    classification = expect_object(bundle["classification"], "$.classification")
    require_exact_keys(
        classification,
        {"tasks", "plans", "project_commands"},
        "$.classification",
    )
    task_mapping = validate_mapping_keys(
        classification["tasks"],
        set(task_ids),
        TASK_MAPPING_KEYS,
        "$.classification.tasks",
    )
    plan_mapping = validate_mapping_keys(
        classification["plans"],
        set(plan_ids),
        PLAN_MAPPING_KEYS,
        "$.classification.plans",
    )
    project_command_mapping = validate_mapping_keys(
        classification["project_commands"],
        set(PROJECT_HOOKS),
        PROJECT_COMMAND_MAPPING_KEYS,
        "$.classification.project_commands",
    )
    migration = validate_migration_event(bundle["migration"], origin["profile"])
    if migration["id"] in {item["id"] for item in origin["migration_history"]}:
        raise MigrationError("$.migration.id: already used in origin migration history")
    last_date = (
        origin["migration_history"][-1]["migrated_on"]
        if origin["migration_history"]
        else origin["initial_generation"]["generated_on"]
    )
    if migration["migrated_on"] < last_date:
        raise MigrationError("$.migration.migrated_on: predates existing provenance")
    return (
        live,
        origin,
        tasks,
        plan,
        project,
        validators,
        task_mapping,
        plan_mapping,
        project_command_mapping,
    )


def classified_target(
    reference: str,
    kind: str,
    source_kind: str,
    location: str,
) -> tuple[str | None, str | None]:
    if source_kind == "task":
        patterns = {
            "hard_task_dependency": ("dependencies", TASK_ID),
            "plan_item_ref": ("plan_item_refs", PLAN_ID),
            "gate_ref": ("gate_refs", GATE_ID),
            "blocking_ref": ("blocking_refs", BLOCKING_REF),
        }
    else:
        patterns = {
            "hard_plan_dependency": ("depends_on", PLAN_ID),
            "task_ref": ("task_refs", TASK_ID),
            "gate_ref": ("gate_refs", GATE_ID),
            "blocking_ref": ("blocking_refs", BLOCKING_REF),
        }
    if kind == "advisory":
        return None, "advisory"
    field, pattern = patterns[kind]
    if not pattern.fullmatch(reference):
        raise MigrationError(
            f"{location}: {reference!r} cannot be classified as {kind!r}"
        )
    return field, None


def migrate_task(
    task: dict[str, Any],
    mapping: dict[str, Any],
    advisories: list[dict[str, Any]],
) -> dict[str, Any]:
    task_id = task["id"]
    location = f"$.classification.tasks.{task_id}"
    kinds = validate_dependency_classification(
        task["dependencies"],
        mapping["dependencies"],
        TASK_DEPENDENCY_KINDS,
        f"{location}.dependencies",
    )
    additions = validate_additional_refs(
        mapping,
        location,
        {
            "additional_plan_item_refs": PLAN_ID,
            "additional_gate_refs": GATE_ID,
            "additional_blocking_refs": BLOCKING_REF,
        },
    )
    migrated = copy.deepcopy(task)
    migrated["schema_version"] = "harness.task.v2"
    migrated["dependencies"] = []
    migrated["plan_item_refs"] = list(additions["additional_plan_item_refs"])
    migrated["gate_refs"] = list(additions["additional_gate_refs"])
    migrated["blocking_refs"] = list(additions["additional_blocking_refs"])
    for reference in task["dependencies"]:
        kind = kinds[reference]
        target, advisory = classified_target(
            reference,
            kind,
            "task",
            f"{location}.dependencies.{reference}",
        )
        if advisory:
            advisories.append(
                {
                    "source_record": task_id,
                    "source_field": "dependencies",
                    "target_ref": reference,
                    "classification": "advisory",
                    "live_readiness_effect": "none",
                }
            )
        elif target is not None:
            migrated[target].append(reference)
    for field in ("dependencies", "plan_item_refs", "gate_refs", "blocking_refs"):
        migrated[field] = sorted(set(migrated[field]))
    if task["status"] == "blocked" and (
        not task["blocked_by"] or not migrated["blocking_refs"]
    ):
        raise MigrationError(
            f"{location}: blocked task requires explanation and an explicit structured blocker"
        )
    return migrated


def migrate_plan_item(
    item: dict[str, Any],
    mapping: dict[str, Any],
    advisories: list[dict[str, Any]],
) -> dict[str, Any]:
    plan_id = item["id"]
    location = f"$.classification.plans.{plan_id}"
    kinds = validate_dependency_classification(
        item["depends_on"],
        mapping["depends_on"],
        PLAN_DEPENDENCY_KINDS,
        f"{location}.depends_on",
    )
    additions = validate_additional_refs(
        mapping,
        location,
        {
            "additional_task_refs": TASK_ID,
            "additional_gate_refs": GATE_ID,
            "additional_blocking_refs": BLOCKING_REF,
        },
    )
    migrated = copy.deepcopy(item)
    migrated["depends_on"] = []
    migrated["task_refs"] = list(additions["additional_task_refs"])
    migrated["gate_refs"] = list(item["gate_refs"]) + list(
        additions["additional_gate_refs"]
    )
    migrated["blocking_refs"] = list(additions["additional_blocking_refs"])
    for reference in item["depends_on"]:
        kind = kinds[reference]
        target, advisory = classified_target(
            reference,
            kind,
            "plan",
            f"{location}.depends_on.{reference}",
        )
        if advisory:
            advisories.append(
                {
                    "source_record": plan_id,
                    "source_field": "depends_on",
                    "target_ref": reference,
                    "classification": "advisory",
                    "live_readiness_effect": "none",
                }
            )
        elif target is not None:
            migrated[target].append(reference)
    for field in ("depends_on", "task_refs", "gate_refs", "blocking_refs"):
        migrated[field] = sorted(set(migrated[field]))
    if item["status"] == "blocked" and (
        not item["blocked_by"] or not migrated["blocking_refs"]
    ):
        raise MigrationError(
            f"{location}: blocked plan requires explanation and an explicit structured blocker"
        )
    return migrated


def check_cycles(records: list[dict[str, Any]], field: str, label: str) -> None:
    by_id = {record["id"]: record for record in records}
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(record_id: str) -> None:
        if record_id in visiting:
            start = stack.index(record_id)
            cycle = stack[start:] + [record_id]
            raise MigrationError(f"{label} dependency cycle: {' -> '.join(cycle)}")
        if record_id in visited:
            return
        visiting.add(record_id)
        stack.append(record_id)
        for dependency in by_id[record_id].get(field, []):
            if dependency not in by_id:
                raise MigrationError(
                    f"{label} {record_id}: unresolved hard dependency {dependency}"
                )
            visit(dependency)
        stack.pop()
        visiting.remove(record_id)
        visited.add(record_id)

    for record_id in sorted(by_id):
        visit(record_id)


def validate_relationships(tasks: list[dict[str, Any]], plan: dict[str, Any]) -> None:
    task_by_id = {task["id"]: task for task in tasks}
    plan_by_id = {item["id"]: item for item in plan["plan_items"]}
    check_cycles(tasks, "dependencies", "task")
    check_cycles(plan["plan_items"], "depends_on", "plan")
    for task in tasks:
        for plan_ref in task["plan_item_refs"]:
            if plan_ref not in plan_by_id:
                raise MigrationError(
                    f"task {task['id']}: unresolved plan item reference {plan_ref}"
                )
            if task["id"] not in plan_by_id[plan_ref]["task_refs"]:
                raise MigrationError(
                    f"task {task['id']}: plan link {plan_ref} is not reciprocal"
                )
    for item in plan["plan_items"]:
        for task_ref in item["task_refs"]:
            if task_ref not in task_by_id:
                raise MigrationError(
                    f"plan {item['id']}: unresolved task reference {task_ref}"
                )
            if item["id"] not in task_by_id[task_ref]["plan_item_refs"]:
                raise MigrationError(
                    f"plan {item['id']}: task link {task_ref} is not reciprocal"
                )


def unassessed_project_command() -> dict[str, Any]:
    return {
        "status": "not_assessed",
        "owner": None,
        "rationale": None,
        "tool_name": None,
        "argv": None,
        "version_argv": None,
        "timeout_seconds": None,
        "evidence_freshness_days": None,
        "side_effects": {
            "classification": "not_assessed",
            "repository_write_paths": [],
            "external_effects": [],
        },
    }


def migrate_project_command(
    hook: str,
    legacy: dict[str, Any],
    mapping: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    location = f"$.classification.project_commands.{hook}"
    action = mapping["action"]
    assessment = mapping["assessment"]
    if legacy["run"] is not None:
        raise MigrationError(
            f"{location}: configured legacy hook cannot be migrated; legacy "
            "command strings are never parsed or treated as v2 argv"
        )
    if action == "preserve_not_assessed":
        if legacy != {"status": "not_assessed", "run": None}:
            raise MigrationError(
                f"{location}: configured legacy hook requires an explicit v2 "
                "assessment; command strings are never parsed"
            )
        if assessment is not None:
            raise MigrationError(
                f"{location}: preserve_not_assessed requires assessment=null"
            )
        migrated = unassessed_project_command()
    elif action == "explicit_v2_assessment":
        if assessment is None:
            raise MigrationError(
                f"{location}: explicit_v2_assessment requires an assessment"
            )
        migrated = copy.deepcopy(
            validate_v2_project_command(assessment, f"{location}.assessment")
        )
    else:
        raise MigrationError(f"{location}.action: unknown action {action!r}")
    return migrated, {
        "hook": hook,
        "legacy_status": legacy["status"],
        "action": action,
        "resulting_status": migrated["status"],
        "legacy_run_interpreted": False,
        "check_executed": False,
        "evidence_created": False,
    }


def migrate_project(
    project: dict[str, Any], mappings: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    migrated = copy.deepcopy(project)
    migrated["schema_version"] = "harness.project.v2"
    migrated["project"]["blueprint_version"] = TO_VERSION
    migrated_commands: dict[str, Any] = {}
    dispositions: list[dict[str, Any]] = []
    for hook in PROJECT_HOOKS:
        command, disposition = migrate_project_command(
            hook,
            project["commands"][hook],
            mappings[hook],
        )
        migrated_commands[hook] = command
        dispositions.append(disposition)
    migrated["commands"] = migrated_commands
    migrated["project_checks"] = copy.deepcopy(PROJECT_CHECKS_CONTRACT)
    if migrated["project"]["adoption_status"] in {"adopted", "superseded"}:
        raise MigrationError(
            "$.live.project.project.adoption_status: adopted or superseded v1 "
            "state requires project-specific v2 evidence and adoption "
            "re-verification; the reference migrator will not preserve the claim"
        )
    return migrated, dispositions


def migrate_validators(validators: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(validators)
    migrated["schema_version"] = "harness.validators.v2"
    migrated["validator_version"] = TO_VERSION
    migrated["commands"] = {
        "bootstrap": copy.deepcopy(V2_FIXED_VALIDATOR_COMMANDS["bootstrap"]),
        "check": copy.deepcopy(V2_FIXED_VALIDATOR_COMMANDS["check"]),
        "ready_frontier": copy.deepcopy(
            V2_FIXED_VALIDATOR_COMMANDS["ready_frontier"]
        ),
        "test": copy.deepcopy(V2_FIXED_VALIDATOR_COMMANDS["test"]),
        "project_checks": copy.deepcopy(
            V2_FIXED_VALIDATOR_COMMANDS["project_checks"]
        ),
        "adoption_verify": copy.deepcopy(
            V2_FIXED_VALIDATOR_COMMANDS["adoption_verify"]
        ),
        "refresh": copy.deepcopy(validators["commands"]["refresh"]),
        "closure": copy.deepcopy(V2_FIXED_VALIDATOR_COMMANDS["closure"]),
    }
    migrated["required_core_checks"] = list(V2_REQUIRED_CORE_CHECKS)
    return migrated


def migrate_origin(origin: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(origin)
    migrated["blueprint_version"] = TO_VERSION
    migrated["generator_version"] = GENERATOR_VERSION
    migrated["harness_kernel_version"] = KERNEL_VERSION
    migrated["migration_history"].append(copy.deepcopy(event))
    return migrated


def rollback_evidence(source_bytes: bytes, live: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": ROLLBACK_SCHEMA,
        "live_state_role": "noncurrent_rollback_evidence",
        "permission_grant": False,
        "authority_effect": "none",
        "source_encoding": "base64_of_exact_utf8_input_bytes",
        "source_sha256": digest_bytes(source_bytes),
        "source_bytes_base64": base64.b64encode(source_bytes).decode("ascii"),
        "live_state_sha256": digest_bytes(canonical_json_bytes(live)),
        "live_state": copy.deepcopy(live),
        "restoration_rule": (
            "Restoration requires separate current authority and must restore the "
            "v1 task, plan, lifecycle, project, validator, and origin contracts "
            "together."
        ),
    }


def migrate_v1_bundle(
    bundle: dict[str, Any], source_bytes: bytes, *, validate_result: bool = True
) -> dict[str, Any]:
    (
        live,
        origin,
        tasks,
        plan,
        project,
        validators,
        task_mapping,
        plan_mapping,
        project_command_mapping,
    ) = validate_v1_bundle(bundle)
    advisories: list[dict[str, Any]] = []
    migrated_tasks = [
        migrate_task(task, task_mapping[task["id"]], advisories) for task in tasks
    ]
    migrated_plan = copy.deepcopy(plan)
    migrated_plan["schema_version"] = "project.dossier.plan.v2"
    migrated_plan["plan_items"] = [
        migrate_plan_item(item, plan_mapping[item["id"]], advisories)
        for item in plan["plan_items"]
    ]
    migrated_tasks.sort(key=lambda item: item["id"])
    migrated_plan["plan_items"].sort(key=lambda item: item["id"])
    validate_relationships(migrated_tasks, migrated_plan)
    migrated_project, command_dispositions = migrate_project(
        project, project_command_mapping
    )
    result = {
        "schema_version": RESULT_SCHEMA,
        "migration_contract": copy.deepcopy(MIGRATION_CONTRACT),
        "live": {
            "lifecycle": copy.deepcopy(V2_LIFECYCLE),
            "origin": migrate_origin(origin, bundle["migration"]),
            "plan": migrated_plan,
            "project": migrated_project,
            "tasks": migrated_tasks,
            "validators": migrate_validators(validators),
        },
        "advisory_relationships": sorted(
            advisories,
            key=lambda item: (
                item["source_record"],
                item["source_field"],
                item["target_ref"],
            ),
        ),
        "project_command_dispositions": command_dispositions,
        "rollback_evidence": rollback_evidence(source_bytes, live),
        "limitations": list(RESULT_LIMITATIONS),
    }
    if validate_result:
        validate_migrated_result(result, replay=False)
    return result


def validate_migrated_live(live: Any) -> None:
    value = expect_object(live, "$.live")
    require_exact_keys(
        value,
        {"lifecycle", "origin", "plan", "project", "tasks", "validators"},
        "$.live",
    )
    if value["lifecycle"] != V2_LIFECYCLE:
        raise MigrationError("$.live.lifecycle: result differs from the v2 lifecycle")
    if not isinstance(value["tasks"], list):
        raise MigrationError("$.live.tasks: expected an array")
    harness_schema = load_current_schema("harness-record.schema.json")
    dossier_schema = load_current_schema("dossier-records.schema.json")
    kernel_schema = load_current_schema("harness-kernel.schema.json")
    # Project and validator records are intentionally absent from the current
    # kernel-schema checks below. Their historical v2 contracts are frozen in
    # validate_v2_project_output and validate_v2_validators_output so a later
    # breaking kernel release cannot retroactively invalidate this migration.
    errors: list[str] = []
    errors.extend(
        validate_schema(
            value["lifecycle"],
            {"$ref": "#/$defs/lifecycle"},
            "$.live.lifecycle",
            root_schema=kernel_schema,
        )
    )
    for index, task in enumerate(value["tasks"]):
        errors.extend(
            validate_schema(
                task,
                {"$ref": "#/$defs/task"},
                f"$.live.tasks[{index}]",
                root_schema=harness_schema,
            )
        )
    errors.extend(
        validate_schema(
            value["plan"],
            {"$ref": "#/$defs/store_plan"},
            "$.live.plan",
            root_schema=dossier_schema,
        )
    )
    if errors:
        raise MigrationError("migrated records fail current schemas: " + "; ".join(errors))
    origin = value["origin"]
    if (
        origin.get("blueprint_version") != TO_VERSION
        or origin.get("generator_version") != GENERATOR_VERSION
        or origin.get("harness_kernel_version") != KERNEL_VERSION
    ):
        raise MigrationError("$.live.origin: mixed live v1/v2 authority is prohibited")
    if value["plan"].get("schema_version") != "project.dossier.plan.v2":
        raise MigrationError("$.live.plan: mixed live v1/v2 authority is prohibited")
    project = validate_v2_project_output(value["project"])
    validators = validate_v2_validators_output(value["validators"])
    if any(task.get("schema_version") != "harness.task.v2" for task in value["tasks"]):
        raise MigrationError("$.live.tasks: mixed live v1/v2 authority is prohibited")
    identity = expect_object(project["project"], "$.live.project.project")
    if (
        identity["id"] != origin["project_slug"]
        or identity["profile"] != origin["profile"]
    ):
        raise MigrationError("$.live: project and origin identity/profile differ")
    for index, task in enumerate(value["tasks"]):
        if isinstance(task, dict):
            validate_task_transition(task, V2_LIFECYCLE, f"$.live.tasks[{index}]")
    validate_origin_history(origin, "$.live.origin")
    validate_relationships(value["tasks"], value["plan"])


def validate_rollback(value: Any) -> tuple[dict[str, Any], bytes]:
    rollback = expect_object(value, "$.rollback_evidence")
    expected_keys = {
        "schema_version",
        "live_state_role",
        "permission_grant",
        "authority_effect",
        "source_encoding",
        "source_sha256",
        "source_bytes_base64",
        "live_state_sha256",
        "live_state",
        "restoration_rule",
    }
    require_exact_keys(rollback, expected_keys, "$.rollback_evidence")
    if rollback["schema_version"] != ROLLBACK_SCHEMA:
        raise MigrationError("$.rollback_evidence.schema_version: invalid")
    if rollback["live_state_role"] != "noncurrent_rollback_evidence":
        raise MigrationError("$.rollback_evidence.live_state_role: invalid")
    if rollback["permission_grant"] is not False or rollback["authority_effect"] != "none":
        raise MigrationError("$.rollback_evidence: rollback evidence cannot grant authority")
    if rollback["source_encoding"] != "base64_of_exact_utf8_input_bytes":
        raise MigrationError("$.rollback_evidence.source_encoding: invalid")
    try:
        source_bytes = base64.b64decode(
            expect_nonempty_string(
                rollback["source_bytes_base64"],
                "$.rollback_evidence.source_bytes_base64",
            ),
            validate=True,
        )
    except (ValueError, binascii.Error) as error:
        raise MigrationError("$.rollback_evidence.source_bytes_base64: invalid") from error
    if digest_bytes(source_bytes) != rollback["source_sha256"]:
        raise MigrationError("$.rollback_evidence.source_sha256: digest mismatch")
    live = expect_object(rollback["live_state"], "$.rollback_evidence.live_state")
    if digest_bytes(canonical_json_bytes(live)) != rollback["live_state_sha256"]:
        raise MigrationError("$.rollback_evidence.live_state_sha256: digest mismatch")
    source = parse_json_bytes(source_bytes, "$.rollback_evidence.source_bytes_base64")
    if source.get("schema_version") != INPUT_SCHEMA:
        raise MigrationError("$.rollback_evidence: source is not a v1 migration input")
    if source.get("live") != live:
        raise MigrationError("$.rollback_evidence: exact source and parsed live state differ")
    return source, source_bytes


def validate_migrated_result(result: dict[str, Any], *, replay: bool = True) -> None:
    require_exact_keys(
        result,
        {
            "schema_version",
            "migration_contract",
            "live",
            "advisory_relationships",
            "project_command_dispositions",
            "rollback_evidence",
            "limitations",
        },
        "$",
    )
    if result["schema_version"] != RESULT_SCHEMA:
        raise MigrationError(f"$.schema_version: expected {RESULT_SCHEMA}")
    if result["migration_contract"] != MIGRATION_CONTRACT:
        raise MigrationError("$.migration_contract: contract differs from the migration tool")
    if result["limitations"] != RESULT_LIMITATIONS:
        raise MigrationError("$.limitations: required migration limitations changed")
    if not isinstance(result["advisory_relationships"], list):
        raise MigrationError("$.advisory_relationships: expected an array")
    for index, item in enumerate(result["advisory_relationships"]):
        location = f"$.advisory_relationships[{index}]"
        entry = expect_object(item, location)
        require_exact_keys(
            entry,
            {
                "source_record",
                "source_field",
                "target_ref",
                "classification",
                "live_readiness_effect",
            },
            location,
        )
        if (
            entry["classification"] != "advisory"
            or entry["live_readiness_effect"] != "none"
        ):
            raise MigrationError(f"{location}: advisory relationship affects readiness")
        if not isinstance(entry["source_record"], str) or not ID4.fullmatch(
            entry["source_record"]
        ):
            raise MigrationError(f"{location}.source_record: invalid")
        if entry["source_field"] not in {"dependencies", "depends_on"}:
            raise MigrationError(f"{location}.source_field: invalid")
        if not isinstance(entry["target_ref"], str) or not GENERAL_REF.fullmatch(
            entry["target_ref"]
        ):
            raise MigrationError(f"{location}.target_ref: invalid")
    dispositions = result["project_command_dispositions"]
    if not isinstance(dispositions, list):
        raise MigrationError("$.project_command_dispositions: expected an array")
    if len(dispositions) != len(PROJECT_HOOKS):
        raise MigrationError(
            "$.project_command_dispositions: expected one entry per project hook"
        )
    for index, raw in enumerate(dispositions):
        location = f"$.project_command_dispositions[{index}]"
        entry = expect_object(raw, location)
        require_exact_keys(
            entry,
            {
                "hook",
                "legacy_status",
                "action",
                "resulting_status",
                "legacy_run_interpreted",
                "check_executed",
                "evidence_created",
            },
            location,
        )
        if entry["hook"] != PROJECT_HOOKS[index]:
            raise MigrationError(f"{location}.hook: unexpected hook or ordering")
        if entry["legacy_status"] != "not_assessed":
            raise MigrationError(f"{location}.legacy_status: unsafe legacy status")
        if entry["action"] not in {
            "preserve_not_assessed",
            "explicit_v2_assessment",
        }:
            raise MigrationError(f"{location}.action: invalid")
        if entry["resulting_status"] not in {
            "not_assessed",
            "configured",
            "not_applicable",
        }:
            raise MigrationError(f"{location}.resulting_status: invalid")
        for field in (
            "legacy_run_interpreted",
            "check_executed",
            "evidence_created",
        ):
            if entry[field] is not False:
                raise MigrationError(f"{location}.{field}: must be false")
    validate_migrated_live(result["live"])
    live_commands = result["live"]["project"]["commands"]
    for entry in dispositions:
        if live_commands[entry["hook"]]["status"] != entry["resulting_status"]:
            raise MigrationError(
                "$.project_command_dispositions: result status differs from live command"
            )
    source, source_bytes = validate_rollback(result["rollback_evidence"])
    if replay:
        expected = migrate_v1_bundle(source, source_bytes, validate_result=False)
        if canonical_json_bytes(expected) != canonical_json_bytes(result):
            raise MigrationError(
                "migrated result differs from deterministic replay of rollback source"
            )


def migrate_document(value: dict[str, Any], source_bytes: bytes) -> dict[str, Any]:
    schema_version = value.get("schema_version")
    if schema_version == INPUT_SCHEMA:
        return migrate_v1_bundle(value, source_bytes)
    if schema_version == RESULT_SCHEMA:
        validate_migrated_result(value, replay=True)
        return copy.deepcopy(value)
    raise MigrationError(
        "unsupported input schema; expected a closed v1 migration input or "
        "a validated migrated result"
    )


def write_new_file(path: Path, content: bytes, input_path: Path) -> None:
    try:
        if path.resolve() == input_path.resolve():
            raise MigrationError(
                "input and output paths must differ; in-place migration is "
                "prohibited"
            )
    except OSError as error:
        raise MigrationError(f"cannot resolve input/output paths: {error}") from error
    if not path.parent.is_dir():
        raise MigrationError(f"output parent must already exist: {path.parent}")
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise MigrationError(f"output already exists; refusing replacement: {path}") from error
    except OSError as error:
        try:
            if path.is_file() and not path.is_symlink():
                path.unlink()
        except OSError:
            pass
        raise MigrationError(f"cannot write output {path}: {error}") from error


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate a closed Project Blueprint 1.0.1 fixture bundle to 2.0.0 "
            "without changing the input."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if sys.version_info < (3, 11):
        print("ERROR: Python 3.11+ is required.", file=sys.stderr)
        return 2
    args = parse_args(argv)
    input_path = args.input.expanduser()
    try:
        value, source_bytes = load_json_document(input_path)
        result = migrate_document(value, source_bytes)
        output_bytes = pretty_json_bytes(result)
        if args.check:
            print(
                json.dumps(
                    {
                        "schema_version": CHECK_SCHEMA,
                        "input_schema": value.get("schema_version"),
                        "result_sha256": digest_bytes(canonical_json_bytes(result)),
                        "would_write": False,
                        "authority_effect": "none",
                        "readiness_claim": False,
                        "project_checks_executed": False,
                        "legacy_project_command_strings_interpreted": False,
                    },
                    sort_keys=True,
                )
            )
        else:
            output_path = args.output.expanduser()
            write_new_file(output_path, output_bytes, input_path)
            print(f"Migrated fixture written: {output_path}")
            print(f"Result SHA-256: {digest_bytes(canonical_json_bytes(result))}")
            print("No authority, approval, evidence result, or readiness was created.")
    except MigrationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
