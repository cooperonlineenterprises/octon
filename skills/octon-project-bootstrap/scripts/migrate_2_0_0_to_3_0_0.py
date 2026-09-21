#!/usr/bin/env python3
"""Deterministic reference migration for Project Blueprint 2.0.0 to 3.0.0.

The reference bundle is deliberately closed. It migrates the v2 project,
tool, validator, and origin contracts plus a project-owned classification that
the vague legacy Git policy was never separately adopted. It does not inspect
GitHub, infer collaborators, execute project commands, adopt a workflow, or
write in place. Live projects still require an authorized reconciliation.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


FROM_VERSION = "2.0.0"
TO_VERSION = "3.0.0"
GENERATOR_VERSION = "3.0.0"
KERNEL_VERSION = "3.0.0"
INPUT_SCHEMA = "project-blueprint.migration-input.2.0.0-to-3.0.0.v1"
RESULT_SCHEMA = "project-blueprint.migration-result.2.0.0-to-3.0.0.v1"
ROLLBACK_SCHEMA = "project-blueprint.rollback-evidence.2.0.0-to-3.0.0.v1"
CHECK_SCHEMA = "project-blueprint.migration-check.2.0.0-to-3.0.0.v1"
MIGRATION_GUIDE = "migrations/2.0.0-to-3.0.0.md"

PROFILE_VALUES = {"minimal", "standard", "high-assurance"}
PROJECT_HOOKS = (
    "project_test",
    "project_lint",
    "project_build",
    "project_closure",
)
PROJECT_KEYS = {
    "schema_version",
    "project",
    "paths",
    "commands",
    "project_checks",
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
PROJECT_COMMAND_KEYS = {
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
SIDE_EFFECT_KEYS = {
    "classification",
    "repository_write_paths",
    "external_effects",
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
V3_REQUIRED_CORE_CHECKS = [
    "python_runtime_floor",
    "strict_json_and_duplicate_keys",
    "schemas_and_versions",
    "authority_and_nested_instruction_invariants",
    "identifiers_references_and_lifecycles",
    "dependency_readiness_and_ready_frontier",
    "collaboration_topology_and_workflow_selection",
    "small_team_git_workflow_and_operation_contract",
    "project_command_assessment_and_current_evidence",
    "dossier_catalog_path_authority_and_traceability",
    "extension_compatibility_confinement_and_validator_protocol",
    "unresolved_generation_placeholders",
    "redacted_secret_detection",
    "repository_symlinks_and_host_metadata",
    "generated_integrity_freshness_when_present",
]
AUTHORITY_TEXT = (
    "Generation provenance only; does not grant permission or establish "
    "project facts, decisions, implementation, or readiness."
)


class MigrationError(ValueError):
    """Raised when the closed reference contract cannot be migrated safely."""


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MigrationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise MigrationError(f"non-finite JSON number is prohibited: {value}")


def loads_json(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise MigrationError(f"input is not UTF-8: {error}") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as error:
        raise MigrationError(f"invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise MigrationError("migration document must be a JSON object")
    return value


def load_json_document(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise MigrationError(f"cannot read {path}: {error}") from error
    return loads_json(data), data


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compact_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def blueprint_root() -> Path:
    skill = Path(__file__).resolve().parents[1]
    candidates = (skill.parents[1], skill / "assets" / "octon-source")
    for candidate in candidates:
        if (
            (candidate / "VERSION").is_file()
            and (candidate / "shared/schemas/harness-kernel.schema.json").is_file()
        ):
            return candidate
    raise MigrationError("cannot locate the bundled 3.0.0 blueprint source")


def current_template(relative: str) -> dict[str, Any]:
    path = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "templates"
        / "core"
        / relative
    )
    if not path.is_file() and relative == ".agent/workflows/small-team-git.json.tmpl":
        path = (
            Path(__file__).resolve().parents[1]
            / "assets/packages/small-team-git-portfolio/templates"
            / relative
        )
    value, _ = load_json_document(path)
    if relative == ".agent/workflows/small-team-git.json.tmpl":
        # Freeze the truthful Project Blueprint 3.0 completion surface. The
        # source package now carries Octon Mini templates, but this closed
        # historical migrator must never retroactively rebrand its output.
        completion = value["completion_orchestrator"]
        completion["authority_ref"] = "project-blueprint:SRC-DEC-0013"
        completion["engine"] = ".agent/scripts/pb_finish.py"
        completion["commands"] = [
            "pb work finish plan",
            "pb work finish apply --accept-digest <digest>",
            "pb work finish resume",
        ]
    return value


def canonical_v2_tools() -> dict[str, Any]:
    return {
        "schema_version": "harness.tools.v1",
        "permission_grant": False,
        "declarative_only": True,
        "real_enforcement_boundary": [
            "platform_and_sandbox_permissions",
            "operating_system_and_workspace_access",
            "credential_scope",
            "protected_remote_controls",
        ],
        "tools": {
            "filesystem": {
                "availability": "required",
                "allowed": ["read_relevant", "write_requested_repository_paths"],
                "denied": [
                    "write_outside_declared_workspace",
                    "follow_untrusted_symlink",
                ],
            },
            "shell": {
                "availability": "required",
                "allowed": ["declared_validation", "scoped_local_commands"],
                "denied": ["undeclared_external_effect", "secret_in_command"],
            },
            "git": {
                "availability": "optional",
                "allowed": ["status", "diff"],
                "task_scoped": ["add", "commit", "branch"],
                "explicit_current_authorization": [
                    "push",
                    "force_push",
                    "remote_mutation",
                ],
            },
        },
        "evidence": {
            "record_material_commands": True,
            "redact_secret_values": True,
            "tool_availability_implies_permission": False,
        },
    }


def unknown_collaboration_profile() -> dict[str, Any]:
    return {
        "schema_version": "harness.collaboration-profile.v1",
        "permission_grant": False,
        "assessment_status": "not_assessed",
        "confidence": "unknown",
        "declared_write_capable_humans": None,
        "observed_repository_access": {
            "write_capable_humans": None,
            "read_only_humans": None,
            "bots_or_automation": None,
        },
        "active_contributors": {
            "human_count": None,
            "bots_or_automation_count": None,
            "window_days": None,
        },
        "independent_review_capacity": None,
        "expected_concurrent_repository_writers": {
            "humans": None,
            "agents_or_automation": None,
        },
        "external_contribution_mode": "unknown",
        "solo_integration_preference": "unknown",
        "evidence": [],
        "assessed_at": None,
        "reassess_after": None,
        "conflicting_signals": [],
        "limitations": ["generated_unassessed_baseline"],
        "team_band": "unknown",
        "workflow_selection": {
            "status": "not_assessed",
            "base_workflow": None,
            "modifiers": [],
            "review_mode": "not_assessed",
            "integration_method": None,
            "adoption_decision_ref": None,
        },
    }


def expect_exact_keys(value: Any, keys: set[str], location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MigrationError(f"{location}: expected object")
    if set(value) != keys:
        missing = sorted(keys - set(value))
        extra = sorted(set(value) - keys)
        raise MigrationError(
            f"{location}: closed keys differ; missing={missing}, extra={extra}"
        )
    return value


def validate_project_command(command: Any, location: str) -> None:
    value = expect_exact_keys(command, PROJECT_COMMAND_KEYS, location)
    side_effects = expect_exact_keys(
        value["side_effects"], SIDE_EFFECT_KEYS, f"{location}.side_effects"
    )
    status = value["status"]
    if status not in {"not_assessed", "configured", "not_applicable"}:
        raise MigrationError(f"{location}.status: invalid")
    if not isinstance(side_effects["repository_write_paths"], list) or not isinstance(
        side_effects["external_effects"], list
    ):
        raise MigrationError(f"{location}.side_effects: invalid arrays")
    if status == "not_assessed":
        if any(
            value[field] is not None
            for field in (
                "owner",
                "rationale",
                "tool_name",
                "argv",
                "version_argv",
                "timeout_seconds",
                "evidence_freshness_days",
            )
        ) or side_effects != {
            "classification": "not_assessed",
            "repository_write_paths": [],
            "external_effects": [],
        }:
            raise MigrationError(f"{location}: noncanonical unassessed hook")
    elif status == "not_applicable":
        if (
            not isinstance(value["owner"], str)
            or not value["owner"].strip()
            or not isinstance(value["rationale"], str)
            or not value["rationale"].strip()
            or any(
                value[field] is not None
                for field in (
                    "tool_name",
                    "argv",
                    "version_argv",
                    "timeout_seconds",
                    "evidence_freshness_days",
                )
            )
            or side_effects["classification"] != "not_applicable"
        ):
            raise MigrationError(f"{location}: invalid not_applicable hook")
    else:
        if (
            not isinstance(value["owner"], str)
            or not isinstance(value["tool_name"], str)
            or not isinstance(value["argv"], list)
            or not value["argv"]
            or not isinstance(value["version_argv"], list)
            or not value["version_argv"]
            or value["argv"][0] != value["version_argv"][0]
            or not isinstance(value["timeout_seconds"], int)
            or not isinstance(value["evidence_freshness_days"], int)
        ):
            raise MigrationError(f"{location}: invalid configured hook")


def validate_v2_project(value: Any) -> dict[str, Any]:
    project = expect_exact_keys(value, PROJECT_KEYS, "live.project")
    if project["schema_version"] != "harness.project.v2":
        raise MigrationError("live.project: mixed or non-v2 project authority")
    identity = expect_exact_keys(
        project["project"], PROJECT_IDENTITY_KEYS, "live.project.project"
    )
    if (
        identity["blueprint_version"] != FROM_VERSION
        or identity["profile"] not in PROFILE_VALUES
        or identity["repository_root"] != "."
        or not isinstance(identity["id"], str)
        or not identity["id"]
        or not isinstance(identity["name"], str)
        or not identity["name"]
    ):
        raise MigrationError("live.project.project: invalid v2 identity/version")
    if identity["adoption_status"] not in {
        "not_assessed",
        "in_progress",
        "adopted",
        "superseded",
    }:
        raise MigrationError("live.project.project.adoption_status: invalid")
    if identity["adoption_status"] in {"adopted", "superseded"}:
        if not isinstance(identity["adoption_decision_ref"], str) or not re.fullmatch(
            r"DEC-[0-9]{4}", identity["adoption_decision_ref"]
        ):
            raise MigrationError("adopted v2 harness lacks its existing decision ref")
    elif identity["adoption_decision_ref"] is not None:
        raise MigrationError("pre-adoption v2 harness has an adoption decision ref")
    paths = expect_exact_keys(
        project["paths"],
        {"source", "tests", "generated", "instruction_roots", "fingerprint_exclusions"},
        "live.project.paths",
    )
    if any(not isinstance(paths[field], list) for field in paths):
        raise MigrationError("live.project.paths: invalid arrays")
    commands = expect_exact_keys(
        project["commands"], set(PROJECT_HOOKS), "live.project.commands"
    )
    for hook in PROJECT_HOOKS:
        validate_project_command(commands[hook], f"live.project.commands.{hook}")
    expected_checks = {
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
    if project["project_checks"] != expected_checks:
        raise MigrationError("live.project.project_checks: noncanonical v2 contract")
    if project["extensions"] != {
        "registry": ".agent/extensions/registry.json",
        "registry_required_in_profile": "standard_or_higher",
    } or project["mutable_work_status"] != "prohibited_here":
        raise MigrationError("live.project: noncanonical extension/status contract")
    return project


def expected_v2_validator_commands(profile: str) -> dict[str, Any]:
    refresh_writes = [
        "project-dossier/ARTIFACT_CATALOG.json",
        "project-dossier/MANIFEST.json",
        "project-dossier/machine-readable/path-authority.json",
    ]
    if profile == "high-assurance":
        refresh_writes = sorted(
            refresh_writes
            + [
                ".agent/generated/manifest.json",
                ".agent/generated/validation-report.json",
                "project-dossier/CHECKSUMS.sha256",
            ]
        )
    return {
        "bootstrap": {"run": "python --version", "writes": []},
        "check": {
            "run": "python -B .agent/scripts/validate.py --check",
            "writes": [],
        },
        "ready_frontier": {
            "run": "python -B .agent/scripts/validate.py --ready-frontier",
            "writes": [],
        },
        "test": {
            "run": "python -B -m unittest discover -s .agent/tests -p \"test_*.py\"",
            "writes": [],
        },
        "project_checks": {
            "run": "python -B .agent/scripts/run_project_checks.py --write-evidence",
            "writes": [".agent/project-checks/evidence.json"],
        },
        "adoption_verify": {
            "run": (
                "python -B .agent/scripts/run_project_checks.py --write-evidence "
                "--verify-adoption"
            ),
            "writes": "project_check_evidence_and_profile_refresh_outputs",
        },
        "refresh": {
            "run": "python -B .agent/scripts/refresh.py --refresh",
            "writes": refresh_writes,
        },
        "closure": {
            "run": "configure_during_project_adoption",
            "writes": "not_assessed",
        },
    }


def validate_v2_validators(value: Any, profile: str) -> dict[str, Any]:
    validators = expect_exact_keys(
        value,
        {
            "schema_version",
            "validator_version",
            "runtime",
            "commands",
            "required_core_checks",
            "limitations",
        },
        "live.validators",
    )
    if (
        validators["schema_version"] != "harness.validators.v2"
        or validators["validator_version"] != FROM_VERSION
        or validators["commands"] != expected_v2_validator_commands(profile)
        or validators["required_core_checks"] != V2_REQUIRED_CORE_CHECKS
    ):
        raise MigrationError("live.validators: mixed or divergent v2 contract")
    if validators["runtime"] != {
        "executable": "python",
        "minimum_version": "3.11",
        "dependencies": "standard_library_only",
        "bytecode_and_cache_writes": "prohibited_for_check",
    } or validators["limitations"] != [
        "structural_checks_do_not_prove_project_readiness",
        "repository_policy_is_not_runtime_sandbox_enforcement",
    ]:
        raise MigrationError("live.validators: noncanonical runtime/limitations")
    return validators


def validate_migration_event(value: Any, profile: str) -> dict[str, Any]:
    event = expect_exact_keys(value, MIGRATION_KEYS, "migration")
    if (
        event["schema_version"] != "project-blueprint.migration.v1"
        or not isinstance(event["id"], str)
        or not re.fullmatch(r"MIG-[0-9]{4}", event["id"])
        or event["from_blueprint_version"] != FROM_VERSION
        or event["to_blueprint_version"] != TO_VERSION
        or event["generator_version"] != GENERATOR_VERSION
        or event["from_profile"] != profile
        or event["to_profile"] != profile
        or event["migration_guide"] != MIGRATION_GUIDE
        or not str(event["authority_source"]).startswith(("authority:", "external:"))
        or not isinstance(event["evidence_refs"], list)
        or not event["evidence_refs"]
        or any(not re.fullmatch(r"EVD-[0-9]{4}", str(item)) for item in event["evidence_refs"])
        or not isinstance(event["limitations"], list)
    ):
        raise MigrationError("migration: invalid version, authority, evidence, or profile")
    return event


def validate_v2_origin(value: Any, project: dict[str, Any]) -> dict[str, Any]:
    origin = expect_exact_keys(value, ORIGIN_KEYS, "live.origin")
    identity = project["project"]
    if (
        origin["schema_version"] != "project-blueprint.origin.v1"
        or origin["blueprint"] != "project-blueprint"
        or origin["blueprint_version"] != FROM_VERSION
        or origin["generator_version"] != FROM_VERSION
        or origin["harness_kernel_version"] != FROM_VERSION
        or origin["profile"] != identity["profile"]
        or origin["project_slug"] != identity["id"]
        or origin["project_name"] != identity["name"]
        or origin["authority"] != AUTHORITY_TEXT
        or not isinstance(origin["migration_history"], list)
        or not isinstance(origin["generated_paths"], list)
        or not isinstance(origin["initial_generation"], dict)
    ):
        raise MigrationError("live.origin: invalid or mixed v2 provenance")
    if origin["migration_history"] and (
        origin["migration_history"][-1].get("to_blueprint_version") != FROM_VERSION
    ):
        raise MigrationError("live.origin: migration history does not reach v2")
    if any(item.get("id") == "MIG-3000" for item in origin["migration_history"]):
        raise MigrationError("live.origin: migration ID already exists")
    return origin


def validate_input_bundle(bundle: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    expect_exact_keys(
        bundle,
        {"schema_version", "migration", "legacy_git_policy_classification", "live"},
        "input",
    )
    if bundle["schema_version"] != INPUT_SCHEMA:
        raise MigrationError("input: mixed live version or invalid schema_version")
    if bundle["legacy_git_policy_classification"] != "canonical_unadopted_baseline":
        raise MigrationError(
            "input: adopted or divergent vague Git policy requires project reconciliation"
        )
    live = expect_exact_keys(
        bundle["live"], {"project", "tools", "validators", "origin"}, "live"
    )
    project = validate_v2_project(live["project"])
    if live["tools"] != canonical_v2_tools():
        raise MigrationError(
            "live.tools: ambiguous, adopted, divergent, or mixed legacy Git policy"
        )
    validate_v2_validators(live["validators"], project["project"]["profile"])
    origin = validate_v2_origin(live["origin"], project)
    event = validate_migration_event(bundle["migration"], origin["profile"])
    if event["id"] in {item.get("id") for item in origin["migration_history"]}:
        raise MigrationError("migration: duplicate migration ID")
    return live, event


def migrate_project(project: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(project)
    migrated["schema_version"] = "harness.project.v3"
    migrated["project"]["blueprint_version"] = TO_VERSION
    migrated = {
        "schema_version": migrated["schema_version"],
        "project": migrated["project"],
        "collaboration_profile": unknown_collaboration_profile(),
        "paths": migrated["paths"],
        "commands": migrated["commands"],
        "project_checks": migrated["project_checks"],
        "extensions": migrated["extensions"],
        "mutable_work_status": migrated["mutable_work_status"],
    }
    return migrated


def migrate_validators(validators: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(validators)
    migrated["schema_version"] = "harness.validators.v3"
    migrated["validator_version"] = TO_VERSION
    commands = migrated["commands"]
    migrated["commands"] = {
        "bootstrap": commands["bootstrap"],
        "check": commands["check"],
        "ready_frontier": commands["ready_frontier"],
        "collaboration_assessment": {
            "run": "python -B .agent/scripts/validate.py --assess-collaboration",
            "writes": [],
        },
        "test": commands["test"],
        "project_checks": commands["project_checks"],
        "adoption_verify": commands["adoption_verify"],
        "refresh": commands["refresh"],
        "closure": commands["closure"],
    }
    migrated["required_core_checks"] = list(V3_REQUIRED_CORE_CHECKS)
    return migrated


def migrate_origin(origin: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(origin)
    migrated["blueprint_version"] = TO_VERSION
    migrated["generator_version"] = GENERATOR_VERSION
    migrated["harness_kernel_version"] = KERNEL_VERSION
    migrated["migration_history"].append(copy.deepcopy(event))
    added = {
        ".agent/schemas/harness-git-workflows.schema.json",
        ".agent/templates/pull-request.md",
        ".agent/workflows/README.md",
        ".agent/workflows/github-adapter.md",
        ".agent/workflows/small-team-git.json",
    }
    migrated["generated_paths"] = sorted(set(migrated["generated_paths"]) | added)
    return migrated


def rollback_evidence(source_bytes: bytes, live: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": ROLLBACK_SCHEMA,
        "live_state_role": "noncurrent_rollback_evidence",
        "permission_grant": False,
        "authority_effect": "none",
        "source_encoding": "base64_of_exact_utf8_input_bytes",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_bytes_base64": base64.b64encode(source_bytes).decode("ascii"),
        "live_state_sha256": hashlib.sha256(canonical_bytes(live)).hexdigest(),
        "live_state": copy.deepcopy(live),
        "restoration_rule": (
            "Rollback is a separately authorized project action; never mix live v2 "
            "and v3 authority."
        ),
    }


def validate_candidate_schemas(live: dict[str, Any]) -> None:
    validator_path = (
        Path(__file__).resolve().parents[1]
        / "assets/templates/core/.agent/scripts/validate.py.tmpl"
    )
    namespace: dict[str, Any] = {"__file__": str(validator_path), "__name__": "v3_schema"}
    exec(compile(validator_path.read_text(encoding="utf-8"), str(validator_path), "exec"), namespace)
    root = blueprint_root()
    kernel = loads_json((root / "shared/schemas/harness-kernel.schema.json").read_bytes())
    workflow_schema = loads_json(
        (root / "shared/schemas/harness-git-workflows.schema.json").read_bytes()
    )
    completion_schema = workflow_schema["properties"]["completion_orchestrator"]["properties"]
    completion_schema["authority_ref"]["const"] = "project-blueprint:SRC-DEC-0013"
    completion_schema["engine"]["const"] = ".agent/scripts/pb_finish.py"
    completion_schema["commands"]["const"] = [
        "pb work finish plan",
        "pb work finish apply --accept-digest <digest>",
        "pb work finish resume",
    ]
    validate_schema = namespace["validate_schema"]
    # The v3 project contract is exhaustively checked by validate_migrated_result
    # above. Do not reinterpret that frozen historical output through a newer
    # current-project schema after the Blueprint advances beyond v3.
    # Tools and validators are exhaustively checked against their frozen v3
    # vocabularies in validate_migrated_result. A later kernel major must not
    # retroactively reinterpret that historical output through current defs.
    findings = validate_schema(live["git_workflows"], workflow_schema)
    if findings:
        raise MigrationError(f"candidate git_workflows fails v3 schema: {findings}")


def validate_migrated_result(result: dict[str, Any], *, replay: bool = False) -> None:
    expect_exact_keys(
        result,
        {
            "schema_version",
            "migration",
            "live",
            "rollback_evidence",
            "transformation",
        },
        "result",
    )
    if result["schema_version"] != RESULT_SCHEMA:
        raise MigrationError("result: invalid schema_version")
    live = expect_exact_keys(
        result["live"],
        {"project", "tools", "validators", "origin", "git_workflows"},
        "result.live",
    )
    if live["project"].get("schema_version") != "harness.project.v3":
        raise MigrationError("result.live.project: not v3")
    if live["project"].get("collaboration_profile") != unknown_collaboration_profile():
        raise MigrationError("result: collaboration facts or workflow adoption were fabricated")
    if live["tools"] != current_template(".agent/tools.json.tmpl"):
        raise MigrationError("result.live.tools: not the exact v3 operation contract")
    if live["git_workflows"] != current_template(
        ".agent/workflows/small-team-git.json.tmpl"
    ):
        raise MigrationError("result.live.git_workflows: not the canonical portfolio")
    if (
        live["validators"].get("schema_version") != "harness.validators.v3"
        or live["validators"].get("validator_version") != TO_VERSION
        or live["validators"].get("required_core_checks") != V3_REQUIRED_CORE_CHECKS
        or live["validators"].get("commands", {}).get("collaboration_assessment")
        != {
            "run": "python -B .agent/scripts/validate.py --assess-collaboration",
            "writes": [],
        }
    ):
        raise MigrationError("result.live.validators: incomplete v3 contract")
    origin = live["origin"]
    if (
        origin.get("blueprint_version") != TO_VERSION
        or origin.get("generator_version") != TO_VERSION
        or origin.get("harness_kernel_version") != TO_VERSION
        or not origin.get("migration_history")
        or origin["migration_history"][-1] != result["migration"]
    ):
        raise MigrationError("result.live.origin: migration provenance is incoherent")
    rollback = expect_exact_keys(
        result["rollback_evidence"],
        {
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
        },
        "result.rollback_evidence",
    )
    try:
        source_bytes = base64.b64decode(
            rollback["source_bytes_base64"], validate=True
        )
    except (ValueError, TypeError) as error:
        raise MigrationError(f"result.rollback_evidence: invalid base64: {error}") from error
    if (
        rollback["schema_version"] != ROLLBACK_SCHEMA
        or rollback["permission_grant"] is not False
        or rollback["live_state_role"] != "noncurrent_rollback_evidence"
        or hashlib.sha256(source_bytes).hexdigest() != rollback["source_sha256"]
        or hashlib.sha256(canonical_bytes(rollback["live_state"])).hexdigest()
        != rollback["live_state_sha256"]
    ):
        raise MigrationError("result.rollback_evidence: digest or authority mismatch")
    source = loads_json(source_bytes)
    if source.get("live") != rollback["live_state"]:
        raise MigrationError("result.rollback_evidence: exact source/live state mismatch")
    transformation = result["transformation"]
    if transformation != {
        "project_commands_executed": False,
        "network_accessed": False,
        "collaborators_inferred": False,
        "workflow_recommended": False,
        "workflow_adopted": False,
        "hosted_state_assumed": False,
    }:
        raise MigrationError("result.transformation: non-authorizing limits changed")
    validate_candidate_schemas(live)
    if replay:
        replayed = migrate_document(copy.deepcopy(result), canonical_bytes(result))
        if replayed != result:
            raise MigrationError("result: second migration application is not an exact no-op")


def migrate_document(document: dict[str, Any], source_bytes: bytes) -> dict[str, Any]:
    if document.get("schema_version") == RESULT_SCHEMA:
        validate_migrated_result(document, replay=False)
        return copy.deepcopy(document)
    live, event = validate_input_bundle(document)
    result = {
        "schema_version": RESULT_SCHEMA,
        "migration": copy.deepcopy(event),
        "live": {
            "project": migrate_project(live["project"]),
            "tools": current_template(".agent/tools.json.tmpl"),
            "validators": migrate_validators(live["validators"]),
            "origin": migrate_origin(live["origin"], event),
            "git_workflows": current_template(
                ".agent/workflows/small-team-git.json.tmpl"
            ),
        },
        "rollback_evidence": rollback_evidence(source_bytes, live),
        "transformation": {
            "project_commands_executed": False,
            "network_accessed": False,
            "collaborators_inferred": False,
            "workflow_recommended": False,
            "workflow_adopted": False,
            "hosted_state_assumed": False,
        },
    }
    validate_migrated_result(result, replay=False)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or materialize the closed 2.0.0-to-3.0.0 reference migration."
    )
    parser.add_argument("--input", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    if sys.version_info < (3, 11):
        print("ERROR: Python 3.11+ is required.", file=sys.stderr)
        return 2
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    try:
        document, source_bytes = load_json_document(input_path)
        result = migrate_document(document, source_bytes)
        validate_migrated_result(result, replay=True)
        if args.output is not None:
            output = args.output.expanduser().resolve()
            if output == input_path:
                raise MigrationError("refusing in-place migration output")
            if output.exists():
                raise MigrationError("refusing to replace an existing output path")
            if not output.parent.is_dir():
                raise MigrationError("output parent must already exist")
            with output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(canonical_bytes(result).decode("utf-8"))
    except (MigrationError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "schema_version": CHECK_SCHEMA,
                "result": "pass",
                "from_version": FROM_VERSION,
                "to_version": TO_VERSION,
                "permission_grant": False,
                "project_commands_executed": False,
                "network_accessed": False,
                "workflow_adopted": False,
                "output_written": args.output is not None,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
