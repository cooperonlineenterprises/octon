#!/usr/bin/env python3
"""Plan/apply a progressive, evidence-scoped collaboration assessment."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
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


TRANSACTION = load_module(
    "octon_collaboration_transaction",
    SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_transaction.py.tmpl",
)
PACKAGE = load_module("octon_collaboration_decisions", SCRIPT_ROOT / "package_project.py")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def parse_time(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO 8601 date-time") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def evidence(source: str, observed_at: str, expires_at: str, limitations: list[str]) -> dict[str, Any]:
    if not source.startswith(("authority:", "external:", "repo:", "url:")):
        raise ValueError("evidence source must begin authority:, external:, repo:, or url:")
    observed = parse_time(observed_at, "--observed-at")
    expires = parse_time(expires_at, "--expires-at")
    if expires <= observed:
        raise ValueError("--expires-at must be later than --observed-at")
    if expires <= datetime.now(timezone.utc):
        raise ValueError("collaboration evidence is already stale")
    return {
        "source": source,
        "observed_at": observed.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "limitations": limitations or ["Aggregate project-owned collaboration fact; identities are intentionally omitted."],
    }


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


def assessed_profile(args: argparse.Namespace) -> tuple[dict[str, Any], list[str]]:
    if not 1 <= args.writer_count <= 5:
        raise ValueError("the supported collaboration bands require --writer-count 1 through 5")
    band = "solo" if args.writer_count == 1 else "pair" if args.writer_count == 2 else "tiny"
    common = evidence(args.source, args.observed_at, args.expires_at, args.limitation)
    facts: dict[str, Any] = {
        "writer_count": {"value": args.writer_count, "evidence": common},
        "solo_integration_preference": {"value": None, "evidence": None},
        "independent_review_capacity": {"value": None, "evidence": None},
        "concurrency": {"human_writers": None, "agents_or_automation": None, "evidence": None},
        "external_contribution_mode": {"value": None, "evidence": None},
    }
    used = ["writer_count"]
    modifiers: list[str] = []
    if band == "solo":
        if args.solo_integration_preference not in {"direct", "reviewable"}:
            raise ValueError("solo assessment requires --solo-integration-preference direct|reviewable")
        facts["solo_integration_preference"] = {
            "value": args.solo_integration_preference,
            "evidence": common,
        }
        used.append("solo_integration_preference")
    else:
        if args.independent_review_capacity is None:
            raise ValueError("pair/tiny assessment requires an explicit --independent-review-capacity yes|no")
        facts["independent_review_capacity"] = {
            "value": args.independent_review_capacity == "yes",
            "evidence": common,
        }
        used.append("independent_review_capacity")

    concurrent = args.concurrent_humans is not None or args.concurrent_agents is not None
    if concurrent:
        if args.concurrent_humans is None or args.concurrent_agents is None:
            raise ValueError("concurrency requires both --concurrent-humans and --concurrent-agents")
        if args.concurrent_humans < 0 or args.concurrent_agents < 0:
            raise ValueError("concurrency counts cannot be negative")
        if args.concurrent_humans > args.writer_count:
            raise ValueError("concurrent humans cannot exceed the write-capable human count")
        facts["concurrency"] = {
            "human_writers": args.concurrent_humans,
            "agents_or_automation": args.concurrent_agents,
            "evidence": common,
        }
        if args.concurrent_humans + args.concurrent_agents > 1:
            used.append("concurrency")
            modifiers.append("concurrent_work")

    if args.external_contribution_mode is not None:
        facts["external_contribution_mode"] = {
            "value": args.external_contribution_mode,
            "evidence": common,
        }
        used.append("external_contribution_mode")

    if band == "solo":
        hybrid = args.solo_integration_preference == "reviewable" or bool(modifiers)
        base = "solo_hybrid" if hybrid else "solo_direct"
        review_mode = "self_review" if hybrid else "none"
        integration = None if hybrid else "not_applicable"
    else:
        base = "pair_pr" if band == "pair" else "tiny_pr"
        capacity = args.independent_review_capacity == "yes"
        review_mode = "one_peer_when_available" if capacity else "block_when_peer_unavailable"
        integration = None

    selection_status = "adopted" if args.adoption_decision_ref else "proposed"
    profile = {
        "schema_version": "harness.collaboration-profile.v2",
        "permission_grant": False,
        "assessment_status": "assessed",
        "facts": facts,
        "conflicting_signals": [],
        "team_band": band,
        "concurrent_work": bool(modifiers),
        "workflow_selection": {
            "status": selection_status,
            "base_workflow": base,
            "modifiers": modifiers,
            "review_mode": review_mode,
            "integration_method": integration,
            "adoption_decision_ref": args.adoption_decision_ref,
            "used_fact_ids": sorted(used),
        },
        "limitations": [
            "This aggregate assessment stores no collaborator identities.",
            "A proposed workflow is non-authorizing until an accepted project-owned decision adopts it.",
        ],
    }
    return profile, used


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    target = args.target.resolve()
    project_path = target / ".agent/project.json"
    project = load_json(project_path)
    if project.get("schema_version") not in {"harness.project.v5", "harness.project.v6", "harness.project.v7", "harness.project.v8"}:
        raise ValueError("target does not use the collaboration-v2 Octon Mini contract")
    profile, used = assessed_profile(args)
    evidence_paths = [".agent/project.json"]
    if args.adoption_decision_ref:
        PACKAGE.require_accepted_decision(target, args.adoption_decision_ref)
        decision = sorted((target / ".agent/decisions").glob(f"{args.adoption_decision_ref}*.md"))[0]
        evidence_paths.append(decision.relative_to(target).as_posix())
    project["collaboration_profile"] = profile
    observations = [
        {
            "id": "collaboration.aggregate_facts",
            "summary": f"Explicit evidence records {args.writer_count} write-capable human(s).",
            "source_refs": [args.source],
            "rule": "writer_count_to_supported_team_band",
            "confidence": "high",
            "limitations": ["Aggregate counts do not identify people or establish authority."],
        }
    ]
    decisions = []
    if args.adoption_decision_ref:
        decisions.append(
            {
                "id": "collaboration.workflow_adoption",
                "summary": f"Accepted decision {args.adoption_decision_ref} adopts the selected workflow.",
                "source_refs": [args.adoption_decision_ref],
                "rule": None,
                "confidence": "deterministic",
                "limitations": ["The decision applies only within its recorded scope."],
            }
        )
    return TRANSACTION.build_plan(
        target,
        operation_name="maintain.collaboration",
        scope="Record a progressive collaboration assessment and optional workflow adoption",
        operations=[
            TRANSACTION.operation(
                "replace",
                ".agent/project.json",
                json_bytes(project),
                "Store only explicitly supplied, evidence-scoped collaboration facts and their derived proposal.",
            )
        ],
        evidence=[
            TRANSACTION.source_evidence(
                "explicit_collaboration_evidence",
                args.source,
                limitations=args.limitation,
            )
        ],
        evidence_paths=evidence_paths,
        assumptions=[],
        confidence="high",
        limitations=[
            "Assurance profile remains independent of collaboration size.",
            "Concurrent work is a modifier, not a team band.",
            "This transaction grants no permission.",
        ],
        analysis={
            "observations": observations,
            "inferences": [
                {
                    "id": "collaboration.workflow_proposal",
                    "summary": f"The progressive contract derives {profile['workflow_selection']['base_workflow']} using {', '.join(used)}.",
                    "source_refs": [args.source],
                    "rule": "progressive_collaboration_v2",
                    "confidence": "high",
                    "limitations": ["The derived workflow remains a proposal unless explicitly adopted."],
                }
            ],
            "explicit_decisions": decisions,
            "authorization_gates": [],
        },
        **transaction_validation(target),
    )


def add_assessment_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--writer-count", type=int, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--expires-at", required=True)
    parser.add_argument("--limitation", action="append", default=[])
    parser.add_argument("--solo-integration-preference", choices=("direct", "reviewable"))
    parser.add_argument("--independent-review-capacity", choices=("yes", "no"))
    parser.add_argument("--concurrent-humans", type=int)
    parser.add_argument("--concurrent-agents", type=int)
    parser.add_argument("--external-contribution-mode")
    parser.add_argument("--adoption-decision-ref")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="octon maintain collaboration",
        description="Assess Octon Mini project collaboration without granting workflow authority"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="plan an evidence-bound collaboration assessment")
    add_assessment_arguments(plan)
    plan.add_argument("--output", type=Path, required=True)
    apply = commands.add_parser("apply", help="apply the exact accepted assessment plan")
    apply.add_argument("--target", type=Path, required=True)
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--accept-digest", required=True)
    args = parser.parse_args()
    try:
        if args.command == "plan":
            value = build_plan(args)
            TRANSACTION.write_new_json(args.output, value)
            print(f"[PLAN] {args.output}")
            print(f"[DIGEST] {value['canonical_plan_digest']}")
            return 0
        target = args.target.resolve()
        value = TRANSACTION.load_plan(args.plan)
        if value.get("operation") != "maintain.collaboration":
            raise ValueError("plan is not a collaboration transaction")
        receipt, receipt_path = TRANSACTION.apply_plan(target, value, args.accept_digest)
        print(f"[APPLIED] {receipt['receipt_id']}")
        print(f"[RECEIPT] {receipt_path}")
        return 0
    except (OSError, RuntimeError, ValueError, TRANSACTION.TransactionError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
