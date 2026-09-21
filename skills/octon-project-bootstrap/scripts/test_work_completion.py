#!/usr/bin/env python3
"""Positive, negative, mutation, read-only, and resume tests for work.finish."""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent


def octon_mini_source_root() -> Path:
    candidates = (
        SKILL_ROOT.parents[1],
        SKILL_ROOT / "assets/octon-source",
    )
    for candidate in candidates:
        if (candidate / "shared/schemas/harness-work-completion.schema.json").is_file():
            return candidate
    return candidates[0]


OCTON_MINI_ROOT = octon_mini_source_root()
FINISH_SOURCE = SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_work_completion.py.tmpl"
TRANSACTION_SOURCE = SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_transaction.py.tmpl"
CHECK_SOURCE = SKILL_ROOT / "assets/templates/core/.agent/scripts/run_project_checks.py.tmpl"
VALIDATOR_SOURCE = SKILL_ROOT / "assets/templates/core/.agent/scripts/validate.py.tmpl"
OCTON_SOURCE = SKILL_ROOT / "assets/templates/core/.agent/scripts/octon.py.tmpl"
CONTINUATION_SOURCE = SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_continuation.py.tmpl"
WORKFLOW_SOURCE = SKILL_ROOT / "assets/packages/small-team-git-portfolio/templates/.agent/workflows/small-team-git.json.tmpl"
TOOLS_SOURCE = SKILL_ROOT / "assets/templates/core/.agent/tools.json.tmpl"
WORK_COMPLETION_SCHEMA = OCTON_MINI_ROOT / "shared/schemas/harness-work-completion.schema.json"
CONFIG_FIXTURE = SKILL_ROOT / "fixtures/work-completion/valid-config.json"
MUTATION_FIXTURE = SKILL_ROOT / "fixtures/work-completion/invalid-mutations.json"


def command(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        check=False,
        shell=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def must(argv: list[str], cwd: Path) -> str:
    result = command(argv, cwd)
    if result.returncode:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout.decode("utf-8", errors="strict").strip()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_module(name: str, path: Path) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
    return module


def snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def decision_text() -> str:
    return """---
{
  "schema_version": "harness.decision.v1",
  "id": "DEC-0001",
  "status": "accepted",
  "authority_source": "authority:fixture-owner"
}
---
# Fixture workflow authority
"""


class FixtureProject:
    def __init__(
        self,
        area: Path,
        workflow: str,
        *,
        concurrent: bool = False,
        required_checks: list[str] | None = None,
    ) -> None:
        self.root = area / "project"
        self.remote = area / "remote.git"
        self.root.mkdir(parents=True)
        must(["git", "init", "--bare", str(self.remote)], area)
        must(["git", "init", "-b", "main"], self.root)
        must(["git", "config", "user.name", "Fixture Operator"], self.root)
        must(["git", "config", "user.email", "fixture@example.invalid"], self.root)
        must(["git", "remote", "add", "origin", str(self.remote)], self.root)
        scripts = self.root / ".agent/scripts"
        scripts.mkdir(parents=True)
        (scripts / "octon_transaction.py").write_bytes(TRANSACTION_SOURCE.read_bytes())
        (scripts / "octon_work_completion.py").write_bytes(FINISH_SOURCE.read_bytes())
        (scripts / "run_project_checks.py").write_bytes(CHECK_SOURCE.read_bytes())
        (scripts / "octon_continuation.py").write_bytes(
            CONTINUATION_SOURCE.read_bytes()
        )
        schema_path = self.root / ".agent/schemas/harness-work-completion.schema.json"
        schema_path.parent.mkdir(parents=True)
        schema_path.write_bytes(WORK_COMPLETION_SCHEMA.read_bytes())
        (self.root / "AGENTS.md").write_text("# Fixture instructions\n", encoding="utf-8")
        (self.root / "task.txt").write_text("base\n", encoding="utf-8")
        workflow_path = self.root / ".agent/workflows/small-team-git.json"
        workflow_path.parent.mkdir(parents=True)
        workflow_path.write_bytes(WORKFLOW_SOURCE.read_bytes())
        (self.root / ".agent/tools.json").write_bytes(TOOLS_SOURCE.read_bytes())
        decisions = self.root / ".agent/decisions"
        decisions.mkdir()
        (decisions / "DEC-0001-workflow.md").write_text(decision_text(), encoding="utf-8")
        config = json.loads(CONFIG_FIXTURE.read_text(encoding="utf-8"))
        config["required_hosted_checks"] = {
            "status": "configured",
            "names": required_checks or [],
        }
        if workflow == "solo_direct":
            integration = "not_applicable"
        else:
            integration = "merge_commit"
            config["cleanup"] = {
                "remote_task_branch": "required",
                "local_task_branch": "required",
            }
        if workflow in {"pair_pr", "tiny_pr"}:
            config["provider"] = {
                "adapter": "github_cli",
                "hosted_repository": "fixture/repository",
                "configuration_is_authority": False,
            }
            config["eligible_peer_reviewers"] = ["peer"]
        if workflow == "solo_hybrid":
            config["solo_hybrid_pull_request"] = "disabled"
        project = {
            "schema_version": "harness.project.v5",
            "project": {
                "id": "fixture-project",
                "name": "Fixture Project",
                "repository_root": ".",
                "profile": "minimal",
                "octon_mini_version": "4.0.0",
                "adoption_status": "not_assessed",
                "adoption_decision_ref": None,
            },
            "collaboration_profile": {
                "workflow_selection": {
                    "status": "adopted",
                    "base_workflow": workflow,
                    "modifiers": ["concurrent_work"] if concurrent else [],
                    "review_mode": "one_peer_when_available" if workflow in {"pair_pr", "tiny_pr"} else "self_review" if workflow == "solo_hybrid" else "none",
                    "integration_method": integration,
                    "adoption_decision_ref": "DEC-0001",
                    "used_fact_ids": [],
                }
            },
            "commands": {
                name: {
                    "status": "configured" if name == "project_test" else "not_applicable",
                    "owner": "fixture-owner",
                    "rationale": "Fixture-only read-only validation" if name == "project_test" else "Not used by this fixture",
                    "tool_name": "python" if name == "project_test" else None,
                    "argv": [sys.executable, "-B", "-c", "print('fixture pass')"] if name == "project_test" else None,
                    "version_argv": [sys.executable, "--version"] if name == "project_test" else None,
                    "timeout_seconds": 30 if name == "project_test" else None,
                    "evidence_freshness_days": 1 if name == "project_test" else None,
                    "side_effects": {
                        "classification": "read_only" if name == "project_test" else "not_applicable",
                        "repository_write_paths": [],
                        "external_effects": [],
                    },
                }
                for name in ("project_test", "project_lint", "project_build", "project_closure")
            },
            "work_completion": config,
        }
        project["commands"]["work_completion_plan"] = {
            "status": "configured",
            "owner": "fixture-owner",
            "rationale": "Fixture-only read-only completion planning",
            "tool_name": "python",
            "argv": ["python", "-B", ".agent/scripts/octon.py", "work", "finish", "plan"],
            "version_argv": ["python", "--version"],
            "timeout_seconds": 30,
            "evidence_freshness_days": 1,
            "side_effects": {
                "classification": "read_only",
                "repository_write_paths": [],
                "external_effects": [],
            },
        }
        write_json(self.root / ".agent/project.json", project)
        must(["git", "add", "."], self.root)
        must(["git", "commit", "-m", "fixture baseline"], self.root)
        must(["git", "push", "-u", "origin", "main"], self.root)
        self.base = must(["git", "rev-parse", "HEAD"], self.root)
        if workflow != "solo_direct":
            must(["git", "switch", "-c", "task/fixture"], self.root)
        concurrent_contract = {
            "shared_base_revision": self.base if concurrent else None,
            "declared_write_scope": ["task.txt"] if concurrent else [],
            "worktree_owner": "fixture-owner" if concurrent else None,
            "handback_state": "complete" if concurrent else "not_assessed",
            "partial_result_state": "resolved" if concurrent else "not_assessed",
            "coordination_evidence_refs": ["external:fixture-handback"] if concurrent else [],
        }
        task = {
            "schema_version": "harness.task.v2",
            "id": "TASK-0001",
            "status": "completed",
            "owner": "fixture-owner",
            "title": "Complete fixture change",
            "work_completion": {
                "eligible_staging_paths": ["task.txt"],
                "commit_message": "feat: complete fixture change",
                "pull_request_title": "Complete fixture change",
                "pull_request_body": "Fixture pull request; grants no authority.",
                "self_review_refs": ["external:fixture-self-review"],
                "concurrent_work": concurrent_contract,
            },
        }
        tasks = self.root / ".agent/tasks"
        tasks.mkdir()
        (tasks / "TASK-0001.md").write_text(
            "---\n" + json.dumps(task, indent=2, sort_keys=True) + "\n---\n# Fixture task\n",
            encoding="utf-8",
        )
        must(["git", "add", ".agent/tasks/TASK-0001.md"], self.root)
        must(["git", "commit", "-m", "chore: add completion fixture task"], self.root)
        if workflow == "solo_direct":
            must(["git", "push", "origin", "main"], self.root)
            self.base = must(["git", "rev-parse", "HEAD"], self.root)
        else:
            # The task record is part of the uncommitted bounded change only in
            # real projects; this fixture commits it on the task branch so the
            # completion subject remains just task.txt.
            self.base = must(["git", "merge-base", "HEAD", "origin/main"], self.root)
        (self.root / "task.txt").write_text("changed\n", encoding="utf-8")


class WorkCompletionTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.continuation = load_module("octon_continuation", CONTINUATION_SOURCE)
        sys.modules["octon_continuation"] = self.continuation
        self.transaction = load_module("octon_transaction", TRANSACTION_SOURCE)
        sys.modules["octon_transaction"] = self.transaction
        self.finish = load_module("octon_work_completion_fixture", FINISH_SOURCE)
        self.validator = load_module("validate_finish_fixture", VALIDATOR_SOURCE)

    def authorization(self, plan: dict[str, object], path: Path) -> Path:
        current = datetime.now(timezone.utc)
        value = {
            "schema_version": "harness.work-completion-authorization.v1",
            "artifact_kind": "external_authorization_attestation",
            "permission_grant": False,
            "plan_digest": plan["canonical_plan_digest"],
            "task_ref": plan["task_ref"],
            "repository_identity": plan["repository"]["identity"],
            "remote": plan["repository"]["remote"],
            "default_branch": plan["branches"]["default"],
            "task_branch": plan["branches"]["task"],
            "operations": plan["external_operations"],
            "authority_source": "authority:fixture-owner",
            "principal_or_role": "fixture-owner",
            "observed_by": "fixture-test",
            "observed_at": current.isoformat(),
            "valid_from": (current - timedelta(minutes=1)).isoformat(),
            "valid_until": (current + timedelta(hours=1)).isoformat(),
            "constraints": ["fixture repository only"],
        }
        value["evidence_fingerprint"] = self.finish.digest(value)
        write_json(path, value)
        return path

    def test_completion_refusals_are_typed_and_receipt_resumable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-work-completion-continuation-") as temporary:
            fixture = FixtureProject(Path(temporary), "solo_direct")
            project_path = fixture.root / ".agent/project.json"
            project = json.loads(project_path.read_text(encoding="utf-8"))
            project["work_completion"]["status"] = "disabled"
            write_json(project_path, project)
            with self.assertRaises(self.finish.FinishBlocked) as blocked:
                self.finish.build_plan(fixture.root)
            self.assertEqual(
                blocked.exception.report["failure_code"],
                "OCTON-WORK-4002",
            )
            self.assertFalse(blocked.exception.report["mutation"]["occurred"])
            self.assertTrue(blocked.exception.report["next_action"]["argv"])

            receipt = {"receipt_id": "WCR-" + "1" * 24}

            @self.finish.named_operation("push_branch")
            def synthetic_failure(root: Path, current: dict[str, object]) -> None:
                raise self.finish.FinishBlocked("synthetic resumable failure")

            with self.assertRaises(self.finish.FinishBlocked) as attempted:
                synthetic_failure(fixture.root, receipt)
            report = attempted.exception.report
            self.assertEqual(report["phase"], "apply")
            self.assertTrue(report["mutation"]["occurred"])
            self.assertEqual(report["mutation"]["external_effects"], ["push_branch"])
            self.assertEqual(
                report["next_action"]["argv"],
                [
                    "./octon",
                    "work",
                    "finish",
                    "resume",
                    "--receipt-id",
                    receipt["receipt_id"],
                ],
            )

    def test_plan_is_read_only_for_all_workflows_and_concurrent_modifier(self) -> None:
        cases = {
            "solo_direct": ("not_required", "none"),
            "solo_hybrid": ("not_required", "self_review_with_limitations"),
            "pair_pr": ("required", "one_peer"),
            "tiny_pr": ("required", "one_peer"),
        }
        external_operations: set[str] = set()
        with tempfile.TemporaryDirectory(prefix="octon-work-completion-plan-") as temporary:
            area = Path(temporary)
            for workflow, expected in cases.items():
                fixture = FixtureProject(
                    area / workflow,
                    workflow,
                    required_checks=["required-check"] if workflow == "pair_pr" else None,
                )
                project = json.loads(
                    (fixture.root / ".agent/project.json").read_text(encoding="utf-8")
                )
                self.assertEqual(
                    self.validator.check_work_completion_config(fixture.root, project),
                    [],
                )
                before = snapshot(fixture.root)
                plan = self.finish.build_plan(fixture.root)
                self.assertEqual(snapshot(fixture.root), before)
                self.assertTrue(plan["read_only"])
                self.assertFalse(plan["permission_grant"])
                self.assertEqual(plan["pull_request"]["requirement"], expected[0])
                self.assertEqual(plan["review"]["requirement"], expected[1])
                summary = self.continuation.plan_summary(plan)
                self.assertEqual(summary["operation"], "work.finish")
                self.assertEqual(
                    summary["effects"]["external"], plan["external_operations"]
                )
                self.assertEqual(
                    json.loads(
                        self.continuation.render_plan_summary(
                            summary, json_output=True
                        )
                    ),
                    summary,
                )
                self.assertIn(
                    plan["canonical_plan_digest"],
                    self.continuation.render_plan_summary(summary),
                )
                external_operations.update(plan["external_operations"])
            concurrent = FixtureProject(area / "concurrent", "solo_hybrid", concurrent=True)
            before = snapshot(concurrent.root)
            plan = self.finish.build_plan(concurrent.root)
            self.assertEqual(snapshot(concurrent.root), before)
            self.assertTrue(plan["concurrent_work"]["enabled"])
            self.assertEqual(plan["concurrent_work"]["handback_state"], "complete")
            self.assertEqual(
                external_operations,
                {
                    "fetch_remote",
                    "push_branch",
                    "locate_pull_request",
                    "open_pull_request",
                    "observe_change_checks",
                    "observe_pull_request_reviews",
                    "merge_pull_request",
                    "delete_remote_branch",
                },
            )
            interrupted: list[str] = []

            def interrupt(operation: str) -> None:
                interrupted.append(operation)
                raise KeyboardInterrupt("synthetic post-operation interruption")

            self.finish.INTERRUPTION_HOOK = interrupt
            completed = subprocess.CompletedProcess(["true"], 0, b"", b"")
            with (
                mock.patch.object(self.finish, "ensure_remote_identity"),
                mock.patch.object(self.finish, "authority_still_current"),
                mock.patch.object(self.finish, "run", return_value=completed),
            ):
                for operation in sorted(external_operations):
                    with self.assertRaises(KeyboardInterrupt):
                        self.finish.external(
                            concurrent.root, {}, operation, ["true"]
                        )
            self.assertEqual(interrupted, sorted(external_operations))

            project_path = concurrent.root / ".agent/project.json"
            project = json.loads(project_path.read_text(encoding="utf-8"))
            project["work_completion"]["completion_hook"][
                "mode"
            ] = "plan_only_on_completion_event"
            write_json(project_path, project)
            exact_argv = [
                "python",
                "-B",
                ".agent/scripts/octon.py",
                "work",
                "finish",
                "plan",
            ]
            event_result = subprocess.CompletedProcess(
                exact_argv,
                0,
                json.dumps(plan).encode("utf-8"),
                b"",
            )
            with mock.patch.object(
                self.finish, "run", return_value=event_result
            ) as event_run:
                self.assertEqual(
                    self.finish.run_completion_plan_event(concurrent.root), plan
                )
                event_run.assert_called_once_with(concurrent.root, exact_argv)

    def test_mutations_reject_unrelated_staged_stale_and_missing_authorization(self) -> None:
        mutations = json.loads(MUTATION_FIXTURE.read_text(encoding="utf-8"))["mutations"]
        self.assertGreaterEqual(len(mutations), 18)
        with tempfile.TemporaryDirectory(prefix="octon-work-completion-negative-") as temporary:
            fixture = FixtureProject(Path(temporary), "solo_direct")
            project_path = fixture.root / ".agent/project.json"
            project = json.loads(project_path.read_text(encoding="utf-8"))
            self.assertEqual(
                self.validator.check_work_completion_config(fixture.root, project),
                [],
            )
            permission_mutation = json.loads(json.dumps(project))
            permission_mutation["work_completion"]["permission_grant"] = True
            self.assertTrue(
                self.validator.check_work_completion_config(
                    fixture.root, permission_mutation
                )
            )
            apply_hook_mutation = json.loads(json.dumps(project))
            apply_hook_mutation["commands"]["work_completion_plan"]["argv"][-1] = "apply"
            self.assertTrue(
                self.validator.check_work_completion_config(
                    fixture.root, apply_hook_mutation
                )
            )
            plan = self.finish.build_plan(fixture.root)
            (fixture.root / "outside-task.txt").write_text("unrelated\n", encoding="utf-8")
            blocked = self.finish.build_plan(fixture.root, "TASK-0001")
            self.assertTrue(any("dirty paths differ" in item for item in blocked["blocking_reasons"]))
            (fixture.root / "outside-task.txt").unlink()
            must(["git", "add", "task.txt"], fixture.root)
            with self.assertRaises(self.finish.FinishBlocked):
                self.finish.build_plan(fixture.root)
            must(["git", "restore", "--staged", "task.txt"], fixture.root)
            (fixture.root / "task.txt").write_text("changed after review\n", encoding="utf-8")
            with self.assertRaises(self.finish.FinishBlocked):
                self.finish.find_plan_by_digest(
                    fixture.root, plan["canonical_plan_digest"], "TASK-0001"
                )
            with self.assertRaises(self.finish.FinishError):
                self.finish.load_authorization(fixture.root / "missing.json", plan)

            hook_path = fixture.root / ".git/hooks/pre-commit"
            hook_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            hook_path.chmod(0o755)
            hook_blocked = self.finish.build_plan(fixture.root, "TASK-0001")
            self.assertTrue(
                any("Git hooks" in item for item in hook_blocked["blocking_reasons"])
            )
            hook_path.unlink()
            must(["git", "config", "core.fsmonitor", "true"], fixture.root)
            with self.assertRaises(self.finish.FinishBlocked):
                self.finish.build_plan(fixture.root, "TASK-0001")

    def test_remote_identity_receipt_tampering_and_missing_authority_block(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-work-completion-integrity-") as temporary:
            area = Path(temporary)
            fixture = FixtureProject(area, "solo_direct")
            plan = self.finish.build_plan(fixture.root)
            authority_path = self.authorization(plan, area / "authorization.json")
            auth = self.finish.load_authorization(authority_path, plan)
            receipt = self.finish.new_receipt(plan, auth)
            self.transaction.write_work_completion_receipt(
                fixture.root, receipt, create=True
            )

            tampered = json.loads(json.dumps(receipt))
            tampered["plan"]["proposed_commit"]["message"] = "tampered"
            with self.assertRaises(self.finish.FinishError):
                self.finish.validate_receipt(tampered)

            self.finish.record(
                fixture.root,
                receipt,
                "planned",
                "synthetic_progress",
                "already_satisfied",
                {},
            )
            regressed = json.loads(json.dumps(receipt))
            regressed["progress"] = []
            with self.assertRaises(self.transaction.TransactionError):
                self.transaction.write_work_completion_receipt(
                    fixture.root, regressed, create=False
                )

            replacement_remote = area / "replacement.git"
            must(["git", "init", "--bare", str(replacement_remote)], area)
            must(
                ["git", "remote", "set-url", "origin", str(replacement_remote)],
                fixture.root,
            )
            with self.assertRaises(self.finish.FinishBlocked):
                self.finish.remote_head(fixture.root, receipt, "main")

            decision = fixture.root / ".agent/decisions/DEC-0001-workflow.md"
            missing_decision = decision.with_suffix(".missing")
            decision.rename(missing_decision)
            with self.assertRaises(self.finish.FinishBlocked):
                self.finish.build_plan(fixture.root)
            missing_decision.rename(decision)

            project_path = fixture.root / ".agent/project.json"
            project = json.loads(project_path.read_text(encoding="utf-8"))
            project["collaboration_profile"]["workflow_selection"][
                "integration_method"
            ] = "unsupported"
            write_json(project_path, project)
            with self.assertRaises(self.finish.FinishBlocked):
                self.finish.build_plan(fixture.root)

    def test_current_closure_receipt_is_bound_without_hiding_other_dirt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-work-completion-closure-") as temporary:
            fixture = FixtureProject(Path(temporary), "solo_direct")
            task_relative = ".agent/tasks/TASK-0001.md"
            task_bytes = (fixture.root / task_relative).read_bytes()
            validation = [[sys.executable, "-B", "-c", "raise SystemExit(0)"]]
            close_plan = self.transaction.build_plan(
                fixture.root,
                operation_name="work.close",
                scope="Synthetic exact v3 closure receipt",
                operations=[
                    self.transaction.operation(
                        "replace",
                        task_relative,
                        task_bytes,
                        "Preserve the completed task bytes while producing a real close receipt.",
                    )
                ],
                evidence=[],
                assumptions=[],
                confidence="deterministic",
                limitations=["Synthetic v3 close-to-finish integration fixture."],
                staged_validation_plan=validation,
                post_apply_validation_plan=validation,
            )
            value, receipt_path = self.transaction.apply_plan(
                fixture.root,
                close_plan,
                close_plan["canonical_plan_digest"],
            )
            self.assertEqual(value["schema_version"], "harness.transaction-receipt.v3")
            self.assertIn("bundle", value)
            self.assertIn("timings", value)
            receipt_id = value["receipt_id"]
            relative = receipt_path.resolve().relative_to(
                fixture.root.resolve()
            ).as_posix()
            plan = self.finish.build_plan(fixture.root)
            self.assertEqual(plan["closure_transaction"]["receipt_ref"], receipt_id)
            self.assertEqual(
                plan["eligible_staging_paths"], sorted(["task.txt", relative])
            )

            (fixture.root / "unrelated.txt").write_text(
                "not task owned\n", encoding="utf-8"
            )
            blocked = self.finish.build_plan(fixture.root, "TASK-0001")
            self.assertTrue(
                any("dirty paths differ" in item for item in blocked["blocking_reasons"])
            )
            (fixture.root / "unrelated.txt").unlink()
            value["status"] = "tampered"
            write_json(receipt_path, value)
            with self.assertRaises(self.finish.FinishBlocked):
                self.finish.find_plan_by_digest(
                    fixture.root, plan["canonical_plan_digest"], "TASK-0001"
                )

    def test_successful_close_apply_dispatches_only_the_plan_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-work-completion-event-") as temporary:
            root = Path(temporary)
            receipt_path = (
                root
                / ".agent/transactions/receipts"
                / ("RCPT-" + "2" * 24 + ".json")
            )
            receipt_path.parent.mkdir(parents=True)
            sys.modules["octon_work_completion"] = self.finish
            sys.modules["octon_doctor"] = types.ModuleType("octon_doctor")
            octon = load_module("octon_work_completion_dispatch_fixture", OCTON_SOURCE)
            octon.ROOT = root
            args = types.SimpleNamespace(
                apply_plan="close.json", accept_digest="3" * 64
            )
            completion_plan = {
                "artifact_kind": "work_completion_plan",
                "canonical_plan_digest": "4" * 64,
            }
            with (
                mock.patch.object(
                    octon.transaction,
                    "load_plan",
                    return_value={"operation": "work.close"},
                ),
                mock.patch.object(
                    octon.transaction,
                    "apply_plan",
                    return_value=({"receipt_id": "RCPT-" + "2" * 24}, receipt_path),
                ),
                mock.patch.object(
                    octon.octon_work_completion,
                    "run_completion_plan_event",
                    return_value=completion_plan,
                ) as event,
            ):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(octon.apply_workflow_plan(args, "work."), 0)
                event.assert_called_once_with(root)
    def test_solo_direct_apply_and_completed_resume_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-work-completion-direct-") as temporary:
            fixture = FixtureProject(Path(temporary), "solo_direct")
            plan = self.finish.build_plan(fixture.root)
            authority_path = self.authorization(plan, Path(temporary) / "authorization.json")
            receipt = self.finish.apply(
                fixture.root, plan["canonical_plan_digest"], authority_path
            )
            self.assertEqual(receipt["state"], "completed")
            self.assertEqual(must(["git", "status", "--porcelain"], fixture.root), "")
            self.assertEqual(
                must(["git", "rev-parse", "HEAD"], fixture.root),
                must(["git", "ls-remote", "origin", "refs/heads/main"], fixture.root).split()[0],
            )
            receipt_path = self.transaction.work_completion_receipt_path(
                fixture.root, receipt["receipt_id"]
            )
            before = receipt_path.read_bytes()
            resumed = self.finish.resume(fixture.root, receipt["receipt_id"])
            self.assertEqual(resumed["state"], "completed")
            self.assertEqual(receipt_path.read_bytes(), before)

    def test_interrupted_push_is_observed_and_not_duplicated_on_resume(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-work-completion-interrupt-") as temporary:
            fixture = FixtureProject(Path(temporary), "solo_direct")
            plan = self.finish.build_plan(fixture.root)
            authority_path = self.authorization(plan, Path(temporary) / "authorization.json")

            def interrupt(operation: str) -> None:
                if operation == "push_branch":
                    raise KeyboardInterrupt("synthetic post-push interruption")

            self.finish.INTERRUPTION_HOOK = interrupt
            with self.assertRaises(KeyboardInterrupt):
                self.finish.apply(
                    fixture.root, plan["canonical_plan_digest"], authority_path
                )
            paths = self.transaction.list_work_completion_receipts(fixture.root)
            self.assertEqual(len(paths), 1)
            interrupted = self.transaction.load_work_completion_receipt(
                fixture.root, paths[0].stem
            )
            self.assertNotIn("push_default_branch", interrupted["completed_operations"])
            remote_before = must(["git", "ls-remote", "origin", "refs/heads/main"], fixture.root)
            self.finish.INTERRUPTION_HOOK = lambda _operation: None
            completed = self.finish.resume(fixture.root, interrupted["receipt_id"])
            remote_after = must(["git", "ls-remote", "origin", "refs/heads/main"], fixture.root)
            self.assertEqual(remote_after, remote_before)
            self.assertEqual(completed["state"], "completed")
            event = next(
                item
                for item in completed["progress"]
                if item["operation"] == "push_default_branch"
            )
            self.assertEqual(event["result"], "already_satisfied")

    def test_peer_review_self_approval_and_cleanup_before_integration_block(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-work-completion-peer-") as temporary:
            fixture = FixtureProject(Path(temporary), "pair_pr")
            plan = self.finish.build_plan(fixture.root)
            authority_path = self.authorization(plan, Path(temporary) / "authorization.json")
            auth = self.finish.load_authorization(authority_path, plan)
            receipt = self.finish.new_receipt(plan, auth)
            receipt["revisions"]["commit"] = plan["expected_revisions"]["head_before_commit"]
            receipt["completed_operations"] = ["create_commit"]
            receipt["pull_request"] = {"number": 1}
            self.transaction.write_work_completion_receipt(fixture.root, receipt, create=True)
            self_review = {
                "headRefOid": receipt["revisions"]["commit"],
                "author": {"login": "author"},
                "reviews": [{"state": "APPROVED", "author": {"login": "author"}}],
            }
            with mock.patch.object(self.finish, "gh_json", return_value=self_review):
                with self.assertRaises(self.finish.FinishBlocked):
                    self.finish.observe_peer_review(fixture.root, receipt)
            peer_review = {
                **self_review,
                "reviews": [{"state": "APPROVED", "author": {"login": "peer"}}],
            }
            with mock.patch.object(self.finish, "gh_json", return_value=peer_review):
                self.finish.observe_peer_review(fixture.root, receipt)
            self.assertIn("observe_peer_review", receipt["completed_operations"])
            with mock.patch.object(
                self.finish, "remote_head", return_value=receipt["revisions"]["commit"]
            ):
                with self.assertRaises(self.finish.FinishBlocked):
                    self.finish.delete_remote(fixture.root, receipt)

    def test_provider_pr_check_and_integration_mutations_block(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-work-completion-provider-") as temporary:
            fixture = FixtureProject(Path(temporary), "pair_pr")
            plan = self.finish.build_plan(fixture.root)
            authority_path = self.authorization(plan, Path(temporary) / "authorization.json")
            auth = self.finish.load_authorization(authority_path, plan)
            receipt = self.finish.new_receipt(plan, auth)
            receipt["revisions"]["commit"] = plan["expected_revisions"]["head_before_commit"]
            receipt["completed_operations"] = ["create_commit"]
            self.transaction.write_work_completion_receipt(fixture.root, receipt, create=True)
            mismatched = {
                "number": 1,
                "state": "OPEN",
                "isDraft": False,
                "headRefName": plan["branches"]["task"],
                "baseRefName": plan["branches"]["default"],
                "headRefOid": "0" * 40,
                "mergeStateStatus": "CLEAN",
                "url": "https://example.invalid/pr/1",
            }
            with mock.patch.object(self.finish, "locate_pr", return_value=mismatched):
                with self.assertRaises(self.finish.FinishBlocked):
                    self.finish.ensure_pr(fixture.root, receipt)
            exact = {**mismatched, "headRefOid": receipt["revisions"]["commit"]}
            with mock.patch.object(
                self.finish, "locate_pr", return_value={**exact, "isDraft": True}
            ):
                with self.assertRaises(self.finish.FinishBlocked):
                    self.finish.merge_pr(fixture.root, receipt)
            with mock.patch.object(
                self.finish,
                "locate_pr",
                return_value={**exact, "mergeStateStatus": "DIRTY"},
            ):
                with self.assertRaises(self.finish.FinishBlocked):
                    self.finish.merge_pr(fixture.root, receipt)

            check_plan = json.loads(json.dumps(plan))
            check_plan["required_hosted_checks"] = ["required-check"]
            check_plan["external_operations"].append("observe_change_checks")
            check_plan.pop("canonical_plan_digest")
            check_plan["canonical_plan_digest"] = self.finish.digest(check_plan)
            check_authority_path = self.authorization(
                check_plan, Path(temporary) / "check-authorization.json"
            )
            check_receipt = self.finish.new_receipt(
                check_plan,
                self.finish.load_authorization(check_authority_path, check_plan),
            )
            check_receipt["revisions"]["commit"] = check_plan["expected_revisions"]["head_before_commit"]
            check_receipt["completed_operations"] = ["create_commit"]
            self.transaction.write_work_completion_receipt(
                fixture.root, check_receipt, create=True
            )
            with mock.patch.object(
                self.finish,
                "gh_json",
                side_effect=[{"check_runs": []}, {"statuses": []}],
            ):
                with self.assertRaises(self.finish.FinishBlocked):
                    self.finish.observe_checks(
                        fixture.root,
                        check_receipt,
                        check_receipt["revisions"]["commit"],
                    )
            with mock.patch.object(
                self.finish,
                "gh_json",
                side_effect=[
                    {
                        "check_runs": [
                            {"name": "required-check", "conclusion": "failure"}
                        ]
                    },
                    {"statuses": []},
                ],
            ):
                with self.assertRaises(self.finish.FinishBlocked):
                    self.finish.observe_checks(
                        fixture.root,
                        check_receipt,
                        check_receipt["revisions"]["commit"],
                    )

    def test_concurrent_owner_empty_commit_and_non_fast_forward_mutations_block(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-work-completion-safety-") as temporary:
            area = Path(temporary)
            concurrent = FixtureProject(area / "concurrent", "solo_hybrid", concurrent=True)
            task_path = concurrent.root / ".agent/tasks/TASK-0001.md"
            text_value = task_path.read_text(encoding="utf-8")
            task = json.loads(text_value.split("---\n", 2)[1])
            task["work_completion"]["concurrent_work"]["worktree_owner"] = "different-owner"
            task_path.write_text(
                "---\n" + json.dumps(task, indent=2, sort_keys=True) + "\n---\n# Fixture task\n",
                encoding="utf-8",
            )
            plan = self.finish.build_plan(concurrent.root, "TASK-0001")
            self.assertTrue(any("ownership" in item for item in plan["blocking_reasons"]))

            empty = FixtureProject(area / "empty", "solo_direct")
            (empty.root / "task.txt").write_text("base\n", encoding="utf-8")
            empty_plan = self.finish.build_plan(empty.root, "TASK-0001")
            self.assertTrue(any("dirty paths differ" in item for item in empty_plan["blocking_reasons"]))

            divergent = FixtureProject(area / "divergent", "pair_pr")
            divergent_plan = self.finish.build_plan(divergent.root)
            authority_path = self.authorization(
                divergent_plan, area / "divergent-authorization.json"
            )
            auth = self.finish.load_authorization(authority_path, divergent_plan)
            receipt = self.finish.new_receipt(divergent_plan, auth)
            receipt["revisions"]["commit"] = divergent_plan["expected_revisions"]["head_before_commit"]
            receipt["revisions"]["integrated"] = "1" * 40
            must(["git", "switch", "main"], divergent.root)
            (divergent.root / "local-only.txt").write_text("diverged\n", encoding="utf-8")
            must(["git", "add", "local-only.txt"], divergent.root)
            must(["git", "commit", "-m", "local divergence"], divergent.root)
            self.transaction.write_work_completion_receipt(divergent.root, receipt, create=True)
            with self.assertRaises(self.finish.FinishBlocked):
                self.finish.sync_default(divergent.root, receipt)

            owned = FixtureProject(area / "owned", "pair_pr")
            owned_plan = self.finish.build_plan(owned.root)
            owned_authority_path = self.authorization(
                owned_plan, area / "owned-authorization.json"
            )
            owned_receipt = self.finish.new_receipt(
                owned_plan,
                self.finish.load_authorization(
                    owned_authority_path, owned_plan
                ),
            )
            task_revision = must(["git", "rev-parse", "HEAD"], owned.root)
            must(["git", "restore", "task.txt"], owned.root)
            must(["git", "switch", "main"], owned.root)
            must(
                [
                    "git",
                    "worktree",
                    "add",
                    str(area / "owned-secondary"),
                    "task/fixture",
                ],
                owned.root,
            )
            default_revision = must(["git", "rev-parse", "HEAD"], owned.root)
            owned_receipt["revisions"] = {
                "commit": task_revision,
                "integrated": default_revision,
                "synchronized_default": default_revision,
            }
            with self.assertRaises(self.finish.FinishBlocked):
                self.finish.delete_local(owned.root, owned_receipt)


if __name__ == "__main__":
    unittest.main()
