#!/usr/bin/env python3
"""Source-repository entry point for the existing closed delivery-effect adapter."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
CORE_PATH = SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_autonomous_delivery.py.tmpl"
RUNTIME_PATH = SKILL_ROOT / "assets/packages/autonomous-delivery/templates/.agent/capabilities/autonomous-delivery/delivery_runtime.py.tmpl"


class SourceEffectError(RuntimeError):
    """Fail-closed source delivery-effect error."""


def load_template(path: Path, name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
    return module


def modules() -> tuple[types.ModuleType, types.ModuleType]:
    core = load_template(CORE_PATH, "octon_source_delivery_core")
    runtime = load_template(RUNTIME_PATH, "octon_source_delivery_effect_runtime")
    runtime.load_core = lambda _root: core
    return core, runtime


def source_root(raw: str) -> Path:
    root = Path(raw).resolve()
    if not root.is_dir() or not (root / "octon-mini.json").is_file() or not (root / "VERSION").is_file() or not (root / ".git").exists():
        raise SourceEffectError("target is not the Octon Mini source repository")
    if (root / ".agent/project.json").exists():
        raise SourceEffectError("source delivery effects are inapplicable to a generated project")
    return root


def external_path(root: Path, raw: str, *, require_file: bool = True) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise SourceEffectError("source delivery-effect evidence paths must be absolute")
    path = path.resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError:
        pass
    else:
        raise SourceEffectError("source delivery-effect evidence must remain outside the repository")
    current = Path(path.anchor)
    for part in path.parts[1:-1]:
        current = current / part
        if current.is_symlink():
            raise SourceEffectError("source delivery-effect evidence has a symlink ancestor")
    if require_file and (not path.is_file() or path.is_symlink()):
        raise SourceEffectError(f"required external evidence is absent or unsafe: {path}")
    return path


def write_new(root: Path, raw: str, value: Any, runtime: types.ModuleType) -> Path:
    path = external_path(root, raw, require_file=False)
    if not path.parent.is_dir() or path.parent.is_symlink() or path.exists():
        raise SourceEffectError("external output parent must exist and output must be new")
    with path.open("xb") as handle:
        handle.write(runtime.canonical_bytes(value))
        handle.flush()
    return path


def work_completion_receipt_directory(root: Path, runtime: types.ModuleType) -> Path:
    raw = runtime.git(root, "rev-parse", "--git-common-dir")
    common = Path(raw)
    common = (common if common.is_absolute() else root / common).resolve(strict=True)
    directory = common / "octon-mini/work-completion/receipts"
    if directory.is_symlink() or not directory.is_dir():
        raise SourceEffectError("post-merge workflow dispatch lacks a safe work-completion receipt store")
    return directory


def require_post_merge_dispatch(
    root: Path,
    projection: dict[str, Any],
    expected_commit: str,
    runtime: types.ModuleType,
) -> None:
    matches: list[dict[str, Any]] = []
    for path in sorted(work_completion_receipt_directory(root, runtime).glob("WCR-*.json")):
        if path.is_symlink() or not path.is_file():
            raise SourceEffectError("post-merge workflow dispatch receipt store is unsafe")
        receipt = runtime.load_json(path)
        if not isinstance(receipt, dict) or receipt.get("plan_digest") != projection.get("plan_digest"):
            continue
        completed = receipt.get("completed_operations")
        revisions = receipt.get("revisions")
        plan = receipt.get("plan")
        required = {
            "record_candidate_matrix_validation",
            "merge_pull_request",
            "synchronize_local_default_branch",
        }
        if (
            receipt.get("schema_version") == "harness.work-completion-receipt.v1"
            and receipt.get("artifact_kind") == "work_completion_receipt"
            and receipt.get("permission_grant") is False
            and receipt.get("receipt_id") == path.stem
            and isinstance(completed, list)
            and all(isinstance(item, str) for item in completed)
            and required <= set(completed)
            and isinstance(revisions, dict)
            and revisions.get("integrated") == expected_commit
            and revisions.get("synchronized_default") == expected_commit
            and isinstance(plan, dict)
            and plan.get("schema_version") == "harness.source-work-completion-plan.v1"
            and plan.get("canonical_plan_digest") == projection.get("plan_digest")
            and isinstance(plan.get("branches"), dict)
            and plan["branches"].get("default") == "main"
            and isinstance(plan.get("expected_revisions"), dict)
            and revisions.get("commit") == plan["expected_revisions"].get("candidate_head")
        ):
            matches.append(receipt)
    if len(matches) != 1:
        raise SourceEffectError(
            "post-merge workflow dispatch requires one exact integrated work-completion receipt"
        )


def execution_branch(action: str, projection: dict[str, Any], requested_branch: str | None = None) -> str:
    if action == "dispatch_hosted_workflow":
        branch = projection.get("task_branch")
        if not isinstance(branch, str) or not branch:
            raise SourceEffectError("candidate workflow dispatch lacks the exact task branch")
        selected = branch if requested_branch is None else requested_branch
        if selected not in {branch, "main"}:
            raise SourceEffectError("source delivery effect uses the wrong execution branch")
        return selected
    return "main"


def source_plan(args: Any, root: Path, runtime: types.ModuleType) -> dict[str, Any]:
    projection = runtime.load_json(external_path(root, args.projection))
    required_branch = execution_branch(args.action, projection, args.default_branch)
    if args.default_branch != required_branch:
        raise SourceEffectError("source delivery effect uses the wrong execution branch")
    if args.action == "dispatch_hosted_workflow":
        if args.commit != runtime.git(root, "rev-parse", f"refs/heads/{required_branch}"):
            raise SourceEffectError("workflow dispatch commit differs from the exact execution branch")
        if required_branch == "main":
            require_post_merge_dispatch(root, projection, args.commit, runtime)
    value = runtime.plan_from(args, root)
    if value.get("default_branch") != required_branch:
        raise SourceEffectError("source delivery-effect plan lost its exact execution branch")
    return value


def validate_effect_inputs(args: Any, root: Path, runtime: types.ModuleType) -> None:
    plan = runtime.load_json(external_path(root, args.plan))
    projection = runtime.load_json(external_path(root, args.projection))
    if not isinstance(plan, dict) or not isinstance(projection, dict):
        raise SourceEffectError("source delivery-effect plan or projection is malformed")
    required_branch = execution_branch(plan.get("action"), projection, plan.get("default_branch"))
    if plan.get("default_branch") != required_branch or plan.get("expected_commit") != runtime.git(root, "rev-parse", f"refs/heads/{required_branch}"):
        raise SourceEffectError("source delivery-effect plan is stale or bound to another branch")
    if plan.get("action") == "dispatch_hosted_workflow" and required_branch == "main":
        require_post_merge_dispatch(root, projection, plan["expected_commit"], runtime)


def main() -> int:
    core, runtime = modules()
    args = runtime.parser().parse_args()
    root = source_root(args.target)
    runtime.root_path = lambda _raw: root
    if args.command == "status":
        value = {
            "schema_version": "harness.autonomous-delivery-source-runtime-status.v1",
            "permission_grant": False,
            "supported_release_effects": sorted(runtime.SUPPORTED),
            "work_completion_operations": [],
            "unknown_outcome_retries": 0,
            "direct_external_spending_usd": 0,
        }
    elif args.command == "plan":
        value = source_plan(args, root, runtime)
        if args.output:
            write_new(root, args.output, value, runtime)
            return 0
    elif args.command == "apply":
        validate_effect_inputs(args, root, runtime)
        value = runtime.apply_effect(args, root)
    elif args.command == "resume":
        validate_effect_inputs(args, root, runtime)
        value = runtime.resume_effect(args, root)
    else:
        raise SourceEffectError("unsupported source delivery-effect command")
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SourceEffectError, RuntimeError, ValueError) as error:
        print(f"source delivery effect blocked: {error}", file=sys.stderr)
        raise SystemExit(2) from error
