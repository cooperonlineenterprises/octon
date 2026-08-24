#!/usr/bin/env python3
"""Functional and integration coverage for optional long-running work."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
SOURCE_CANDIDATE = SKILL_ROOT.parents[1]
BUNDLED_CANDIDATE = SKILL_ROOT / "assets/octon-mini-source"
REPO_ROOT = (
    SOURCE_CANDIDATE
    if (SOURCE_CANDIDATE / "octon-mini.json").is_file()
    else BUNDLED_CANDIDATE
)
SCAFFOLDER = SCRIPT_ROOT / "scaffold_project.py"
PACKAGE = SCRIPT_ROOT / "package_project.py"


def run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def snapshot(root: Path) -> dict[str, tuple[str, int]]:
    return {
        path.relative_to(root).as_posix(): (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            path.stat().st_mode & 0o777,
        )
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def staged_diagnostic(target: Path, plan: dict[str, object]) -> str:
    path = SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_transaction.py.tmpl"
    spec = importlib.util.spec_from_file_location("octon_lrw_test_transaction", path)
    if spec is None or spec.loader is None:
        module = types.ModuleType("octon_lrw_test_transaction")
        module.__file__ = str(path)
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
    else:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="octon-lrw-diagnostic-") as temporary:
        stage = Path(temporary) / "project"
        module._clone_for_staging(target, stage)
        module._apply_static(stage, plan, module._decode_operations(plan))
        result = run([sys.executable, "-B", ".agent/scripts/refresh.py", "--refresh"], stage)
        return result.stderr or result.stdout


def load_transaction_module():
    path = SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_transaction.py.tmpl"
    module = types.ModuleType("octon_lrw_test_transaction_build")
    module.__file__ = str(path)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
    return module


def load_generated_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generated module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def accepted_decision(target: Path, identifier: str) -> None:
    path = target / ".agent/decisions" / f"{identifier}-long-running-work.md"
    record = {
        "schema_version": "harness.decision.v1",
        "id": identifier,
        "status": "accepted",
        "previous_status": "proposed",
        "title": "Adopt bounded long-running work for the synthetic task",
        "created_at": "2026-08-19",
        "authority_source": "authority:synthetic-program-operator",
        "owner": "synthetic-program-operator",
        "scope": "long-running-work package trust and project adoption",
        "supersedes": None,
        "successor": None,
        "governance_register_refs": [],
        "limitations": ["Synthetic disposable-project decision only."],
    }
    path.write_text(
        "---\n" + json.dumps(record, indent=2, sort_keys=True) + "\n---\n\n# Decision\nSynthetic fixture.\n",
        encoding="utf-8",
    )


def task_and_evidence(target: Path) -> None:
    evidence_path = target / ".agent/evidence/EVD-0001-validation.md"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence = {
        "schema_version": "harness.evidence.v1",
        "id": "EVD-0001",
        "title": "Synthetic bounded validation",
        "task": "TASK-0001",
        "recorded_at": "2026-08-19",
        "authority_source": "authority:synthetic-program-operator",
        "owner": "synthetic-program-operator",
        "scope": "Synthetic long-running work fixture",
        "method": "Deterministic local fixture assertion",
        "environment": "temporary generated project",
        "subject_revision_or_fingerprint": "synthetic-current",
        "result": "pass",
        "fresh_until": "2099-12-31",
        "supersedes": None,
        "limitations": ["Not real-project or readiness evidence."],
    }
    evidence_path.write_text(
        "---\n" + json.dumps(evidence, indent=2, sort_keys=True) + "\n---\n\n# Evidence\nSynthetic fixture.\n",
        encoding="utf-8",
    )
    task_path = target / ".agent/tasks/TASK-0001.md"
    task = {
        "schema_version": "harness.task.v2",
        "id": "TASK-0001",
        "status": "ready",
        "previous_status": "proposed",
        "title": "Complete one bounded synthetic long-running task",
        "authority_basis": "authority:synthetic-program-operator",
        "owner": "synthetic-program-operator",
        "created_at": "2026-08-19",
        "updated_at": "2026-08-19",
        "dependencies": [],
        "plan_item_refs": [],
        "gate_refs": [],
        "blocking_refs": [],
        "scope": "Only synthetic.txt and documentation under docs/",
        "acceptance_criteria": ["Synthetic result is validated."],
        "validation_plan": ["Use EVD-0001."],
        "implementation_result": None,
        "review_evidence": [],
        "blocked_by": [],
        "reopened_by": None,
        "acceptance_criteria_met": False,
        "closure_evidence": [],
        "external_effects": "none",
        "limitations": ["Synthetic disposable-project task."],
    }
    task_path.write_text(
        "---\n" + json.dumps(task, indent=2, sort_keys=True) + "\n---\n\n# Task\nSynthetic fixture.\n",
        encoding="utf-8",
    )
    refreshed = run([sys.executable, "-I", "-B", ".agent/scripts/refresh.py", "--refresh"], target)
    if refreshed.returncode:
        raise AssertionError(refreshed.stderr or refreshed.stdout)


class LongRunningWorkTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="octon-long-work-")
        area = Path(self.temporary.name)
        self.target = area / "project"
        generated = run(
            [
                sys.executable,
                "-B",
                str(SCAFFOLDER),
                "--target",
                str(self.target),
                "--project-name",
                "Long Work Fixture",
                "--profile",
                "standard",
            ],
            REPO_ROOT,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr or generated.stdout)
        self.limits_path = area / "limits.json"
        self.write_limits()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_limits(self, **changes: int | None) -> None:
        limits: dict[str, int | None] = {
            "maximum_iterations": 6,
            "maximum_elapsed_seconds": 600,
            "maximum_consecutive_failures": 2,
            "maximum_repeated_failure_signature": 2,
            "maximum_no_progress_iterations": 2,
            "maximum_context_bytes": 131072,
            "maximum_context_items": 32,
            "maximum_validation_retries": 2,
            "maximum_reported_tokens": None,
            "maximum_reported_cost_microunits": None,
        }
        limits.update(changes)
        write_json(self.limits_path, limits)

    def octon(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, "-I", "-B", "octon", *arguments], self.target)

    def install_and_enable(self) -> None:
        accepted_decision(self.target, "DEC-9001")
        plan_path = self.target / ".agent/transactions/plans/long-work-package.json"
        planned = run(
            [
                sys.executable, "-B", str(PACKAGE), "plan",
                "--target", str(self.target), "--package", "long-running-work",
                "--owner", "synthetic-program-operator",
                "--trust-decision-ref", "DEC-9001", "--assess-applicable",
                "--output", str(plan_path),
            ],
            REPO_ROOT,
        )
        self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        applied = run(
            [sys.executable, "-B", str(PACKAGE), "apply", "--target", str(self.target), "--plan", str(plan_path), "--accept-digest", plan["canonical_plan_digest"]],
            REPO_ROOT,
        )
        self.assertEqual(
            applied.returncode,
            0,
            (applied.stderr or applied.stdout) + "\nSTAGED:\n" + staged_diagnostic(self.target, plan),
        )
        config_plan = ".agent/transactions/plans/long-work-config.json"
        planned = self.octon(
            "work", "run", "configure", "plan", "--status", "enabled",
            "--decision-ref", "DEC-9001", "--owner", "synthetic-program-operator",
            "--output", config_plan,
        )
        self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
        digest = json.loads((self.target / config_plan).read_text(encoding="utf-8"))["canonical_plan_digest"]
        applied = self.octon("work", "run", "configure", "apply", "--plan", config_plan, "--accept-digest", digest)
        self.assertEqual(
            applied.returncode,
            0,
            (applied.stderr or applied.stdout) + "\nSTAGED:\n" + staged_diagnostic(self.target, plan),
        )
        task_and_evidence(self.target)
        checked = self.octon("check")
        self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)

    def start(self) -> dict[str, object]:
        result = self.octon(
            "work", "run", "start", "--task-id", "TASK-0001", "--limits", str(self.limits_path),
            "--allow-path", "synthetic.txt", "--allow-path", "docs",
            "--prohibit-path", ".agent/policy.json",
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def accept_current_context(self, run_id: str) -> dict[str, object]:
        built = self.octon("work", "run", "context", "--run-id", run_id, "--json")
        self.assertEqual(built.returncode, 0, built.stderr or built.stdout)
        first = json.loads(built.stdout)
        repeated = self.octon("work", "run", "context", "--run-id", run_id, "--json")
        self.assertEqual(built.stdout, repeated.stdout)
        accepted = self.octon(
            "work", "run", "accept-context", "--run-id", run_id,
            "--manifest-digest", first["canonical_manifest_digest"],
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)
        return first

    def test_absent_package_refuses_with_continuation_and_no_change(self) -> None:
        before = snapshot(self.target)
        result = self.octon("work", "run", "status", "--json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("OCTON-LRW-1000", result.stderr)
        self.assertEqual(snapshot(self.target), before)

    def test_install_context_start_progress_pause_and_read_only_resume(self) -> None:
        self.install_and_enable()
        run_value = self.start()
        run_id = str(run_value["run_id"])
        manifest = self.accept_current_context(run_id)
        self.assertEqual(manifest["status"], "ready")
        self.assertTrue(manifest["included"])
        recorded = self.octon(
            "work", "run", "record", "--run-id", run_id, "--outcome", "progress",
            "--no-mutation", "--validation-ref", "EVD-0001",
            "--result-fingerprint", "a" * 64,
        )
        self.assertEqual(recorded.returncode, 0, recorded.stderr or recorded.stdout)
        paused = self.octon("work", "run", "pause", "--run-id", run_id, "--reason", "synthetic interruption")
        self.assertEqual(paused.returncode, 0, paused.stderr or paused.stdout)
        before = snapshot(self.target)
        resumed = self.octon("work", "run", "resume", "--run-id", run_id, "--json")
        self.assertEqual(resumed.returncode, 0, resumed.stderr or resumed.stdout)
        report = json.loads(resumed.stdout)
        self.assertEqual(report["status"], "safely_paused")
        self.assertTrue(report["retry_safe"])
        self.assertEqual(snapshot(self.target), before)

    def test_one_local_transaction_step_is_path_bounded_validated_and_checkpointed(self) -> None:
        self.install_and_enable()
        run_id = str(self.start()["run_id"])
        self.accept_current_context(run_id)
        transaction = load_transaction_module()
        validators = json.loads((self.target / ".agent/validators.json").read_text(encoding="utf-8"))
        derived_writes = validators["commands"]["refresh"]["writes"]
        plan = transaction.build_plan(
            self.target,
            operation_name="work.long-running.synthetic-step",
            scope="Create one allowed synthetic task result.",
            operations=[
                transaction.operation(
                    "create", "synthetic.txt", b"validated result\n",
                    "Synthetic long-running-work integration fixture.",
                )
            ],
            evidence=[], assumptions=[], confidence="deterministic",
            limitations=["Synthetic disposable-project operation."],
            staged_validation_plan=[
                [sys.executable, "-B", ".agent/scripts/refresh.py", "--refresh"],
                [sys.executable, "-B", ".agent/scripts/validate.py", "--check"],
            ],
            post_apply_validation_plan=[[sys.executable, "-B", ".agent/scripts/validate.py", "--check"]],
            derived_write_paths=derived_writes,
        )
        plan_path = self.target / ".agent/transactions/plans/long-work-step.json"
        transaction.write_new_json(plan_path, plan)
        applied = self.octon(
            "transaction", "apply", "--plan", plan_path.relative_to(self.target).as_posix(),
            "--accept-digest", plan["canonical_plan_digest"],
        )
        self.assertEqual(
            applied.returncode,
            0,
            (applied.stderr or applied.stdout) + "\nSTAGED:\n" + staged_diagnostic(self.target, plan),
        )
        receipt_path = self.target / ".agent/transactions/receipts" / f"{plan['planned_receipt_id']}.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertTrue(all(item["exit_code"] == 0 for item in receipt["validation"]))
        recorded = self.octon(
            "work", "run", "record", "--run-id", run_id, "--outcome", "progress",
            "--transaction-receipt", receipt_path.relative_to(self.target).as_posix(),
            "--validation-ref", "EVD-0001", "--result-fingerprint", hashlib.sha256((self.target / "synthetic.txt").read_bytes()).hexdigest(),
        )
        self.assertEqual(recorded.returncode, 0, recorded.stderr or recorded.stdout)
        value = json.loads(recorded.stdout)
        self.assertEqual(value["accounting"]["iterations"], 1)
        self.assertEqual(value["last_committed_checkpoint"], "LWC-000002")
        close_path = ".agent/transactions/plans/close-long-work.json"
        closed = self.octon(
            "work", "close", "TASK-0001", "--criteria-met",
            "--implementation-result", "Created the bounded validated result.",
            "--review-evidence", "EVD-0001", "--closure-evidence", "EVD-0001",
            "--external-effects", "none", "--next-action", "No further task work.",
            "--operator", "synthetic-program-operator", "--output", close_path,
        )
        self.assertEqual(closed.returncode, 0, closed.stderr or closed.stdout)
        close_plan = json.loads((self.target / close_path).read_text(encoding="utf-8"))
        applied_close = self.octon(
            "transaction", "apply", "--plan", close_path,
            "--accept-digest", close_plan["canonical_plan_digest"],
        )
        self.assertEqual(applied_close.returncode, 0, applied_close.stderr or applied_close.stdout)
        completed = self.octon(
            "work", "run", "complete", "--run-id", run_id,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertEqual(json.loads(completed.stdout)["status"], "completed_with_current_evidence")

    def test_no_progress_limit_is_deterministic_and_admits_no_extra_iteration(self) -> None:
        self.write_limits(maximum_no_progress_iterations=1)
        self.install_and_enable()
        run_id = str(self.start()["run_id"])
        self.accept_current_context(run_id)
        first = self.octon(
            "work", "run", "record", "--run-id", run_id, "--outcome", "progress",
            "--no-mutation", "--validation-ref", "EVD-0001", "--result-fingerprint", "b" * 64,
        )
        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        self.accept_current_context(run_id)
        second = self.octon(
            "work", "run", "record", "--run-id", run_id, "--outcome", "progress",
            "--no-mutation", "--validation-ref", "EVD-0001", "--result-fingerprint", "b" * 64,
        )
        self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
        value = json.loads(second.stdout)
        self.assertEqual(value["status"], "limit_stopped")
        self.assertEqual(value["last_result"]["limit"], "maximum_no_progress_iterations")
        third = self.octon(
            "work", "run", "record", "--run-id", run_id, "--outcome", "progress",
            "--no-mutation", "--validation-ref", "EVD-0001", "--result-fingerprint", "c" * 64,
        )
        self.assertEqual(third.returncode, 2)

    def test_changed_instruction_is_reported_without_mutating_resume(self) -> None:
        self.install_and_enable()
        run_id = str(self.start()["run_id"])
        paused = self.octon("work", "run", "pause", "--run-id", run_id, "--reason", "change instructions")
        self.assertEqual(paused.returncode, 0, paused.stderr or paused.stdout)
        agents = self.target / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8") + "\nChanged instruction.\n", encoding="utf-8")
        before = snapshot(self.target)
        result = self.octon("work", "run", "resume", "--run-id", run_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertFalse(report["retry_safe"])
        self.assertTrue(any("instructions changed" in item for item in report["findings"]))
        self.assertEqual(snapshot(self.target), before)

    def test_duplicate_limit_key_and_critical_context_exhaustion_fail_closed(self) -> None:
        self.install_and_enable()
        self.limits_path.write_text(
            '{"maximum_iterations": 2, "maximum_iterations": 3}\n',
            encoding="utf-8",
        )
        duplicate = self.octon(
            "work", "run", "start", "--task-id", "TASK-0001", "--limits", str(self.limits_path),
            "--allow-path", "synthetic.txt",
        )
        self.assertEqual(duplicate.returncode, 2)
        self.assertIn("duplicate JSON key", duplicate.stderr)
        self.write_limits(maximum_context_bytes=1)
        run_id = str(self.start()["run_id"])
        before = snapshot(self.target)
        built = self.octon("work", "run", "context", "--run-id", run_id, "--json")
        self.assertEqual(built.returncode, 0, built.stderr or built.stdout)
        manifest = json.loads(built.stdout)
        self.assertEqual(manifest["status"], "blocked_budget")
        self.assertTrue(manifest["omitted"])
        self.assertEqual(snapshot(self.target), before)

    def test_second_active_run_and_premature_completion_are_refused(self) -> None:
        self.install_and_enable()
        run_id = str(self.start()["run_id"])
        second = self.octon(
            "work", "run", "start", "--task-id", "TASK-0001", "--limits", str(self.limits_path),
            "--allow-path", "synthetic.txt",
        )
        self.assertEqual(second.returncode, 2)
        self.assertIn("only one nonterminal", second.stderr)
        complete = self.octon("work", "run", "complete", "--run-id", run_id)
        self.assertEqual(complete.returncode, 2)
        self.assertIn("subordinate to completed task acceptance", complete.stderr)

    def test_noncanonical_path_narrowing_is_rejected_before_run_creation(self) -> None:
        self.install_and_enable()
        for unsafe in ("", "docs/", "docs/../outside", "/absolute"):
            with self.subTest(path=unsafe):
                result = self.octon(
                    "work", "run", "start", "--task-id", "TASK-0001",
                    "--limits", str(self.limits_path), "--allow-path", unsafe,
                )
                self.assertEqual(result.returncode, 2)
                self.assertFalse((self.target / ".agent/work-runs/runs").exists())

    def test_unknown_outcome_is_terminal_and_never_retry_safe(self) -> None:
        self.install_and_enable()
        run_id = str(self.start()["run_id"])
        self.accept_current_context(run_id)
        stopped = self.octon(
            "work", "run", "record", "--run-id", run_id,
            "--outcome", "partial_unknown", "--result-fingerprint", "d" * 64,
            "--partial-effect", "synthetic acknowledgement was lost",
        )
        self.assertEqual(stopped.returncode, 0, stopped.stderr or stopped.stdout)
        self.assertEqual(json.loads(stopped.stdout)["status"], "stopped_partial_or_unknown")
        resumed = self.octon("work", "run", "resume", "--run-id", run_id, "--json")
        report = json.loads(resumed.stdout)
        self.assertFalse(report["retry_safe"])
        self.assertEqual(report["partial_or_external_effects"], ["synthetic acknowledgement was lost"])

    def test_repeated_failure_and_elapsed_time_limits_are_exact(self) -> None:
        self.write_limits(
            maximum_consecutive_failures=2,
            maximum_repeated_failure_signature=2,
        )
        self.install_and_enable()
        run_id = str(self.start()["run_id"])
        self.accept_current_context(run_id)
        first = self.octon(
            "work", "run", "record", "--run-id", run_id, "--outcome", "failure",
            "--result-fingerprint", "e" * 64, "--failure-code", "validation_failed",
            "--failure-detail", "same deterministic failure",
        )
        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        self.accept_current_context(run_id)
        second = self.octon(
            "work", "run", "record", "--run-id", run_id, "--outcome", "failure",
            "--result-fingerprint", "e" * 64, "--failure-code", "validation_failed",
            "--failure-detail", "same deterministic failure",
        )
        self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
        value = json.loads(second.stdout)
        self.assertEqual(value["status"], "limit_stopped")
        self.assertIn(value["last_result"]["limit"], {"maximum_consecutive_failures", "maximum_repeated_failure_signature"})

    def test_elapsed_limit_and_superseded_adoption_stop_before_iteration(self) -> None:
        self.write_limits(maximum_elapsed_seconds=1)
        self.install_and_enable()
        run_id = str(self.start()["run_id"])
        built = self.octon("work", "run", "context", "--run-id", run_id, "--json")
        manifest = json.loads(built.stdout)
        spoofed = self.octon(
            "work", "run", "accept-context", "--run-id", run_id,
            "--manifest-digest", manifest["canonical_manifest_digest"],
            "--observed-at", "2026-08-19T12:00:01Z",
        )
        self.assertEqual(spoofed.returncode, 2)
        self.assertIn("reserved for direct disposable-fixture", spoofed.stderr)
        time.sleep(1.05)
        expired = self.octon(
            "work", "run", "accept-context", "--run-id", run_id,
            "--manifest-digest", manifest["canonical_manifest_digest"],
        )
        self.assertEqual(expired.returncode, 2)
        self.assertIn("maximum_elapsed_seconds", expired.stderr)
        decision = self.target / ".agent/decisions/DEC-9001-long-running-work.md"
        text = decision.read_text(encoding="utf-8").replace('"status": "accepted"', '"status": "superseded"')
        decision.write_text(text, encoding="utf-8")
        superseded = self.octon(
            "work", "run", "accept-context", "--run-id", run_id,
            "--manifest-digest", manifest["canonical_manifest_digest"],
        )
        self.assertEqual(superseded.returncode, 2)
        self.assertIn("current accepted project-owned decision", superseded.stderr)

    def test_changed_accepted_adoption_decision_digest_stops_work(self) -> None:
        self.install_and_enable()
        run_id = str(self.start()["run_id"])
        decision = self.target / ".agent/decisions/DEC-9001-long-running-work.md"
        decision.write_text(
            decision.read_text(encoding="utf-8").replace(
                "Synthetic fixture.", "Changed accepted decision bytes."
            ),
            encoding="utf-8",
        )
        context = self.octon("work", "run", "context", "--run-id", run_id, "--json")
        self.assertEqual(context.returncode, 2)
        self.assertIn("adoption decision bytes changed", context.stderr)

    def test_changed_task_owner_invalidates_the_committed_run_contract(self) -> None:
        self.install_and_enable()
        run_id = str(self.start()["run_id"])
        task = self.target / ".agent/tasks/TASK-0001.md"
        task.write_text(
            task.read_text(encoding="utf-8").replace(
                '"owner": "synthetic-program-operator"',
                '"owner": "changed-owner"',
            ),
            encoding="utf-8",
        )
        resumed = self.octon("work", "run", "resume", "--run-id", run_id, "--json")
        self.assertEqual(resumed.returncode, 0, resumed.stderr or resumed.stdout)
        report = json.loads(resumed.stdout)
        self.assertFalse(report["retry_safe"])
        self.assertTrue(any("task contract changed" in item for item in report["findings"]))

    def test_planned_blocked_activated_and_known_failed_lifecycle(self) -> None:
        self.install_and_enable()
        planned = self.octon(
            "work", "run", "start", "--task-id", "TASK-0001",
            "--limits", str(self.limits_path), "--allow-path", "synthetic.txt",
            "--planned",
        )
        self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
        run_id = json.loads(planned.stdout)["run_id"]
        resumed = self.octon("work", "run", "resume", "--run-id", run_id, "--json")
        resume_value = json.loads(resumed.stdout)
        self.assertEqual(resume_value["status"], "planned")
        activate_argv = resume_value["next_action"]["argv"]
        activated = self.octon(*activate_argv[1:])
        self.assertEqual(activated.returncode, 0, activated.stderr or activated.stdout)
        blocked = self.octon(
            "work", "run", "block", "--run-id", run_id,
            "--reason", "Synthetic missing input.",
        )
        self.assertEqual(blocked.returncode, 0, blocked.stderr or blocked.stdout)
        resumed = self.octon("work", "run", "resume", "--run-id", run_id, "--json")
        activate_argv = json.loads(resumed.stdout)["next_action"]["argv"]
        activated = self.octon(*activate_argv[1:])
        self.assertEqual(activated.returncode, 0, activated.stderr or activated.stdout)
        failed = self.octon(
            "work", "run", "fail", "--run-id", run_id,
            "--failure-code", "known_fixture_failure",
            "--failure-detail", "The local fixture outcome is known to have failed.",
        )
        self.assertEqual(failed.returncode, 0, failed.stderr or failed.stdout)
        self.assertEqual(json.loads(failed.stdout)["status"], "failed_known_outcome")

    def test_result_and_reported_accounting_cannot_fake_progress_or_move_backwards(self) -> None:
        self.install_and_enable()
        run_id = str(self.start()["run_id"])
        self.accept_current_context(run_id)
        malformed = self.octon(
            "work", "run", "record", "--run-id", run_id, "--outcome", "progress",
            "--no-mutation", "--validation-ref", "EVD-0001",
            "--result-fingerprint", "not-a-digest",
        )
        self.assertEqual(malformed.returncode, 2)
        first = self.octon(
            "work", "run", "record", "--run-id", run_id, "--outcome", "progress",
            "--no-mutation", "--validation-ref", "EVD-0001",
            "--result-fingerprint", "f" * 64, "--reported-tokens", "10",
            "--reported-cost-microunits", "20",
        )
        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        self.accept_current_context(run_id)
        decreasing = self.octon(
            "work", "run", "record", "--run-id", run_id, "--outcome", "failure",
            "--result-fingerprint", "f" * 64, "--failure-code", "fixture",
            "--failure-detail", "Known failure.", "--reported-tokens", "9",
        )
        self.assertEqual(decreasing.returncode, 2)
        self.assertIn("monotonic", decreasing.stderr)
        status = json.loads(self.octon("work", "run", "status", "--run-id", run_id, "--json").stdout)
        self.assertEqual(status["budget"]["accounting"]["iterations"], 1)
        self.assertEqual(status["budget"]["accounting"]["reported_tokens"], 10)

    def test_work_run_state_does_not_self_stale_project_check_fingerprints(self) -> None:
        self.install_and_enable()
        writer = load_generated_module(
            self.target / ".agent/scripts/run_project_checks.py",
            "octon_lrw_test_project_checks",
        )
        project = json.loads((self.target / ".agent/project.json").read_text(encoding="utf-8"))
        before, exclusions = writer.project_check_source_fingerprint(project)
        self.assertIn(".agent/work-runs", exclusions)
        self.start()
        after, _ = writer.project_check_source_fingerprint(project)
        self.assertEqual(after, before)

    def test_state_symlink_and_non_authoritative_receipt_paths_fail_closed(self) -> None:
        self.install_and_enable()
        outside = self.target.parent / "outside-state"
        outside.mkdir()
        runs_root = self.target / ".agent/work-runs/runs"
        try:
            runs_root.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symlink creation unavailable: {error}")
        started = self.octon(
            "work", "run", "start", "--task-id", "TASK-0001",
            "--limits", str(self.limits_path), "--allow-path", "synthetic.txt",
        )
        self.assertEqual(started.returncode, 2)
        self.assertEqual(list(outside.iterdir()), [])
        runs_root.unlink()
        run_id = str(self.start()["run_id"])
        self.accept_current_context(run_id)
        rejected = self.octon(
            "work", "run", "record", "--run-id", run_id, "--outcome", "progress",
            "--transaction-receipt", str(self.limits_path),
            "--validation-ref", "EVD-0001", "--result-fingerprint", "a" * 64,
        )
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("not authoritative", rejected.stderr)

    def test_nonsoftware_context_pressure_is_source_linked_and_omission_visible(self) -> None:
        self.install_and_enable()
        research = self.target / "research"
        research.mkdir()
        references = []
        for name, statement in (
            ("source-a.md", "Observed option A has lower setup cost.\n"),
            ("source-b.md", "Observed option B has stronger recovery.\n"),
            ("source-c.md", "The sources conflict; owner decision remains unresolved.\n"),
        ):
            path = research / name
            # Keep the byte-budget fixture identical on every operating system.
            # Text-mode writes expand LF to CRLF on Windows and can move every
            # explicit reference just beyond the deliberately tight budget.
            path.write_bytes((statement * 180).encode("utf-8"))
            references.append(path.relative_to(self.target).as_posix())
        for index in range(50):
            (research / f"irrelevant-{index:03d}.txt").write_text("not selected\n", encoding="utf-8")
        refreshed = run([sys.executable, "-I", "-B", ".agent/scripts/refresh.py", "--refresh"], self.target)
        self.assertEqual(refreshed.returncode, 0, refreshed.stderr or refreshed.stdout)
        before = snapshot(self.target)
        argv = [
            "work", "run", "context", "--task-id", "TASK-0001",
            "--max-bytes", "24000", "--max-items", "32", "--scope-path", "research",
            "--json",
        ]
        for reference in references:
            argv.extend(["--include-ref", reference])
        first = self.octon(*argv)
        second = self.octon(*argv)
        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        self.assertEqual(first.stdout, second.stdout)
        manifest = json.loads(first.stdout)
        included = {item["reference"] for item in manifest["included"]}
        omitted = {item["reference"] for item in manifest["omitted"]}
        self.assertTrue(included & set(references))
        self.assertTrue(omitted & set(references))
        self.assertTrue(all("irrelevant-" not in item for item in included | omitted))
        self.assertTrue(all(item["content_persisted"] is False for item in manifest["included"] + manifest["omitted"]))
        self.assertEqual(snapshot(self.target), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
