#!/usr/bin/env python3
"""Plan and apply content-addressed trigger-package installation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
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


SCAFFOLDER = load_module("octon_package_scaffolder", SCRIPT_ROOT / "scaffold_project.py")
TRANSACTION = load_module(
    "octon_package_transaction",
    SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_transaction.py.tmpl",
)


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def loads_json(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=strict_pairs,
        parse_constant=reject_json_constant,
    )


def load_json(path: Path) -> Any:
    return loads_json(path.read_text(encoding="utf-8"))


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def transaction_validation(target: Path) -> dict[str, Any]:
    validators = load_json(target / ".agent/validators.json")
    writes = validators.get("commands", {}).get("refresh", {}).get("writes", [])
    if not isinstance(writes, list) or any(not isinstance(item, str) for item in writes):
        raise ValueError("target refresh writer paths are not a closed path array")
    return {
        "staged_validation_plan": [
            [sys.executable, "-B", ".agent/scripts/refresh.py", "--refresh"],
            [sys.executable, "-B", ".agent/scripts/validate.py", "--check"],
        ],
        "derived_write_paths": writes,
        "post_apply_validation_plan": [
            [sys.executable, "-B", ".agent/scripts/validate.py", "--check"]
        ],
    }


def output_path(relative: str) -> str:
    return relative[: -len(".tmpl")] if relative.endswith(".tmpl") else relative


def require_accepted_decision(target: Path, decision_ref: str) -> dict[str, Any]:
    if re.fullmatch(r"DEC-[0-9]{4}", decision_ref) is None:
        raise ValueError("package trust requires an exact DEC-0000 reference")
    candidates = sorted((target / ".agent/decisions").glob(f"{decision_ref}*.md"))
    if len(candidates) != 1 or candidates[0].is_symlink():
        raise ValueError(f"package trust decision must resolve exactly once: {decision_ref}")
    text = candidates[0].read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"package trust decision lacks JSON front matter: {decision_ref}")
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
        record = loads_json("".join(lines[1:end]))
    except (StopIteration, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"package trust decision is malformed: {decision_ref}") from error
    if (
        not isinstance(record, dict)
        or record.get("id") != decision_ref
        or record.get("status") != "accepted"
        or not str(record.get("authority_source", "")).startswith(("authority:", "external:"))
    ):
        raise ValueError(
            f"package trust requires an accepted project-owned decision with external authority: {decision_ref}"
        )
    return record


def package_contract(package_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = SCAFFOLDER.load_generation_policy()
    value = SCAFFOLDER.package_contract(manifest, package_id)
    return manifest, value


def package_files(value: dict[str, Any]) -> dict[str, bytes]:
    source_root = SCAFFOLDER.policy_source_path(
        value["source"], f"package {value.get('id', '<unknown>')}.source"
    )
    files: dict[str, bytes] = {}
    for raw in value["inventory_paths"]:
        relative = PurePosixPath(raw)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise ValueError(f"unsafe package inventory path: {raw}")
        source = source_root.joinpath(*relative.parts)
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"package source is absent or unsafe: {raw}")
        files[output_path(raw)] = source.read_bytes()
    return files


def installed_content_digest(files: dict[str, bytes]) -> str:
    """Bind the registry to the exact rendered paths and bytes installed."""
    digest = hashlib.sha256()
    for relative, content in sorted(files.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def installed_target_path(target: Path, raw: str) -> Path:
    relative = PurePosixPath(raw)
    if (
        relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
        or relative.as_posix() != raw
    ):
        raise ValueError(f"unsafe installed package path: {raw}")
    candidate = target.joinpath(*relative.parts)
    current = target
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"installed package path has a symlink ancestor: {raw}")
    try:
        candidate.parent.resolve(strict=False).relative_to(target.resolve())
    except (OSError, ValueError) as error:
        raise ValueError(f"installed package path escapes the target: {raw}") from error
    return candidate


def extension_entry(package_id: str, owner: str, trust_ref: str) -> dict[str, Any]:
    return {
        "id": package_id,
        "enabled": False,
        "version": "1.0.0",
        "path": f".agent/extensions/{package_id}",
        "requires_core": "^4.2.0",
        "config": f".agent/extensions/{package_id}/config.json",
        "validator": f".agent/extensions/{package_id}/validate.py",
        "owner": owner,
        "provenance": f"package:{package_id}@1.0.0",
        "trust_class": "trusted_project_local_code",
        "trust_decision_ref": trust_ref,
        "side_effects": "read_only",
        "network_access": "denied",
        "filesystem_writes": "prohibited",
        "authority_effect": "restrictions_only",
        "deprecated_at": None,
        "removal_version": None,
        "successor": None,
    }


def registry_baseline() -> dict[str, Any]:
    return {
        "schema_version": "harness.extension-registry.v1",
        "core_version": "4.2.0",
        "extension_api": "harness.extension.v1",
        "permission_grant": False,
        "execution_boundary": (
            "trusted_project_local_code_with_least_environment_and_post_execution_write_detection; "
            "external sandbox required for strong isolation"
        ),
        "extensions": [],
    }


def installation_plan(
    target: Path,
    package_id: str,
    owner: str,
    trust_ref: str,
    *,
    assess_applicable: bool = False,
    update: bool = False,
    remove: bool = False,
) -> dict[str, Any]:
    target = target.resolve()
    if not owner.strip():
        raise ValueError("package owner must be nonempty")
    if not (target / ".octon-mini-origin.json").is_file():
        raise ValueError("target is not a generated Octon Mini snapshot")
    manifest, package = package_contract(package_id)
    require_accepted_decision(target, trust_ref)
    project_path = target / ".agent/project.json"
    project = load_json(project_path)
    profile = project.get("project", {}).get("profile") if isinstance(project, dict) else None
    if profile not in package["profiles"]:
        raise ValueError(f"package {package_id} is unavailable for profile {profile}")
    registry_path = target / ".agent/packages.json"
    registry = load_json(registry_path)
    installed = next(
        (
            item
            for item in registry.get("packages", [])
            if isinstance(item, dict) and item.get("id") == package_id
        ),
        None,
    )
    if update and remove:
        raise ValueError("package update and removal are mutually exclusive")
    if installed is not None and not update and not remove:
        raise ValueError(f"package {package_id} is already installed; use an explicit update plan")
    if installed is None and (update or remove):
        raise ValueError(f"package {package_id} is not installed and cannot be updated or removed")
    if update and package_id not in {"small-team-git-portfolio", "long-running-work", "autonomous-delivery"}:
        raise ValueError("package update is currently limited to reviewed packages with explicit compatibility coverage")
    files = package_files(package)
    operations: list[dict[str, Any]] = []
    if remove:
        if package_id not in {"long-running-work", "autonomous-delivery"}:
            raise ValueError("package removal is limited to workflow capabilities with explicit lifecycle coverage")
        assert installed is not None
        old_paths = installed.get("installed_paths")
        if not isinstance(old_paths, list) or any(not isinstance(item, str) for item in old_paths):
            raise ValueError("installed package inventory is malformed")
        current: dict[str, bytes] = {}
        for relative in old_paths:
            path = installed_target_path(target, relative)
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"installed package path is absent or unsafe: {relative}")
            current[relative] = path.read_bytes()
        if installed_content_digest(current) != installed.get("installed_paths_sha256"):
            raise ValueError("installed package content differs from its recorded baseline; removal refuses")
        adoption_path = target / ".agent/work-runs/adoption.json"
        if package_id == "long-running-work":
            if adoption_path.is_symlink():
                raise ValueError("long-running-work adoption path is unsafe")
            if adoption_path.is_file():
                adoption = load_json(adoption_path)
                if adoption.get("status") != "disabled":
                    raise ValueError("long-running-work must be disabled before package removal")
            runs_root = target / ".agent/work-runs/runs"
            if runs_root.is_symlink():
                raise ValueError("long-running-work runs root is unsafe")
            if runs_root.is_dir() and any(runs_root.iterdir()):
                raise ValueError("package removal refuses retained run history without a separate project-owned disposition")
            active_path = target / ".agent/work-runs/active.json"
            if active_path.exists() or active_path.is_symlink():
                raise ValueError("package removal refuses while an active-run pointer exists")
        else:
            delivery = project.get("autonomous_delivery", {})
            if not isinstance(delivery, dict) or delivery.get("status") not in {"disabled", "revoked", "expired"}:
                raise ValueError("autonomous-delivery must be disabled, revoked, or expired before package removal")
        for relative in sorted(old_paths):
            operations.append(
                TRANSACTION.operation(
                    "delete",
                    relative,
                    None,
                    f"Remove exact-pristine {package_id} package payload after lifecycle checks.",
                )
            )
        if package_id == "long-running-work" and adoption_path.is_file():
            operations.append(
                TRANSACTION.operation(
                    "delete",
                    ".agent/work-runs/adoption.json",
                    None,
                    "Remove disabled adoption configuration; no run history exists.",
                )
            )
    elif update:
        assert installed is not None
        old_paths = installed.get("installed_paths")
        if not isinstance(old_paths, list) or any(not isinstance(item, str) for item in old_paths):
            raise ValueError("installed package inventory is malformed")
        current: dict[str, bytes] = {}
        for relative in old_paths:
            path = installed_target_path(target, relative)
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"installed package path is absent or unsafe: {relative}")
            current[relative] = path.read_bytes()
        if installed_content_digest(current) != installed.get("installed_paths_sha256"):
            raise ValueError("installed package content differs from its recorded baseline; update refuses overwrite")
        if installed.get("version") == package["version"] and installed.get("sha256") == package["sha256"]:
            raise ValueError("installed package already matches the requested version and digest")
        for relative in sorted(set(old_paths) - set(files)):
            operations.append(
                TRANSACTION.operation(
                    "delete",
                    relative,
                    None,
                    f"Remove an exact-pristine path retired by package {package_id}.",
                )
            )
        for relative, content in files.items():
            operations.append(
                TRANSACTION.operation(
                    "replace" if relative in current else "create",
                    relative,
                    content,
                    f"Update reviewed content-addressed package {package_id} without preserving provider or workflow settings in package files.",
                    mode=0o755 if relative.endswith("/validate.py") else 0o644,
                )
            )
    else:
        for relative, content in files.items():
            operations.append(
                TRANSACTION.operation(
                    "create",
                    relative,
                    content,
                    f"Vendor reviewed content-addressed package {package_id}.",
                    mode=0o755 if relative.endswith("/validate.py") else 0o644,
                )
            )

    if not remove and package["kind"] in {"domain_extension", "reference_extension", "workflow_capability"}:
        assessment_key = package_id.replace("-", "_")
        assessments = project.get("packages", {}).get("trigger_assessments", {})
        if package["kind"] in {"domain_extension", "workflow_capability"}:
            if assessments.get(assessment_key) != "applicable":
                if not assess_applicable:
                    raise ValueError(
                        f"project-owned trigger assessment {assessment_key} is not applicable; "
                        "repeat planning with --assess-applicable only when the accepted decision covers that assessment"
                    )
                assessments[assessment_key] = "applicable"
                operations.append(
                    TRANSACTION.operation(
                        "replace",
                        ".agent/project.json",
                        json_bytes(project),
                        "Record the explicitly decision-backed trigger assessment in the same transaction as installation.",
                    )
                )
        if package["kind"] in {"domain_extension", "reference_extension"}:
            extension_registry_path = target / ".agent/extensions/registry.json"
            if extension_registry_path.is_file():
                extension_registry = load_json(extension_registry_path)
                action = "replace"
            else:
                extension_registry = registry_baseline()
                action = "create"
            if any(item.get("id") == package_id for item in extension_registry["extensions"]):
                raise ValueError(f"extension registry already contains {package_id}")
            extension_registry["extensions"].append(extension_entry(package_id, owner, trust_ref))
            operations.append(
                TRANSACTION.operation(
                    action,
                    ".agent/extensions/registry.json",
                    json_bytes(extension_registry),
                    "Register installed extension without enabling it or granting authority.",
                )
            )
            config_path = f".agent/extensions/{package_id}/config.json"
            if config_path in files:
                config = loads_json(files[config_path].decode("utf-8"))
                config["adoption"] = {
                    "status": "applicable",
                    "owner": owner,
                    "assessed_on": date.today().isoformat(),
                    "decision_ref": trust_ref,
                    "rationale": "Project trigger was explicitly assessed applicable; package remains disabled until its records are ready.",
                }
                files[config_path] = json_bytes(config)
                for index, item in enumerate(operations):
                    if item["path"] == config_path:
                        operations[index] = TRANSACTION.operation(
                            "create",
                            config_path,
                            json_bytes(config),
                            "Record explicit applicability without inferring readiness.",
                        )
                        break

    if package_id == "small-team-git-portfolio":
        scm = load_json(target / ".agent/scm.json")
        if not update:
            scm.update(selection="git", selection_decision_ref=trust_ref)
            if "git" not in scm["detected_candidates"] and (target / ".git").exists():
                scm["detected_candidates"].append("git")
        scm["portfolio"]["status"] = "installed"
        scm["portfolio"]["version"] = package["version"]
        scm["portfolio"]["sha256"] = package["sha256"]
        operations.append(
            TRANSACTION.operation(
                "replace",
                ".agent/scm.json",
                json_bytes(scm),
                "Record the explicit Git selection and installed portfolio digest.",
            )
        )

    installed_paths = sorted(files)
    planned_receipt_id = TRANSACTION.new_receipt_id()
    prior_evidence = (
        installed.get("evidence_refs", [])
        if update and isinstance(installed, dict)
        else []
    )
    if not isinstance(prior_evidence, list) or any(
        not isinstance(item, str) or not item for item in prior_evidence
    ):
        raise ValueError("installed package evidence inventory is malformed")
    registry_entry = {
        "id": package_id,
        "kind": package["kind"],
        "version": package["version"],
        "sha256": package["sha256"],
        "installed_paths": installed_paths,
        "installed_paths_sha256": installed_content_digest(files),
        "owner": owner,
        "trust_decision_ref": trust_ref,
        "validation_status": "pass",
        "validation_receipt_ref": planned_receipt_id,
        "evidence_refs": sorted(
            set(prior_evidence) | {trust_ref, planned_receipt_id}
        ),
    }
    if remove:
        assert installed is not None
        registry["packages"].remove(installed)
        assessment_key = package_id.replace("-", "_")
        project["packages"]["trigger_assessments"][assessment_key] = "not_assessed"
        if package_id == "autonomous-delivery":
            project["autonomous_delivery"] = {
                "schema_version": "harness.autonomous-delivery-config.v2",
                "status": "available_not_activated",
                "write_capability": "locked",
                "external_effects": "locked",
                "delivery_profile": None,
                "compute_mode": None,
                "adoption_decision_ref": None,
                "authorization_record_ref": None,
                "authorization_record_digest": None,
                "activation_receipt_ref": None,
                "limitations": [
                    "The dormant read-only surface remains available after write-capable package removal.",
                    "No package lifecycle action creates standing authority.",
                ],
            }
        operations.append(
            TRANSACTION.operation(
                "replace",
                ".agent/project.json",
                json_bytes(project),
                f"Return {package_id} applicability to not assessed without asserting non-applicability.",
            )
        )
    elif update:
        assert installed is not None
        registry["packages"][registry["packages"].index(installed)] = registry_entry
    else:
        registry["packages"].append(registry_entry)
    operations.append(
        TRANSACTION.operation(
            "replace",
            ".agent/packages.json",
            json_bytes(registry),
            "Record package version, digest, ownership, trust, paths, and validation.",
        )
    )
    return TRANSACTION.build_plan(
        target,
        operation_name=("maintain.package.remove" if remove else "maintain.package.update" if update else "maintain.package.install"),
        scope=f"{'Remove' if remove else 'Update' if update else 'Install'} triggered package {package_id}",
        operations=operations,
        evidence=[
            TRANSACTION.source_evidence(
                "content_addressed_octon_mini_package",
                package["source"],
                limitations=["Package installation does not establish target-project readiness."],
            ),
            TRANSACTION.source_evidence("explicit_trust_and_trigger_decision", trust_ref),
        ],
        assumptions=[],
        confidence="deterministic",
        limitations=[
            "Installation never marks a trigger not applicable.",
            "Extensions are installed disabled; enabling requires current project configuration.",
            "Workflow capabilities are installed inactive; project adoption is a separate digest-bound transaction.",
            "A package update changes only exact-pristine package-owned paths and never enables work completion or rewrites project-owned workflow authority or settings.",
        ],
        planned_receipt_id=planned_receipt_id,
        **transaction_validation(target),
    )


def write_plan(plan: dict[str, Any], output: Path) -> None:
    TRANSACTION.write_new_json(output, plan)
    print(f"[PLAN] {output}")
    print(f"[DIGEST] {plan['canonical_plan_digest']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="octon maintain package",
        description="Install or update an applicable Octon Mini project package"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="plan a content-addressed package installation")
    plan.add_argument("--target", type=Path, required=True)
    plan.add_argument("--package", required=True)
    plan.add_argument("--owner", required=True)
    plan.add_argument("--trust-decision-ref", required=True)
    plan.add_argument(
        "--assess-applicable",
        action="store_true",
        help="also record applicability when the accepted trust decision explicitly covers it",
    )
    plan.add_argument(
        "--update",
        action="store_true",
        help="plan an exact-pristine update of an already installed supported package",
    )
    plan.add_argument(
        "--remove",
        action="store_true",
        help="plan safe removal of a disabled supported package with no retained run state",
    )
    plan.add_argument("--output", type=Path, required=True)
    apply = commands.add_parser("apply", help="apply the exact accepted package plan")
    apply.add_argument("--target", type=Path, required=True)
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--accept-digest", required=True)
    args = parser.parse_args()
    try:
        if args.command == "plan":
            write_plan(
                installation_plan(
                    args.target,
                    args.package,
                    args.owner,
                    args.trust_decision_ref,
                    assess_applicable=args.assess_applicable,
                    update=args.update,
                    remove=args.remove,
                ),
                args.output,
            )
            return 0
        target = args.target.resolve()
        plan_value = TRANSACTION.load_plan(args.plan)
        if plan_value.get("operation") not in {"maintain.package.install", "maintain.package.update", "maintain.package.remove"}:
            raise ValueError("plan is not a package install/update/remove transaction")
        receipt, receipt_path = TRANSACTION.apply_plan(
            target,
            plan_value,
            args.accept_digest,
        )
        print(f"[APPLIED] {receipt['receipt_id']}")
        print(f"[RECEIPT] {receipt_path}")
        return 0
    except (OSError, RuntimeError, ValueError, TRANSACTION.TransactionError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
