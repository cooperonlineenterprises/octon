#!/usr/bin/env python3
"""Plan and apply bounded, fingerprint-bound established-project adoption."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
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


PLANNER = load_module("octon_adoption_planner", SCRIPT_ROOT / "plan_adoption.py")
SCAFFOLDER = load_module("octon_adoption_scaffolder", SCRIPT_ROOT / "scaffold_project.py")
SETUP = load_module("octon_adoption_setup", SCRIPT_ROOT / "setup_session.py")
TRANSACTION = load_module(
    "octon_adoption_transaction",
    SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_transaction.py.tmpl",
)
CONTINUATION = load_module(
    "octon_adoption_continuation",
    SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_continuation.py.tmpl",
)


class AdoptionError(ValueError):
    """The adoption proposal is ambiguous, stale, or not explicitly reviewed."""


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AdoptionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    except (OSError, json.JSONDecodeError) as error:
        raise AdoptionError(f"cannot load {path}: {error}") from error


def write_output(path: Path, value: object, *, json_output: bool = False) -> None:
    TRANSACTION.write_new_json(path, value)
    digest = value.get("canonical_plan_digest") or value.get("canonical_proposal_digest")
    if isinstance(value, dict) and value.get("artifact_kind") == "transaction_plan":
        summary = CONTINUATION.plan_summary(value)
        print(
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False)
            if json_output
            else f"[PLAN] {path}\n{CONTINUATION.render_plan_summary(summary)}"
        )
    elif not json_output:
        print(f"[PROPOSAL] {path}")
        if digest:
            print(f"[DIGEST] {digest}")


def proposal_digest(value: dict[str, Any]) -> str:
    unsigned = dict(value)
    supplied = unsigned.pop("canonical_proposal_digest", None)
    expected = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if supplied != expected:
        raise AdoptionError("adoption proposal digest is invalid")
    return expected


def validate_stored_proposal(
    proposal: dict[str, Any], target: Path, profile: str, layout: str
) -> str:
    if (
        proposal.get("schema_version") != "octon-mini.bootstrap.adoption-proposal.v1"
        or proposal.get("authority", "").startswith("Read-only") is False
        or proposal.get("target") != str(target)
        or proposal.get("requested_profile") != profile
        or proposal.get("requested_layout") != layout
        or proposal.get("octon_mini_version") != SCAFFOLDER.octon_mini_version()
    ):
        raise AdoptionError("stored proposal target, version, profile, layout, or authority differs")
    digest = proposal_digest(proposal)
    for item in proposal.get("semantic_inspection", {}).get("inspected", []):
        path = target / item.get("path", "")
        if path.is_symlink() or not path.is_file():
            raise AdoptionError(f"proposal evidence path changed: {item.get('path')}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != item.get("sha256"):
            raise AdoptionError(f"proposal evidence content changed: {item.get('path')}")
    return digest


def review_dispositions(
    proposal: dict[str, Any], review_path: Path | None
) -> list[dict[str, Any]]:
    ambiguities = proposal.get("unresolved_ambiguity", [])
    if not ambiguities:
        return []
    if review_path is None:
        raise AdoptionError(
            "functional-equivalence candidates require --review bound to the proposal digest"
        )
    review = load_json(review_path)
    if (
        not isinstance(review, dict)
        or set(review) != {"schema_version", "permission_grant", "proposal_digest", "dispositions", "limitations"}
        or review.get("schema_version") != "octon-mini.bootstrap.adoption-review.v1"
        or review.get("permission_grant") is not False
        or review.get("proposal_digest") != proposal.get("canonical_proposal_digest")
        or not isinstance(review.get("dispositions"), list)
        or not isinstance(review.get("limitations"), list)
    ):
        raise AdoptionError("adoption review uses an invalid or unbound closed contract")
    expected = {item["id"] for item in ambiguities}
    observed: set[str] = set()
    for item in review["dispositions"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"ambiguity_id", "disposition", "rationale"}
            or item.get("ambiguity_id") in observed
            or item.get("ambiguity_id") not in expected
            or item.get("disposition") not in {
                "add_parallel_after_review",
                "manual_reconcile_before_replan",
                "confirmed_equivalent_requires_project_specific_mapping",
            }
            or not isinstance(item.get("rationale"), str)
            or not item["rationale"].strip()
        ):
            raise AdoptionError("adoption review contains an invalid disposition")
        observed.add(item["ambiguity_id"])
    if observed != expected:
        raise AdoptionError("adoption review must disposition every current ambiguity exactly once")
    blocked = [
        item for item in review["dispositions"]
        if item["disposition"] != "add_parallel_after_review"
    ]
    if blocked:
        raise AdoptionError(
            "manual reconciliation or functional mapping is required before a complete scaffold can be planned"
        )
    return review["dispositions"]


def generate_candidate(
    project_name: str,
    profile: str,
    layout: str,
    project_slug: str | None,
    generation_identifier: str,
) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temporary = tempfile.TemporaryDirectory(prefix="octon-mini-adoption-candidate-")
    candidate = Path(temporary.name) / "candidate"
    command = [
        sys.executable,
        "-B",
        str(SCRIPT_ROOT / "scaffold_project.py"),
        "--target",
        str(candidate),
        "--project-name",
        project_name,
        "--profile",
        profile,
        "--layout",
        layout,
        "--generation-id",
        generation_identifier,
    ]
    if project_slug is not None:
        command.extend(["--project-slug", project_slug])
    result = subprocess.run(
        command,
        cwd=SCRIPT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode:
        temporary.cleanup()
        raise AdoptionError(
            "candidate generation failed without changing the target: "
            + (result.stderr.strip() or result.stdout.strip())[:1000]
        )
    return temporary, candidate


def set_adoption_in_progress(candidate: Path) -> None:
    project_path = candidate / ".agent/project.json"
    policy_path = candidate / ".agent/policy.json"
    project = load_json(project_path)
    policy = load_json(policy_path)
    project["project"]["adoption_status"] = "in_progress"
    project["project"]["adoption_decision_ref"] = None
    policy["project_specific_adoption"]["status"] = "in_progress"
    project_path.write_text(json.dumps(project, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    origin_path = candidate / ".octon-origin.json"
    origin = load_json(origin_path)
    for item in origin["installed_inventory"]["paths"]:
        if item["role"] in {"derived", "provenance"}:
            continue
        path = candidate / item["path"]
        item["mode"] = path.stat().st_mode & 0o7777
        item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    origin_path.write_text(json.dumps(origin, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def analysis_item(
    identifier: str,
    summary: str,
    source_refs: list[str],
    *,
    rule: str | None,
    confidence: str,
    limitations: list[str],
) -> dict[str, Any]:
    return {
        "id": identifier,
        "summary": summary,
        "source_refs": source_refs,
        "rule": rule,
        "confidence": confidence,
        "limitations": limitations,
    }


def transaction_plan(
    target: Path,
    proposal: dict[str, Any],
    *,
    project_name: str,
    project_slug: str | None,
    profile: str,
    layout: str,
    authority_source: str,
    review_path: Path | None,
    setup_binding: tuple[dict[str, Any], Path] | None = None,
    predecessor_plan: tuple[dict[str, Any], Path] | None = None,
) -> dict[str, Any]:
    proposal_hash = validate_stored_proposal(proposal, target, profile, layout)
    dispositions = review_dispositions(proposal, review_path)
    if proposal.get("confirmed_collisions"):
        paths = ", ".join(item["path"] for item in proposal["confirmed_collisions"][:20])
        raise AdoptionError(
            "exact path collisions require project-specific reconciliation before re-planning: " + paths
        )
    if not authority_source.startswith(("authority:", "external:")):
        raise AdoptionError("--authority-source must use an authority: or external: reference")
    generation_identifier = hashlib.sha256(
        TRANSACTION.canonical_bytes(
            {
                "operation": "adopt.install",
                "octon_mini_version": SCAFFOLDER.octon_mini_version(),
                "proposal_digest": proposal_hash,
                "project_name": project_name,
                "project_slug": project_slug,
                "profile": profile,
                "layout": layout,
            }
        )
    ).hexdigest()[:32]
    temporary, candidate = generate_candidate(
        project_name,
        profile,
        layout,
        project_slug,
        generation_identifier,
    )
    try:
        set_adoption_in_progress(candidate)
        origin = load_json(candidate / ".octon-origin.json")
        derived = {
            item["path"]
            for item in origin["installed_inventory"]["paths"]
            if item["role"] == "derived"
        }
        inventory_by_path = {
            item["path"]: item for item in origin["installed_inventory"]["paths"]
        }
        operations = []
        for relative in origin["generated_paths"]:
            if relative in derived:
                continue
            path = candidate / relative
            operations.append(
                TRANSACTION.operation(
                    "create",
                    relative,
                    path.read_bytes(),
                    "Install a reviewed non-overwriting Octon snapshot path during established-project adoption.",
                    mode=path.stat().st_mode & 0o7777,
                )
            )
        proposal_ref = f"proposal:{proposal_hash}"
        observations = [
            analysis_item(
                "adoption.semantic-inspection",
                f"Bounded inspection read {proposal['semantic_inspection']['files_inspected']} allowlisted files and retained no content.",
                [proposal_ref],
                rule="200 files / 256 KiB each / 4 MiB total unless explicitly overridden",
                confidence="deterministic",
                limitations=["Uninspected and excluded content may contain additional relevant context."],
            )
        ]
        if setup_binding is not None:
            observations.append(
                analysis_item(
                    "adoption.guided-setup-session",
                    "A current non-authorizing guided setup session supplied reviewed inputs without converting selections into accepted authority.",
                    [setup_binding[0]["canonical_session_digest"]],
                    rule="octon-mini.bootstrap.setup-session.v2",
                    confidence="deterministic",
                    limitations=["Optional unresolved matters remain explicit and work completion is not enabled."],
                )
            )
        inferences = [
            analysis_item(
                f"adoption.{item['id'].casefold()}",
                f"{item['concern']} candidate at {item['path']} was explicitly dispositioned as add_parallel_after_review.",
                [proposal_ref, f"path:{item['path']}"],
                rule="bounded semantic/path-name candidate plus explicit review",
                confidence=item["confidence"],
                limitations=["Parallel addition does not make either representation authoritative by inference."],
            )
            for item in proposal.get("unresolved_ambiguity", [])
        ]
        decisions = [
            analysis_item(
                "adoption.explicit-configuration",
                f"Explicit inputs selected project name {project_name!r}, profile {profile}, and layout {layout}.",
                [authority_source],
                rule=None,
                confidence="deterministic",
                limitations=["These inputs do not establish target-project readiness or final harness adoption."],
            )
        ]
        gates = [
            analysis_item(
                "adoption.finalization-gate",
                "Final adoption remains gated on an accepted project decision, explicit hook assessments, full project checks, and readiness review.",
                [authority_source],
                rule="adoption_status remains in_progress",
                confidence="deterministic",
                limitations=["This transaction installs structure only and grants no permission."],
            )
        ]
        evidence_paths = sorted(
            {
                item["path"]
                for item in proposal["semantic_inspection"]["inspected"]
            }
            | {
                item["path"]
                for items in proposal["likely_functional_equivalents"].values()
                for item in items
            }
        )
        return TRANSACTION.build_plan(
            target,
            operation_name="adopt.install",
            scope=f"Install Octon {profile}/{layout} structure into the established project",
            operations=operations,
            evidence=[
                TRANSACTION.source_evidence(
                    "bounded_adoption_proposal",
                    proposal_ref,
                    content=json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode("utf-8"),
                    limitations=["The proposal records hashes and signals, not inspected content."],
                ),
                TRANSACTION.source_evidence("explicit_repository_local_authority", authority_source),
                *SETUP.transaction_evidence(setup_binding, TRANSACTION),
            ],
            assumptions=[],
            confidence="high",
            limitations=[
                "Existing files are never overwritten; any new collision makes apply fail closed.",
                "Installed structure remains adoption-in-progress and does not prove target readiness.",
                "Hook and archetype candidates remain unadopted proposals.",
            ],
            excluded_paths=[item["path"] for item in proposal["semantic_inspection"]["excluded"]],
            staged_validation_plan=[
                [sys.executable, "-B", ".agent/scripts/refresh.py", "--refresh"],
                [sys.executable, "-B", ".agent/scripts/validate.py", "--check"],
                [sys.executable, "-B", ".agent/tests/test_validate.py", "--tier", "release"],
            ],
            derived_write_paths=sorted(derived),
            post_apply_validation_plan=[
                [sys.executable, "-B", ".agent/scripts/validate.py", "--check"]
            ],
            evidence_paths=evidence_paths,
            analysis={
                "observations": observations,
                "inferences": inferences,
                "explicit_decisions": decisions,
                "authorization_gates": gates,
            },
            predecessor_plan=predecessor_plan,
        )
    finally:
        temporary.cleanup()


def initial_or_exact_plan(args: argparse.Namespace) -> int:
    target = args.target.expanduser().resolve()
    reject_existing_installation(target)
    output = args.output.expanduser().resolve()
    setup_binding = SETUP.prepare_plan_session("adoption", args)
    args._setup_binding = setup_binding
    if args.project_name is None:
        raise AdoptionError("adoption requires --project-name or setup.project-name")
    if args.profile is None:
        raise AdoptionError("adoption requires --profile or setup.assurance-profile")
    if args.layout is None:
        args.layout = "compact"
    if args.proposal is None:
        proposal = PLANNER.build_plan(
            target,
            args.profile,
            layout=args.layout,
            max_files=args.max_files,
            max_file_bytes=args.max_file_bytes,
            max_total_bytes=args.max_total_bytes,
            sensitive_opt_in=set(args.include_sensitive_path),
        )
        if proposal["confirmed_collisions"] or proposal["unresolved_ambiguity"] or args.authority_source is None:
            write_output(output, proposal, json_output=args.json)
            successor_output = output.with_name(output.stem + "-successor.json")
            review_output = output.with_name(output.stem + "-review.json")
            if args.authority_source is None:
                next_description = "Collect the missing project authority reference in an immutable setup successor."
                next_argv = [
                    "./octon", "adopt", "setup", "--target", str(target),
                    "--tty", "--output", str(output.with_name(output.stem + "-authority-session.json")),
                ]
            elif proposal["confirmed_collisions"]:
                next_description = "After project-owned collision reconciliation, re-run bounded adoption planning into the named successor."
                next_argv = [
                    "./octon", "adopt", "plan", "--target", str(target),
                    "--project-name", args.project_name, "--profile", args.profile,
                    "--layout", args.layout, "--authority-source", args.authority_source,
                    "--output", str(successor_output),
                ]
            else:
                next_description = "Create the exact proposal-bound review file, then run this successor-plan command."
                next_argv = [
                    "./octon", "adopt", "plan", "--target", str(target),
                    "--project-name", args.project_name, "--profile", args.profile,
                    "--layout", args.layout, "--authority-source", args.authority_source,
                    "--proposal", str(output), "--review", str(review_output),
                    "--output", str(successor_output),
                ]
            report = CONTINUATION.finding(
                failure_code="OCTON-ADOPT-1101",
                blocked_operation="adopt.install",
                phase="review",
                root_cause="Adoption found collisions, functional-equivalence ambiguity, or missing current authority.",
                authority_source="proposal_bound_adoption_review_and_project_authority",
                repair_class="review_required",
                next_action=CONTINUATION.action(
                    next_description,
                    next_argv,
                    read_only=True,
                ),
                invalidated=[],
                preserved=[CONTINUATION.proof_state("plan", str(output), "The immutable adoption proposal remains current review input.", ["source_fingerprint_bound"])],
                safe_read_only_actions=[CONTINUATION.action("Inspect coded recovery guidance.", ["./octon", "doctor", "--json"], read_only=True)],
                successor_plan=True,
                successor_reason="A transaction-plan successor can be generated after every proposal-bound ambiguity is dispositioned.",
            )
            CONTINUATION.record_local_artifact_writes(report, target, [output])
            print(CONTINUATION.render_finding(report, json_output=args.json), file=sys.stderr)
            return 3
    else:
        proposal = load_json(args.proposal.expanduser())
    if args.authority_source is None:
        raise AdoptionError("exact adoption planning requires --authority-source")
    predecessor = None
    if args.prior_plan is not None:
        prior_path = args.prior_plan.expanduser().resolve()
        predecessor = (CONTINUATION.load_exact_plan(prior_path), prior_path)
    plan = transaction_plan(
        target,
        proposal,
        project_name=args.project_name,
        project_slug=args.project_slug,
        profile=args.profile,
        layout=args.layout,
        authority_source=args.authority_source,
        review_path=args.review.expanduser() if args.review else None,
        setup_binding=setup_binding,
        predecessor_plan=predecessor,
    )
    write_output(output, plan, json_output=args.json)
    return 0


def apply(args: argparse.Namespace) -> int:
    target = args.target.expanduser().resolve()
    reject_existing_installation(target)
    plan = TRANSACTION.load_plan(args.plan.expanduser())
    if plan.get("operation") != "adopt.install":
        raise AdoptionError("plan is not an established-project adoption transaction")
    SETUP.verify_plan_binding(target, plan)
    receipt, receipt_path = TRANSACTION.apply_plan(target, plan, args.accept_digest)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False))
    else:
        print(f"[APPLIED] {receipt['receipt_id']}")
        print(f"[RECEIPT] {receipt_path}")
        print("[TIMING] " + json.dumps(TRANSACTION.LAST_PHASE_TIMINGS, sort_keys=True))
        print("[STATUS] harness structure installed; project adoption remains in_progress")
    return 0


def reject_existing_installation(target: Path) -> None:
    for name in (".octon", ".octon-origin.json", ".octon-mini-origin.json", ".project-blueprint-origin.json"):
        path = target / name
        if path.exists() or path.is_symlink():
            raise AdoptionError(f"existing installation at {name}; use its explicit supported upgrade path")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="octon adopt",
        description="Add the Octon harness and dossier to an established project"
    )
    commands = root.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="inspect and plan a collision-safe adoption")
    plan.add_argument("--target", type=Path, required=True)
    plan.add_argument("--project-name")
    plan.add_argument("--project-slug")
    plan.add_argument("--profile", choices=("minimal", "standard", "high-assurance"))
    plan.add_argument("--layout", choices=("compact", "separated"))
    plan.add_argument("--authority-source")
    plan.add_argument("--proposal", type=Path)
    plan.add_argument("--review", type=Path)
    plan.add_argument("--output", type=Path, required=True)
    plan.add_argument("--max-files", type=int, default=PLANNER.DEFAULT_MAX_FILES)
    plan.add_argument("--max-file-bytes", type=int, default=PLANNER.DEFAULT_MAX_FILE_BYTES)
    plan.add_argument("--max-total-bytes", type=int, default=PLANNER.DEFAULT_MAX_TOTAL_BYTES)
    plan.add_argument("--include-sensitive-path", action="append", default=[])
    plan.add_argument("--setup-session", type=Path)
    plan.add_argument("--prior-plan", type=Path)
    plan.add_argument("--json", action="store_true")
    apply_parser = commands.add_parser("apply", help="apply the exact accepted adoption plan")
    apply_parser.add_argument("--target", type=Path, required=True)
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--accept-digest", required=True)
    apply_parser.add_argument("--json", action="store_true")
    SETUP.add_setup_parser(commands, "adoption")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "setup":
            return SETUP.run_setup(args)
        return initial_or_exact_plan(args) if args.command == "plan" else apply(args)
    except (AdoptionError, OSError, RuntimeError, ValueError, SETUP.SetupError, TRANSACTION.TransactionError) as error:
        report = getattr(error, "report", None)
        if not isinstance(report, dict):
            report = CONTINUATION.fallback(
                error,
                blocked_operation="adopt.install",
                phase="apply" if getattr(args, "command", None) == "apply" else "plan",
                next_argv=["./octon", "adopt", "--help"],
            )
        print(CONTINUATION.render_finding(report, json_output=getattr(args, "json", False)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
