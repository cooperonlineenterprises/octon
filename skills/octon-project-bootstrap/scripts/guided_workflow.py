#!/usr/bin/env python3
"""Interactive inspect-question-plan-confirm-apply orchestration."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, Callable


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
MODE_COMMAND = {
    "initialization": "init",
    "adoption": "adopt",
    "upgrade": "upgrade",
}
MODE_SCRIPT = {
    "initialization": "init_project.py",
    "adoption": "adopt_project.py",
    "upgrade": "upgrade_project.py",
}


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


SETUP = load_module("octon_guided_setup", SCRIPT_ROOT / "setup_session.py")
CONTINUATION = load_module(
    "octon_guided_continuation",
    SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_continuation.py.tmpl",
)


def next_artifact(directory: Path, stem: str) -> Path:
    for sequence in range(1, 10000):
        path = directory / f"{stem}-{sequence:04d}.json"
        if not path.exists() and not path.is_symlink():
            return path
    raise ValueError(f"review directory exhausted artifact identities for {stem}")


def run_command(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
        shell=False,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_OPTIONAL_LOCKS": "0",
        },
    )


def write_session(directory: Path, session: dict[str, Any]) -> Path:
    path = next_artifact(directory, "setup-session")
    SETUP.write_new_json(path, session)
    return path


def ensure_review_directory(target: Path, review_dir: Path) -> Path:
    review = review_dir.expanduser().resolve()
    SETUP.ensure_output_outside_target(review / "placeholder.json", target)
    if review.exists() and (review.is_symlink() or not review.is_dir()):
        raise ValueError("guided review path must be a real directory")
    review.mkdir(parents=True, exist_ok=True)
    return review


def collect_required_answers(
    session: dict[str, Any],
    catalog: dict[str, Any],
    review_dir: Path,
    *,
    require_tty: bool,
    initial_path: Path | None = None,
) -> tuple[dict[str, Any], Path]:
    session_path = initial_path or write_session(review_dir, session)
    try:
        while session["session_status"] != "ready_for_plan":
            blocking_ids = {
                item["question_id"] for item in session["unresolved_blockers"]
            }
            necessary = [
                identifier
                for identifier in session["next_eligible_questions"]
                if identifier in blocking_ids
            ]
            if not necessary:
                raise ValueError("guided setup is blocked but has no eligible next question")
            prompt_session = dict(session)
            prompt_session["next_eligible_questions"] = necessary
            # Persist after each answer so an EOF or interrupt never discards a
            # valid response that preceded it in the same interactive run.
            payload = SETUP.tty_answer_batch(
                prompt_session,
                catalog,
                1,
                require_tty=require_tty,
            )
            session = SETUP.apply_answer_batch(session, payload, catalog)
            session_path = write_session(review_dir, session)
    except (EOFError, KeyboardInterrupt, ValueError, SETUP.SetupError) as error:
        report = CONTINUATION.finding(
            failure_code="OCTON-GUIDE-1004",
            blocked_operation=f"{MODE_COMMAND[session['mode']]}.guided",
            phase="questions",
            root_cause=(
                "Interactive question collection paused before the next answer was accepted: "
                + (str(error).strip() or type(error).__name__)
            ),
            authority_source="current_operator_answers_and_setup_question_catalog",
            repair_class="input_required",
            next_action=CONTINUATION.action(
                "Resume from the latest immutable setup session.",
                [
                    "./octon",
                    MODE_COMMAND[session["mode"]],
                    "--target",
                    session["target_identity"]["canonical_path"],
                    "--review-dir",
                    str(review_dir),
                    "--session",
                    str(session_path),
                ],
                read_only=False,
                requires_confirmation=True,
            ),
            preserved=[
                CONTINUATION.proof_state(
                    "session",
                    str(session_path),
                    "All answers accepted before the pause remain in this immutable session.",
                    ["dependency_bound", "source_fingerprint_bound"],
                )
            ],
            safe_read_only_actions=[
                CONTINUATION.action(
                    "Inspect the preserved setup session.",
                    [
                        "python",
                        "-B",
                        str(SCRIPT_ROOT / "setup_session.py"),
                        session["mode"],
                        "--target",
                        session["target_identity"]["canonical_path"],
                        "--session",
                        str(session_path),
                        "--json",
                    ],
                    read_only=True,
                )
            ],
            successor_session=True,
            successor_reason="The preserved session can be resumed directly or reinspected into an immutable successor if dependencies changed.",
            mutation_occurred=True,
            limitations=[
                "Only immutable review artifacts outside the target were written; the target project was not changed."
            ],
        )
        report["mutation"]["statement"] = (
            "The target project was unchanged; immutable review session artifacts were written outside it."
        )
        raise CONTINUATION.ContinuationError(report) from error
    return session, session_path


def plan_argv(
    mode: str,
    target: Path,
    session_path: Path,
    output: Path,
    args: argparse.Namespace,
) -> list[str]:
    argv = [
        sys.executable,
        "-B",
        str(SCRIPT_ROOT / MODE_SCRIPT[mode]),
        "plan",
        "--target",
        str(target),
        "--setup-session",
        str(session_path),
        "--output",
        str(output),
    ]
    if args.json:
        argv.append("--json")
    if args.prior_plan:
        argv.extend(["--prior-plan", str(args.prior_plan.expanduser().resolve())])
    if mode in {"adoption", "upgrade"}:
        if args.proposal:
            argv.extend(["--proposal", str(args.proposal.expanduser().resolve())])
        if args.review:
            argv.extend(["--review", str(args.review.expanduser().resolve())])
    if mode == "upgrade" and args.project_blueprint_seed:
        argv.extend(
            [
                "--project-blueprint-seed",
                str(args.project_blueprint_seed.expanduser().resolve()),
            ]
        )
    return argv


def apply_argv(
    mode: str,
    target: Path,
    plan_path: Path,
    digest: str,
    *,
    json_output: bool,
) -> list[str]:
    argv = [
        sys.executable,
        "-B",
        str(SCRIPT_ROOT / MODE_SCRIPT[mode]),
        "apply",
        "--target",
        str(target),
        "--plan",
        str(plan_path),
        "--accept-digest",
        digest,
    ]
    if json_output:
        argv.append("--json")
    return argv


def run_guided(
    args: argparse.Namespace,
    *,
    require_tty: bool = True,
    input_fn: Callable[[str], str] = input,
) -> int:
    if require_tty and not sys.stdin.isatty():
        report = CONTINUATION.finding(
            failure_code="OCTON-GUIDE-1001",
            blocked_operation=f"{MODE_COMMAND[args.mode]}.guided",
            phase="questions",
            root_cause="One-command orchestration is interactive; this input is not a terminal.",
            authority_source="current_operator_confirmation",
            repair_class="input_required",
            next_action=CONTINUATION.action(
                "Use the explicit non-interactive plan/apply flow with --accept-digest.",
                ["./octon", MODE_COMMAND[args.mode], "plan", "--help"],
                read_only=True,
            ),
            safe_read_only_actions=[
                CONTINUATION.action(
                    "Inspect guided setup questions as strict JSON.",
                    ["./octon", MODE_COMMAND[args.mode], "plan", "--help"],
                    read_only=True,
                )
            ],
        )
        print(CONTINUATION.render_finding(report, json_output=args.json), file=sys.stderr)
        return 2
    target_value = str(args.target) if args.target else input_fn("Target path: ").strip()
    if not target_value:
        raise ValueError("guided workflow requires an exact target path")
    target = Path(target_value).expanduser().resolve()
    review_value = str(args.review_dir) if args.review_dir else input_fn("External review directory: ").strip()
    if not review_value:
        raise ValueError("guided workflow requires an explicit external review directory")
    review_dir = ensure_review_directory(target, Path(review_value))
    catalog = SETUP.load_catalog()
    if args.session:
        supplied_session_path = args.session.expanduser().resolve()
        prior = SETUP.load_session(supplied_session_path, require_current=False)
        if SETUP.current_state_mismatches(prior):
            session = SETUP.reinspect_session(prior)
            session_path = write_session(review_dir, session)
        else:
            session = prior
            session_path = supplied_session_path
    else:
        session = SETUP.create_session(args.mode, target)
        session_path = None
    try:
        session, session_path = collect_required_answers(
            session,
            catalog,
            review_dir,
            require_tty=require_tty,
            initial_path=session_path,
        )
    except CONTINUATION.ContinuationError as error:
        print(
            CONTINUATION.render_finding(error.report, json_output=args.json),
            file=sys.stderr,
        )
        return 2
    plan_path = next_artifact(
        review_dir,
        "init-plan" if args.mode == "initialization" else "adoption-plan" if args.mode == "adoption" else "upgrade-plan",
    )
    planned = run_command(plan_argv(args.mode, target, session_path, plan_path, args))
    if planned.returncode:
        if planned.stdout:
            print(planned.stdout.rstrip())
        if planned.stderr:
            print(planned.stderr.rstrip(), file=sys.stderr)
        return planned.returncode
    plan_bytes_before = plan_path.read_bytes()
    plan = CONTINUATION.load_exact_plan(plan_path)
    summary = CONTINUATION.plan_summary(plan)
    print(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False)
        if args.json
        else CONTINUATION.render_plan_summary(summary)
    )
    try:
        confirmation = input_fn("Type 'apply' to accept the exact displayed digest, or anything else to stop: ").strip()
    except (EOFError, KeyboardInterrupt) as error:
        report = CONTINUATION.finding(
            failure_code="OCTON-GUIDE-1005",
            blocked_operation=f"{MODE_COMMAND[args.mode]}.guided",
            phase="confirm",
            root_cause="Plan confirmation was interrupted before any target mutation began.",
            authority_source="current_operator_confirmation",
            repair_class="review_required",
            next_action=CONTINUATION.action(
                "Resume with explicit apply after reviewing the preserved exact plan.",
                [
                    "./octon",
                    MODE_COMMAND[args.mode],
                    "apply",
                    "--target",
                    str(target),
                    "--plan",
                    str(plan_path),
                    "--accept-digest",
                    plan["canonical_plan_digest"],
                ],
                read_only=False,
                requires_confirmation=True,
            ),
            preserved=[
                CONTINUATION.proof_state(
                    "session",
                    str(session_path),
                    "The completed setup session remains immutable.",
                    ["dependency_bound", "source_fingerprint_bound"],
                ),
                CONTINUATION.proof_state(
                    "plan",
                    str(plan_path),
                    "The exact displayed plan remains available for review.",
                    ["source_fingerprint_bound"],
                ),
            ],
            successor_session=True,
            successor_plan=True,
            successor_reason="The exact artifacts can resume if current, or serve as predecessors for semantic-delta successors.",
            mutation_occurred=True,
            limitations=[
                "Only immutable review artifacts outside the target were written; the target project was not changed."
            ],
        )
        report["mutation"]["statement"] = (
            "The target project was unchanged; immutable review session and plan artifacts were written outside it."
        )
        print(CONTINUATION.render_finding(report, json_output=args.json), file=sys.stderr)
        return 2
    if confirmation != "apply":
        report = CONTINUATION.finding(
            failure_code="OCTON-GUIDE-1002",
            blocked_operation=f"{MODE_COMMAND[args.mode]}.guided",
            phase="confirm",
            root_cause="The operator did not confirm the exact displayed plan digest.",
            authority_source="current_operator_confirmation",
            repair_class="review_required",
            next_action=CONTINUATION.action(
                "Resume with the preserved exact plan through explicit apply after review.",
                ["./octon", MODE_COMMAND[args.mode], "apply", "--target", str(target), "--plan", str(plan_path), "--accept-digest", plan["canonical_plan_digest"]],
                read_only=False,
                requires_confirmation=True,
            ),
            preserved=[CONTINUATION.proof_state("plan", str(plan_path), "The exact unmodified plan remains available for review.", ["source_fingerprint_bound"])],
            successor_session=True,
            successor_plan=True,
            successor_reason="The preserved plan may be applied if it remains current, or used as a predecessor for re-planning.",
        )
        report["preserved"].insert(
            0,
            CONTINUATION.proof_state(
                "session",
                str(session_path),
                "The completed setup session remains immutable.",
                ["dependency_bound", "source_fingerprint_bound"],
            ),
        )
        CONTINUATION.record_local_artifact_writes(
            report,
            target,
            [session_path, plan_path],
        )
        print(CONTINUATION.render_finding(report, json_output=args.json), file=sys.stderr)
        return 2
    if plan_path.read_bytes() != plan_bytes_before:
        raise CONTINUATION.ContinuationError(
            CONTINUATION.finding(
                failure_code="OCTON-GUIDE-1003",
                blocked_operation=f"{MODE_COMMAND[args.mode]}.guided",
                phase="revalidate",
                root_cause="The plan bytes changed after display and before apply.",
                authority_source="immutable_transaction_plan",
                repair_class="replan_required",
                next_action=CONTINUATION.action(
                    "Create and review an immutable successor plan.",
                    ["./octon", MODE_COMMAND[args.mode], "plan", "--prior-plan", str(plan_path), "--help"],
                    read_only=True,
                ),
                invalidated=[CONTINUATION.proof_state("plan", str(plan_path), "Displayed bytes no longer match apply bytes.", ["source_fingerprint_bound"])],
                successor_plan=True,
                successor_reason="A successor plan can expose the semantic delta from the displayed predecessor.",
            )
        )
    applied = run_command(
        apply_argv(
            args.mode,
            target,
            plan_path,
            plan["canonical_plan_digest"],
            json_output=args.json,
        )
    )
    if applied.stdout:
        print(applied.stdout.rstrip())
    if applied.stderr:
        print(applied.stderr.rstrip(), file=sys.stderr)
    return applied.returncode


def parser(mode: str) -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog=f"octon {MODE_COMMAND[mode]}",
        description="Interactive Octon guided inspect-question-plan-confirm-apply workflow"
    )
    root.add_argument("--target", type=Path)
    root.add_argument("--review-dir", type=Path)
    root.add_argument("--session", type=Path)
    root.add_argument("--proposal", type=Path)
    root.add_argument("--review", type=Path)
    root.add_argument("--prior-plan", type=Path)
    root.add_argument("--project-blueprint-seed", type=Path)
    root.add_argument("--json", action="store_true")
    return root


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in MODE_COMMAND:
        print("[FAIL] guided workflow requires initialization, adoption, or upgrade mode", file=sys.stderr)
        return 2
    mode = sys.argv[1]
    args = parser(mode).parse_args(sys.argv[2:])
    args.mode = mode
    try:
        return run_guided(args)
    except (EOFError, KeyboardInterrupt, OSError, RuntimeError, ValueError, SETUP.SetupError) as error:
        report = getattr(error, "report", None)
        if not isinstance(report, dict):
            report = CONTINUATION.fallback(
                error,
                blocked_operation=f"{MODE_COMMAND[args.mode]}.guided",
                phase="inspect",
                next_argv=["./octon", MODE_COMMAND[args.mode], "--help"],
            )
        print(CONTINUATION.render_finding(report, json_output=args.json), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
