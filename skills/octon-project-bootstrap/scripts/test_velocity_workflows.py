#!/usr/bin/env python3
"""Integration tests for the Octon 4.0 velocity workflows."""

from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
SCAFFOLDER = SCRIPT_ROOT / "scaffold_project.py"
INIT = SCRIPT_ROOT / "init_project.py"
ADOPT = SCRIPT_ROOT / "adopt_project.py"
COLLABORATION = SCRIPT_ROOT / "collaboration_project.py"
DETECTOR = SCRIPT_ROOT / "detect_project.py"
TRANSACTION_TEMPLATE = SCRIPT_ROOT.parent / "assets/templates/core/.agent/scripts/octon_transaction.py.tmpl"


def run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    command = list(argv)
    if command and os.name == "nt" and Path(command[0]).name.casefold() == "octon":
        command = [sys.executable, "-B", command[0], *command[1:]]
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot(root: Path, *, omit_git: bool = False) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if omit_git and (relative == ".git" or relative.startswith(".git/")):
            continue
        if path.is_file() and not path.is_symlink():
            values[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def import_transaction(project: Path):
    path = project / ".agent/scripts/octon_transaction.py"
    spec = importlib.util.spec_from_file_location(
        f"octon_velocity_transaction_{hash(project)}", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import generated transaction module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def import_source_transaction():
    spec = importlib.util.spec_from_file_location(
        "octon_velocity_source_transaction", TRANSACTION_TEMPLATE
    )
    if spec is None or spec.loader is None:
        module = types.ModuleType("octon_velocity_source_transaction")
        module.__file__ = str(TRANSACTION_TEMPLATE)
        exec(
            compile(
                TRANSACTION_TEMPLATE.read_text(encoding="utf-8"),
                str(TRANSACTION_TEMPLATE),
                "exec",
            ),
            module.__dict__,
        )
        return module
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def task_record(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").splitlines()
    if not text or text[0] != "---":
        raise ValueError("task lacks JSON front matter")
    end = text.index("---", 1)
    return json.loads("\n".join(text[1:end]))


def apply_plan(project: Path, plan_path: Path) -> subprocess.CompletedProcess[str]:
    plan = load(plan_path)
    return run(
        [
            str(project / "octon"),
            "transaction",
            "apply",
            "--plan",
            str(plan_path),
            "--accept-digest",
            plan["canonical_plan_digest"],
        ],
        project,
    )


class VelocityWorkflowTests(unittest.TestCase):
    maxDiff = None

    def test_safe_bundles_apply_and_rollback_atomically_and_reject_unsafe_members(self) -> None:
        transaction = import_source_transaction()
        with tempfile.TemporaryDirectory(prefix="octon-mini-bundle-") as temporary:
            area = Path(temporary)
            root = area / "project"
            root.mkdir()
            (root / "AGENTS.md").write_text("# Synthetic instructions\n", encoding="utf-8")
            validation = [[sys.executable, "-B", "-c", "raise SystemExit(0)"]]

            def member(
                operation_name: str,
                path: str,
                *,
                authority: str = "authority:bundle-owner",
                freshness: str = "apply_revalidation",
            ) -> dict[str, Any]:
                return transaction.build_plan(
                    root,
                    operation_name=operation_name,
                    scope=operation_name,
                    operations=[
                        transaction.operation(
                            "create",
                            path,
                            f"{operation_name}\n".encode("utf-8"),
                            "Synthetic reversible bundle member.",
                        )
                    ],
                    evidence=[],
                    assumptions=[],
                    confidence="deterministic",
                    limitations=["Synthetic bundle fixture."],
                    staged_validation_plan=validation,
                    post_apply_validation_plan=validation,
                    analysis={
                        "observations": [],
                        "inferences": [],
                        "explicit_decisions": [],
                        "authorization_gates": [
                            {
                                "id": f"{operation_name}.authority",
                                "summary": "Current repository-local authority is explicit.",
                                "source_refs": [authority],
                                "rule": None,
                                "confidence": "deterministic",
                                "limitations": [],
                            }
                        ],
                    },
                    bundle_freshness_boundary=freshness,
                )

            first = member("test.first", "first.txt")
            second = member("test.second", "second.txt")
            legacy = copy.deepcopy(first)
            legacy["schema_version"] = "harness.transaction-plan.v2"
            for operation in legacy["operations"]:
                operation.pop("bundle_member", None)
            for field in (
                "project_identity",
                "predecessor_plan",
                "semantic_delta",
                "bundle",
                "effects",
                "bundle_requirements",
            ):
                legacy.pop(field, None)
            for field in ("proof_reuse", "shell_interpretation", "external_effects"):
                legacy["validation"].pop(field, None)
            legacy["canonical_plan_digest"] = transaction.plan_digest(legacy)
            with self.assertRaises(transaction.TransactionError) as legacy_apply:
                transaction.apply_plan(
                    root, legacy, legacy["canonical_plan_digest"]
                )
            self.assertEqual(
                legacy_apply.exception.report["failure_code"], "OCTON-TXN-2006"
            )
            with self.assertRaises(transaction.TransactionError) as legacy_bundle:
                transaction.build_bundle_plan(
                    root,
                    [("legacy", legacy), ("current", second)],
                    authority_sources=["authority:bundle-owner"],
                )
            self.assertEqual(
                legacy_bundle.exception.report["failure_code"],
                "OCTON-BUNDLE-3009",
            )
            bundle = transaction.build_bundle_plan(
                root,
                [("first", first), ("second", second)],
            )
            self.assertEqual(bundle["operation"], "bundle.repository_local")
            self.assertEqual([item["id"] for item in bundle["bundle"]["members"]], ["first", "second"])
            receipt, receipt_path = transaction.apply_plan(
                root, bundle, bundle["canonical_plan_digest"]
            )
            expected_receipt_timings = {
                "staging_seconds",
                "refresh_seconds",
                "staged_validation_seconds",
                "apply_seconds",
                "post_apply_validation_seconds",
                "receipt_preparation_seconds",
                "total_before_receipt_persist_seconds",
            }
            self.assertEqual(set(receipt["timings"]), expected_receipt_timings)
            self.assertTrue(
                all(
                    transaction.LAST_PHASE_TIMINGS[key] == receipt["timings"][key]
                    for key in expected_receipt_timings
                )
            )
            self.assertIn("receipt_persist_seconds", transaction.LAST_PHASE_TIMINGS)
            self.assertIn("total_seconds", transaction.LAST_PHASE_TIMINGS)
            self.assertGreaterEqual(
                transaction.LAST_PHASE_TIMINGS["total_seconds"],
                receipt["timings"]["total_before_receipt_persist_seconds"],
            )
            self.assertEqual({item["path"] for item in receipt["paths"]}, {"first.txt", "second.txt"})
            self.assertTrue((root / "first.txt").is_file())
            self.assertTrue((root / "second.txt").is_file())
            rolled_back = transaction.rollback(root, receipt_path)
            self.assertEqual(rolled_back["status"], "rolled_back")
            self.assertFalse((root / "first.txt").exists())
            self.assertFalse((root / "second.txt").exists())

            with self.assertRaises(transaction.TransactionError) as overlap:
                transaction.build_bundle_plan(
                    root,
                    [("one", member("test.one", "same.txt")), ("two", member("test.two", "same.txt"))],
                )
            self.assertEqual(overlap.exception.report["failure_code"], "OCTON-BUNDLE-3005")
            self.assertFalse(overlap.exception.report["mutation"]["occurred"])

            with self.assertRaises(transaction.TransactionError) as authority:
                transaction.build_bundle_plan(
                    root,
                    [("one", member("test.auth_one", "auth-one.txt")), ("two", member("test.auth_two", "auth-two.txt", authority="authority:other-owner"))],
                )
            self.assertEqual(authority.exception.report["failure_code"], "OCTON-BUNDLE-3006")

            with self.assertRaises(transaction.TransactionError) as freshness:
                transaction.build_bundle_plan(
                    root,
                    [("one", member("test.fresh_one", "fresh-one.txt")), ("two", member("test.fresh_two", "fresh-two.txt", freshness="release_gate"))],
                )
            self.assertEqual(freshness.exception.report["failure_code"], "OCTON-BUNDLE-3007")

            external = member("test.external", "external.txt")
            external["effects"] = {
                "repository_local": True,
                "external": ["network_access"],
                "monotonic_external": True,
            }
            external["canonical_plan_digest"] = transaction.plan_digest(external)
            with self.assertRaises(transaction.TransactionError) as external_error:
                transaction.build_bundle_plan(
                    root,
                    [("local", member("test.local", "local.txt")), ("external", external)],
                )
            self.assertEqual(external_error.exception.report["failure_code"], "OCTON-BUNDLE-3003")

            shell_member = copy.deepcopy(first)
            shell_member["validation"]["staged_argv"] = [["sh", "-c", "true"]]
            shell_member["canonical_plan_digest"] = transaction.plan_digest(shell_member)
            with self.assertRaises(transaction.TransactionError) as shell_error:
                transaction.build_bundle_plan(
                    root,
                    [("shell", shell_member), ("local", second)],
                )
            self.assertEqual(
                shell_error.exception.report["failure_code"],
                "OCTON-BUNDLE-3003",
            )
            self.assertFalse(shell_error.exception.report["mutation"]["occurred"])

            other_root = area / "byte-identical-copy"
            other_root.mkdir()
            (other_root / "AGENTS.md").write_bytes((root / "AGENTS.md").read_bytes())
            foreign = transaction.build_plan(
                other_root,
                operation_name="test.foreign",
                scope="Foreign project member",
                operations=[
                    transaction.operation(
                        "create",
                        "foreign.txt",
                        b"foreign\n",
                        "Synthetic cross-project bundle member.",
                    )
                ],
                evidence=[],
                assumptions=[],
                confidence="deterministic",
                limitations=["Synthetic cross-project identity fixture."],
                staged_validation_plan=validation,
                post_apply_validation_plan=validation,
                analysis={
                    "observations": [],
                    "inferences": [],
                    "explicit_decisions": [],
                    "authorization_gates": [
                        {
                            "id": "test.foreign.authority",
                            "summary": "Synthetic authority.",
                            "source_refs": ["authority:bundle-owner"],
                            "rule": None,
                            "confidence": "deterministic",
                            "limitations": [],
                        }
                    ],
                },
            )
            with self.assertRaises(transaction.TransactionError) as project_error:
                transaction.build_bundle_plan(
                    root,
                    [("foreign", foreign), ("local", second)],
                )
            self.assertEqual(
                project_error.exception.report["failure_code"],
                "OCTON-BUNDLE-3010",
            )
            with self.assertRaises(transaction.TransactionError) as apply_project_error:
                transaction.apply_plan(
                    root,
                    foreign,
                    foreign["canonical_plan_digest"],
                )
            self.assertEqual(
                apply_project_error.exception.report["failure_code"],
                "OCTON-TXN-2008",
            )

            stale_member = member("test.stale", "stale.txt")
            (root / "stale.txt").write_text("independent write\n", encoding="utf-8")
            with self.assertRaises(transaction.TransactionError) as stale_error:
                transaction.build_bundle_plan(
                    root,
                    [("stale", stale_member), ("current", member("test.current", "current.txt"))],
                )
            self.assertEqual(stale_error.exception.report["failure_code"], "OCTON-BUNDLE-3008")
            self.assertFalse(stale_error.exception.report["mutation"]["occurred"])

            rogue_plan = transaction.build_plan(
                root,
                operation_name="test.post_validation_isolation",
                scope="Reject a mutating post-apply validator",
                operations=[
                    transaction.operation(
                        "create", "planned.txt", b"planned\n", "Synthetic planned path."
                    )
                ],
                evidence=[],
                assumptions=[],
                confidence="deterministic",
                limitations=["Synthetic isolation fixture."],
                staged_validation_plan=validation,
                post_apply_validation_plan=[
                    [
                        sys.executable,
                        "-B",
                        "-c",
                        "from pathlib import Path; Path('rogue.txt').write_text('must not escape')",
                    ]
                ],
            )
            with self.assertRaises(transaction.TransactionError) as rogue_error:
                transaction.apply_plan(
                    root,
                    rogue_plan,
                    rogue_plan["canonical_plan_digest"],
                )
            self.assertFalse((root / "planned.txt").exists())
            self.assertFalse((root / "rogue.txt").exists())
            self.assertEqual(
                rogue_error.exception.report["failure_code"],
                "OCTON-TXN-2202",
            )
            self.assertEqual(rogue_error.exception.report["phase"], "validate")
            self.assertEqual(
                rogue_error.exception.report["blocked_operation"],
                "test.post_validation_isolation",
            )
            self.assertTrue(rogue_error.exception.report["invalidated"])
            self.assertTrue(rogue_error.exception.report["preserved"])
            self.assertIn(
                "no lasting target change",
                rogue_error.exception.report["mutation"]["statement"],
            )

    def test_guided_first_task_lifecycle_stale_plan_and_interruption_recovery(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-mini-velocity-init-") as temporary:
            area = Path(temporary)
            project = area / "project"
            plan_path = area / "init-plan.json"
            now = datetime.now(timezone.utc)
            result = run(
                [
                    sys.executable,
                    "-B",
                    str(INIT),
                    "plan",
                    "--target",
                    str(project),
                    "--project-name",
                    "Guided Velocity Fixture",
                    "--profile",
                    "minimal",
                    "--layout",
                    "compact",
                    "--writer-count",
                    "1",
                    "--collaboration-source",
                    "authority:velocity-fixture-owner",
                    "--collaboration-observed-at",
                    now.isoformat(),
                    "--collaboration-expires-at",
                    (now + timedelta(days=30)).isoformat(),
                    "--solo-integration-preference",
                    "direct",
                    "--first-task-title",
                    "Reach the first meaningful task",
                    "--first-task-scope",
                    "Exercise the guided initialization and lifecycle boundary",
                    "--first-task-authority-basis",
                    "authority:velocity-fixture-owner",
                    "--first-task-owner",
                    "fixture-owner",
                    "--first-task-operator",
                    "fixture-operator",
                    "--first-task-acceptance",
                    "The workflow integration test passes",
                    "--first-task-validation",
                    "Run the generated structural check",
                    "--first-task-next-action",
                    "Inspect the generated focus view",
                    "--output",
                    str(plan_path),
                ],
                SCRIPT_ROOT,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            plan = load(plan_path)
            result = run(
                [
                    sys.executable,
                    "-B",
                    str(INIT),
                    "apply",
                    "--target",
                    str(project),
                    "--plan",
                    str(plan_path),
                    "--accept-digest",
                    plan["canonical_plan_digest"],
                ],
                SCRIPT_ROOT,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(
                task_record(project / ".agent/tasks/TASK-0001.md")["status"],
                "in_progress",
            )

            before_resume = snapshot(project)
            resumed = run([str(project / "octon"), "work", "resume"], project)
            self.assertEqual(resumed.returncode, 0, resumed.stderr or resumed.stdout)
            self.assertEqual(snapshot(project), before_resume)
            self.assertEqual(json.loads(resumed.stdout)["focus"]["current_task_id"], "TASK-0001")

            second_plan = project / ".agent/transactions/plans/start-second.json"
            result = run(
                [
                    str(project / "octon"),
                    "work",
                    "start",
                    "--title",
                    "Stale plan fixture",
                    "--scope",
                    "Prove target preimage binding",
                    "--authority-basis",
                    "authority:velocity-fixture-owner",
                    "--owner",
                    "fixture-owner",
                    "--operator",
                    "fixture-operator",
                    "--acceptance",
                    "Stale apply is refused",
                    "--validation",
                    "Run the structural check",
                    "--next-action",
                    "Exercise stale apply",
                    "--output",
                    str(second_plan),
                ],
                project,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            instructions = project / "AGENTS.md"
            instruction_bytes = instructions.read_bytes()
            instructions.write_bytes(instruction_bytes + b"\n# Changed after planning\n")
            instruction_stale = apply_plan(project, second_plan)
            self.assertNotEqual(instruction_stale.returncode, 0)
            self.assertIn("OCTON-TXN-2002", instruction_stale.stderr)
            self.assertIn("Nothing changed", instruction_stale.stderr)
            instructions.write_bytes(instruction_bytes)
            collision = project / ".agent/tasks/TASK-0002.md"
            collision.write_text("independent concurrent write\n", encoding="utf-8")
            stale = apply_plan(project, second_plan)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("OCTON-TXN-2004", stale.stderr)
            self.assertIn("Nothing changed", stale.stderr)
            self.assertIn("Argv:", stale.stderr)
            collision.unlink()
            applied = apply_plan(project, second_plan)
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
            second = load(second_plan)
            receipt = project / ".agent/transactions/receipts" / f"{second['planned_receipt_id']}.json"
            transaction = import_transaction(project)
            original_restore = transaction._restore

            def interrupt_rollback(root: Path, paths: list[dict[str, Any]], created: list[str]) -> None:
                original_restore(root, paths[:1], [])
                raise KeyboardInterrupt("synthetic rollback interruption")

            with mock.patch.object(transaction, "_restore", side_effect=interrupt_rollback):
                with self.assertRaises(KeyboardInterrupt):
                    transaction.rollback(project, receipt)
            self.assertEqual(load(receipt)["status"], "rollback_in_progress")
            rolled_back = run(
                [str(project / "octon"), "transaction", "rollback", "--receipt", str(receipt)],
                project,
            )
            self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr or rolled_back.stdout)
            self.assertFalse(collision.exists())

            interruption_plan = project / ".agent/transactions/plans/interrupted-handoff.json"
            result = run(
                [
                    str(project / "octon"),
                    "work",
                    "handoff",
                    "--task-id",
                    "TASK-0001",
                    "--next-action",
                    "Resume after exact transaction recovery",
                    "--summary",
                    "Synthetic interruption window",
                    "--operator",
                    "fixture-operator",
                    "--output",
                    str(interruption_plan),
                ],
                project,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            interrupted = load(interruption_plan)
            decoded = transaction._decode_operations(interrupted)
            derived, _, _ = transaction._staged_result(project, interrupted, decoded)
            outcomes = transaction._planned_outcomes(interrupted, decoded, derived)
            receipt_paths = transaction._receipt_paths(project, interrupted, outcomes)
            created = transaction._created_parent_directories(
                project, [item["path"] for item in receipt_paths]
            )
            pending, pending_path = transaction._write_pending(
                project,
                interrupted["planned_receipt_id"],
                interrupted,
                receipt_paths,
                created,
            )
            self.assertTrue(all(item["after"] is not None for item in pending["paths"]))
            transaction._apply_static(project, interrupted, decoded)
            recovered = run(
                [str(project / "octon"), "transaction", "recover", "--pending", str(pending_path)],
                project,
            )
            self.assertEqual(recovered.returncode, 0, recovered.stderr or recovered.stdout)
            self.assertEqual(
                task_record(project / ".agent/tasks/TASK-0001.md")["status"],
                "in_progress",
            )
            self.assertTrue(
                (project / ".agent/transactions/recovered" / pending_path.name).is_file()
            )
            recovery_path = project / ".agent/transactions/recovered" / pending_path.name
            recovery_before = recovery_path.read_bytes()
            transaction.write_new_json(pending_path, pending)
            finalized = run(
                [str(project / "octon"), "transaction", "recover", "--pending", str(pending_path)],
                project,
            )
            self.assertEqual(finalized.returncode, 0, finalized.stderr or finalized.stdout)
            self.assertFalse(pending_path.exists())
            self.assertEqual(recovery_path.read_bytes(), recovery_before)

            finalize_plan = project / ".agent/transactions/plans/finalize-receipted-apply.json"
            result = run(
                [
                    str(project / "octon"),
                    "work",
                    "handoff",
                    "--task-id",
                    "TASK-0001",
                    "--next-action",
                    "Continue from the receipted apply",
                    "--summary",
                    "Synthetic receipt finalization window",
                    "--operator",
                    "fixture-operator",
                    "--output",
                    str(finalize_plan),
                ],
                project,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            finalize = load(finalize_plan)
            finalize_pending = (
                project
                / ".agent/transactions/pending"
                / f"{finalize['planned_receipt_id']}.json"
            )
            finalize_receipt = (
                project
                / ".agent/transactions/receipts"
                / f"{finalize['planned_receipt_id']}.json"
            )
            original_unlink = Path.unlink

            def interrupt_pending_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
                if path.resolve(strict=False) == finalize_pending.resolve(strict=False):
                    raise KeyboardInterrupt("synthetic post-receipt interruption")
                original_unlink(path, *args, **kwargs)

            with mock.patch.object(Path, "unlink", interrupt_pending_unlink):
                with self.assertRaises(KeyboardInterrupt):
                    transaction.apply_plan(
                        project,
                        finalize,
                        finalize["canonical_plan_digest"],
                    )
            self.assertTrue(finalize_pending.is_file())
            self.assertTrue(finalize_receipt.is_file())
            focus_after_apply = load(project / ".agent/state/focus.json")
            finalized_apply = run(
                [
                    str(project / "octon"),
                    "transaction",
                    "recover",
                    "--pending",
                    str(finalize_pending),
                ],
                project,
            )
            self.assertEqual(
                finalized_apply.returncode,
                0,
                finalized_apply.stderr or finalized_apply.stdout,
            )
            self.assertIn("[FINALIZED]", finalized_apply.stdout)
            self.assertFalse(finalize_pending.exists())
            self.assertEqual(load(project / ".agent/state/focus.json"), focus_after_apply)

            evidence_path = project / ".agent/evidence/EVD-0001-velocity.md"
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence = {
                "schema_version": "harness.evidence.v1",
                "id": "EVD-0001",
                "title": "Velocity workflow integration evidence",
                "task": "TASK-0001",
                "recorded_at": now.date().isoformat(),
                "authority_source": "authority:velocity-fixture-owner",
                "owner": "fixture-owner",
                "scope": "Generated lifecycle integration fixture",
                "method": "Deterministic local integration test",
                "environment": "Disposable temporary project",
                "subject_revision_or_fingerprint": "velocity-fixture",
                "result": "pass",
                "fresh_until": (now + timedelta(days=30)).date().isoformat(),
                "supersedes": None,
                "limitations": ["Proves only this disposable workflow fixture"],
            }
            evidence_path.write_text(
                "---\n"
                + json.dumps(evidence, indent=2, sort_keys=True)
                + "\n---\n\n# Velocity workflow evidence\n",
                encoding="utf-8",
            )
            refreshed = run([str(project / "octon"), "maintain", "refresh", "--apply"], project)
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr or refreshed.stdout)

            handoff_plan = project / ".agent/transactions/plans/handoff.json"
            handoff = run(
                [
                    str(project / "octon"),
                    "work",
                    "handoff",
                    "--task-id",
                    "TASK-0001",
                    "--next-action",
                    "Review closure evidence",
                    "--summary",
                    "Integration work is ready for closure review",
                    "--operator",
                    "fixture-operator",
                    "--output",
                    str(handoff_plan),
                ],
                project,
            )
            self.assertEqual(handoff.returncode, 0, handoff.stderr or handoff.stdout)
            applied = apply_plan(project, handoff_plan)
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)

            close_plan = project / ".agent/transactions/plans/close.json"
            close = run(
                [
                    str(project / "octon"),
                    "work",
                    "close",
                    "TASK-0001",
                    "--criteria-met",
                    "--implementation-result",
                    "Guided initialization and lifecycle paths passed",
                    "--review-evidence",
                    "EVD-0001",
                    "--closure-evidence",
                    "EVD-0001",
                    "--external-effects",
                    "none",
                    "--next-action",
                    "Select the next project-owned task",
                    "--operator",
                    "fixture-operator",
                    "--output",
                    str(close_plan),
                ],
                project,
            )
            self.assertEqual(close.returncode, 0, close.stderr or close.stdout)
            applied = apply_plan(project, close_plan)
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
            self.assertEqual(
                task_record(project / ".agent/tasks/TASK-0001.md")["status"],
                "completed",
            )
            check = run([str(project / "octon"), "check", "--json"], project)
            self.assertEqual(check.returncode, 0, check.stderr or check.stdout)

    def test_detector_archetypes_are_read_only_in_clean_and_dirty_repositories(self) -> None:
        fixtures = {
            "software-product": {
                "package.json": json.dumps(
                    {"scripts": {"test": "node --test", "lint": "eslint ."}}
                )
                + "\n"
            },
            "research": {"references.bib": "@misc{fixture}\n", "paper/notes.md": "# Notes\n"},
            "brand": {"brand/guide.md": "# Brand guide\n"},
            "operations-hybrid": {"Makefile": "test:\n\t@true\n", "operations/runbook.md": "# Runbook\n"},
        }
        with tempfile.TemporaryDirectory(prefix="octon-mini-velocity-detect-") as temporary:
            area = Path(temporary)
            for index, (name, files) in enumerate(fixtures.items()):
                with self.subTest(name=name):
                    target = area / name
                    target.mkdir()
                    for relative, content in files.items():
                        path = target / relative
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(content, encoding="utf-8")
                    if index == 0:
                        initialized = run(["git", "init", "--quiet"], target)
                        self.assertEqual(initialized.returncode, 0, initialized.stderr)
                        (target / "untracked-dirty.txt").write_text("dirty\n", encoding="utf-8")
                    before = snapshot(target)
                    result = run(
                        [sys.executable, "-B", str(DETECTOR), "--target", str(target)],
                        SCRIPT_ROOT,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
                    self.assertEqual(snapshot(target), before)
                    report = json.loads(result.stdout)
                    self.assertFalse(report["permission_grant"])
                    self.assertTrue(report["archetype_candidates"])
                    if name == "software-product":
                        self.assertIn(
                            "project_test",
                            {item["hook"] for item in report["hook_candidates"]},
                        )

    def test_collaboration_bands_and_concurrency_remain_profile_independent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-mini-velocity-collaboration-") as temporary:
            area = Path(temporary)
            project = area / "project"
            result = run(
                [
                    sys.executable,
                    "-B",
                    str(SCAFFOLDER),
                    "--target",
                    str(project),
                    "--project-name",
                    "Collaboration Matrix Fixture",
                    "--profile",
                    "standard",
                    "--layout",
                    "compact",
                ],
                SCRIPT_ROOT,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            now = datetime.now(timezone.utc)
            base = [
                sys.executable,
                "-B",
                str(COLLABORATION),
                "plan",
                "--target",
                str(project),
                "--source",
                "authority:collaboration-fixture-owner",
                "--observed-at",
                now.isoformat(),
                "--expires-at",
                (now + timedelta(days=30)).isoformat(),
            ]
            cases = (
                ("solo", ["--writer-count", "1", "--solo-integration-preference", "direct"], "solo", False),
                ("pair", ["--writer-count", "2", "--independent-review-capacity", "yes"], "pair", False),
                (
                    "tiny-concurrent",
                    [
                        "--writer-count",
                        "4",
                        "--independent-review-capacity",
                        "no",
                        "--concurrent-humans",
                        "2",
                        "--concurrent-agents",
                        "1",
                    ],
                    "tiny",
                    True,
                ),
            )
            before = snapshot(project)
            plans: dict[str, Path] = {}
            for name, arguments, band, concurrent in cases:
                with self.subTest(case=name):
                    output = area / f"{name}.json"
                    result = run([*base, *arguments, "--output", str(output)], SCRIPT_ROOT)
                    self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
                    plan = load(output)
                    operation = next(
                        item for item in plan["operations"] if item["path"] == ".agent/project.json"
                    )
                    project_value = json.loads(
                        base64.b64decode(operation["content_base64"], validate=True)
                    )
                    collaboration = project_value["collaboration_profile"]
                    self.assertEqual(collaboration["team_band"], band)
                    self.assertEqual(collaboration["concurrent_work"], concurrent)
                    self.assertEqual(
                        collaboration["workflow_selection"]["status"], "proposed"
                    )
                    plans[name] = output
            self.assertEqual(snapshot(project), before)

            stale_output = area / "stale.json"
            stale = run(
                [
                    sys.executable,
                    "-B",
                    str(COLLABORATION),
                    "plan",
                    "--target",
                    str(project),
                    "--writer-count",
                    "1",
                    "--source",
                    "authority:collaboration-fixture-owner",
                    "--observed-at",
                    (now - timedelta(days=2)).isoformat(),
                    "--expires-at",
                    (now - timedelta(days=1)).isoformat(),
                    "--solo-integration-preference",
                    "direct",
                    "--output",
                    str(stale_output),
                ],
                SCRIPT_ROOT,
            )
            self.assertNotEqual(stale.returncode, 0)
            self.assertFalse(stale_output.exists())
            self.assertEqual(snapshot(project), before)

            pair_plan = load(plans["pair"])
            applied = run(
                [
                    sys.executable,
                    "-B",
                    str(COLLABORATION),
                    "apply",
                    "--target",
                    str(project),
                    "--plan",
                    str(plans["pair"]),
                    "--accept-digest",
                    pair_plan["canonical_plan_digest"],
                ],
                SCRIPT_ROOT,
            )
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
            installed = load(project / ".agent/project.json")
            self.assertEqual(installed["collaboration_profile"]["team_band"], "pair")
            self.assertEqual(load(project / ".octon-origin.json")["profile"], "standard")

    def test_semantic_adoption_preserves_established_and_dirty_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-mini-velocity-adoption-") as temporary:
            area = Path(temporary)
            project = area / "low-conflict"
            project.mkdir()
            initialized = run(["git", "init", "--quiet"], project)
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            established = project / "existing-project.txt"
            established.write_text("established bytes\n", encoding="utf-8")
            dirty = project / "untracked-work.txt"
            dirty.write_text("partial work\n", encoding="utf-8")
            before = snapshot(project, omit_git=True)
            plan_path = area / "adoption-plan.json"
            planned = run(
                [
                    sys.executable,
                    "-B",
                    str(ADOPT),
                    "plan",
                    "--target",
                    str(project),
                    "--project-name",
                    "Established Velocity Fixture",
                    "--profile",
                    "minimal",
                    "--layout",
                    "compact",
                    "--authority-source",
                    "authority:adoption-fixture-owner",
                    "--output",
                    str(plan_path),
                ],
                SCRIPT_ROOT,
            )
            self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
            self.assertEqual(snapshot(project, omit_git=True), before)
            plan = load(plan_path)
            applied = run(
                [
                    sys.executable,
                    "-B",
                    str(ADOPT),
                    "apply",
                    "--target",
                    str(project),
                    "--plan",
                    str(plan_path),
                    "--accept-digest",
                    plan["canonical_plan_digest"],
                ],
                SCRIPT_ROOT,
            )
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
            self.assertEqual(established.read_text(encoding="utf-8"), "established bytes\n")
            self.assertEqual(dirty.read_text(encoding="utf-8"), "partial work\n")
            self.assertEqual(
                load(project / ".agent/project.json")["project"]["adoption_status"],
                "in_progress",
            )

            conflict = area / "high-conflict"
            conflict.mkdir()
            (conflict / "AGENTS.md").write_text("# Existing authority\n", encoding="utf-8")
            conflict_before = snapshot(conflict)
            proposal = area / "adoption-conflict.json"
            blocked = run(
                [
                    sys.executable,
                    "-B",
                    str(ADOPT),
                    "plan",
                    "--target",
                    str(conflict),
                    "--project-name",
                    "Conflict Fixture",
                    "--profile",
                    "minimal",
                    "--authority-source",
                    "authority:adoption-fixture-owner",
                    "--output",
                    str(proposal),
                ],
                SCRIPT_ROOT,
            )
            self.assertEqual(blocked.returncode, 3, blocked.stderr or blocked.stdout)
            self.assertEqual(snapshot(conflict), conflict_before)
            self.assertTrue(load(proposal)["confirmed_collisions"])
            self.assertIn("OCTON-ADOPT-1101", blocked.stderr)
            self.assertIn("target project was unchanged", blocked.stderr)
            self.assertIn("Argv:", blocked.stderr)


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        raise SystemExit("Python 3.11+ is required")
    unittest.main(verbosity=2)
