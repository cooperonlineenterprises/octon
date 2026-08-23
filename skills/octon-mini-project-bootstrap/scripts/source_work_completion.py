#!/usr/bin/env python3
"""Source-repository mode for the existing governed work-completion engine."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
TEMPLATE_ROOT = SKILL_ROOT / "assets/templates/core/.agent/scripts"
WORK_COMPLETION_SCHEMA = SKILL_ROOT.parents[1] / "shared/schemas/harness-work-completion.schema.json"
TASK_SCHEMA = "harness.external-codex-task-reference.v1"
TASK_PATTERN = re.compile(r"^external:codex-task:[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$")
SOURCE_INPUTS = [
    "AGENTS.md",
    "ARCHITECTURE_DECISIONS.md",
    "GIT_WORKFLOW.md",
    "RELEASE.md",
    "RELEASE_READINESS.md",
    "VERSION",
    "shared/source-contracts/commands.json",
]


class SourceCompletionError(RuntimeError):
    """Fail-closed source work-completion error."""


def duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=duplicate_pairs,
            parse_constant=lambda raw: (_ for _ in ()).throw(ValueError(raw)),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise SourceCompletionError(f"cannot load strict JSON {path}: {error}") from error


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest_without(value: dict[str, Any], field: str) -> str:
    candidate = dict(value)
    candidate.pop(field, None)
    return digest(candidate)


def timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise SourceCompletionError(f"{label} is malformed")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise SourceCompletionError(f"{label} is malformed") from error
    if result.tzinfo is None:
        raise SourceCompletionError(f"{label} requires a timezone")
    return result


def source_root(raw: str) -> Path:
    root = Path(raw).resolve()
    if not root.is_dir() or not (root / "octon-mini.json").is_file() or not (root / "VERSION").is_file() or not (root / ".git").exists():
        raise SourceCompletionError("target is not the Octon Mini source repository")
    if (root / ".agent/project.json").exists():
        raise SourceCompletionError("source mode is inapplicable to a generated project")
    return root


def external_path(root: Path, raw: str, *, require_file: bool = True) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise SourceCompletionError("source work-completion evidence paths must be absolute")
    path = path.resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError:
        pass
    else:
        raise SourceCompletionError("source work-completion evidence must remain outside the repository")
    current = Path(path.anchor)
    for part in path.parts[1:-1]:
        current = current / part
        if current.is_symlink():
            raise SourceCompletionError("source work-completion evidence has a symlink ancestor")
    if require_file and (not path.is_file() or path.is_symlink()):
        raise SourceCompletionError(f"required external evidence is absent or unsafe: {path}")
    return path


def write_new(root: Path, raw: str, value: Any) -> Path:
    path = external_path(root, raw, require_file=False)
    if not path.parent.is_dir() or path.parent.is_symlink() or path.exists():
        raise SourceCompletionError("external output parent must exist and output must be new")
    try:
        with path.open("xb") as handle:
            handle.write(canonical_bytes(value))
            handle.flush()
    except FileExistsError as error:
        raise SourceCompletionError("external output already exists") from error
    return path


def load_template(path: Path, name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
    return module


def engine_modules() -> tuple[types.ModuleType, types.ModuleType, types.ModuleType]:
    transaction = load_template(TEMPLATE_ROOT / "octon_transaction.py.tmpl", "octon_source_transaction")
    previous = sys.modules.get("octon_transaction")
    sys.modules["octon_transaction"] = transaction
    try:
        completion = load_template(TEMPLATE_ROOT / "octon_work_completion.py.tmpl", "octon_source_work_completion")
    finally:
        if previous is None:
            sys.modules.pop("octon_transaction", None)
        else:
            sys.modules["octon_transaction"] = previous
    autonomous = load_template(TEMPLATE_ROOT / "octon_autonomous_delivery.py.tmpl", "octon_source_autonomous_delivery")
    return transaction, completion, autonomous


def validate_source_schema(value: Any, definition: str) -> None:
    schema = load_json(WORK_COMPLETION_SCHEMA)
    validator = load_template(TEMPLATE_ROOT / "validate.py.tmpl", "octon_source_work_completion_validator")
    schema_errors = validator.lint_schema_contract(schema)
    if schema_errors:
        raise SourceCompletionError("source work-completion schema is invalid: " + "; ".join(schema_errors))
    candidate = schema.get("$defs", {}).get(definition) if isinstance(schema, dict) else None
    if not isinstance(candidate, dict):
        raise SourceCompletionError(f"source work-completion schema definition is absent: {definition}")
    errors = validator.validate_schema(value, candidate, root_schema=schema)
    if errors:
        raise SourceCompletionError(f"source work-completion {definition} is malformed: " + "; ".join(errors))


def validate_task_reference(value: Any, root: Path, completion: types.ModuleType) -> dict[str, Any]:
    required = {
        "schema_version", "artifact_kind", "permission_grant", "task_ref",
        "priority_authority_ref", "scope", "acceptance_refs", "branch",
        "pull_request", "self_review_refs", "validation_evidence_refs",
        "authority_source", "observed_at", "valid_until", "limitations",
        "task_reference_digest",
    }
    if not isinstance(value, dict) or set(value) != required or value.get("schema_version") != TASK_SCHEMA or value.get("artifact_kind") != "external_codex_task_reference" or value.get("permission_grant") is not False:
        raise SourceCompletionError("external Codex task reference is absent or malformed")
    if value.get("task_reference_digest") != digest_without(value, "task_reference_digest"):
        raise SourceCompletionError("external Codex task-reference digest is invalid")
    if not isinstance(value.get("task_ref"), str) or TASK_PATTERN.fullmatch(value["task_ref"]) is None:
        raise SourceCompletionError("external Codex task identity is malformed")
    if not isinstance(value.get("priority_authority_ref"), str) or not value["priority_authority_ref"].startswith(("authority:", "external:")):
        raise SourceCompletionError("external Codex task lacks a priority authority reference")
    if not isinstance(value.get("scope"), str) or not value["scope"].strip():
        raise SourceCompletionError("external Codex task scope is absent")
    acceptance = completion.string_inventory(value.get("acceptance_refs"), "source task acceptance references", allow_empty=False)
    if not {"SRC-DEC-0019", "SRC-DEC-0020"} <= set(acceptance):
        raise SourceCompletionError("source task acceptance does not bind the accepted delivery decisions")
    branch = value.get("branch")
    if not isinstance(branch, str) or completion.run(root, ["git", "check-ref-format", "--branch", branch], check=False).returncode:
        raise SourceCompletionError("external Codex task branch is malformed")
    pull_request = value.get("pull_request")
    if not isinstance(pull_request, dict) or set(pull_request) != {"title", "body"} or any(not isinstance(pull_request.get(key), str) or not pull_request[key].strip() for key in pull_request):
        raise SourceCompletionError("external Codex task pull-request projection is malformed")
    completion.string_inventory(value.get("self_review_refs"), "source task self-review references", allow_empty=False)
    completion.string_inventory(value.get("validation_evidence_refs"), "source task validation evidence references", allow_empty=False)
    completion.string_inventory(value.get("limitations"), "source task limitations")
    if not isinstance(value.get("authority_source"), str) or not value["authority_source"].startswith(("authority:", "external:")):
        raise SourceCompletionError("external Codex task lacks an authority source")
    observed = timestamp(value.get("observed_at"), "task observed_at")
    valid_until = timestamp(value.get("valid_until"), "task valid_until")
    now = datetime.now(timezone.utc)
    if observed > now or not observed <= now <= valid_until:
        raise SourceCompletionError("external Codex task reference is future-dated or expired")
    return value


def require_source_authority_documents(root: Path) -> None:
    architecture = (root / "ARCHITECTURE_DECISIONS.md").read_text(encoding="utf-8")
    workflow = (root / "GIT_WORKFLOW.md").read_text(encoding="utf-8")
    if "## SRC-DEC-0019 — Governed autonomous-delivery capability" not in architecture or "| Source-repository mode |" not in architecture or "| Status | `accepted` |" not in architecture.split("## SRC-DEC-0019 —", 1)[1].split("## SRC-DEC-0020 —", 1)[0]:
        raise SourceCompletionError("accepted source-repository work-completion amendment is absent")
    for statement in ("| Base workflow | `solo_hybrid` |", "| Integration method | `merge_commit` |", "stable `required` check"):
        if statement not in workflow:
            raise SourceCompletionError(f"source Git workflow lacks required accepted statement: {statement}")


def build_plan(root: Path, task_path: Path, standing_path: Path) -> dict[str, Any]:
    root = root.resolve()
    task_path = external_path(root, str(task_path))
    standing_path = external_path(root, str(standing_path))
    transaction, completion, autonomous = engine_modules()
    task_bytes = task_path.read_bytes()
    task_value = load_json(task_path)
    validate_source_schema(task_value, "external_task_reference")
    task = validate_task_reference(task_value, root, completion)
    record = autonomous.validate_record(autonomous.load_json(standing_path))
    contract = record["contract"]
    require_source_authority_documents(root)
    repository = contract["repository"]
    if Path(repository["root"]).resolve() != root or repository["identity"] != "cooperonlineenterprises/octon-mini" or repository["remote"] != "origin" or repository["default_branch"] != "main":
        raise SourceCompletionError("standing authorization does not bind the exact Octon Mini source repository")
    if contract.get("merge_method") != "merge_commit":
        raise SourceCompletionError("source work completion requires the accepted merge-commit method")
    required_actions = {"push_task_branch", "create_pull_request", "observe_hosted_state", "merge_pull_request", "delete_merged_task_branch"}
    if not required_actions <= set(contract.get("permitted_actions", [])):
        raise SourceCompletionError("standing authorization omits a required source work-completion action")
    dirty, staged = completion.dirty_state(root)
    if dirty or staged:
        raise SourceCompletionError("source work-completion planning requires a clean worktree and index")
    branch = completion.git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if branch != task["branch"] or not fnmatch.fnmatchcase(branch, repository["task_branch_pattern"]):
        raise SourceCompletionError("current branch differs from the exact external task or standing contract")
    remote_url = completion.git(root, "remote", "get-url", repository["remote"], check=False)
    if not remote_url:
        raise SourceCompletionError("configured source remote is unavailable")
    remote_default = completion.revision(root, f"refs/remotes/{repository['remote']}/{repository['default_branch']}")
    head = completion.revision(root, "HEAD")
    base = completion.git(root, "merge-base", "HEAD", f"refs/remotes/{repository['remote']}/{repository['default_branch']}")
    if base != remote_default or head == remote_default:
        raise SourceCompletionError("source candidate must be a nonempty branch based on the exact observed remote default")
    commits = [item for item in completion.git(root, "rev-list", "--reverse", f"{base}..{head}").splitlines() if item]
    changed = sorted(item for item in completion.git(root, "diff", "--name-only", "--diff-filter=ACDMRTUXB", base, head).splitlines() if item)
    if not commits or not changed:
        raise SourceCompletionError("source candidate commit range or changed-path inventory is empty")
    remote_task = completion.remote_tracking_revision(root, repository["remote"], branch)
    hooks = completion.git_hook_observation(root, "require_none")
    blocking = []
    if hooks["active_hook_names"]:
        blocking.append("active or unsafe Git hooks are outside source work completion")
    source_inputs = list(SOURCE_INPUTS)
    external_binding = {
        "path": str(task_path),
        "file_sha256": hashlib.sha256(task_bytes).hexdigest(),
        "task_reference_digest": task["task_reference_digest"],
    }
    operations = [
        "fetch_remote", "push_branch", "locate_pull_request", "open_pull_request",
        "observe_change_checks", "merge_pull_request", "delete_remote_branch",
    ]
    plan: dict[str, Any] = {
        "schema_version": completion.SOURCE_PLAN_SCHEMA,
        "artifact_kind": "work_completion_plan",
        "permission_grant": False,
        "read_only": True,
        "source_mode": True,
        "task_ref": task["task_ref"],
        "task_status": "externally_bound",
        "external_task_binding": external_binding,
        "external_task_valid_until": task["valid_until"],
        "priority_authority_ref": task["priority_authority_ref"],
        "workflow": "solo_hybrid",
        "adopted_workflow_authority_ref": "SRC-DEC-0001",
        "assurance_profile": "source_release_policy",
        "assurance_control_refs": ["SRC-DEC-0019", "SRC-DEC-0020"],
        "standing_authorization_record_ref": str(standing_path),
        "repository": {
            "root": ".",
            "identity": repository["identity"],
            "remote": repository["remote"],
            "observed_remote_url_sha256": hashlib.sha256(remote_url.encode("utf-8")).hexdigest(),
            "provider_adapter": "github_cli",
            "hosted_repository": repository["identity"],
        },
        "branches": {"default": repository["default_branch"], "task": branch, "current": branch},
        "expected_revisions": {
            "base": base,
            "head_before_commit": head,
            "candidate_head": head,
            "remote_default": remote_default,
            "remote_task": remote_task,
        },
        "candidate_commits": commits,
        "eligible_staging_paths": changed,
        "path_preconditions": [completion.path_precondition(root, path) for path in changed],
        "closure_transaction": None,
        "git_hook_observation": hooks,
        "proposed_commit": {
            "message": completion.git(root, "show", "-s", "--format=%B", head).rstrip("\n"),
            "allow_empty": False,
            "amend": False,
            "history_rewrite": False,
            "mode": "precommitted_candidate_range",
        },
        "validation_commands": [],
        "validation_evidence_refs": task["validation_evidence_refs"],
        "pull_request": {"requirement": "required", "title": task["pull_request"]["title"], "body": task["pull_request"]["body"], "draft_allowed": False},
        "review": {
            "requirement": "self_review_with_limitations",
            "maximum_peer_approvals": 0,
            "eligible_peer_reviewers": [],
            "self_review_refs": task["self_review_refs"],
            "limitations": ["Automated or self-review evidence is not independent human approval."],
        },
        "required_hosted_checks": ["required"],
        "integration_method": "merge_commit",
        "cleanup": {"remote_task_branch": True, "local_task_branch": True},
        "post_merge_validation": {
            "required": True,
            "evidence_schema": "harness.source-post-merge-validation.v1",
            "cleanup_before_pass": False,
        },
        "concurrent_work": {
            "enabled": False,
            "shared_base_revision": None,
            "declared_write_scope": [],
            "worktree": str(root),
            "handback_state": "not_applicable",
            "partial_result_state": "not_applicable",
            "coordination_evidence_refs": [],
        },
        "external_operations": operations,
        "authorization_contract": {
            "required": True,
            "attestation_schema": completion.AUTH_SCHEMA,
            "exact_plan_binding": True,
            "revalidate_before_each_effect": True,
        },
        "stop_conditions": [
            "external task, source authority, standing authorization, or instructions change",
            "local or remote revisions differ from the reviewed preconditions",
            "required checks or mergeability are absent, pending, failed, stale, or unknown",
            "integrated-main validation evidence is absent or incomplete",
            "cleanup lacks integration, synchronization, and post-merge evidence",
        ],
        "blocking_reasons": sorted(set(blocking)),
        "source_inputs": source_inputs,
        "relevant_input_fingerprint": "",
        "limitations": [
            "The external Codex task reference is an immutable authority pointer, not a second task lifecycle.",
            "The candidate is already committed; planning performs no repository or provider mutation.",
            "Cleanup pauses until exact integrated-main validation evidence is recorded.",
            "External effects remain monotonic, receipt-backed, and fix-forward.",
        ],
    }
    plan["relevant_input_fingerprint"] = completion.source_repository_fingerprint(root, plan)
    plan["canonical_plan_digest"] = completion.digest(plan)
    completion.stored_plan_digest(plan)
    validate_source_schema(plan, "source_plan")
    return plan


def load_current_plan(root: Path, path: Path) -> tuple[dict[str, Any], types.ModuleType, types.ModuleType]:
    transaction, completion, _autonomous = engine_modules()
    plan = load_json(path)
    if not isinstance(plan, dict) or plan.get("schema_version") != completion.SOURCE_PLAN_SCHEMA:
        raise SourceCompletionError("source work-completion plan is absent or malformed")
    validate_source_schema(plan, "source_plan")
    try:
        completion.stored_plan_digest(plan)
    except completion.FinishError as error:
        raise SourceCompletionError("source work-completion plan is absent or malformed") from error
    task_path = external_path(root, plan["external_task_binding"]["path"])
    standing_path = external_path(root, plan["standing_authorization_record_ref"])
    current = build_plan(root, task_path, standing_path)
    if current != plan:
        raise SourceCompletionError("source work-completion plan is stale")
    return plan, transaction, completion


def apply_plan(root: Path, plan_path: Path, accepted_digest: str, authorization_path: Path) -> dict[str, Any]:
    plan, transaction, completion = load_current_plan(root, plan_path)
    if accepted_digest != plan["canonical_plan_digest"]:
        raise SourceCompletionError("source work-completion apply requires the exact reviewed digest")
    authorization = completion.load_authorization(authorization_path, plan)
    receipt = completion.new_receipt(plan, authorization)
    receipt["resume"] = ["./octon", "work", "finish", "resume", "--receipt-id", receipt["receipt_id"]]
    completion.validate_receipt(receipt)
    transaction.write_work_completion_receipt(root, receipt, create=True)
    completion.record(root, receipt, "planned", "accept_plan", "performed", {"plan_digest": accepted_digest})
    receipt["revisions"]["commit"] = plan["expected_revisions"]["candidate_head"]
    completion.record(
        root,
        receipt,
        "locally_committed",
        "create_commit",
        "already_satisfied",
        {"commit": receipt["revisions"]["commit"], "candidate_commits": plan["candidate_commits"]},
        completed=True,
    )
    try:
        return completion.execute(root, receipt)
    except completion.FinishError as error:
        completion.block(root, receipt, getattr(error, "operation", "execute"), error)
        raise


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--target", default=".")
    commands = value.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--task-reference", required=True)
    plan.add_argument("--authorization-record", required=True)
    plan.add_argument("--output")
    apply = commands.add_parser("apply")
    apply.add_argument("--plan", required=True)
    apply.add_argument("--accept-digest", required=True)
    apply.add_argument("--authorization", required=True)
    resume = commands.add_parser("resume")
    resume.add_argument("--receipt-id", required=True)
    resume.add_argument("--authorization", required=True)
    attest = commands.add_parser("attest-post-merge")
    attest.add_argument("--receipt-id", required=True)
    attest.add_argument("--evidence", required=True)
    return value


def main() -> int:
    args = parser().parse_args()
    root = source_root(args.target)
    if args.command == "plan":
        task_path = external_path(root, args.task_reference)
        standing_path = external_path(root, args.authorization_record)
        value = build_plan(root, task_path, standing_path)
        if args.output:
            write_new(root, args.output, value)
        else:
            sys.stdout.buffer.write(canonical_bytes(value))
    elif args.command == "apply":
        value = apply_plan(root, external_path(root, args.plan), args.accept_digest, external_path(root, args.authorization))
        print(json.dumps(value, indent=2, sort_keys=True))
    elif args.command == "resume":
        _transaction, completion, _autonomous = engine_modules()
        value = completion.resume(root, args.receipt_id, external_path(root, args.authorization))
        print(json.dumps(value, indent=2, sort_keys=True))
    elif args.command == "attest-post-merge":
        transaction, completion, _autonomous = engine_modules()
        receipt = completion.validate_receipt(transaction.load_work_completion_receipt(root, args.receipt_id))
        value = completion.record_source_post_merge_validation(root, receipt, external_path(root, args.evidence))
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        raise SourceCompletionError("unsupported source work-completion command")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as error:
        print(f"source work completion blocked: {error}", file=sys.stderr)
        raise SystemExit(2) from error
