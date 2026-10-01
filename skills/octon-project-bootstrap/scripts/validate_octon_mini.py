#!/usr/bin/env python3
"""Validate Octon source, contracts, templates, and profile builds."""

from __future__ import annotations

import importlib.util
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
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
            and (candidate / "dossier/artifact-types.json").is_file()
            and (candidate / "shared/schemas").is_dir()
        ):
            return candidate
    return candidates[0]


ROOT = octon_mini_source_root()


def repository_path(value: str) -> Path:
    path = Path(value)
    skill_prefix = Path("skills/octon-project-bootstrap")
    try:
        relative = path.relative_to(skill_prefix)
    except ValueError:
        return ROOT / path
    return SKILL_ROOT / relative
REQUIRED_PATHS = (
    ".github/workflows/validate.yml",
    ".gitignore",
    "AGENTS.md",
    "ARCHITECTURE_DECISIONS.md",
    "ARCHITECTURAL_PATTERN_INTEGRATION_REVIEW.md",
    "CHANGELOG.md",
    "GIT_WORKFLOW.md",
    "LICENSE",
    "README.md",
    "RELEASE.md",
    "RELEASE_READINESS.md",
    "VERSION",
    "VELOCITY_ROADMAP.md",
    "VELOCITY_VALIDATION.md",
    "octon",
    "octon.json",
    "docs/COMPATIBILITY.md",
    "docs/AUTONOMOUS_DELIVERY.md",
    "docs/AUTONOMOUS_DELIVERY_VALIDATION.md",
    "docs/DECISION_GOVERNANCE.md",
    "docs/GUIDED_SETUP.md",
    "docs/GOLDEN_PATHS.md",
    "docs/LONG_RUNNING_WORK.md",
    "docs/LONG_RUNNING_WORK_VALIDATION.md",
    "docs/REAL_PROJECT_VALIDATION.md",
    "docs/examples/DECISION_GOVERNANCE_WORKED_EXAMPLE.md",
    "docs/examples/GUIDED_SETUP_WORKED_EXAMPLE.md",
    "dossier/SPECIFICATION.md",
    "dossier/artifact-types.json",
    "dossier/references/REFERENCE_EVIDENCE.md",
    "harness/SPECIFICATION.md",
    "harness/references/REFERENCE_EVIDENCE.md",
    "migrations/0.2.0-to-1.0.0.md",
    "migrations/1.0.0-to-1.0.1.md",
    "migrations/1.0.1-to-2.0.0.md",
    "migrations/2.0.0-to-3.0.0.md",
    "migrations/3.0.0-to-3.1.0.md",
    "migrations/3.1.0-to-4.0.0.md",
    "migrations/3.1.0-to-4.1.0.md",
    "migrations/3.1.0-to-4.2.0.md",
    "migrations/4.0.0-to-4.1.0.md",
    "migrations/4.1.0-to-4.2.0.md",
    "patterns/README.md",
    "patterns/catalog.json",
    "patterns/schemas/pattern-catalog.schema.json",
    "patterns/schemas/pattern-record.schema.json",
    "patterns/records/PAT-0001-lifecycle-disposition.json",
    "patterns/records/PAT-0002-governed-change-and-effects.json",
    "patterns/records/PAT-0003-architecture-proof.json",
    "patterns/architecture-proof/README.md",
    "patterns/architecture-proof/schema.json",
    "patterns/architecture-proof/templates/spike.json",
    "patterns/architecture-proof/templates/reference-slice.json",
    "patterns/architecture-proof/templates/provider-qualification.json",
    "patterns/architecture-proof/templates/adversarial-fixture-pack.json",
    "patterns/architecture-proof/templates/readiness-evidence.json",
    "patterns/fixtures/context-pack/valid/active.json",
    "patterns/fixtures/architecture-proof/valid/unsupported-spike.json",
    "patterns/fixtures/architecture-proof/valid/inconclusive-provider.json",
    "pyproject.toml",
    "shared/GENERATION_CONTRACT.md",
    "shared/source-contracts/large-project-phase-profile.schema.json",
    "shared/source-contracts/long-running-work-benchmark-report.schema.json",
    "shared/source-contracts/autonomous-delivery-benchmark-report.schema.json",
    "shared/optional-schemas/context-pack-manifest.schema.json",
    "shared/reference-evidence.json",
    "shared/source-contracts/information-state-semantics.json",
    "shared/source-contracts/information-state-semantics.schema.json",
    "shared/source-contracts/commands.json",
    "shared/source-contracts/commands.schema.json",
    "shared/source-contracts/diagnostic-catalog.json",
    "shared/source-contracts/diagnostic-catalog.schema.json",
    "shared/source-contracts/hook-detector-protocol.json",
    "shared/source-contracts/hook-detector-protocol.schema.json",
    "shared/source-contracts/setup-questions.json",
    "shared/source-contracts/setup-questions.schema.json",
    "shared/source-contracts/legacy-reference-allowlist.json",
    "shared/source-contracts/legacy-reference-allowlist.schema.json",
    "shared/source-contracts/validation-benchmark-report.schema.json",
    "shared/source-contracts/profile-manifest.json",
    "shared/source-contracts/profile-manifest-v3.schema.json",
    "shared/source-contracts/profile-manifest.schema.json",
    "docs/DISPOSABLE_RUNTIME_QUALIFICATION.md",
    "skills/octon-project-bootstrap/scripts/installation_runtime.py",
    "skills/octon-project-bootstrap/scripts/qualify_disposable_runtime.py",
    "skills/octon-project-bootstrap/scripts/test_disposable_runtime.py",
    "skills/octon-project-bootstrap/scripts/fixture_admission.py",
    "skills/octon-project-bootstrap/scripts/installation_runtime_v2.py",
    "skills/octon-project-bootstrap/scripts/test_fixture_admission.py",
    "shared/source-contracts/admission-fixture-inventory.json",
    "docs/AUTHORIZATION_ADMISSION_QUALIFICATION.md",
    "skills/octon-project-bootstrap/scripts/protected_fixture.py",
    "skills/octon-project-bootstrap/scripts/test_protected_fixture.py",
    "shared/source-contracts/protected-fixture-inventory.json",
    "shared/source-contracts/protected-fixture-v1.schema.json",
    "docs/PROTECTED_FIXTURE_QUALIFICATION.md",
    "shared/schemas/artifact-catalog.schema.json",
    "shared/schemas/dossier-artifact-registry.schema.json",
    "shared/schemas/dossier-path-authority.schema.json",
    "shared/schemas/dossier-records.schema.json",
    "shared/schemas/harness-artifact-registry.schema.json",
    "shared/schemas/harness-assurance-records.schema.json",
    "shared/schemas/harness-autonomous-delivery.schema.json",
    "shared/schemas/harness-capability-records.schema.json",
    "shared/schemas/harness-collaboration-profile.schema.json",
    "shared/schemas/harness-continuation.schema.json",
    "shared/schemas/harness-current-state.schema.json",
    "shared/schemas/harness-decision-governance.schema.json",
    "shared/schemas/harness-decision-reuse.schema.json",
    "shared/schemas/harness-diagnostics-v2.schema.json",
    "shared/schemas/harness-diagnostics.schema.json",
    "shared/schemas/harness-extension-registry.schema.json",
    "shared/schemas/harness-focus.schema.json",
    "shared/schemas/harness-git-workflows.schema.json",
    "shared/schemas/harness-hook-candidate.schema.json",
    "shared/schemas/harness-kernel.schema.json",
    "shared/schemas/harness-package-registry.schema.json",
    "shared/schemas/harness-plan-summary.schema.json",
    "shared/schemas/harness-project-check-evidence-v3.schema.json",
    "shared/schemas/harness-project-check-evidence.schema.json",
    "shared/schemas/harness-record.schema.json",
    "shared/schemas/harness-scm.schema.json",
    "shared/schemas/harness-transaction-v3.schema.json",
    "shared/schemas/harness-transaction.schema.json",
    "shared/schemas/harness-validation-proof.schema.json",
    "shared/schemas/harness-work-completion.schema.json",
    "shared/schemas/octon-mini-bootstrap-migration-seed.schema.json",
    "shared/schemas/octon-mini-project-origin.schema.json",
    "shared/schemas/octon-project-origin.schema.json",
    "shared/schemas/octon-bootstrap-upgrade.schema.json",
    "migrations/4.2.0-to-5.0.0.md",
    "docs/IDENTITY_TRANSITION.md",
    "skills/octon-project-bootstrap/scripts/test_identity_transition.py",
    "shared/schemas/octon-mini-bootstrap-setup-answers.schema.json",
    "shared/schemas/octon-mini-bootstrap-setup-session-v2.schema.json",
    "shared/schemas/octon-mini-bootstrap-setup-session.schema.json",
    "shared/schemas/octon-mini-bootstrap-upgrade.schema.json",
    "shared/schemas/reference-evidence.schema.json",
    "skills/octon-project-bootstrap/SKILL.md",
    "skills/octon-project-bootstrap/agents/openai.yaml",
    "skills/octon-project-bootstrap/references/dossier-model.md",
    "skills/octon-project-bootstrap/references/autonomous-delivery.md",
    "skills/octon-project-bootstrap/references/generation-workflow.md",
    "skills/octon-project-bootstrap/references/guided-setup.md",
    "skills/octon-project-bootstrap/references/harness-model.md",
    "skills/octon-project-bootstrap/references/profile-selection.md",
    "skills/octon-project-bootstrap/scripts/install_skill.py",
    "skills/octon-project-bootstrap/scripts/migrate_1_0_1_to_2_0_0.py",
    "skills/octon-project-bootstrap/scripts/migrate_2_0_0_to_3_0_0.py",
    "skills/octon-project-bootstrap/scripts/migrate_3_1_0_to_4_0_0.py",
    "skills/octon-project-bootstrap/scripts/adopt_project.py",
    "skills/octon-project-bootstrap/scripts/benchmark_validation.py",
    "skills/octon-project-bootstrap/scripts/benchmark_long_running_work.py",
    "skills/octon-project-bootstrap/scripts/benchmark_autonomous_delivery.py",
    "skills/octon-project-bootstrap/scripts/collaboration_project.py",
    "skills/octon-project-bootstrap/scripts/detect_project.py",
    "skills/octon-project-bootstrap/scripts/guided_workflow.py",
    "skills/octon-project-bootstrap/scripts/init_project.py",
    "skills/octon-project-bootstrap/scripts/package_project.py",
    "skills/octon-project-bootstrap/scripts/profile_large_project.py",
    "skills/octon-project-bootstrap/scripts/octon.py",
    "skills/octon-project-bootstrap/scripts/source_delivery_effect.py",
    "skills/octon-project-bootstrap/scripts/source_work_completion.py",
    "skills/octon-project-bootstrap/scripts/plan_adoption.py",
    "skills/octon-project-bootstrap/scripts/scaffold_project.py",
    "skills/octon-project-bootstrap/scripts/setup_session.py",
    "skills/octon-project-bootstrap/scripts/test_acceptance.py",
    "skills/octon-project-bootstrap/scripts/test_autonomous_delivery.py",
    "skills/octon-project-bootstrap/scripts/test_autonomous_delivery_faults.py",
    "skills/octon-project-bootstrap/scripts/test_autonomous_delivery_package.py",
    "skills/octon-project-bootstrap/scripts/test_autonomous_delivery_benchmark.py",
    "skills/octon-project-bootstrap/scripts/test_architectural_patterns.py",
    "skills/octon-project-bootstrap/scripts/test_benchmark_validation.py",
    "skills/octon-project-bootstrap/scripts/test_long_running_work_benchmark.py",
    "skills/octon-project-bootstrap/scripts/test_long_running_work.py",
    "skills/octon-project-bootstrap/scripts/test_long_running_work_faults.py",
    "skills/octon-project-bootstrap/scripts/test_long_running_work_package.py",
    "skills/octon-project-bootstrap/scripts/test_adapter_safety.py",
    "skills/octon-project-bootstrap/scripts/test_migration_1_0_1_to_2_0_0.py",
    "skills/octon-project-bootstrap/scripts/test_migration_2_0_0_to_3_0_0.py",
    "skills/octon-project-bootstrap/scripts/test_migration_3_1_0_to_4_0_0.py",
    "skills/octon-project-bootstrap/scripts/test_migration_4_0_0_to_4_1_0.py",
    "skills/octon-project-bootstrap/scripts/test_migration_4_1_0_to_4_2_0.py",
    "skills/octon-project-bootstrap/scripts/test_velocity_workflows.py",
    "skills/octon-project-bootstrap/scripts/test_work_completion.py",
    "skills/octon-project-bootstrap/scripts/test_source_delivery_effect.py",
    "skills/octon-project-bootstrap/scripts/test_source_work_completion.py",
    "skills/octon-project-bootstrap/scripts/test_guided_setup.py",
    "skills/octon-project-bootstrap/scripts/test_octon_launchers.py",
    "skills/octon-project-bootstrap/scripts/test_installation_binding.py",
    "skills/octon-project-bootstrap/scripts/upgrade_project.py",
    "skills/octon-project-bootstrap/scripts/validate_octon_mini.py",
    "skills/octon-project-bootstrap/scripts/validate_source_contracts.py",
    "skills/octon-project-bootstrap/scripts/validate_skill_package.py",
    "skills/octon-project-bootstrap/scripts/verify_reference_evidence.py",
    "skills/octon-project-bootstrap/fixtures/decision-governance/README.md",
    "skills/octon-project-bootstrap/fixtures/continuation/README.md",
    "skills/octon-project-bootstrap/fixtures/continuation/valid/blocked-operation.json",
    "skills/octon-project-bootstrap/fixtures/continuation/invalid/mutations.json",
    "skills/octon-project-bootstrap/fixtures/work-completion/README.md",
    "skills/octon-project-bootstrap/fixtures/work-completion/valid-config.json",
    "skills/octon-project-bootstrap/fixtures/work-completion/invalid-mutations.json",
    "skills/octon-project-bootstrap/fixtures/guided-setup/README.md",
    "skills/octon-project-bootstrap/fixtures/guided-setup/valid/initialization-answers.json",
    "skills/octon-project-bootstrap/fixtures/guided-setup/valid/adoption-answers.json",
    "skills/octon-project-bootstrap/fixtures/guided-setup/valid/upgrade-answers.json",
    "skills/octon-project-bootstrap/fixtures/guided-setup/invalid/mutations.json",
    "skills/octon-project-bootstrap/fixtures/decision-governance/valid/empty-register.json",
    "skills/octon-project-bootstrap/fixtures/decision-governance/invalid/mutations.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/README.md",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/valid/v1-standard.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/valid/expectations.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/adopted-without-v2-evidence.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/ambiguous-dependency.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/configured-legacy-command.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/hard-advisory-confusion.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/legacy-blocked-direct-to-execution.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/mixed-live-authority.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/mixed-live-project-authority.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/mixed-live-validator-authority.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/mismatched-version-executable.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/nonexternal-migration-authority.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/nonreciprocal-plan-task-link.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/task-cycle.json",
    "skills/octon-project-bootstrap/fixtures/migrations/1.0.1-to-2.0.0/invalid/unsafe-explicit-command.json",
    "skills/octon-project-bootstrap/fixtures/migrations/2.0.0-to-3.0.0/README.md",
    "skills/octon-project-bootstrap/fixtures/migrations/2.0.0-to-3.0.0/valid/v2-minimal.json",
    "skills/octon-project-bootstrap/fixtures/migrations/2.0.0-to-3.0.0/valid/expectations.json",
    "skills/octon-project-bootstrap/fixtures/migrations/2.0.0-to-3.0.0/invalid/adopted-legacy-git-policy.json",
    "skills/octon-project-bootstrap/fixtures/migrations/2.0.0-to-3.0.0/invalid/divergent-legacy-tools.json",
    "skills/octon-project-bootstrap/fixtures/migrations/2.0.0-to-3.0.0/invalid/fabricated-collaboration-evidence.json",
    "skills/octon-project-bootstrap/fixtures/migrations/2.0.0-to-3.0.0/invalid/fabricated-workflow-adoption.json",
    "skills/octon-project-bootstrap/fixtures/migrations/2.0.0-to-3.0.0/invalid/mixed-live-project-version.json",
    "skills/octon-project-bootstrap/fixtures/migrations/2.0.0-to-3.0.0/invalid/mixed-live-validator-version.json",
    "skills/octon-project-bootstrap/fixtures/migrations/3.1.0-to-4.0.0/README.md",
    "skills/octon-project-bootstrap/fixtures/migrations/4.0.0-to-4.1.0/README.md",
    "skills/octon-project-bootstrap/fixtures/migrations/4.1.0-to-4.2.0/README.md",
    "skills/octon-project-bootstrap/fixtures/long-running-work/fault-matrix.json",
    "skills/octon-project-bootstrap/fixtures/adapter-safety/cases.json",
    "skills/octon-project-bootstrap/fixtures/autonomous-delivery/invalid-mutations.json",
    "skills/octon-project-bootstrap/fixtures/migrations/2.0.0-to-3.0.0/invalid/nonexternal-migration-authority.json",
)
DOSSIER_HEADINGS = (
    "## 1. Executive summary",
    "## 2. Design principles",
    "## 3. Reference-dossier crosswalk",
    "## 4. General artifact taxonomy",
    "## 5. Coverage profiles",
    "## 6. Recommended directory structure",
    "## 7. Core artifact section outlines and schemas",
    "## 8. Relationships and lifecycle",
    "## 9. Governance model",
    "## 10. Adoption checklist and quality gates",
    "## 11. Gaps and new recommendations",
)
HARNESS_HEADINGS = tuple(f"## {number}." for number in range(1, 18))


class DuplicateKeyError(ValueError):
    pass


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


def lint_supported_schema(
    schema: Any,
    location: str,
    issues: list[str],
    *,
    root_schema: dict[str, Any] | None = None,
) -> None:
    if not isinstance(schema, dict):
        issues.append(f"{location}: schema node must be an object")
        return
    root_schema = root_schema or schema
    unexpected = sorted(set(schema) - SUPPORTED_SCHEMA_KEYWORDS)
    if unexpected:
        issues.append(
            f"{location}: unsupported schema keywords: {', '.join(unexpected)}"
        )
    schema_type = schema.get("type")
    allowed_types = {
        "array",
        "boolean",
        "integer",
        "null",
        "number",
        "object",
        "string",
    }
    declared_types = (
        schema_type if isinstance(schema_type, list) else [schema_type]
    )
    if schema_type is not None and (
        not declared_types
        or any(not isinstance(item, str) for item in declared_types)
        or len(declared_types) != len(set(declared_types))
        or any(item not in allowed_types for item in declared_types)
    ):
        issues.append(f"{location}.type: unsupported or duplicate JSON type")
    required = schema.get("required")
    if required is not None and (
        not isinstance(required, list)
        or any(not isinstance(item, str) for item in required)
        or len(required) != len(set(required))
    ):
        issues.append(f"{location}.required: expected unique string array")
    enum = schema.get("enum")
    if enum is not None and (not isinstance(enum, list) or not enum):
        issues.append(f"{location}.enum: expected nonempty array")
    for field in ("minItems", "maxItems", "minLength"):
        value = schema.get(field)
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            issues.append(f"{location}.{field}: expected nonnegative integer")
    minimum = schema.get("minimum")
    if minimum is not None and (
        not isinstance(minimum, (int, float))
        or isinstance(minimum, bool)
    ):
        issues.append(f"{location}.minimum: expected number")
    maximum = schema.get("maximum")
    if maximum is not None and (
        not isinstance(maximum, (int, float))
        or isinstance(maximum, bool)
    ):
        issues.append(f"{location}.maximum: expected number")
    if (
        isinstance(minimum, (int, float))
        and not isinstance(minimum, bool)
        and isinstance(maximum, (int, float))
        and not isinstance(maximum, bool)
        and minimum > maximum
    ):
        issues.append(f"{location}: minimum exceeds maximum")
    min_items = schema.get("minItems")
    max_items = schema.get("maxItems")
    if (
        isinstance(min_items, int)
        and not isinstance(min_items, bool)
        and isinstance(max_items, int)
        and not isinstance(max_items, bool)
        and min_items > max_items
    ):
        issues.append(f"{location}: minItems exceeds maxItems")
    if "uniqueItems" in schema and not isinstance(schema["uniqueItems"], bool):
        issues.append(f"{location}.uniqueItems: expected boolean")
    pattern = schema.get("pattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            issues.append(f"{location}.pattern: expected string")
        else:
            try:
                re.compile(pattern)
            except re.error as error:
                issues.append(f"{location}.pattern: invalid regular expression: {error}")
    reference = schema.get("$ref")
    if reference is not None and (
        not isinstance(reference, str) or not reference.startswith("#/")
    ):
        issues.append(f"{location}.$ref: only local references are supported")
    elif isinstance(reference, str):
        current: Any = root_schema
        for raw_part in reference[2:].split("/"):
            part = raw_part.replace("~1", "/").replace("~0", "~")
            if not isinstance(current, dict) or part not in current:
                issues.append(f"{location}.$ref: unresolved reference {reference}")
                break
            current = current[part]
    schema_format = schema.get("format")
    if schema_format not in {None, "date", "date-time"}:
        issues.append(f"{location}.format: unsupported format {schema_format!r}")
    if "additionalProperties" in schema and not isinstance(
        schema["additionalProperties"], bool
    ):
        issues.append(f"{location}.additionalProperties: expected boolean")
    for field in ("properties", "$defs"):
        children = schema.get(field)
        if children is None:
            continue
        if not isinstance(children, dict):
            issues.append(f"{location}.{field}: expected object")
            continue
        for name, child in children.items():
            lint_supported_schema(
                child,
                f"{location}.{field}.{name}",
                issues,
                root_schema=root_schema,
            )
    items = schema.get("items")
    if items is not None:
        lint_supported_schema(
            items,
            f"{location}.items",
            issues,
            root_schema=root_schema,
        )
    all_of = schema.get("allOf")
    if all_of is not None:
        if not isinstance(all_of, list):
            issues.append(f"{location}.allOf: expected array")
        else:
            for index, child in enumerate(all_of):
                lint_supported_schema(
                    child,
                    f"{location}.allOf[{index}]",
                    issues,
                    root_schema=root_schema,
                )
    for field in ("if", "then", "else"):
        child = schema.get(field)
        if child is not None:
            lint_supported_schema(
                child,
                f"{location}.{field}",
                issues,
                root_schema=root_schema,
            )


def load_scaffolder():
    path = SKILL_ROOT / "scripts" / "scaffold_project.py"
    spec = importlib.util.spec_from_file_location("octon_mini_scaffold", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load scaffolder: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_docs(issues: list[str]) -> None:
    dossier = (ROOT / "dossier/SPECIFICATION.md").read_text(encoding="utf-8")
    positions = [dossier.find(heading) for heading in DOSSIER_HEADINGS]
    for heading, position in zip(DOSSIER_HEADINGS, positions):
        if position < 0:
            issues.append(f"dossier blueprint missing section: {heading}")
    if positions != sorted(positions):
        issues.append("dossier blueprint sections are out of order")
    for label in (
        "[Observed: CF]",
        "[Observed: COE]",
        "[Observed: both]",
        "[Inferred]",
        "[Recommended]",
    ):
        if label not in dossier:
            issues.append(f"dossier blueprint missing evidence label: {label}")
    for field in (
        "Category / classification:",
        "Purpose:",
        "Questions it must answer:",
        "Intended audience:",
        "Expected owner or maintainer:",
        "Required inputs:",
        "Outputs / downstream consumers:",
        "Recommended format:",
        "Source-of-truth expectations:",
        "Dependencies and related artifacts:",
        "Creation timing:",
        "Update triggers:",
        "Validation / quality checks:",
        "Omission or combination:",
        "Representative evidence:",
    ):
        if field not in dossier:
            issues.append(f"dossier artifact specifications missing field: {field}")
    if len(
        re.findall(
            r"^#### [A-Z][A-Z0-9]*-[0-9]{4} — ",
            dossier,
            re.MULTILINE,
        )
    ) < 25:
        issues.append("dossier blueprint has too few stable artifact specifications")

    harness = (ROOT / "harness/SPECIFICATION.md").read_text(encoding="utf-8")
    positions = [harness.find(prefix) for prefix in HARNESS_HEADINGS]
    for prefix, position in zip(HARNESS_HEADINGS, positions):
        if position < 0:
            issues.append(f"harness blueprint missing numbered section: {prefix}")
    if positions != sorted(positions):
        issues.append("harness blueprint sections are out of order")
    if "stable domain-neutral kernel" not in harness:
        issues.append("harness blueprint lacks bounded universal-kernel definition")
    if "strict JSON" not in harness:
        issues.append("harness blueprint lacks canonical strict JSON contract")
    if "Observed — both" not in harness or "Recommendation" not in harness:
        issues.append("harness blueprint lacks evidence/recommendation distinction")

    for path in (
        ROOT / "dossier/references/REFERENCE_EVIDENCE.md",
        ROOT / "harness/references/REFERENCE_EVIDENCE.md",
    ):
        text = path.read_text(encoding="utf-8")
        if "/Users/" in text:
            issues.append(f"{path.relative_to(ROOT)} exposes an absolute source path")


def validate_config_and_schemas(issues: list[str], scaffolder: Any) -> None:
    try:
        config = load_json(ROOT / "octon.json")
    except (ValueError, json.JSONDecodeError) as error:
        issues.append(f"invalid octon.json: {error}")
        return
    if config.get("overwrite_existing_paths") is not False:
        issues.append("octon.json must prohibit overwriting")
    if config.get("new_generation_requires_empty_target") is not True:
        issues.append("octon.json must require an empty new-project target")
    if config.get("minimum_python") != "3.11":
        issues.append("octon.json Python minimum must be 3.11")
    if config.get("schema_version") != "octon.source.repository.v1":
        issues.append("octon.json schema version must be octon-mini.source.repository.v2")
    if config.get("product") != "octon" or config.get("display_name") != "Octon":
        issues.append("octon.json product identity differs")
    if config.get("octon_mini_version_source") != "VERSION":
        issues.append("octon.json version source differs")
    if config.get("license") != {
        "spdx": "MIT-0",
        "file": "LICENSE",
        "copyright": "Copyright 2026 Cooper Online Enterprises",
        "installed_source_bundle_includes_license": True,
        "generated_project_includes_license": False,
        "generated_project_license_requires_project_owned_decision": True,
    }:
        issues.append("octon.json MIT-0 source-license boundary differs")
    if config.get("bootstrap_capability") != {
        "display_name": "Octon Project Bootstrap",
        "skill_id": "octon-project-bootstrap",
        "description": "Create, adopt, configure, operate, recover, or upgrade a project-local Octon agent harness and project dossier.",
    }:
        issues.append("octon.json bootstrap capability identity differs")
    try:
        manifest = scaffolder.load_generation_policy()
        profiles = tuple(scaffolder.profile_layers(manifest))
    except ValueError as error:
        issues.append(f"invalid authoritative profile manifest: {error}")
        return
    source_license_rules = [
        item
        for item in manifest.get("rules", [])
        if isinstance(item, dict) and item.get("id") == "source-license"
    ]
    if len(source_license_rules) != 1 or source_license_rules[0] != {
        "id": "source-license",
        "source": "octon-mini:LICENSE",
        "match": "exact",
        "suffix": None,
        "disposition": "source_only",
        "profiles": [],
        "inventory_paths": None,
        "inventory_count": None,
        "inventory_paths_sha256": None,
        "output": None,
        "reason": "The repository MIT-0 license ships in the source and installed source bundle; target-project licensing remains project-owned.",
    }:
        issues.append("profile manifest lacks the exact source-only MIT-0 license rule")
    if not any(
        isinstance(item, dict)
        and item.get("path") == "LICENSE"
        and item.get("match") == "exact"
        for item in manifest.get("forbidden_outputs", [])
    ):
        issues.append("profile manifest must forbid LICENSE in generated projects")
    if config.get("reference_evidence_registry") != "shared/reference-evidence.json":
        issues.append("octon.json reference-evidence registry path mismatch")
    workflow_paths = {
        "workflow_interface": "skills/octon-project-bootstrap/scripts/octon.py",
        "new_project_initializer": "skills/octon-project-bootstrap/scripts/init_project.py",
        "established_project_adopter": "skills/octon-project-bootstrap/scripts/adopt_project.py",
        "live_project_upgrader": "skills/octon-project-bootstrap/scripts/upgrade_project.py",
        "guided_setup_engine": "skills/octon-project-bootstrap/scripts/setup_session.py",
        "advanced_new_project_generator": (
            "skills/octon-project-bootstrap/scripts/scaffold_project.py"
        ),
        "advanced_existing_project_planner": (
            "skills/octon-project-bootstrap/scripts/plan_adoption.py"
        ),
    }
    for key, expected_path in workflow_paths.items():
        if config.get(key) != expected_path:
            issues.append(f"octon.json {key} path mismatch")
        elif not repository_path(expected_path).is_file():
            issues.append(f"octon.json {key} path is absent")
    kernel = scaffolder.kernel_paths(manifest)
    if len(kernel) != 7 or any(path.parent != Path(".agent") for path in kernel):
        issues.append("profile manifest kernel files do not define the seven-file kernel")
    harness = config.get("modules", {}).get("harness", {})
    expected_trigger_contract = {
        "command_manifest": "shared/source-contracts/commands.json",
        "scm_trigger_file": ".agent/scm.json",
        "package_registry_file": ".agent/packages.json",
        "collaboration_workflow_package": "small-team-git-portfolio",
        "installed_collaboration_workflow_file": (
            ".agent/workflows/small-team-git.json"
        ),
        "collaboration_workflow_installed_by_default": False,
    }
    for key, value in expected_trigger_contract.items():
        if harness.get(key) != value:
            issues.append(f"octon.json harness {key} contract mismatch")
    if harness.get("supported_base_workflows") != [
        "solo_direct",
        "solo_hybrid",
        "pair_pr",
        "tiny_pr",
    ]:
        issues.append("octon.json small-team workflow vocabulary mismatch")
    if harness.get("maximum_supported_write_capable_humans") != 5:
        issues.append("octon.json maximum supported team size must be five")
    source_governance = config.get("source_governance", {})
    if source_governance != {
        "architecture_decisions": "ARCHITECTURE_DECISIONS.md",
        "decision_governance": "docs/DECISION_GOVERNANCE.md",
        "decision_governance_schema": "shared/schemas/harness-decision-governance.schema.json",
        "architectural_pattern_catalog": "patterns/catalog.json",
        "pattern_catalog_generated": False,
        "pattern_catalog_automatic_adoption": False,
        "profile_manifest": "shared/source-contracts/profile-manifest.json",
        "information_state_semantics": (
            "shared/source-contracts/information-state-semantics.json"
        ),
        "setup_question_catalog": "shared/source-contracts/setup-questions.json",
        "setup_question_catalog_generated": False,
        "setup_session_schema": (
            "shared/schemas/octon-mini-bootstrap-setup-session.schema.json"
        ),
        "setup_answers_schema": (
            "shared/schemas/octon-mini-bootstrap-setup-answers.schema.json"
        ),
        "autonomous_delivery_schema": "shared/schemas/harness-autonomous-delivery.schema.json",
        "architecture_proof_schema": "patterns/architecture-proof/schema.json",
        "architecture_proof_generated": False,
        "intent_delegation_foundation": {
            "status": "source_only_shadow",
            "schema": "shared/source-contracts/governance-foundation-v2.schema.json",
            "implementation": "skills/octon-project-bootstrap/scripts/governance_shadow.py",
            "qualification": "skills/octon-project-bootstrap/scripts/test_governance_shadow.py",
            "generated": False,
            "runtime_authorization": False,
        },
    }:
        issues.append("octon.json source-governance contract differs")
    if "profiles" in config or "optional_contracts" in config:
        issues.append(
            "octon.json must not duplicate profile or optional-package inventory"
        )

    profile_schema_path = ROOT / "shared/source-contracts/profile-manifest-v3.schema.json"
    try:
        profile_schema = load_json(profile_schema_path)
    except (ValueError, json.JSONDecodeError) as error:
        issues.append(f"invalid profile-manifest schema: {error}")
    else:
        lint_supported_schema(
            profile_schema,
            "profile-manifest.schema.json",
            issues,
        )

    if not profiles:
        issues.append("profile manifest resolved no profiles")

    for path in sorted((ROOT / "shared/schemas").glob("*.schema.json")):
        try:
            schema = load_json(path)
        except (ValueError, json.JSONDecodeError) as error:
            issues.append(f"invalid strict JSON schema {path.name}: {error}")
            continue
        if not isinstance(schema, dict) or not schema.get("$id"):
            issues.append(f"{path.name}: schema lacks $id")
        elif "example.invalid" in schema["$id"]:
            issues.append(f"{path.name}: placeholder schema ID remains")
        lint_supported_schema(schema, path.name, issues)


def markdown_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*$", text, re.MULTILINE):
        normalized = heading.strip().casefold()
        normalized = re.sub(r"[^a-z0-9 _-]", "", normalized)
        normalized = re.sub(r"[\s_]+", "-", normalized).strip("-")
        anchors.add(normalized)
    return anchors


def validate_manifest_projections(issues: list[str], scaffolder: Any) -> None:
    try:
        manifest = scaffolder.load_generation_policy()
        profiles = scaffolder.profile_contracts(manifest)
    except ValueError as error:
        issues.append(f"cannot validate manifest projections: {error}")
        return

    for projection in manifest.get("documentation_projections", []):
        if not isinstance(projection, dict):
            continue
        source = projection.get("source")
        for raw_target in projection.get("targets", []):
            if not isinstance(raw_target, str):
                continue
            raw_path, separator, anchor = raw_target.partition("#")
            target = repository_path(raw_path)
            if not target.is_file():
                issues.append(
                    f"manifest documentation projection target is absent: {raw_target}"
                )
                continue
            text = target.read_text(encoding="utf-8")
            if separator and anchor not in markdown_anchors(text):
                issues.append(
                    f"manifest documentation projection anchor is absent: {raw_target}"
                )
            if source == "profiles":
                folded = text.casefold()
                for profile_id, profile in profiles.items():
                    label = str(profile.get("label", "")).casefold()
                    if profile_id.casefold() not in folded and label not in folded:
                        issues.append(
                            f"{raw_path}: profile projection omits {profile_id}"
                        )
            elif source == "acceptance_criteria":
                if raw_path == "harness/SPECIFICATION.md":
                    section = text.split("## 14. Acceptance criteria", 1)[-1].split(
                        "## 15. Evidence crosswalk", 1
                    )[0]
                    documented = {
                        int(match.group(1))
                        for match in re.finditer(
                            r"^(\d+)\. ", section, re.MULTILINE
                        )
                    }
                    expected = {
                        int(item["id"])
                        for item in manifest.get("acceptance_criteria", [])
                        if isinstance(item, dict) and isinstance(item.get("id"), int)
                    }
                    if documented != expected:
                        issues.append(
                            "harness acceptance criteria differ from the profile manifest"
                        )
                elif raw_path.endswith("test_acceptance.py") and (
                    'PROFILE_MANIFEST["acceptance_criteria"]' not in text
                ):
                    issues.append(
                        "acceptance suite does not derive coverage from the profile manifest"
                    )

    profile_fields = {"profile", "from_profile", "to_profile", "minimum_profile"}
    expected_profile_ids = set(profiles)

    def visit(value: Any, location: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_location = f"{location}.{key}"
                if (
                    key in profile_fields
                    and isinstance(child, dict)
                    and isinstance(child.get("enum"), list)
                    and set(child["enum"]) != expected_profile_ids
                ):
                    issues.append(
                        f"{child_location}: profile enum differs from the manifest"
                    )
                visit(child, child_location)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{location}[{index}]")

    for path in sorted((ROOT / "shared/schemas").glob("*.schema.json")):
        try:
            visit(load_json(path), path.name)
        except (OSError, ValueError, json.JSONDecodeError):
            continue

    validator_template = (
        SKILL_ROOT / "assets/templates/core/.agent/scripts/validate.py.tmpl"
    ).read_text(encoding="utf-8")
    if (
        "{{PROFILE_OPERATIONAL_FILES_JSON}}" not in validator_template
        or "{{KERNEL_FILES_JSON}}" not in validator_template
        or "CORE_OPERATIONAL_FILES" in validator_template
    ):
        issues.append(
            "generated validator inventories are not projected from the manifest"
        )


def validate_artifact_types(issues: list[str], scaffolder: Any) -> None:
    try:
        manifest = scaffolder.load_generation_policy()
        profiles = tuple(scaffolder.profile_layers(manifest))
    except ValueError as error:
        issues.append(f"cannot validate artifact profiles: {error}")
        return
    try:
        source = load_json(ROOT / "dossier/artifact-types.json")
    except (ValueError, json.JSONDecodeError) as error:
        issues.append(f"invalid dossier/artifact-types.json: {error}")
        return
    if (
        not isinstance(source, dict)
        or source.get("schema_version")
        != "octon-mini.source.dossier-artifact-types.v1"
        or source.get("permission_grant") is not False
        or not isinstance(source.get("artifact_types"), list)
        or not isinstance(source.get("representations"), list)
    ):
        issues.append("dossier/artifact-types.json has an invalid v2 envelope")
        return
    artifact_types = source["artifact_types"]
    representations = source["representations"]
    ids: set[str] = set()
    paths: set[str] = set()
    for index, artifact in enumerate(artifact_types):
        if not isinstance(artifact, dict):
            issues.append(f"artifact type {index} is not an object")
            continue
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, str) or not re.fullmatch(
            r"[A-Z][A-Z0-9]*-[0-9]{4}", artifact_id
        ):
            issues.append(f"artifact type {index} has invalid four-digit ID")
        elif artifact_id in ids:
            issues.append(f"duplicate artifact type ID: {artifact_id}")
        ids.add(artifact_id)
        for required in (
            "recommended_name",
            "category",
            "classification",
            "purpose",
            "questions",
            "intended_audiences",
            "owner_role",
            "required_inputs",
            "downstream_consumers",
            "recommended_formats",
            "source_of_truth_expectations",
            "dependencies",
            "creation_timing",
            "review_cadence",
            "update_triggers",
            "validation_checks",
            "triggers",
            "omission_or_combination",
            "representative_evidence",
        ):
            if required not in artifact:
                issues.append(f"artifact {artifact_id}: missing {required}")
    if len(artifact_types) < 25:
        issues.append("artifact taxonomy is unexpectedly incomplete")

    representation_ids: set[str] = set()
    for index, representation in enumerate(representations):
        if not isinstance(representation, dict):
            issues.append(f"representation {index} is not an object")
            continue
        representation_id = representation.get("id")
        path = representation.get("path")
        type_refs = representation.get("artifact_type_ids")
        if (
            not isinstance(representation_id, str)
            or not re.fullmatch(r"REP-[0-9]{4}", representation_id)
            or representation_id in representation_ids
        ):
            issues.append(f"representation {index} has invalid or duplicate ID")
        representation_ids.add(str(representation_id))
        if (
            not isinstance(path, str)
            or not path.startswith((".agent/decisions/", "project-dossier/"))
            or path in paths
        ):
            issues.append(f"representation {representation_id}: invalid/duplicate path")
        paths.add(str(path))
        if (
            not isinstance(type_refs, list)
            or not type_refs
            or len(type_refs) != len(set(type_refs))
            or any(item not in ids for item in type_refs)
        ):
            issues.append(
                f"representation {representation_id}: invalid artifact_type_ids"
            )
        if representation.get("profile") not in profiles:
            issues.append(f"representation {representation_id}: invalid profile")
        status = representation.get("applicability", {}).get("status")
        if len(type_refs or []) > 1 and status != "combined":
            issues.append(
                f"representation {representation_id}: combined mapping lacks status"
            )
        if len(type_refs or []) == 1 and status == "combined":
            issues.append(
                f"representation {representation_id}: singleton marked combined"
            )

    for profile in profiles:
        try:
            expected_paths = (
                set(scaffolder.collect_templates(profile))
                | set(scaffolder.schema_outputs(profile))
                | set(scaffolder.project_local_source_paths(profile, manifest))
                | set(scaffolder.derived_output_paths(profile, manifest))
                | {scaffolder.origin_path(manifest)}
            )
            selected = scaffolder.selected_artifact_registry(
                profile,
                date.today().isoformat(),
                "source-validation",
                expected_paths,
            )
        except ValueError as error:
            issues.append(f"{profile} artifact selection failed: {error}")
            continue
        if not selected.get("artifact_types") or not selected.get("representations"):
            issues.append(f"{profile} artifact selection is empty")


def validate_templates(issues: list[str], scaffolder: Any) -> None:
    try:
        manifest = scaffolder.load_generation_policy()
        profiles = tuple(scaffolder.profile_layers(manifest))
        ranks = scaffolder.profile_ranks(manifest)
        highest_profile = max(ranks, key=ranks.__getitem__)
    except ValueError as error:
        issues.append(f"cannot validate templates without profile manifest: {error}")
        return
    variables = {
        "PROJECT_NAME": 'Template "Validation" [α]',
        "PROJECT_NAME_JSON": json.dumps('Template "Validation" [α]', ensure_ascii=False),
        "PROJECT_SLUG": "template-validation",
        "CREATED_DATE": "2030-01-02",
        "OCTON_MINI_VERSION": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "HARNESS_KERNEL_VERSION": scaffolder.KERNEL_VERSION,
        "PROFILE": highest_profile,
        "HARNESS_REFRESH_COMMAND": "python -B .agent/scripts/refresh.py --refresh",
        "HARNESS_REFRESH_WRITES": "[]",
        "PROFILE_OPERATIONAL_FILES_JSON": "[]",
        "DERIVED_OPERATIONAL_FILES_JSON": "[]",
        "KERNEL_FILES_JSON": "[]",
        "CURRENT_DISPATCHER_PARENT_INDEX": str(
            scaffolder.current_dispatcher_parent_index(manifest)
        ),
        "GIT_PORTFOLIO_VERSION": str(
            scaffolder.package_contract(manifest, "small-team-git-portfolio")["version"]
        ),
        "GIT_PORTFOLIO_SHA256": str(
            scaffolder.package_contract(manifest, "small-team-git-portfolio")["sha256"]
        ),
        "AUTONOMOUS_DELIVERY_VERSION": str(
            scaffolder.package_contract(manifest, "autonomous-delivery")["version"]
        ),
        "AUTONOMOUS_DELIVERY_SHA256": str(
            scaffolder.package_contract(manifest, "autonomous-delivery")["sha256"]
        ),
        "AUTONOMOUS_DELIVERY_INSTALLED_SHA256": scaffolder.installed_package_content_digest(
            scaffolder.policy_source_path(scaffolder.package_contract(manifest, "autonomous-delivery")["source"], "autonomous-delivery source"),
            scaffolder.package_contract(manifest, "autonomous-delivery")["inventory_paths"],
        ),
        "AUTONOMOUS_DELIVERY_PAYLOAD_JSON": json.dumps(
            scaffolder.package_payload_projection(
                scaffolder.policy_source_path(scaffolder.package_contract(manifest, "autonomous-delivery")["source"], "autonomous-delivery source"),
                scaffolder.package_contract(manifest, "autonomous-delivery")["inventory_paths"],
            ),
            separators=(",", ":"),
        ),
        "LONG_RUNNING_WORK_VERSION": str(
            scaffolder.package_contract(manifest, "long-running-work")["version"]
        ),
        "LONG_RUNNING_WORK_SHA256": str(
            scaffolder.package_contract(manifest, "long-running-work")["sha256"]
        ),
        "LONG_RUNNING_WORK_INSTALLED_SHA256": scaffolder.installed_package_content_digest(
            scaffolder.policy_source_path(scaffolder.package_contract(manifest, "long-running-work")["source"], "long-running-work source"),
            scaffolder.package_contract(manifest, "long-running-work")["inventory_paths"],
        ),
        "LONG_RUNNING_WORK_PAYLOAD_JSON": json.dumps(
            scaffolder.package_payload_projection(
                scaffolder.policy_source_path(scaffolder.package_contract(manifest, "long-running-work")["source"], "long-running-work source"),
                scaffolder.package_contract(manifest, "long-running-work")["inventory_paths"],
            ),
            separators=(",", ":"),
        ),
    }
    templates_root = SKILL_ROOT / "assets/templates"
    extension_registry_template = (
        templates_root / "standard/.agent/extensions/registry.json.tmpl"
    )
    if (
        '"core_version": "{{HARNESS_KERNEL_VERSION}}"'
        not in extension_registry_template.read_text(encoding="utf-8")
    ):
        issues.append(
            "extension registry must use the harness-kernel version axis, "
            "not the blueprint release version"
        )
    for profile in profiles:
        try:
            templates = scaffolder.collect_templates(profile)
            variables["PROFILE"] = profile
            variables["PROFILE_OPERATIONAL_FILES_JSON"] = json.dumps(
                scaffolder.canonical_posix_paths(
                    scaffolder.operational_project_paths(profile, manifest)
                ),
                separators=(",", ":"),
            )
            variables["DERIVED_OPERATIONAL_FILES_JSON"] = json.dumps(
                scaffolder.canonical_posix_paths(
                    scaffolder.derived_output_paths(profile, manifest)
                    & scaffolder.operational_project_paths(profile, manifest)
                ),
                separators=(",", ":"),
            )
            variables["KERNEL_FILES_JSON"] = json.dumps(
                scaffolder.canonical_posix_paths(scaffolder.kernel_paths(manifest)),
                separators=(",", ":"),
            )
        except ValueError as error:
            issues.append(f"{profile} template collection failed: {error}")
            continue
        missing = sorted(set(scaffolder.kernel_paths(manifest)) - set(templates))
        if missing:
            issues.append(f"{profile} missing manifest-declared kernel paths: {missing}")
        if any(path.suffix in {".yaml", ".yml"} for path in templates):
            issues.append(f"{profile} canonical templates still emit YAML")
        if profile != highest_profile and any(
            path.as_posix().startswith(".agents/") for path in templates
        ):
            issues.append(f"{profile} unexpectedly emits capability packages")
        for relative, template in templates.items():
            try:
                rendered = scaffolder.render(template, variables)
            except ValueError as error:
                issues.append(str(error))
                continue
            if "/Users/" in rendered:
                issues.append(f"{template.relative_to(ROOT)} contains host path")
            invalid_fixture = relative.as_posix().startswith(
                ".agent/tests/fixtures/invalid/"
            )
            if relative.suffix == ".json" and not invalid_fixture:
                try:
                    json.loads(
                        rendered,
                        object_pairs_hook=strict_object,
                        parse_constant=reject_json_constant,
                    )
                except (ValueError, json.JSONDecodeError) as error:
                    issues.append(f"{template.relative_to(ROOT)}: invalid JSON: {error}")
            if relative.suffix == ".py":
                try:
                    compile(rendered, str(template), "exec")
                except SyntaxError as error:
                    issues.append(f"{template.relative_to(ROOT)}: {error}")
            if (
                '"permission_grant": true' in rendered
                and not invalid_fixture
                and not relative.as_posix().startswith(".agent/tests/")
            ):
                issues.append(f"{template.relative_to(ROOT)} authorizes by default")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    if ".DS_Store" not in gitignore:
        issues.append(".gitignore must exclude Finder metadata")
    if list(templates_root.rglob("*.yaml.tmpl")) or list(
        templates_root.rglob("*.yml.tmpl")
    ):
        issues.append("canonical template tree contains YAML outputs")


def validate_skill_and_release(issues: list[str]) -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    if "TODO" in skill:
        issues.append("SKILL.md contains TODO")
    non_transfer_terms = (
        "Transfer structure and validators",
        "facts",
        "identities",
        "permissions",
        "accepted decisions",
        "evidence",
        "readiness",
    )
    if not all(term in skill for term in non_transfer_terms):
        issues.append("SKILL.md lacks explicit non-transfer boundary")
    if "octon adopt plan|apply" not in skill or "bounded semantic" not in skill:
        issues.append("SKILL.md lacks established-project adoption routing")
    openai = (SKILL_ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
    if "$octon-project-bootstrap" not in openai:
        issues.append("agents/openai.yaml does not invoke $octon-project-bootstrap")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if version != "5.0.0":
        issues.append(f"current VERSION must be 5.0.0, found {version!r}")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    release = (ROOT / "RELEASE.md").read_text(encoding="utf-8")
    release_compact = re.sub(r"\s+", " ", release)
    for path, text in (("CHANGELOG.md", changelog), ("RELEASE.md", release)):
        if version not in text:
            issues.append(f"{path} lacks the {version} release")
    release_statements = (
        "The GitHub repository rename to `cooperonlineenterprises/octon-mini`",
        "local project-directory rename to `octon-mini` are complete",
        "The repository is public.",
        "Octon Mini 4.2.0 is released through its annotated tag and GitHub Release",
        "Final candidate `96d79099e5e84077565b0a9e91866084c62d50b0`",
        "Exact released main `22c1c142e42caa91edbf6550315c3938ff747c6f`",
        "required run `32703858216`",
        "candidate matrix `32707378408`",
        "automatic smoke run `32714926981`",
        "integrated-main matrix `32715261752`",
        "Annotated tag object `d5d67efea6105d9ec51eab3022420a49b3cf875c`",
        "https://github.com/cooperonlineenterprises/octon-mini/releases/tag/v4.2.0",
        "No separate package registry or package channel was used",
        "Final corrective candidate `242ef4c496cc8fc95a7b550371beeb01bb4a6513`",
        "Integrated `main` revision `6d1cfb0f13d300b9d4b78bf7078cf07daa7febd6`",
        "`main-smoke` run `32540532990`",
        "integrated-main split-matrix run `32540555019`",
        "all 24 matrix jobs successful",
        "Annotated tag object `1df893ec42ac2c49e5944268cafec30757d06430`",
        "https://github.com/cooperonlineenterprises/octon-mini/releases/tag/v4.1.0",
        "release-evidence policy `accept_disclosed_absence`",
        "Independent real-project maturity, target-project adoption, and project or production readiness are not established",
        "Repository ruleset `21013176` applies Stage A `solo_hybrid` protection",
        "did not itself authorize the later repository rename, visibility change,",
        "approved `KEEP_PUBLIC_WITH_LICENSE — MIT-0`",
        "canonical MIT No Attribution license, SPDX identifier `MIT-0`",
        "Public visibility, licensed source reuse, and an Octon Mini release are separate facts",
        "generator does not copy the source `LICENSE` into a target snapshot",
    )
    for statement in release_statements:
        if statement not in release_compact:
            issues.append(f"RELEASE.md lacks current repository-state assertion: {statement}")
    if "## 4.1.0 — 2026-08-22" not in changelog:
        issues.append("CHANGELOG.md must contain the exact 4.1.0 release heading")
    if "## 4.2.0 — 2026-08-24" not in changelog:
        issues.append("CHANGELOG.md must contain the exact 4.2.0 release heading")
    if "## 4.0.0 — 2026-08-18" not in changelog:
        issues.append("CHANGELOG.md must retain the exact 4.0.0 release heading")
    for stale in (
        "## 4.1.0 — Unreleased",
        "## 4.2.0 — Unreleased",
        "Current development targets unreleased Octon Mini `4.2.0`",
        "This source work is unreleased",
        "Current source development targets `4.1.0` and is unreleased",
        "This source work is not released",
        "## 4.0.0 — Unreleased",
        "Octon Mini 4.0.0 remains unreleased",
        "no `v4.0.0` tag, GitHub Release, or package publication has occurred",
    ):
        if stale in changelog or stale in release:
            issues.append(f"current release material retains stale pre-release text: {stale}")
    release_record_requirements = {
        "README.md": (
            "Octon Mini 4.2.0 is",
            "annotated tag `v4.2.0` targets",
            "`22c1c142e42caa91edbf6550315c3938ff747c6f`",
            "do not acquire the release",
        ),
        "RELEASE_READINESS.md": (
            "# Octon Mini Release-Readiness Record",
            "## 4.2.0 completed release",
            "`96d79099e5e84077565b0a9e91866084c62d50b0`",
            "`d5d67efea6105d9ec51eab3022420a49b3cf875c`",
            "`32715261752`",
            "## 4.1.0 completed release",
            "`242ef4c496cc8fc95a7b550371beeb01bb4a6513`",
            "`1df893ec42ac2c49e5944268cafec30757d06430`",
            "`32540555019`",
            "`accept_disclosed_absence`",
            "Independent real-project maturity | `not_established`",
        ),
        "GIT_WORKFLOW.md": (
            "Octon Mini 4.2.0 was integrated through",
            "`22c1c142e42caa91edbf6550315c3938ff747c6f`",
            "`32714926981`",
            "`32715261752`",
            "annotated tag `v4.2.0`",
            "Octon Mini 4.1.0 was integrated through",
            "`6d1cfb0f13d300b9d4b78bf7078cf07daa7febd6`",
            "`32540532990`",
            "`32540555019`",
            "annotated tag `v4.1.0`",
        ),
        "docs/LONG_RUNNING_WORK_VALIDATION.md": (
            "Final candidate: `242ef4c496cc8fc95a7b550371beeb01bb4a6513`",
            "Integrated and released revision: `6d1cfb0f13d300b9d4b78bf7078cf07daa7febd6`",
            "`32540555019`",
            "`accept_disclosed_absence`",
            "independent field maturity is not established",
        ),
    }
    for relative_path, statements in release_record_requirements.items():
        record_text = (ROOT / relative_path).read_text(encoding="utf-8")
        for statement in statements:
            if statement not in record_text:
                issues.append(
                    f"{relative_path} lacks current release assertion: {statement}"
                )
    source_decisions = (ROOT / "ARCHITECTURE_DECISIONS.md").read_text(
        encoding="utf-8"
    )
    for statement in (
        "## SRC-DEC-0015 — Post-rebrand audit remediation controls",
        "licensing disposition remains blocked pending explicit owner input",
        "excluding the unset `LICENSE_DECISION`",
        "| `permission_grant` | `false` |",
    ):
        if statement not in source_decisions:
            issues.append(f"SRC-DEC-0015 lacks required non-authority boundary: {statement}")
    for statement in (
        "## SRC-DEC-0016 — Public MIT-0 source licensing",
        "`LICENSE_DECISION: KEEP_PUBLIC_WITH_LICENSE — MIT-0`",
        "`Copyright 2026 Cooper Online Enterprises`",
        "Automatic project generation does not copy the source `LICENSE`",
        "| `permission_grant` | `false` |",
    ):
        if statement not in source_decisions:
            issues.append(f"SRC-DEC-0016 lacks required license boundary: {statement}")
    for decision_id, statements in {
        "SRC-DEC-0019": (
            "## SRC-DEC-0019 — Governed autonomous-delivery capability",
            "`available_not_activated`",
            "only independent human confirmation of those exact bytes supplies authority",
            "unknown outcome stops with zero automatic retries",
            "| `permission_grant` | `false` |",
        ),
        "SRC-DEC-0020": (
            "## SRC-DEC-0020 — Standing source-release evidence policy",
            "Technically scoped final patch and minor",
            "Direct autonomous-worker spending remains zero",
            "v4.1.0 `accept_disclosed_absence` choice remains release-specific",
            "| `permission_grant` | `false` |",
        ),
    }.items():
        for statement in statements:
            if statement not in source_decisions:
                issues.append(f"{decision_id} lacks required accepted boundary: {statement}")

    expected_license = (
        "MIT No Attribution\n\n"
        "Copyright 2026 Cooper Online Enterprises\n\n"
        "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \"Software\"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so.\n\n"
        "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n"
    )
    try:
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    except OSError as error:
        issues.append(f"LICENSE cannot be read: {error}")
    else:
        if license_text != expected_license:
            issues.append("LICENSE differs from the exact owner-approved MIT-0 text")
    try:
        with (ROOT / "pyproject.toml").open("rb") as source:
            pyproject = tomllib.load(source)
    except (OSError, tomllib.TOMLDecodeError) as error:
        issues.append(f"pyproject.toml is invalid: {error}")
        pyproject = {}
    project_metadata = pyproject.get("project", {})
    if not isinstance(project_metadata, dict):
        issues.append("pyproject.toml project metadata must be a table")
        project_metadata = {}
    if project_metadata.get("requires-python") != ">=3.11":
        issues.append("pyproject.toml does not enforce Python 3.11+")
    if project_metadata.get("version") != version:
        issues.append("pyproject.toml version differs from VERSION")
    if project_metadata.get("name") != "octon":
        issues.append("pyproject.toml project name differs from release identity")
    if project_metadata.get("license") != "MIT-0":
        issues.append("pyproject.toml license expression must be MIT-0")
    if project_metadata.get("license-files") != ["LICENSE"]:
        issues.append("pyproject.toml license-files must contain only LICENSE")
    octon_mini_metadata = pyproject.get("tool", {}).get("octon-mini", {})
    if not isinstance(octon_mini_metadata, dict) or (
        octon_mini_metadata.get("runtime-dependencies") != []
        or octon_mini_metadata.get("canonical-structured-format") != "strict-json"
    ):
        issues.append("pyproject.toml Octon Mini runtime contract is invalid")
    config = load_json(ROOT / "octon.json")
    kernel_version = config.get("modules", {}).get("harness", {}).get(
        "kernel_version"
    )
    if kernel_version != "4.2.0":
        issues.append("octon-mini.json harness kernel must be 4.2.0")
    scaffolder = load_scaffolder()
    if scaffolder.GENERATOR_VERSION != version:
        issues.append("scaffolder generator version differs from VERSION")
    if scaffolder.KERNEL_VERSION != kernel_version:
        issues.append("scaffolder kernel version differs from octon-mini.json")
    schema_template = (
        SKILL_ROOT / "assets/templates/core/.agent/schema.json.tmpl"
    ).read_text(encoding="utf-8")
    validator_template = (
        SKILL_ROOT / "assets/templates/core/.agent/scripts/validate.py.tmpl"
    ).read_text(encoding="utf-8")
    if f'"kernel_version": "{kernel_version}"' not in schema_template:
        issues.append("generated schema kernel version differs from octon-mini.json")
    if f'KERNEL_VERSION = "{kernel_version}"' not in validator_template:
        issues.append("generated validator kernel version differs from octon-mini.json")

    commands = (
        (
            [sys.executable, "-B", "scripts/validate_skill_package.py"],
            SKILL_ROOT,
            "skill package validator",
        ),
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/verify_reference_evidence.py"),
            ],
            ROOT,
            "reference evidence validator",
        ),
    )
    for command, cwd, label in commands:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            issues.append(
                f"{label} failed: {result.stderr.strip() or result.stdout.strip()}"
            )


def validate_ci_contract(issues: list[str]) -> None:
    workflow_path = ROOT / ".github/workflows/validate.yml"
    try:
        workflow = workflow_path.read_text(encoding="utf-8")
    except OSError as error:
        issues.append(f"cannot read CI workflow: {error}")
        return
    push_block = re.search(
        r"(?ms)^  push:\n(?P<body>.*?)(?=^  [A-Za-z_][^:\n]*:|\Z)",
        workflow,
    )
    if (
        push_block is None
        or push_block.group("body") != "    branches:\n      - main\n"
    ):
        issues.append("CI workflow push validation must target only main")
    if re.search(r"(?m)^  pull_request:\s*$", workflow) is None:
        issues.append("CI workflow must retain pull-request validation")
    expected_concurrency = (
        "concurrency:\n"
        "  group: ${{ github.workflow }}-${{ github.event_name }}-${{ "
        "github.event.pull_request.number || github.run_id }}\n"
        "  cancel-in-progress: ${{ github.event_name == 'pull_request' }}"
    )
    if expected_concurrency not in workflow:
        issues.append(
            "CI workflow concurrency must cancel only superseded runs for the "
            "same pull request and give push/manual evidence unique groups"
        )
    required_snippets = {
        "read-only contents permission": "permissions:\n  contents: read",
        "manual full-matrix trigger": "workflow_dispatch:",
        "stable pull-request gate": (
            "pull-request-gate:\n    name: required\n"
            "    if: github.event_name == 'pull_request'"
        ),
        "minimum-runtime pull-request gate": 'python-version: "3.11"',
        "main smoke gate": (
            "main-smoke:\n    name: main-smoke\n"
            "    if: github.event_name == 'push' && "
            "github.ref == 'refs/heads/main'"
        ),
        "current-runtime main smoke": 'python-version: "3.14"',
        "manual-only full source matrix": (
            "full-source-matrix:\n    name: full source / ${{ matrix.os }} / Python "
            "${{ matrix.python }}\n"
            "    if: github.event_name == 'workflow_dispatch'"
        ),
        "manual-only full acceptance matrix": (
            "full-acceptance-matrix:\n    name: full acceptance / ${{ matrix.os }} / Python "
            "${{ matrix.python }}\n"
            "    if: github.event_name == 'workflow_dispatch'"
        ),
        "evidence-preserving cancellation": (
            "cancel-in-progress: ${{ github.event_name == 'pull_request' }}"
        ),
        "pull-request timeout": "timeout-minutes: 45",
        "main timeout": "timeout-minutes: 45",
        "release timeout": "timeout-minutes: 90",
        "pinned checkout action": (
            "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803"
        ),
        "pinned setup-python action": (
            "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1"
        ),
        "skill metadata validation": (
            "python -B skills/octon-project-bootstrap/scripts/"
            "validate_skill_package.py"
        ),
        "reference evidence validation": (
            "python -B skills/octon-project-bootstrap/scripts/"
            "verify_reference_evidence.py"
        ),
        "benchmark methodology validation": (
            "python -B skills/octon-project-bootstrap/scripts/"
            "test_benchmark_validation.py"
        ),
        "cross-platform launcher validation": (
            "python -B skills/octon-project-bootstrap/scripts/"
            "test_octon_launchers.py"
        ),
        "Octon source validation": (
            "python -B skills/octon-project-bootstrap/scripts/validate_octon_mini.py"
        ),
        "acceptance suite": (
            "python -B skills/octon-project-bootstrap/scripts/test_acceptance.py"
        ),
    }
    for label, snippet in required_snippets.items():
        if snippet not in workflow:
            issues.append(f"CI workflow lacks {label}")
    tag_aware_checkout = (
        "      - uses: actions/checkout@"
        "d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0\n"
        "        with:\n"
        "          fetch-tags: true\n"
        "          fetch-depth: 0"
    )
    if workflow.count(tag_aware_checkout) != 4:
        issues.append(
            "every CI checkout must fetch tags and full history for the exact pinned preparation-baseline fixture"
        )
    matrix_os = "os: [ubuntu-latest, macos-latest, windows-latest]"
    if workflow.count(matrix_os) != 2:
        issues.append(
            "manual source and acceptance matrices must each cover Ubuntu, macOS, and Windows"
        )
    matrix_python = 'python: ["3.11", "3.12", "3.13", "3.14"]'
    if workflow.count(matrix_python) != 2:
        issues.append(
            "manual source and acceptance matrices must each cover Python 3.11-3.14"
        )
    if workflow.count("timeout-minutes: 90") != 2:
        issues.append(
            "manual source and acceptance matrices must retain separate 90-minute bounds"
        )
    source_validation_command = (
        "python -B skills/octon-project-bootstrap/scripts/validate_octon_mini.py"
    )
    if workflow.count(source_validation_command) != 3:
        issues.append(
            "CI workflow must run source/profile validation in the pull-request, main-smoke, "
            "and manually dispatched source matrix jobs"
        )
    acceptance_command = (
        "python -B skills/octon-project-bootstrap/scripts/test_acceptance.py"
    )
    if workflow.count(acceptance_command) != 2:
        issues.append(
            "CI workflow must run acceptance exactly in the pull-request gate "
            "and manually dispatched acceptance matrix"
        )


def validate_executable_contracts(issues: list[str]) -> None:
    commands = (
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/validate_source_contracts.py"),
            ],
            ROOT,
            "source-only architectural contract validation",
        ),
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/test_architectural_patterns.py"),
            ],
            ROOT,
            "architectural pattern adversarial fixtures",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_governance_shadow.py")],
            ROOT,
            "intent/delegation shadow coverage and compatibility fixtures",
        ),
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/test_benchmark_validation.py"),
            ],
            ROOT,
            "validation benchmark methodology and enforcement fixtures",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_long_running_work_benchmark.py")],
            ROOT,
            "long-running-work benchmark methodology fixtures",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_autonomous_delivery_benchmark.py")],
            ROOT,
            "autonomous-delivery benchmark methodology fixtures",
        ),
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/test_octon_launchers.py"),
            ],
            ROOT,
            "cross-platform source, installed, and generated launcher fixtures",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_disposable_runtime.py")],
            ROOT,
            "disposable target runtime, dependencies, work/recovery and supported fixture conversion",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_fixture_admission.py")],
            ROOT,
            "source-only authenticated fixture admission, current effect guards and recovery",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_protected_fixture.py")],
            ROOT,
            "protected fixture remains disabled without explicit owned Linux container qualification",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_installation_binding.py")],
            ROOT,
            "explicit installation binding, confinement, collision, and state-owner fixtures",
        ),
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/test_migration_1_0_1_to_2_0_0.py"),
            ],
            ROOT,
            "1.0.1 to 2.0.0 migration fixtures",
        ),
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/test_migration_2_0_0_to_3_0_0.py"),
            ],
            ROOT,
            "2.0.0 to 3.0.0 migration fixtures",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_identity_transition.py")],
            ROOT,
            "released Mini 4.2 to Octon 5.0 identity, refusal, recovery and independence fixtures",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_long_running_work.py")],
            ROOT,
            "long-running-work functional and integration fixtures",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_long_running_work_faults.py")],
            ROOT,
            "long-running-work checkpoint fault-injection fixtures",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_long_running_work_package.py")],
            ROOT,
            "long-running-work package lifecycle fixtures",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_adapter_safety.py")],
            ROOT,
            "adapter safety fixture contract",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_autonomous_delivery.py")],
            ROOT,
            "autonomous-delivery functional and activation fixtures",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_autonomous_delivery_faults.py")],
            ROOT,
            "autonomous-delivery interruption and monotonic-effect fixtures",
        ),
        (
            [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_autonomous_delivery_package.py")],
            ROOT,
            "autonomous-delivery offline package and profile fixtures",
        ),
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/test_velocity_workflows.py"),
            ],
            ROOT,
            "4.0.0 guided, adoption, collaboration, lifecycle, and recovery workflows",
        ),
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/test_guided_setup.py"),
            ],
            ROOT,
            "guided setup catalog, read-only interview, staleness, mutation, and resume workflows",
        ),
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/test_work_completion.py"),
            ],
            ROOT,
            "governed work-completion planning, authorization, recovery, and cleanup workflows",
        ),
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/test_source_delivery_effect.py"),
            ],
            ROOT,
            "source-repository closed delivery-effect adapter and execution-branch boundaries",
        ),
        (
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts/test_source_work_completion.py"),
            ],
            ROOT,
            "source-repository work-completion task binding, candidate planning, and post-merge cleanup gates",
        ),
        (
            [
                sys.executable,
                "-B",
                str(
                    SKILL_ROOT
                    / "assets/packages/operations-observability/templates/.agent/extensions/"
                    "operations-observability/tests/test_validate.py.tmpl"
                ),
            ],
            ROOT,
            "operations and observability extension fixtures",
        ),
        (
            [
                sys.executable,
                "-B",
                str(
                    SKILL_ROOT
                    / "assets/packages/security-supply-chain/templates/.agent/extensions/"
                    "security-supply-chain/tests/test_validate.py.tmpl"
                ),
            ],
            ROOT,
            "security and supply-chain extension fixtures",
        ),
    )
    def run_fixture(item: tuple[list[str], Path, str]) -> subprocess.CompletedProcess[str]:
        command, cwd, _label = item
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    # Each suite uses its own disposable fixtures. Keep all suites and their
    # reporting order while bounding the Windows-heavy source gate's wall time.
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run_fixture, commands))
    for (_command, _cwd, label), result in zip(commands, results):
        if result.returncode:
            issues.append(
                f"{label} failed: {result.stderr.strip() or result.stdout.strip()}"
            )

    source_launcher = ROOT / "octon"
    if not source_launcher.is_file() or source_launcher.is_symlink():
        issues.append("source root octon launcher must be a regular file")
    elif not os.access(source_launcher, os.X_OK):
        issues.append("source root octon launcher must be executable")
    else:
        source_command = (
            [str(source_launcher)]
            if os.name != "nt"
            else [sys.executable, "-B", str(source_launcher)]
        )
        help_result = subprocess.run(
            [*source_command, "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if help_result.returncode:
            issues.append(f"source octon help failed: {help_result.stderr.strip()}")
        for invocation in ("./octon", "python -B octon", "py -3 -B octon"):
            if invocation not in help_result.stdout:
                issues.append(
                    f"source octon help lacks documented platform invocation {invocation!r}"
                )
        if re.search(r"(?<![A-Za-z0-9_])p" + r"b(?![A-Za-z0-9_])", help_result.stdout):
            issues.append("source octon help exposes the removed legacy command")
        local_result = subprocess.run(
            [*source_command, "check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        refusal_output = local_result.stderr + local_result.stdout
        if (
            local_result.returncode != 2
            or "OCTON-CMD-1002" not in refusal_output
            or "Nothing changed" not in refusal_output
            or 'Argv: ["./octon", "--help"]' not in refusal_output
        ):
            issues.append("source octon generated-command refusal is missing or recursive")


def snapshot_files(root: Path) -> dict[str, tuple[int, str]]:
    """Capture exact bytes and modes for a generated read-only-check assertion."""
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            result[path.relative_to(root).as_posix()] = (-1, "symlink")
        elif path.is_file():
            result[path.relative_to(root).as_posix()] = (
                path.stat().st_mode & 0o7777,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return result


def validate_generated_capabilities(target: Path) -> list[str]:
    errors: list[str] = []
    try:
        manifest = load_json(target / ".agent/commands.json")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"generated command inventory cannot be loaded: {error}"]
    capabilities = manifest.get("capabilities", []) if isinstance(manifest, dict) else []
    commands = manifest.get("commands", []) if isinstance(manifest, dict) else []
    capability_ids = {
        item.get("id") for item in capabilities if isinstance(item, dict)
    }
    if None in capability_ids or len(capability_ids) != len(capabilities):
        errors.append("generated capability IDs are missing or ambiguous")
    for capability in capabilities:
        if not isinstance(capability, dict):
            continue
        if capability.get("display_name") in {
            "Octon Skill",
            "Octon Engine",
            "Octon Manager",
            "Octon Tool",
            "Octon Service",
        }:
            errors.append(f"generated capability has a vague name: {capability.get('id')}")
        if not capability.get("purpose"):
            errors.append(f"generated capability lacks a purpose: {capability.get('id')}")
    for command in commands:
        if not isinstance(command, dict) or command.get("capability_id") not in capability_ids:
            errors.append(f"generated command lacks one valid capability: {command!r}")
    return errors


def source_text_inventory() -> dict[str, str]:
    """Return current source text under stable repository-relative labels."""
    inventory: dict[str, str] = {}

    def collect(root: Path, prefix: Path = Path(""), *, skip_bundle: bool = False) -> None:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(root)
            if any(part in {".git", "__pycache__"} for part in relative.parts):
                continue
            if path.name == ".DS_Store" or path.suffix in {".pyc", ".pyo"}:
                continue
            if skip_bundle and relative.parts[:2] == ("assets", "octon-source"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            inventory[(prefix / relative).as_posix()] = text

    try:
        SKILL_ROOT.relative_to(ROOT)
    except ValueError:
        collect(ROOT)
        collect(
            SKILL_ROOT,
            Path("skills/octon-project-bootstrap"),
            skip_bundle=True,
        )
    else:
        collect(ROOT)
    return inventory


def validate_legacy_reference_allowlist(issues: list[str]) -> None:
    """Require every old identity reference to match one exact reviewed exception."""
    allowlist_path = ROOT / "shared/source-contracts/legacy-reference-allowlist.json"
    try:
        allowlist = load_json(allowlist_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        issues.append(f"legacy reference allowlist cannot be loaded: {error}")
        return
    entries = allowlist.get("entries", []) if isinstance(allowlist, dict) else []
    if not isinstance(entries, list):
        issues.append("legacy reference allowlist entries must be an array")
        return
    pattern = allowlist.get("legacy_pattern")
    if not isinstance(pattern, str):
        issues.append("legacy reference allowlist pattern must be text")
        return
    try:
        matcher = re.compile(pattern)
    except re.error as error:
        issues.append(f"legacy reference allowlist pattern is invalid: {error}")
        return
    inventory = source_text_inventory()
    inventory.pop("shared/source-contracts/legacy-reference-allowlist.json", None)
    inventory.pop("shared/source-contracts/legacy-reference-allowlist.schema.json", None)
    allowed_spans: dict[str, list[tuple[int, int, str]]] = {}
    identifiers: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            issues.append("legacy reference allowlist contains a non-object entry")
            continue
        identifier = entry.get("id")
        path = entry.get("path")
        expected_sha256 = entry.get("file_sha256")
        expected_count = entry.get("occurrence_count")
        identifiers.append(str(identifier))
        if not isinstance(path, str) or path not in inventory:
            issues.append(f"legacy allowlist {identifier} path is absent: {path}")
            continue
        actual_sha256 = hashlib.sha256(inventory[path].encode("utf-8")).hexdigest()
        if expected_sha256 != actual_sha256:
            issues.append(
                f"legacy allowlist {identifier} file digest differs for {path}"
            )
        matches = list(matcher.finditer(inventory[path]))
        if not matches:
            issues.append(f"legacy allowlist {identifier} is stale and matches nothing")
            continue
        if not isinstance(expected_count, int) or len(matches) != expected_count:
            issues.append(
                f"legacy allowlist {identifier} matches {len(matches)} occurrences, "
                f"not the reviewed count {expected_count}"
            )
        allowed_spans.setdefault(path, []).extend(
            (match.start(), match.end(), str(identifier)) for match in matches
        )
    if len(identifiers) != len(set(identifiers)):
        issues.append("legacy reference allowlist IDs must be unique")

    legacy_pattern = re.compile(
        "|".join(
            (
                r"Project " + r"Blue" + r"print",
                r"\bBlue" + r"print\b",
                r"project" + r"-blueprint",
                r"project" + r"_bootstrap",
                r"(?<!octon-mini-)(?<!octon-)project" + r"-bootstrap",
                r"blueprint" + r"_(?:version|implementation_asset)",
                r"BLUEPRINT" + r"_VERSION",
                r"blueprint" + r":",
                r"(?<![A-Za-z0-9_])p" + r"b(?:_[A-Za-z0-9_]+|\.py)?(?![A-Za-z0-9_])",
                r"p" + r"bv-",
            )
        )
    )
    for path, text in inventory.items():
        spans = allowed_spans.get(path, [])
        for match in legacy_pattern.finditer(text):
            if any(start <= match.start() and end >= match.end() for start, end, _ in spans):
                continue
            line = text.count("\n", 0, match.start()) + 1
            issues.append(
                f"unapproved legacy reference in {path}:{line}: {match.group(0)!r}"
            )


def validate_profile_builds(issues: list[str], scaffolder: Any) -> None:
    try:
        manifest = scaffolder.load_generation_policy()
        profiles = tuple(scaffolder.profile_layers(manifest))
    except ValueError as error:
        issues.append(f"cannot build profiles without profile manifest: {error}")
        return
    try:
        git_portfolio_contract = scaffolder.package_contract(
            manifest, "small-team-git-portfolio"
        )
    except ValueError as error:
        issues.append(f"cannot validate generated Git portfolio identity: {error}")
        return
    try:
        legacy_allowlist = load_json(
            ROOT / "shared/source-contracts/legacy-reference-allowlist.json"
        )
        legacy_matcher = re.compile(legacy_allowlist["legacy_pattern"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError, re.error) as error:
        issues.append(f"cannot inspect generated legacy projections: {error}")
        return
    allowed_legacy_projections: dict[str, dict[str, Any]] = {}
    for entry in legacy_allowlist.get("entries", []):
        if not isinstance(entry, dict):
            continue
        source_path = entry.get("path")
        if (
            entry.get("classification") == "explicit_legacy_migration_input"
            and isinstance(source_path, str)
            and source_path.startswith("shared/schemas/")
        ):
            allowed_legacy_projections[
                f".agent/schemas/{Path(source_path).name}"
            ] = entry
    scaffolder_script = SKILL_ROOT / "scripts/scaffold_project.py"
    with tempfile.TemporaryDirectory(prefix="octon-mini-source-check-") as temp:
        for profile in profiles:
            for layout in ("compact", "separated"):
                target = Path(temp) / f"{profile}-{layout}"
                result = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(scaffolder_script),
                        "--target",
                        str(target),
                        "--project-name",
                        f'Source Check "{profile}" ({layout})',
                        "--profile",
                        profile,
                        "--layout",
                        layout,
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode:
                    issues.append(
                        f"{profile}/{layout} profile generation failed: "
                        f"{result.stderr.strip() or result.stdout.strip()}"
                    )
                    continue
                generated_license = target / "LICENSE"
                if generated_license.exists() or generated_license.is_symlink():
                    issues.append(
                        f"{profile}/{layout} generated the source LICENSE instead "
                        "of leaving target-project licensing project-owned"
                    )
                try:
                    scm = load_json(target / ".agent/scm.json")
                except (OSError, ValueError, json.JSONDecodeError) as error:
                    issues.append(
                        f"{profile}/{layout} generated SCM record cannot be loaded: {error}"
                    )
                else:
                    portfolio = scm.get("portfolio", {}) if isinstance(scm, dict) else {}
                    if not isinstance(portfolio, dict) or (
                        portfolio.get("version"), portfolio.get("sha256")
                    ) != (
                        git_portfolio_contract["version"],
                        git_portfolio_contract["sha256"],
                    ):
                        issues.append(
                            f"{profile}/{layout} generated SCM portfolio identity differs "
                            "from the authoritative package contract"
                        )
                launcher = target / "octon"
                required_runtime = (
                    launcher,
                    target / ".agent/scripts/octon.py",
                    target / ".agent/scripts/octon_doctor.py",
                    target / ".agent/scripts/octon_transaction.py",
                    target / ".agent/scripts/octon_work_completion.py",
                    target / ".octon-origin.json",
                )
                for path in required_runtime:
                    if not path.is_file() or path.is_symlink():
                        issues.append(
                            f"{profile}/{layout} lacks regular current runtime path {path.relative_to(target)}"
                        )
                if launcher.is_file() and not os.access(launcher, os.X_OK):
                    issues.append(f"{profile}/{layout} octon launcher is not executable")
                legacy_command = "p" + "b"
                obsolete_paths = (
                    target / legacy_command,
                    target / f".agent/scripts/{legacy_command}.py",
                    target / f".agent/scripts/{legacy_command}_doctor.py",
                    target / f".agent/scripts/{legacy_command}_finish.py",
                    target / f".agent/scripts/{legacy_command}_transaction.py",
                    target / (".project" + "-blueprint-origin.json"),
                )
                for path in obsolete_paths:
                    if path.exists() or path.is_symlink():
                        issues.append(
                            f"{profile}/{layout} contains obsolete runtime path {path.relative_to(target)}"
                        )
                for path in target.rglob("*"):
                    if (
                        path.name == legacy_command
                        or path.name.startswith(f"{legacy_command}_")
                        or path.name.startswith(f"{legacy_command}.")
                    ):
                        issues.append(
                            f"{profile}/{layout} contains an obsolete command-named output {path.relative_to(target)}"
                        )
                issues.extend(
                    f"{profile}/{layout}: {error}"
                    for error in validate_generated_capabilities(target)
                )
                for path in sorted(target.rglob("*")):
                    if not path.is_file() or path.is_symlink():
                        continue
                    try:
                        text = path.read_text(encoding="utf-8")
                    except (OSError, UnicodeError):
                        continue
                    matches = list(legacy_matcher.finditer(text))
                    if not matches:
                        continue
                    relative = path.relative_to(target).as_posix()
                    exception = allowed_legacy_projections.get(relative)
                    source = (
                        ROOT / str(exception.get("path"))
                        if isinstance(exception, dict)
                        else None
                    )
                    exact_projection = (
                        source is not None
                        and source.is_file()
                        and path.read_bytes() == source.read_bytes()
                        and len(matches) == exception.get("occurrence_count")
                        and hashlib.sha256(path.read_bytes()).hexdigest()
                        == exception.get("file_sha256")
                    )
                    if not exact_projection:
                        issues.append(
                            f"{profile}/{layout} current output contains unapproved "
                            f"legacy identity in {relative}"
                        )
                if not launcher.is_file():
                    continue
                launcher_command = [str(launcher)]
                if os.name == "nt":
                    launcher_command = [sys.executable, "-B", *launcher_command]
                help_result = subprocess.run(
                    [*launcher_command, "--help"],
                    cwd=target,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                if help_result.returncode:
                    issues.append(f"{profile}/{layout} octon help failed")
                for invocation in (
                    "Unix/macOS: ./octon",
                    "Windows: python -B octon",
                    "py -3 -B octon",
                ):
                    if invocation not in help_result.stdout:
                        issues.append(
                            f"{profile}/{layout} octon help lacks platform invocation {invocation!r}"
                        )
                before = snapshot_files(target)
                check_result = subprocess.run(
                    [*launcher_command, "check"],
                    cwd=target,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=60,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                after = snapshot_files(target)
                if check_result.returncode:
                    issues.append(
                        f"{profile}/{layout} octon check failed: "
                        f"{check_result.stderr.strip() or check_result.stdout.strip()}"
                    )
                if before != after:
                    issues.append(f"{profile}/{layout} octon check mutated the snapshot")
                residue = [
                    path.relative_to(target).as_posix()
                    for path in target.rglob("*")
                    if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}
                ]
                if residue:
                    issues.append(
                        f"{profile}/{layout} octon check left Python cache artifacts: {residue}"
                    )


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--installed-smoke",
        action="store_true",
        help="validate copied contracts and profile builds without rerunning the source checkout's exhaustive executable matrix",
    )
    args = parser.parse_args()
    issues: list[str] = []
    if sys.version_info < (3, 11):
        issues.append(f"Python 3.11+ required; found {sys.version.split()[0]}")
    for path in REQUIRED_PATHS:
        if not repository_path(path).is_file():
            issues.append(f"missing required file: {path}")
    if issues:
        print(f"FAIL: {len(issues)} issue(s)")
        for issue in issues:
            print(f"- {issue}")
        return 1
    try:
        scaffolder = load_scaffolder()
    except RuntimeError as error:
        print(f"FAIL: {error}")
        return 1
    validate_docs(issues)
    validate_config_and_schemas(issues, scaffolder)
    validate_manifest_projections(issues, scaffolder)
    validate_artifact_types(issues, scaffolder)
    validate_templates(issues, scaffolder)
    validate_skill_and_release(issues)
    validate_legacy_reference_allowlist(issues)
    validate_ci_contract(issues)
    if not args.installed_smoke:
        validate_executable_contracts(issues)
    validate_profile_builds(issues, scaffolder)
    if issues:
        print(f"FAIL: {len(issues)} issue(s)")
        for issue in issues:
            print(f"- {issue}")
        return 1
    template_count = len(list((SKILL_ROOT / "assets/templates").rglob("*.tmpl")))
    print("PASS: Octon source and profile builds are valid")
    print(f"- required files: {len(REQUIRED_PATHS)}")
    print(f"- templates: {template_count}")
    manifest = scaffolder.load_generation_policy()
    print(f"- profiles: {', '.join(scaffolder.profile_layers(manifest))}")
    print("- generated coverage: compact and separated layouts for every profile")
    print("- structured kernel: strict JSON")
    if args.installed_smoke:
        print("- installed scope: contracts and all profile/layout builds; exhaustive executable suites run in the source checkout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
