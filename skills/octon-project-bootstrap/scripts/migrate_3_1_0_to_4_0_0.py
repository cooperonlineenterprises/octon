#!/usr/bin/env python3
"""Create reviewed inert input for Project Blueprint 3.1.0 to Octon Mini 4.0.0."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import types
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
LEGACY_PRODUCT = "project-blueprint"
CURRENT_PRODUCT = "octon-mini"
LEGACY_VERSION = "3.1.0"
CURRENT_VERSION = "4.0.0"
LEGACY_ORIGIN_PATH = ".project-blueprint-origin.json"
CURRENT_ORIGIN_PATH = ".octon-mini-origin.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        module = types.ModuleType(name)
        module.__file__ = str(path)
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
        return module
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TRANSACTION = load_module(
    "octon_cross_brand_seed_transaction",
    SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_transaction.py.tmpl",
)
UPGRADE = load_module("octon_cross_brand_seed_upgrade", SCRIPT_ROOT / "upgrade_project.py")


class MigrationSeedError(ValueError):
    """Legacy provenance cannot be seeded without exact reviewed baselines."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MigrationSeedError(f"cannot load {path}: {error}") from error


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_digest(value: dict[str, Any]) -> str:
    unsigned = dict(value)
    supplied = unsigned.pop("canonical_seed_digest", None)
    expected = hashlib.sha256(TRANSACTION.canonical_bytes(unsigned)).hexdigest()
    if supplied is not None and supplied != expected:
        raise MigrationSeedError("cross-brand migration seed digest is invalid")
    return expected


def safe_path(target: Path, raw: str) -> Path:
    relative = PurePosixPath(raw)
    if (
        not raw
        or "\\" in raw
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise MigrationSeedError(f"unsafe generated path: {raw!r}")
    path = target.joinpath(*relative.parts)
    try:
        path.parent.resolve(strict=False).relative_to(target.resolve())
    except (OSError, ValueError) as error:
        raise MigrationSeedError(f"generated path escapes target: {raw}") from error
    return path


def legacy_contract(target: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    legacy_path = target / LEGACY_ORIGIN_PATH
    current_path = target / CURRENT_ORIGIN_PATH
    if current_path.exists():
        if not legacy_path.exists():
            raise MigrationSeedError(
                "Project Blueprint snapshot is already migrated to Octon Mini; second application is refused"
            )
        raise MigrationSeedError(
            "both legacy and current origin records exist; reconcile the ambiguous target before migration"
        )
    if not legacy_path.is_file() or legacy_path.is_symlink():
        raise MigrationSeedError("Project Blueprint 3.1.0 origin record is absent or unsafe")
    origin = load_json(legacy_path)
    project = load_json(target / ".agent/project.json")
    if (
        origin.get("schema_version") != "project-blueprint.origin.v1"
        or origin.get("blueprint_version") != LEGACY_VERSION
        or origin.get("blueprint") not in {None, LEGACY_PRODUCT}
        or project.get("schema_version") != "harness.project.v3"
        or project.get("project", {}).get("blueprint_version") != LEGACY_VERSION
        or origin.get("profile") != project.get("project", {}).get("profile")
    ):
        raise MigrationSeedError(
            "target is not a coherent Project Blueprint 3.1.0 snapshot"
        )
    generated_paths = origin.get("generated_paths")
    if (
        not isinstance(generated_paths, list)
        or not generated_paths
        or any(not isinstance(item, str) for item in generated_paths)
        or len(generated_paths) != len(set(generated_paths))
        or LEGACY_ORIGIN_PATH not in generated_paths
    ):
        raise MigrationSeedError("legacy generated-path provenance is malformed")
    for raw in generated_paths:
        safe_path(target, raw)
    collaboration = project.get("collaboration_profile", {})
    if collaboration.get("assessment_status") != "not_assessed":
        raise MigrationSeedError(
            "assessed collaboration v1 requires a separate project-owned v2 reassessment; it cannot be inferred by migration"
        )
    return origin, project


def derived_paths(target: Path) -> set[str]:
    validators = load_json(target / ".agent/validators.json")
    writes = validators.get("commands", {}).get("refresh", {}).get("writes", [])
    if not isinstance(writes, list) or any(not isinstance(item, str) for item in writes):
        raise MigrationSeedError("legacy refresh write contract is malformed")
    return set(writes)


def expected_role(path: str, derived: set[str]) -> tuple[str, str, str]:
    if path in derived:
        return "derived", "regenerate", "derived"
    if path == LEGACY_ORIGIN_PATH:
        return "provenance", "provenance_transaction_only", "provenance"
    if path.startswith("project-dossier/") or path in {
        ".agent/project.json",
        ".agent/policy.json",
        ".agent/context.json",
        ".agent/project-checks/evidence.json",
    }:
        return "project_owned_authoritative", "always_review", "review_required"
    if path == "AGENTS.md" or path.startswith(".agents/") or path in {
        ".agent/schema.json",
        ".agent/lifecycle.json",
        ".agent/tools.json",
        ".agent/validators.json",
        ".agent/extensions/registry.json",
    }:
        return "review_required_governance", "always_review", "review_required"
    return "octon_mini_implementation_asset", "exact_pristine_or_additive", "review_required"


def inspection(target: Path) -> dict[str, Any]:
    origin, _ = legacy_contract(target)
    derived = derived_paths(target)
    paths: list[dict[str, Any]] = []
    for raw in sorted(origin["generated_paths"]):
        role, policy, confirmation = expected_role(raw, derived)
        paths.append(
            {
                "path": raw,
                "expected_role": role,
                "expected_upgrade_policy": policy,
                "baseline_product": LEGACY_PRODUCT,
                "baseline_version": LEGACY_VERSION,
                "current": TRANSACTION.path_state(target, raw),
                "required_baseline_confirmation": confirmation,
                "review_instruction": (
                    "Derived/provenance entries carry no hash. Every static entry requires an exact old pristine hash and mode; "
                    "if that baseline is unknown, stop for specialist reconciliation."
                ),
            }
        )
    return {
        "schema_version": "octon-mini.bootstrap.cross-brand-migration-inspection.v1",
        "artifact_kind": "read_only_legacy_inventory_inspection",
        "permission_grant": False,
        "source_product": LEGACY_PRODUCT,
        "source_version": LEGACY_VERSION,
        "target_product": CURRENT_PRODUCT,
        "target_version": CURRENT_VERSION,
        "target": str(target),
        "observed_at": TRANSACTION.utc_timestamp(),
        "origin_sha256": sha(target / LEGACY_ORIGIN_PATH),
        "project_sha256": sha(target / ".agent/project.json"),
        "layout_proposal": "separated",
        "paths": paths,
        "limitations": [
            "Current hashes are observations, not claims of pristine Project Blueprint content.",
            "Legacy command and module paths are inspected only as inert data and are never imported, dispatched, or executed.",
            "This inspection cannot infer ownership, modification history, authority, or readiness.",
            "A reviewed baseline with any unknown static hash cannot produce an automatic upgrade seed.",
        ],
    }


def converted_initial_generation(origin: dict[str, Any]) -> dict[str, Any]:
    initial = origin.get("initial_generation")
    if not isinstance(initial, dict):
        raise MigrationSeedError("legacy initial-generation provenance is malformed")
    required = {
        "blueprint_version",
        "generator_version",
        "generation_id",
        "generated_on",
        "profile",
    }
    if set(initial) != required:
        raise MigrationSeedError("legacy initial-generation provenance has an unsupported shape")
    return {
        "product": LEGACY_PRODUCT,
        "version": initial["blueprint_version"],
        "generator_version": initial["generator_version"],
        "generation_id": initial["generation_id"],
        "generated_on": initial["generated_on"],
        "profile": initial["profile"],
        "layout": "separated",
    }


def convert_history(
    history: list[Any], initial: dict[str, Any], final_profile: str
) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    expected_version = initial["version"]
    expected_profile = initial["profile"]
    seen: set[str] = set()
    for item in history:
        if (
            not isinstance(item, dict)
            or item.get("schema_version") != "project-blueprint.migration.v1"
            or item.get("from_blueprint_version") != expected_version
            or item.get("from_profile") != expected_profile
            or not isinstance(item.get("id"), str)
            or re.fullmatch(r"MIG-[0-9]{4}", item["id"]) is None
            or item["id"] in seen
            or not str(item.get("authority_source", "")).startswith(("authority:", "external:"))
            or not isinstance(item.get("evidence_refs"), list)
            or not item["evidence_refs"]
        ):
            raise MigrationSeedError("legacy migration history contains an unsupported or broken entry")
        seen.add(item["id"])
        converted.append(
            {
                "schema_version": "octon-mini.project.migration.v1",
                "id": item["id"],
                "from_product": LEGACY_PRODUCT,
                "from_version": item["from_blueprint_version"],
                "to_product": LEGACY_PRODUCT,
                "to_version": item["to_blueprint_version"],
                "generator_version": item["generator_version"],
                "migrated_on": item["migrated_on"],
                "from_profile": item["from_profile"],
                "to_profile": item["to_profile"],
                "from_layout": "separated",
                "to_layout": "separated",
                "migration_guide": item["migration_guide"],
                "authority_source": item["authority_source"],
                "evidence_refs": item["evidence_refs"],
                "limitations": item["limitations"],
            }
        )
        expected_version = item["to_blueprint_version"]
        expected_profile = item["to_profile"]
    if expected_version != LEGACY_VERSION or expected_profile != final_profile:
        raise MigrationSeedError("legacy migration history does not reach the recorded 3.1.0 snapshot")
    return converted


def reviewed_seed(target: Path, review_path: Path) -> dict[str, Any]:
    origin, _ = legacy_contract(target)
    review = load_json(review_path)
    if (
        review.get("schema_version")
        != "octon-mini.bootstrap.cross-brand-migration-review.v1"
        or review.get("permission_grant") is not False
        or review.get("source_product") != LEGACY_PRODUCT
        or review.get("source_version") != LEGACY_VERSION
        or review.get("target_product") != CURRENT_PRODUCT
        or review.get("target_version") != CURRENT_VERSION
        or not isinstance(review.get("reviewed_at"), str)
        or review.get("layout") != "separated"
        or review.get("origin_sha256") != sha(target / LEGACY_ORIGIN_PATH)
        or review.get("project_sha256") != sha(target / ".agent/project.json")
    ):
        raise MigrationSeedError("cross-brand migration review is malformed or stale")
    try:
        reviewed_at = datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise MigrationSeedError("migration review reviewed_at is invalid") from error
    if reviewed_at.tzinfo is None:
        raise MigrationSeedError("migration review reviewed_at requires a timezone")
    if not str(review.get("authority_source", "")).startswith(("authority:", "external:")):
        raise MigrationSeedError("migration review lacks current project-owned authority")
    evidence_refs = review.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or not evidence_refs:
        raise MigrationSeedError("migration review requires evidence references")
    UPGRADE.evidence_record_paths(target, evidence_refs)
    derived = derived_paths(target)
    expected = set(origin["generated_paths"])
    review_paths = review.get("paths", [])
    supplied = {
        item.get("path"): item
        for item in review_paths
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    if not isinstance(review_paths, list) or len(supplied) != len(review_paths) or set(supplied) != expected:
        raise MigrationSeedError("reviewed inventory must cover every generated path exactly once")
    inventory: list[dict[str, Any]] = []
    for raw in sorted(expected):
        item = supplied[raw]
        role, policy, expected_confirmation = expected_role(raw, derived)
        if (
            item.get("role") != role
            or item.get("upgrade_policy") != policy
            or item.get("baseline_product") != LEGACY_PRODUCT
            or item.get("baseline_version") != LEGACY_VERSION
        ):
            raise MigrationSeedError(f"review attempted to weaken the fixed upgrade policy for {raw}")
        confirmation = item.get("baseline_confirmation")
        state = TRANSACTION.path_state(target, raw)
        if expected_confirmation in {"derived", "provenance"}:
            if confirmation != expected_confirmation or item.get("mode") is not None or item.get("sha256") is not None:
                raise MigrationSeedError(f"{raw} must remain hash-free {expected_confirmation} provenance")
        else:
            if confirmation not in {"exact_pristine", "project_modified"}:
                raise MigrationSeedError(f"{raw} lacks an exact reviewed static baseline")
            if not isinstance(item.get("mode"), int) or re.fullmatch(r"[a-f0-9]{64}", str(item.get("sha256"))) is None:
                raise MigrationSeedError(f"{raw} lacks an exact old mode or pristine hash")
            if confirmation == "exact_pristine" and (
                state["type"] != "file"
                or state["mode"] != item["mode"]
                or state["sha256"] != item["sha256"]
            ):
                raise MigrationSeedError(f"{raw} was confirmed pristine but differs from its reviewed baseline")
            if confirmation == "project_modified" and state["sha256"] == item["sha256"] and state["mode"] == item["mode"]:
                raise MigrationSeedError(f"{raw} is marked modified but matches its supplied pristine baseline")
        if not str(item.get("rationale", "")).strip():
            raise MigrationSeedError(f"{raw} review lacks a rationale")
        inventory.append(
            {
                "path": raw,
                "role": role,
                "upgrade_policy": policy,
                "baseline_product": LEGACY_PRODUCT,
                "baseline_version": LEGACY_VERSION,
                "mode": item.get("mode"),
                "sha256": item.get("sha256"),
            }
        )

    initial = converted_initial_generation(origin)
    legacy_baseline = {
        "schema_version": "octon-mini.bootstrap.legacy-baseline.v1",
        "product": LEGACY_PRODUCT,
        "version": LEGACY_VERSION,
        "generator_version": origin["generator_version"],
        "generation_id": origin["generation_id"],
        "profile": origin["profile"],
        "layout": "separated",
        "generated_on": origin["generated_on"],
        "project_name": origin["project_name"],
        "project_slug": origin["project_slug"],
        "harness_kernel_version": origin["harness_kernel_version"],
        "authority": origin["authority"],
        "initial_generation": initial,
        "migration_history": convert_history(
            origin.get("migration_history", []), initial, origin["profile"]
        ),
        "generated_paths": origin["generated_paths"],
        "installed_inventory": {
            "schema_version": "octon-mini.bootstrap.legacy-installed-inventory.v1",
            "product": LEGACY_PRODUCT,
            "version": LEGACY_VERSION,
            "profile": origin["profile"],
            "layout": "separated",
            "captured_on": date.today().isoformat(),
            "profile_manifest_status": "legacy_unavailable_reviewed",
            "profile_manifest_sha256": None,
            "paths": inventory,
        },
    }
    value = {
        "schema_version": "octon-mini.bootstrap.cross-brand-migration-seed.v1",
        "artifact_kind": "reviewed_legacy_inventory_seed",
        "permission_grant": False,
        "source_product": LEGACY_PRODUCT,
        "source_version": LEGACY_VERSION,
        "target_product": CURRENT_PRODUCT,
        "target_version": CURRENT_VERSION,
        "target": str(target),
        "created_at": review["reviewed_at"],
        "source_origin_state": TRANSACTION.path_state(target, LEGACY_ORIGIN_PATH),
        "source_project_state": TRANSACTION.path_state(target, ".agent/project.json"),
        "authority_source": review["authority_source"],
        "evidence_refs": sorted(set(evidence_refs)),
        "legacy_baseline": legacy_baseline,
        "limitations": [
            "This seed is reviewed planning evidence and is never written directly to the target.",
            "Legacy pb launchers and modules are inert preimages only; neither this tool nor the live upgrader executes them.",
            "The live upgrader must recheck source states, stage the complete result, and produce the only applied migration receipt.",
            "Collaboration remains unassessed; no workflow, package, hook, permission, authority, or readiness is inferred.",
        ],
    }
    value["canonical_seed_digest"] = seed_digest(value)
    return value


def write_new(path: Path, value: object) -> None:
    TRANSACTION.write_new_json(path, value)
    print(f"[ARTIFACT] {path}")


def validate_current_seed(target: Path, value: dict[str, Any]) -> None:
    legacy_contract(target)
    if (
        value.get("schema_version") != "octon-mini.bootstrap.cross-brand-migration-seed.v1"
        or value.get("permission_grant") is not False
        or value.get("source_product") != LEGACY_PRODUCT
        or value.get("source_version") != LEGACY_VERSION
        or value.get("target_product") != CURRENT_PRODUCT
        or value.get("target_version") != CURRENT_VERSION
        or value.get("target") != str(target)
        or seed_digest(value) != value.get("canonical_seed_digest")
    ):
        raise MigrationSeedError("cross-brand migration seed target, identity, or digest is invalid")
    for field, path in (
        ("source_origin_state", LEGACY_ORIGIN_PATH),
        ("source_project_state", ".agent/project.json"),
    ):
        if value.get(field) != TRANSACTION.path_state(target, path):
            raise MigrationSeedError(f"cross-brand migration seed is stale at {path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect and seed an explicit Project Blueprint 3.1.0 to Octon Mini 4.0.0 migration; "
            "legacy runtime files are treated only as inert data"
        )
    )
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--target", type=Path, required=True)
    inspect.add_argument("--output", type=Path, required=True)
    seed = commands.add_parser("seed")
    seed.add_argument("--target", type=Path, required=True)
    seed.add_argument("--review", type=Path, required=True)
    seed.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("check")
    check.add_argument("--target", type=Path, required=True)
    check.add_argument("--seed", type=Path, required=True)
    args = parser.parse_args()
    try:
        target = args.target.resolve()
        if args.command == "inspect":
            write_new(args.output, inspection(target))
            return 0
        if args.command == "seed":
            value = reviewed_seed(target, args.review)
            write_new(args.output, value)
            print(f"[DIGEST] {value['canonical_seed_digest']}")
            return 0
        value = load_json(args.seed)
        validate_current_seed(target, value)
        print("[PASS] reviewed cross-brand migration seed is current, inert, and non-authorizing")
        return 0
    except (OSError, RuntimeError, ValueError, MigrationSeedError, TRANSACTION.TransactionError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
