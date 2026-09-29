#!/usr/bin/env python3
"""Three-way, fingerprint-bound live-project upgrade planning and application."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import stat
import subprocess
import sys
import tempfile
import types
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent


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


SCAFFOLDER = load_module("octon_upgrade_scaffolder", SCRIPT_ROOT / "scaffold_project.py")
SETUP = load_module("octon_upgrade_setup", SCRIPT_ROOT / "setup_session.py")
TRANSACTION = load_module(
    "octon_upgrade_transaction",
    SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_transaction.py.tmpl",
)
CONTINUATION = load_module(
    "octon_upgrade_continuation",
    SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_continuation.py.tmpl",
)
VALIDATOR = load_module(
    "octon_upgrade_schema_validator",
    SKILL_ROOT / "assets/templates/core/.agent/scripts/validate.py.tmpl",
)


class UpgradeError(ValueError):
    """A live upgrade is ambiguous, stale, or outside automatic policy."""


CURRENT_PRODUCT = "octon"
MINI_PRODUCT = "octon-mini"
MINI_ORIGIN_PATH = ".octon-mini-origin.json"
LEGACY_PRODUCT = "project-blueprint"
CURRENT_ORIGIN_PATH = ".octon-origin.json"
LEGACY_ORIGIN_PATH = ".project-blueprint-origin.json"
LEGACY_RUNTIME_PATHS = {
    "pb",
    ".agent/scripts/pb.py",
    ".agent/scripts/pb_doctor.py",
    ".agent/scripts/pb_finish.py",
    ".agent/scripts/pb_transaction.py",
}


def origin_product(origin: dict[str, Any]) -> str:
    return str(origin.get("product", LEGACY_PRODUCT))


def origin_version(origin: dict[str, Any]) -> str:
    if origin_product(origin) in {CURRENT_PRODUCT, MINI_PRODUCT}:
        return str(origin.get("octon_mini_version", ""))
    return str(origin.get("version", origin.get("blueprint_version", "")))


def input_origin_path(origin: dict[str, Any]) -> str:
    return MINI_ORIGIN_PATH if origin_product(origin) == MINI_PRODUCT else CURRENT_ORIGIN_PATH


def load_upgrade_origin(target: Path) -> dict[str, Any]:
    """Admit exactly one typed origin; never treat the original runtime as this kit."""
    try:
        policy = SCAFFOLDER.load_generation_policy()
        occupied = SCAFFOLDER.target_installation_path_occupied(target, policy)
    except ValueError as error:
        raise UpgradeError(f"target installation binding is invalid: {error}") from error
    if occupied:
        raise UpgradeError("original Octon runtime installation conflicts with the project-local successor")
    present = [
        name for name in (CURRENT_ORIGIN_PATH, MINI_ORIGIN_PATH, LEGACY_ORIGIN_PATH)
        if (target / name).exists() or (target / name).is_symlink()
    ]
    if len(present) != 1:
        raise UpgradeError("exactly one origin is required; missing or conflicting origins refuse upgrade")
    name = present[0]
    path = target / name
    if path.is_symlink() or not path.is_file():
        raise UpgradeError("origin must be a regular file, never a symlink")
    if name == LEGACY_ORIGIN_PATH:
        raise UpgradeError("upgrade older snapshots through the released Octon Mini 4.2.0 tools first")
    try:
        origin = SCAFFOLDER.load_json(path)
        schema_name = "octon-mini-project-origin.schema.json" if name == MINI_ORIGIN_PATH else "octon-project-origin.schema.json"
        schema = SCAFFOLDER.load_json(SCAFFOLDER.octon_mini_source_root() / "shared/schemas" / schema_name)
        errors = VALIDATOR.validate_schema(origin, schema)
    except (OSError, ValueError) as error:
        raise UpgradeError(f"invalid origin: {error}") from error
    if errors:
        raise UpgradeError("invalid origin: " + "; ".join(errors[:5]))
    if name == MINI_ORIGIN_PATH and origin_version(origin) != "4.2.0":
        raise UpgradeError("the supported Mini baseline is exactly 4.2.0; use its released upgrade path first")
    inventory = origin["installed_inventory"]
    if (
        inventory["product"] != origin["product"]
        or inventory["octon_mini_version"] != origin_version(origin)
        or inventory["profile"] != origin["profile"]
        or inventory["layout"] != origin["layout"]
        or len({item["path"] for item in inventory["paths"]}) != len(inventory["paths"])
        or set(origin["generated_paths"]) != {item["path"] for item in inventory["paths"]}
        or name not in origin["generated_paths"]
    ):
        raise UpgradeError("origin and installed inventory disagree")
    for relative in origin["generated_paths"]:
        if PurePosixPath(relative).as_posix() != relative:
            raise UpgradeError("origin paths must use their exact canonical spelling")
        TRANSACTION.confined_path(target, relative)
        current = target
        for part in PurePosixPath(relative).parts:
            current = current / part
            if current.is_symlink():
                raise UpgradeError(f"symlink in installed path: {relative}")
    project_path = TRANSACTION.confined_path(target, ".agent/project.json")
    if project_path.is_symlink() or not project_path.is_file():
        raise UpgradeError("project contract must be a confined regular file")
    project = SCAFFOLDER.load_json(project_path)
    if (
        project.get("project", {}).get("octon_mini_version") != origin_version(origin)
        or project.get("project", {}).get("profile") != origin["profile"]
        or project.get("project", {}).get("id") != origin["project_slug"]
    ):
        raise UpgradeError("project identity/version/profile disagrees with origin")
    return origin


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise UpgradeError(f"cannot load {path}: {error}") from error


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def version_tuple(value: str) -> tuple[int, int, int]:
    if re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", value) is None:
        raise UpgradeError(f"invalid semantic version: {value!r}")
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def proposal_digest(value: dict[str, Any]) -> str:
    unsigned = dict(value)
    supplied = unsigned.pop("canonical_proposal_digest", None)
    expected = hashlib.sha256(TRANSACTION.canonical_bytes(unsigned)).hexdigest()
    if supplied is not None and supplied != expected:
        raise UpgradeError("upgrade proposal digest is invalid")
    return expected


def candidate_state(candidate: Path, path: str) -> dict[str, Any] | None:
    source = candidate.joinpath(*PurePosixPath(path).parts)
    if not source.exists() or source.is_symlink() or not source.is_file():
        return None
    return {
        "mode": stat.S_IMODE(source.stat().st_mode),
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }


def run_scaffold(target: Path, origin: dict[str, Any], generation_identifier: str) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_ROOT / "scaffold_project.py"),
            "--target",
            str(target),
            "--project-name",
            origin["project_name"],
            "--project-slug",
            origin["project_slug"],
            "--profile",
            origin["profile"],
            "--layout",
            origin["layout"],
            "--generation-id",
            generation_identifier,
        ],
        cwd=SCRIPT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )
    if result.returncode:
        raise UpgradeError("cannot generate candidate snapshot: " + (result.stderr or result.stdout)[:2000])


def evidence_record_paths(target: Path, refs: list[str]) -> list[str]:
    found: dict[str, list[str]] = {value: [] for value in refs}
    evidence_root = target / ".agent/evidence"
    if evidence_root.is_dir() and not evidence_root.is_symlink():
        for path in sorted(evidence_root.glob("EVD-*.md")):
            if path.is_symlink() or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines(keepends=True)
            if not lines or lines[0].strip() != "---":
                continue
            try:
                end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
                value = json.loads("".join(lines[1:end]))
            except (StopIteration, json.JSONDecodeError):
                continue
            record_id = value.get("id") if isinstance(value, dict) else None
            if record_id in found:
                found[record_id].append(path.relative_to(target).as_posix())
    index_path = target / "project-dossier/machine-readable/evidence-index.json"
    if index_path.is_file() and not index_path.is_symlink():
        value = load_json(index_path)
        for record in value.get("evidence", []) if isinstance(value, dict) else []:
            record_id = record.get("id") if isinstance(record, dict) else None
            if record_id in found:
                found[record_id].append(index_path.relative_to(target).as_posix())
    unresolved = [record_id for record_id, paths in found.items() if len(set(paths)) != 1]
    if unresolved:
        raise UpgradeError(
            "every migration evidence reference must resolve exactly once: " + ", ".join(unresolved)
        )
    return sorted({paths[0] for paths in found.values()})


def classification_rows(target: Path, candidate: Path, origin: dict[str, Any]) -> list[dict[str, Any]]:
    inventory = origin.get("installed_inventory")
    supported_inventory_schemas = {
        "octon-mini.project.installed-inventory.v1",
        "octon.project.installed-inventory.v1",
        "octon-mini.bootstrap.legacy-installed-inventory.v1",
    }
    if not isinstance(inventory, dict) or inventory.get("schema_version") not in supported_inventory_schemas:
        raise UpgradeError(
            "the recorded snapshot lacks a supported installed inventory; Project Blueprint 3.1.0 requires an exact reviewed cross-brand seed"
        )
    candidate_origin = load_json(candidate / CURRENT_ORIGIN_PATH)
    candidate_inventory = candidate_origin["installed_inventory"]
    old = {item["path"]: item for item in inventory["paths"]}
    new = {item["path"]: item for item in candidate_inventory["paths"]}
    rows: list[dict[str, Any]] = []
    for number, path in enumerate(sorted(set(old) | set(new)), 1):
        old_item = old.get(path)
        new_item = new.get(path)
        policy_item = new_item or old_item
        assert policy_item is not None
        role = policy_item["role"]
        policy = policy_item["upgrade_policy"]
        current = TRANSACTION.path_state(target, path)
        candidate_value = (
            None
            if role in {"derived", "provenance"}
            else candidate_state(candidate, path)
        )
        automatic = False
        reason: str | None = None
        dispositions: list[str] = []
        if old_item is not None and new_item is None:
            kind = "removed_upstream"
            if (origin_product(origin) == MINI_PRODUCT and path == MINI_ORIGIN_PATH) or (origin_product(origin) == LEGACY_PRODUCT and path in {
                LEGACY_ORIGIN_PATH,
                *LEGACY_RUNTIME_PATHS,
            }):
                reason = (
                    "the clean-break migration requires explicit reviewed removal; "
                    "the legacy runtime is never executed or retained"
                )
                dispositions = ["delete", "defer"]
            else:
                reason = "deletion is never automatic"
                dispositions = ["preserve_current", "delete", "defer"]
        elif role == "derived":
            kind = "derived"
            automatic = True
        elif role == "provenance":
            kind = "provenance"
            automatic = True
        elif old_item is None:
            if current["type"] == "absent":
                kind = "additive"
                automatic = role == "octon_mini_implementation_asset" and policy == "exact_pristine_or_additive"
                if not automatic:
                    reason = "new project-owned or governance-bearing path requires review"
                    dispositions = ["accept_candidate", "defer"]
            else:
                kind = "conflicting"
                reason = "candidate addition collides with current project content"
                dispositions = ["accept_candidate", "preserve_current", "defer"]
        else:
            pristine = (
                current["type"] == "file"
                and current["sha256"] == old_item.get("sha256")
                and current["mode"] == old_item.get("mode")
            )
            if pristine and candidate_value is not None and (
                candidate_value["sha256"] == current["sha256"]
                and candidate_value["mode"] == current["mode"]
            ):
                kind = "unchanged_from_pristine"
                automatic = True
            elif pristine and role == "octon_mini_implementation_asset" and policy == "exact_pristine_or_additive":
                kind = "exact_pristine_update"
                automatic = True
            else:
                kind = "project_modified" if current["type"] == "file" else "conflicting"
                reason = (
                    "instructions, policy, configuration, project facts, stable IDs, or locally modified content require review"
                )
                dispositions = ["accept_candidate", "preserve_current", "defer"]
                if path == ".agent/project.json" and current["type"] == "file":
                    dispositions.insert(1, "merge_version_only")
                    if (
                        old_item.get("baseline_product") == LEGACY_PRODUCT
                        and old_item.get("baseline_version") == "3.1.0"
                    ):
                        dispositions.insert(2, "migrate_legacy_project_contract")
                if (
                    path == ".agent/project-checks/evidence.json"
                    and current["type"] == "file"
                    and old_item.get("baseline_product") == LEGACY_PRODUCT
                    and old_item.get("baseline_version") == "3.1.0"
                ):
                    dispositions.insert(1, "migrate_legacy_project_check_evidence")
        rows.append(
            {
                "id": f"UPG-{number:04d}",
                "path": path,
                "classification": kind,
                "role": role,
                "upgrade_policy": policy,
                "old_baseline": old_item,
                "current": current,
                "candidate": candidate_value,
                "automatic": automatic,
                "review_reason": reason,
                "allowed_dispositions": dispositions,
            }
        )
    return rows


def build_proposal(
    target: Path,
    origin: dict[str, Any],
    rows: list[dict[str, Any]],
    authority_source: str,
    evidence_refs: list[str],
    cross_brand_seed_digest: str | None = None,
) -> dict[str, Any]:
    from_product = origin_product(origin)
    from_version = origin_version(origin)
    value = {
        "schema_version": "octon.bootstrap.upgrade-proposal.v1",
        "artifact_kind": "upgrade_proposal",
        "permission_grant": False,
        "created_at": TRANSACTION.utc_timestamp(),
        "target": str(target),
        "migration_kind": (
            "octon_mini_to_octon"
            if from_product == MINI_PRODUCT
            else "octon_upgrade"
        ),
        "from_product": from_product,
        "from_version": from_version,
        "to_product": CURRENT_PRODUCT,
        "to_version": SCAFFOLDER.octon_mini_version(),
        "profile": origin["profile"],
        "layout": origin["layout"],
        "authority_source": authority_source,
        "evidence_refs": sorted(set(evidence_refs)),
        "cross_brand_seed_digest": cross_brand_seed_digest,
        "governing_instruction_fingerprint": TRANSACTION.instruction_fingerprint(target),
        "classifications": rows,
        "limitations": [
            "Classification is structural and does not establish target-project readiness.",
            "Project-owned, authority-bearing, modified, deleted, moved, permission, and symlink cases require explicit review.",
            "Derived outputs are regenerated and never treated as migration evidence.",
        ],
    }
    value["canonical_proposal_digest"] = proposal_digest(value)
    return value


def validate_stored_proposal(value: dict[str, Any], target: Path) -> None:
    if (
        value.get("schema_version") != "octon.bootstrap.upgrade-proposal.v1"
        or value.get("permission_grant") is not False
        or value.get("target") != str(target)
        or value.get("to_product") != CURRENT_PRODUCT
        or value.get("to_version") != SCAFFOLDER.octon_mini_version()
    ):
        raise UpgradeError("stored upgrade proposal target, version, or authority differs")
    proposal_digest(value)
    if value.get("governing_instruction_fingerprint") != TRANSACTION.instruction_fingerprint(target):
        raise UpgradeError("governing instructions changed after upgrade proposal")
    for row in value.get("classifications", []):
        if TRANSACTION.path_state(target, row["path"]) != row["current"]:
            raise UpgradeError(f"upgrade proposal is stale at {row['path']}")


def review_map(proposal: dict[str, Any], path: Path) -> dict[str, str]:
    review = load_json(path)
    if (
        review.get("schema_version") != "octon.bootstrap.upgrade-review.v1"
        or review.get("permission_grant") is not False
        or review.get("proposal_digest") != proposal["canonical_proposal_digest"]
    ):
        raise UpgradeError("upgrade review is not bound to the exact proposal digest")
    required = {row["id"]: row for row in proposal["classifications"] if not row["automatic"]}
    dispositions: dict[str, str] = {}
    for item in review.get("dispositions", []):
        if not isinstance(item, dict) or item.get("id") in dispositions:
            raise UpgradeError("upgrade review dispositions must be unique objects")
        row = required.get(item.get("id"))
        if row is None or item.get("disposition") not in row["allowed_dispositions"]:
            raise UpgradeError(f"invalid or unexpected upgrade disposition: {item}")
        if not str(item.get("rationale", "")).strip():
            raise UpgradeError("every upgrade disposition requires a rationale")
        dispositions[item["id"]] = item["disposition"]
    missing = sorted(set(required) - set(dispositions))
    if missing:
        raise UpgradeError("upgrade review must disposition every review item: " + ", ".join(missing))
    deferred = sorted(item for item, disposition in dispositions.items() if disposition == "defer")
    if deferred:
        raise UpgradeError("deferred upgrade conflicts cannot enter an apply plan: " + ", ".join(deferred))
    return dispositions


def next_migration_id(origin: dict[str, Any]) -> str:
    numbers = []
    for item in origin.get("migration_history", []):
        match = re.fullmatch(r"MIG-([0-9]{4})", str(item.get("id"))) if isinstance(item, dict) else None
        if match:
            numbers.append(int(match.group(1)))
    number = max(numbers, default=0) + 1
    if number > 9999:
        raise UpgradeError("migration ID space is exhausted")
    return f"MIG-{number:04d}"


def migrate_legacy_commands(
    legacy: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    """Preserve project hooks without carrying a legacy pb runtime reference."""
    migrated = json.loads(json.dumps(candidate))
    for name in ("project_test", "project_lint", "project_build", "project_closure"):
        if name in legacy:
            migrated[name] = legacy[name]
    for name, command in migrated.items():
        if not isinstance(command, dict):
            raise UpgradeError(f"project command {name} is malformed")
        for field in ("argv", "version_argv"):
            argv = command.get(field)
            if argv is None:
                continue
            if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
                raise UpgradeError(f"project command {name}.{field} is malformed")
            if any(
                item == "pb"
                or item.startswith("./pb")
                or ".agent/scripts/pb" in item
                for item in argv
            ):
                raise UpgradeError(
                    f"project command {name}.{field} invokes the removed pb runtime; "
                    "review and replace that project-owned hook before migration"
                )
    return migrated


def exact_plan(
    target: Path,
    proposal: dict[str, Any],
    candidate: Path,
    dispositions: dict[str, str],
    evidence_paths: list[str],
    baseline_origin: dict[str, Any] | None = None,
    setup_binding: tuple[dict[str, Any], Path] | None = None,
    predecessor_plan: tuple[dict[str, Any], Path] | None = None,
) -> dict[str, Any]:
    current_origin = baseline_origin or load_json(target / CURRENT_ORIGIN_PATH)
    candidate_origin = load_json(candidate / CURRENT_ORIGIN_PATH)
    old_inventory = {item["path"]: item for item in current_origin["installed_inventory"]["paths"]}
    final_contents: dict[str, tuple[bytes, int]] = {}
    operations: list[dict[str, Any]] = []
    preserved: set[str] = set()
    for row in proposal["classifications"]:
        path = row["path"]
        if row["classification"] in {"derived", "provenance", "unchanged_from_pristine"}:
            continue
        disposition = dispositions.get(row["id"])
        take_candidate = row["automatic"] or disposition == "accept_candidate"
        if take_candidate:
            source = candidate.joinpath(*PurePosixPath(path).parts)
            if not source.is_file() or source.is_symlink():
                raise UpgradeError(f"candidate source is absent or unsafe: {path}")
            content = source.read_bytes()
            mode = stat.S_IMODE(source.stat().st_mode)
            action = "create" if row["current"]["type"] == "absent" else "replace"
            operations.append(
                TRANSACTION.operation(action, path, content, "Apply an automatic-safe or explicitly reviewed candidate path.", mode=mode)
            )
            final_contents[path] = (content, mode)
        elif disposition == "merge_version_only":
            if path != ".agent/project.json":
                raise UpgradeError("merge_version_only is limited to .agent/project.json")
            current = load_json(target / path)
            candidate_value = load_json(candidate / path)
            if set(current) != set(candidate_value) or set(current.get("project", {})) != set(candidate_value.get("project", {})):
                raise UpgradeError("project contract shape changed; version-only merge is unsafe")
            current["schema_version"] = candidate_value["schema_version"]
            current["project"].pop("blueprint_version", None)
            current["project"]["octon_mini_version"] = candidate_value["project"]["octon_mini_version"]
            content = json_bytes(current)
            mode = stat.S_IMODE((target / path).stat().st_mode)
            operations.append(
                TRANSACTION.operation("replace", path, content, "Apply only the explicitly reviewed mechanical Octon version fields.", mode=mode)
            )
            final_contents[path] = (content, mode)
            preserved.add(path)
        elif disposition == "migrate_legacy_project_contract":
            if (
                path != ".agent/project.json"
                or proposal["from_product"] != LEGACY_PRODUCT
                or proposal["from_version"] != "3.1.0"
            ):
                raise UpgradeError("legacy project migration is limited to the reviewed 3.1.0 project contract")
            current = load_json(target / path)
            candidate_value = load_json(candidate / path)
            collaboration = current.get("collaboration_profile", {})
            if (
                current.get("schema_version") != "harness.project.v3"
                or collaboration.get("schema_version") != "harness.collaboration-profile.v1"
                or collaboration.get("assessment_status") != "not_assessed"
            ):
                raise UpgradeError("legacy project contract has assessed or unsupported collaboration state")
            migrated = {
                "schema_version": candidate_value["schema_version"],
                "project": dict(current["project"]),
                "collaboration_profile": candidate_value["collaboration_profile"],
                "paths": current["paths"],
                "commands": migrate_legacy_commands(
                    current["commands"], candidate_value["commands"]
                ),
                "project_checks": candidate_value["project_checks"],
                "work_completion": candidate_value["work_completion"],
                "autonomous_delivery": candidate_value["autonomous_delivery"],
                "packages": candidate_value["packages"],
                "mutable_work_status": current["mutable_work_status"],
            }
            migrated["project"].pop("blueprint_version", None)
            migrated["project"]["octon_mini_version"] = proposal["to_version"]
            content = json_bytes(migrated)
            mode = stat.S_IMODE((target / path).stat().st_mode)
            operations.append(
                TRANSACTION.operation(
                    "replace",
                    path,
                    content,
                    "Migrate the explicitly reviewed unassessed 3.1 project contract without inferring collaboration, hooks, packages, authority, or readiness.",
                    mode=mode,
                )
            )
            final_contents[path] = (content, mode)
            preserved.add(path)
        elif disposition == "migrate_legacy_project_check_evidence":
            if (
                path != ".agent/project-checks/evidence.json"
                or proposal["from_product"] != LEGACY_PRODUCT
                or proposal["from_version"] != "3.1.0"
            ):
                raise UpgradeError("legacy evidence migration is limited to the reviewed 3.1.0 project-check store")
            current = load_json(target / path)
            if (
                current.get("schema_version") != "harness.project-check-evidence-store.v2"
                or current.get("permission_grant") is not False
                or not isinstance(current.get("records"), list)
                or not isinstance(current.get("successor_relationships"), list)
            ):
                raise UpgradeError("legacy project-check evidence store is unsupported or malformed")
            migrated = dict(current)
            migrated["schema_version"] = "harness.project-check-evidence-store.v3"
            migrated["document_role"] = "bounded_current_index_and_content_addressed_proofs_of_project_owned_execution_evidence"
            migrated["proofs"] = []
            content = json_bytes(migrated)
            mode = stat.S_IMODE((target / path).stat().st_mode)
            operations.append(
                TRANSACTION.operation(
                    "replace",
                    path,
                    content,
                    "Migrate the explicitly reviewed project-check evidence header while preserving every prior record and adding no proof.",
                    mode=mode,
                )
            )
            final_contents[path] = (content, mode)
            preserved.add(path)
        elif disposition == "delete":
            operations.append(TRANSACTION.operation("delete", path, None, "Perform an explicitly reviewed upstream deletion."))
        else:
            preserved.add(path)

    candidate_inventory = candidate_origin["installed_inventory"]
    for item in candidate_inventory["paths"]:
        path = item["path"]
        if item["role"] in {"derived", "provenance"}:
            continue
        if path in final_contents and path not in preserved:
            content, mode = final_contents[path]
            item["sha256"] = hashlib.sha256(content).hexdigest()
            item["mode"] = mode
            item["baseline_product"] = proposal["to_product"]
            item["baseline_version"] = proposal["to_version"]
        elif path in preserved:
            old = old_inventory.get(path)
            if old is not None:
                item.update(
                    baseline_product=old["baseline_product"],
                    baseline_version=old["baseline_version"],
                    sha256=old["sha256"],
                    mode=old["mode"],
                )

    guide = f"migrations/{proposal['from_version']}-to-{proposal['to_version']}.md"
    if not (SCAFFOLDER.octon_mini_source_root() / guide).is_file():
        raise UpgradeError(f"migration guide is absent: {guide}")
    candidate_origin["initial_generation"] = current_origin["initial_generation"]
    candidate_origin["migration_history"] = [
        *current_origin.get("migration_history", []),
        {
            "schema_version": "octon.project.migration.v1",
            "id": next_migration_id(current_origin),
            "from_product": proposal["from_product"],
            "from_version": proposal["from_version"],
            "to_product": proposal["to_product"],
            "to_version": proposal["to_version"],
            "generator_version": SCAFFOLDER.GENERATOR_VERSION,
            "migrated_on": date.today().isoformat(),
            "from_profile": current_origin["profile"],
            "to_profile": candidate_origin["profile"],
            "from_layout": current_origin["layout"],
            "to_layout": candidate_origin["layout"],
            "migration_guide": guide,
            "authority_source": proposal["authority_source"],
            "evidence_refs": proposal["evidence_refs"],
            "limitations": [
                "Structural upgrade does not establish harness adoption or target-project readiness.",
                "Project-modified paths retain their prior pristine baseline for future three-way review.",
            ],
        },
    ]
    operations.append(
        TRANSACTION.operation(
            "create" if TRANSACTION.path_state(target, CURRENT_ORIGIN_PATH)["type"] == "absent" else "replace",
            CURRENT_ORIGIN_PATH,
            json_bytes(candidate_origin),
            "Record the independent upgraded snapshot, installed baselines, and migration provenance.",
        )
    )
    validators = load_json(candidate / ".agent/validators.json")
    derived = validators["commands"]["refresh"]["writes"]
    return TRANSACTION.build_plan(
        target,
        operation_name="upgrade.project",
        scope=(
            f"Upgrade {proposal['from_product']} {proposal['from_version']} "
            f"to {proposal['to_product']} {proposal['to_version']}"
        ),
        operations=operations,
        evidence=[
            TRANSACTION.source_evidence("accepted_upgrade_proposal", proposal["canonical_proposal_digest"]),
            TRANSACTION.source_evidence("project_owned_upgrade_authority", proposal["authority_source"]),
            *[TRANSACTION.source_evidence("migration_evidence", value) for value in proposal["evidence_refs"]],
            *SETUP.transaction_evidence(setup_binding, TRANSACTION),
        ],
        evidence_paths=[
            LEGACY_ORIGIN_PATH
            if proposal["from_product"] == LEGACY_PRODUCT
            else input_origin_path(current_origin),
            *evidence_paths,
        ],
        assumptions=[],
        confidence="deterministic",
        limitations=proposal["limitations"],
        analysis={
            "observations": [
                {
                    "id": "upgrade.three_way_classification",
                    "summary": "Recorded old baselines, current path states, and candidate bytes were classified path by path.",
                    "source_refs": [
                        LEGACY_ORIGIN_PATH
                        if proposal["from_product"] == LEGACY_PRODUCT
                        else input_origin_path(current_origin),
                        proposal["canonical_proposal_digest"],
                    ],
                    "rule": "installed_inventory_three_way_v1",
                    "confidence": "deterministic",
                    "limitations": ["Renames are never inferred from content similarity."],
                },
                *(
                    [
                        {
                            "id": "upgrade.guided_setup_session",
                            "summary": "A current non-authorizing guided setup session supplied reviewed inputs without changing accepted project authority.",
                            "source_refs": [setup_binding[0]["canonical_session_digest"]],
                            "rule": "octon-mini.bootstrap.setup-session.v2",
                            "confidence": "deterministic",
                            "limitations": ["The session does not enable work completion or establish readiness."],
                        }
                    ]
                    if setup_binding is not None
                    else []
                ),
            ],
            "inferences": [],
            "explicit_decisions": [
                {
                    "id": "upgrade.review_dispositions",
                    "summary": "Every non-automatic path has an exact proposal-bound disposition.",
                    "source_refs": [proposal["canonical_proposal_digest"], proposal["authority_source"]],
                    "rule": None,
                    "confidence": "deterministic",
                    "limitations": ["Plan acceptance applies only to this digest and these preimages."],
                }
            ],
            "authorization_gates": [],
        },
        derived_write_paths=derived,
        staged_validation_plan=[
            [sys.executable, "-B", ".agent/scripts/refresh.py", "--refresh"],
            [sys.executable, "-B", ".agent/scripts/validate.py", "--check"],
            [sys.executable, "-B", ".agent/tests/test_validate.py", "--tier", "release"],
        ],
        post_apply_validation_plan=[
            [sys.executable, "-B", ".agent/scripts/validate.py", "--check"]
        ],
        predecessor_plan=predecessor_plan,
    )


def write_artifact(path: Path, value: dict[str, Any], *, json_output: bool = False) -> None:
    TRANSACTION.write_new_json(path, value)
    digest = value.get("canonical_plan_digest") or value.get("canonical_proposal_digest")
    if value.get("artifact_kind") == "transaction_plan":
        summary = CONTINUATION.plan_summary(value)
        print(
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False)
            if json_output
            else f"[PLAN] {path}\n{CONTINUATION.render_plan_summary(summary)}"
        )
    elif not json_output:
        print(f"[PROPOSAL] {path}")
        print(f"[DIGEST] {digest}")


def plan_command(args: argparse.Namespace) -> int:
    if args.target.is_symlink():
        raise UpgradeError("upgrade target cannot be a symlink")
    target = args.target.resolve()
    if args.project_blueprint_seed:
        raise UpgradeError("Octon 5.0 supports reviewed Mini 4.2.0 upgrades; use the released Mini tools for older migrations")
    admitted_origin = load_upgrade_origin(target)
    output = args.output.expanduser().resolve()
    setup_binding = SETUP.prepare_plan_session("upgrade", args)
    args._setup_binding = setup_binding
    if args.authority_source is None:
        raise UpgradeError("upgrade requires --authority-source or setup.upgrade-authority")
    if not args.evidence_ref:
        raise UpgradeError("upgrade requires --evidence-ref or setup.upgrade-evidence")
    cross_brand_seed: dict[str, Any] | None = None
    predecessor = None
    if args.prior_plan is not None:
        prior_path = args.prior_plan.expanduser().resolve()
        predecessor = (CONTINUATION.load_exact_plan(prior_path), prior_path)
    if args.project_blueprint_seed:
        if (target / CURRENT_ORIGIN_PATH).exists():
            if not (target / LEGACY_ORIGIN_PATH).exists():
                raise UpgradeError("Project Blueprint snapshot is already migrated to Octon")
            raise UpgradeError(
                "both legacy and current origin records exist; reconcile the ambiguous target before migration"
            )
        cross_brand_seed = load_json(args.project_blueprint_seed)
        unsigned = dict(cross_brand_seed)
        supplied_seed_digest = unsigned.pop("canonical_seed_digest", None)
        expected_seed_digest = hashlib.sha256(TRANSACTION.canonical_bytes(unsigned)).hexdigest()
        if (
            cross_brand_seed.get("schema_version")
            != "octon-mini.bootstrap.cross-brand-migration-seed.v1"
            or cross_brand_seed.get("permission_grant") is not False
            or cross_brand_seed.get("source_product") != LEGACY_PRODUCT
            or cross_brand_seed.get("source_version") != "3.1.0"
            or cross_brand_seed.get("target_product") != CURRENT_PRODUCT
            or cross_brand_seed.get("target_version")
            not in {"4.0.0", SCAFFOLDER.octon_mini_version()}
            or cross_brand_seed.get("target") != str(target)
            or supplied_seed_digest != expected_seed_digest
            or cross_brand_seed.get("source_origin_state")
            != TRANSACTION.path_state(target, LEGACY_ORIGIN_PATH)
            or cross_brand_seed.get("source_project_state")
            != TRANSACTION.path_state(target, ".agent/project.json")
        ):
            if (
                not (target / LEGACY_ORIGIN_PATH).exists()
                and (target / CURRENT_ORIGIN_PATH).is_file()
            ):
                raise UpgradeError("Project Blueprint snapshot is already migrated to Octon")
            raise UpgradeError(
                "Project Blueprint cross-brand migration seed is malformed, stale, or targets another project"
            )
        origin = cross_brand_seed["legacy_baseline"]
    else:
        if (target / LEGACY_ORIGIN_PATH).exists() and not (target / CURRENT_ORIGIN_PATH).exists():
            raise UpgradeError(
                "Project Blueprint 3.1.0 requires an exact reviewed --project-blueprint-seed"
            )
        origin = admitted_origin
    supported_origins = {
        "octon.project.origin.v1",
        "octon-mini.project.origin.v1",
        "octon-mini.bootstrap.legacy-baseline.v1",
    }
    if origin.get("schema_version") not in supported_origins:
        raise UpgradeError(
            "live upgrade requires Octon origin provenance or an exact reviewed Project Blueprint seed"
        )
    if not args.authority_source.startswith(("authority:", "external:")):
        raise UpgradeError("--authority-source must be a current project-owned authority reference")
    to_version = SCAFFOLDER.octon_mini_version()
    from_version = origin_version(origin)
    if version_tuple(to_version) <= version_tuple(from_version):
        raise UpgradeError("candidate Octon version must be newer than the recorded snapshot")
    evidence_paths = evidence_record_paths(target, args.evidence_ref)
    if cross_brand_seed is not None and (
        cross_brand_seed.get("authority_source") != args.authority_source
        or sorted(cross_brand_seed.get("evidence_refs", [])) != sorted(set(args.evidence_ref))
    ):
        raise UpgradeError("authority or evidence differs from the reviewed cross-brand migration seed")
    with tempfile.TemporaryDirectory(prefix="octon-mini-upgrade-") as temporary:
        candidate = Path(temporary) / "candidate"
        generation_identifier = hashlib.sha256(
            TRANSACTION.canonical_bytes(
                {
                    "operation": "upgrade.project",
                    "from_product": origin_product(origin),
                    "from_version": from_version,
                    "to_product": CURRENT_PRODUCT,
                    "to_version": to_version,
                    "prior_generation_id": origin.get("generation_id"),
                    "profile": origin["profile"],
                    "layout": origin["layout"],
                }
            )
        ).hexdigest()[:32]
        run_scaffold(candidate, origin, generation_identifier)
        if args.proposal:
            proposal = load_json(args.proposal)
            validate_stored_proposal(proposal, target)
            if proposal["authority_source"] != args.authority_source or sorted(proposal["evidence_refs"]) != sorted(set(args.evidence_ref)):
                raise UpgradeError("authority or evidence differs from the stored proposal")
            expected_seed_digest = (
                cross_brand_seed.get("canonical_seed_digest")
                if cross_brand_seed
                else None
            )
            if proposal.get("cross_brand_seed_digest") != expected_seed_digest:
                raise UpgradeError("cross-brand migration seed differs from the stored proposal")
            rows = classification_rows(target, candidate, origin)
            stable_rows = [{key: value for key, value in row.items()} for row in rows]
            if stable_rows != proposal["classifications"]:
                raise UpgradeError("candidate or classification changed after proposal; re-plan")
            if not args.review:
                raise UpgradeError("--proposal requires its exact --review file")
            dispositions = review_map(proposal, args.review)
            value = exact_plan(
                target,
                proposal,
                candidate,
                dispositions,
                evidence_paths,
                baseline_origin=origin,
                setup_binding=setup_binding,
                predecessor_plan=predecessor,
            )
            write_artifact(output, value, json_output=args.json)
            return 0
        rows = classification_rows(target, candidate, origin)
        proposal = build_proposal(
            target,
            origin,
            rows,
            args.authority_source,
            args.evidence_ref,
            cross_brand_seed_digest=(
                cross_brand_seed.get("canonical_seed_digest")
                if cross_brand_seed
                else None
            ),
        )
        review_required = any(not row["automatic"] for row in rows)
        if review_required:
            write_artifact(output, proposal, json_output=args.json)
            review_output = output.with_name(output.stem + "-review.json")
            successor_output = output.with_name(output.stem + "-successor.json")
            next_argv = [
                "./octon", "upgrade", "plan", "--target", str(target),
                "--authority-source", args.authority_source,
            ]
            for evidence_ref in args.evidence_ref:
                next_argv.extend(["--evidence-ref", evidence_ref])
            if args.project_blueprint_seed:
                next_argv.extend(
                    ["--project-blueprint-seed", str(args.project_blueprint_seed.expanduser().resolve())]
                )
            next_argv.extend(
                [
                    "--proposal", str(output), "--review", str(review_output),
                    "--output", str(successor_output),
                ]
            )
            report = CONTINUATION.finding(
                failure_code="OCTON-UPGRADE-1101",
                blocked_operation="upgrade.project",
                phase="review",
                root_cause="The three-way upgrade contains non-automatic paths requiring exact proposal-bound dispositions.",
                authority_source="upgrade_proposal_review_and_project_owned_authority",
                repair_class="review_required",
                next_action=CONTINUATION.action(
                    "Create the exact proposal-bound review file, then run this successor-plan command.",
                    next_argv,
                    read_only=True,
                ),
                preserved=[CONTINUATION.proof_state("plan", str(output), "The immutable three-way proposal remains current review input.", ["source_fingerprint_bound"])],
                safe_read_only_actions=[CONTINUATION.action("Inspect coded recovery guidance.", ["./octon", "doctor", "--json"], read_only=True)],
                successor_plan=True,
                successor_reason="A successor transaction plan can be generated after exact review dispositions are supplied.",
            )
            CONTINUATION.record_local_artifact_writes(report, target, [output])
            print(CONTINUATION.render_finding(report, json_output=args.json), file=sys.stderr)
            return 3
        value = exact_plan(
            target,
            proposal,
            candidate,
            {},
            evidence_paths,
            baseline_origin=origin,
            setup_binding=setup_binding,
            predecessor_plan=predecessor,
        )
        write_artifact(output, value, json_output=args.json)
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="octon upgrade",
        description="Plan or apply a reviewed Octon version migration",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser(
        "plan", help="inspect and plan a reviewed three-way version migration"
    )
    plan.add_argument("--target", type=Path, required=True)
    plan.add_argument("--authority-source")
    plan.add_argument("--evidence-ref", action="append", default=[])
    plan.add_argument(
        "--project-blueprint-seed",
        type=Path,
        help="exact reviewed inert input for Project Blueprint 3.1.0 to Octon 4.0.0",
    )
    plan.add_argument("--proposal", type=Path)
    plan.add_argument("--review", type=Path)
    plan.add_argument("--output", type=Path, required=True)
    plan.add_argument("--setup-session", type=Path)
    plan.add_argument("--prior-plan", type=Path)
    plan.add_argument("--json", action="store_true")
    apply = commands.add_parser(
        "apply", help="apply the exact accepted version-migration plan"
    )
    apply.add_argument("--target", type=Path, required=True)
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--accept-digest", required=True)
    apply.add_argument("--json", action="store_true")
    SETUP.add_setup_parser(commands, "upgrade")
    args = parser.parse_args()
    try:
        if args.command == "setup":
            return SETUP.run_setup(args)
        if args.command == "plan":
            return plan_command(args)
        target = args.target.resolve()
        if args.target.is_symlink():
            raise UpgradeError("upgrade target cannot be a symlink")
        load_upgrade_origin(target)
        value = TRANSACTION.load_plan(args.plan)
        if value.get("operation") != "upgrade.project":
            raise UpgradeError("plan is not a live-upgrade transaction")
        SETUP.verify_plan_binding(target, value)
        receipt, receipt_path = TRANSACTION.apply_plan(target, value, args.accept_digest)
        if args.json:
            print(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False))
        else:
            print(f"[APPLIED] {receipt['receipt_id']}")
            print(f"[RECEIPT] {receipt_path}")
            print("[TIMING] " + json.dumps(TRANSACTION.LAST_PHASE_TIMINGS, sort_keys=True))
            print("[STATUS] structural conformance passed; adoption and readiness were not inferred")
        return 0
    except (OSError, RuntimeError, ValueError, UpgradeError, SETUP.SetupError, TRANSACTION.TransactionError) as error:
        report = getattr(error, "report", None)
        if not isinstance(report, dict):
            report = CONTINUATION.fallback(
                error,
                blocked_operation="upgrade.project",
                phase="apply" if getattr(args, "command", None) == "apply" else "plan",
                next_argv=["./octon", "upgrade", "--help"],
            )
        print(CONTINUATION.render_finding(report, json_output=getattr(args, "json", False)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
