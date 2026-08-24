#!/usr/bin/env python3
"""Source-repository work-completion contract and safety coverage."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


SCRIPT_ROOT = Path(__file__).resolve().parent
RUNNER_PATH = SCRIPT_ROOT / "source_work_completion.py"
SCHEMA_PATH = SCRIPT_ROOT.parents[2] / "shared/schemas/harness-work-completion.schema.json"
VALIDATOR_PATH = SCRIPT_ROOT.parent / "assets/templates/core/.agent/scripts/validate.py.tmpl"


def load_python(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        import types
        module = types.ModuleType(name)
        module.__file__ = str(path)
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
        return module
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load_python(RUNNER_PATH, "octon_source_work_completion_tests")
load_json = RUNNER.load_json


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class SourceWorkCompletionTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="octon-source-work-completion-")
        self.area = Path(self.temporary.name)
        self.remote = self.area / "remote.git"
        self.root = self.area / "source"
        subprocess.run(["git", "init", "--bare", str(self.remote)], capture_output=True, check=True)
        subprocess.run(["git", "init", "-b", "main", str(self.root)], capture_output=True, check=True)
        git(self.root, "config", "user.name", "Synthetic Source Worker")
        git(self.root, "config", "user.email", "synthetic@example.invalid")
        (self.root / "shared/source-contracts").mkdir(parents=True)
        (self.root / "octon-mini.json").write_text("{}\n", encoding="utf-8")
        (self.root / "VERSION").write_text("4.2.0\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("# Synthetic source instructions\n", encoding="utf-8")
        (self.root / "ARCHITECTURE_DECISIONS.md").write_text(
            "## SRC-DEC-0019 — Governed autonomous-delivery capability\n\n| Status | `accepted` |\n\n| Source-repository mode | Synthetic accepted source mode |\n\n## SRC-DEC-0020 — Standing source-release evidence policy\n",
            encoding="utf-8",
        )
        (self.root / "GIT_WORKFLOW.md").write_text(
            "| Base workflow | `solo_hybrid` |\n| Integration method | `merge_commit` |\nstable `required` check\n",
            encoding="utf-8",
        )
        (self.root / "RELEASE.md").write_text("# Synthetic release gate\n", encoding="utf-8")
        (self.root / "RELEASE_READINESS.md").write_text("# Synthetic readiness evidence\n", encoding="utf-8")
        write_json(self.root / "shared/source-contracts/commands.json", {"permission_grant": False})
        source_evaluator = self.root / "skills/octon-mini-project-bootstrap/assets/templates/core/.agent/scripts/octon_autonomous_delivery.py.tmpl"
        source_evaluator.parent.mkdir(parents=True)
        source_evaluator.write_text(
            (RUNNER.TEMPLATE_ROOT / "octon_autonomous_delivery.py.tmpl").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (self.root / "subject.txt").write_text("base\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "chore: synthetic source base")
        git(self.root, "remote", "add", "origin", str(self.remote))
        git(self.root, "push", "-u", "origin", "main")
        git(self.root, "switch", "-c", "chore/autonomous-source-test")
        (self.root / "subject.txt").write_text("candidate\n", encoding="utf-8")
        git(self.root, "add", "subject.txt")
        git(self.root, "commit", "-m", "feat: synthetic source candidate")
        self.control = self.area / "control"
        self.evidence = self.area / "evidence"
        self.control.mkdir()
        self.evidence.mkdir()
        self.transaction, self.completion, self.autonomous = RUNNER.engine_modules()
        self.validator = load_python(VALIDATOR_PATH, "source_work_completion_schema_validator")
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc).replace(microsecond=0)
        args = argparse.Namespace(
            profile="fast_delivery",
            compute_mode="included_subscription",
            subscription_plan_ref="authority:synthetic-included-plan",
            supersedes_authorization_record=None,
            valid_from=(now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            valid_until=(now + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            authority_dir=str(self.control),
            evidence_root=str(self.evidence),
            custom_contract=None,
            repository_root=str(self.root),
            repository_identity="cooperonlineenterprises/octon-mini",
            remote="origin",
            default_branch="main",
            task_branch_pattern="chore/autonomous-*",
            authorization_id="SAC-90",
            ai_budget_per_run=250.0,
            ai_budget_per_authorization=1000.0,
        )
        contract = self.autonomous.contract_from(args, self.root)
        confirmation = {
            "schema_version": self.autonomous.CONFIRMATION_SCHEMA,
            "artifact_kind": "standing_authorization_confirmation_evidence",
            "permission_grant": False,
            "authorization_id": contract["authorization_id"],
            "contract_digest": contract["canonical_contract_digest"],
            "confirmation_method": "independent_exact_digest_statement",
            "confirmation_statement": self.autonomous.expected_confirmation_statement(contract["canonical_contract_digest"], contract["authorization_id"]),
            "authority_source": "authority:synthetic-source-test",
            "confirmed_by_role": "synthetic-source-owner",
            "confirmed_at": now.isoformat().replace("+00:00", "Z"),
        }
        confirmation["confirmation_fingerprint"] = self.autonomous.digest(confirmation)
        self.confirmation_path = self.control / "SAC-90.confirmation.json"
        write_json(self.confirmation_path, confirmation)
        self.record = self.autonomous.accepted_record(contract, confirmation)
        self.record_path = self.control / "SAC-90.json"
        write_json(self.record_path, self.record)
        task = {
            "schema_version": RUNNER.TASK_SCHEMA,
            "artifact_kind": "external_codex_task_reference",
            "permission_grant": False,
            "task_ref": "external:codex-task:11111111-2222-3333-4444-555555555555",
            "priority_authority_ref": "authority:synthetic-priority",
            "scope": "Deliver the synthetic Octon Mini source candidate.",
            "acceptance_refs": ["SRC-DEC-0019", "SRC-DEC-0020"],
            "branch": "chore/autonomous-source-test",
            "pull_request": {"title": "Synthetic source PR", "body": "Synthetic source validation only."},
            "self_review_refs": ["external:synthetic-self-review"],
            "validation_evidence_refs": ["external:synthetic-local-validation"],
            "authority_source": "authority:synthetic-source-test",
            "observed_at": now.isoformat().replace("+00:00", "Z"),
            "valid_until": (now + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            "limitations": ["Synthetic fixture only; no live external authority."],
        }
        task["task_reference_digest"] = RUNNER.digest(task)
        self.task_path = self.area / "task-reference.json"
        write_json(self.task_path, task)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def authorization(self, plan: dict[str, object]) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        value = {
            "schema_version": self.completion.AUTH_SCHEMA,
            "artifact_kind": "external_authorization_attestation",
            "permission_grant": False,
            "plan_digest": plan["canonical_plan_digest"],
            "task_ref": plan["task_ref"],
            "repository_identity": plan["repository"]["identity"],
            "remote": plan["repository"]["remote"],
            "default_branch": plan["branches"]["default"],
            "task_branch": plan["branches"]["task"],
            "operations": plan["external_operations"],
            "authority_source": "authority:synthetic-source-test",
            "principal_or_role": "synthetic-worker",
            "observed_by": "synthetic-observer",
            "observed_at": now.isoformat().replace("+00:00", "Z"),
            "valid_from": (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            "valid_until": (now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
            "constraints": [],
        }
        value["evidence_fingerprint"] = self.completion.digest(value)
        return value

    def test_source_plan_is_read_only_strict_and_binds_precommitted_candidate(self) -> None:
        before = git(self.root, "status", "--porcelain=v1")
        plan = RUNNER.build_plan(self.root, self.task_path, self.record_path)
        self.assertEqual(plan["schema_version"], self.completion.SOURCE_PLAN_SCHEMA)
        self.assertTrue(plan["source_mode"])
        self.assertEqual(plan["task_ref"], "external:codex-task:11111111-2222-3333-4444-555555555555")
        self.assertEqual(plan["expected_revisions"]["candidate_head"], git(self.root, "rev-parse", "HEAD"))
        self.assertEqual(plan["candidate_commits"], [git(self.root, "rev-parse", "HEAD")])
        self.assertEqual(plan["external_operations"], ["fetch_remote", "push_branch", "locate_pull_request", "open_pull_request", "observe_change_checks", "merge_pull_request", "delete_remote_branch"])
        self.assertTrue(plan["candidate_validation"]["required"])
        self.assertEqual(plan["candidate_validation"]["expected_matrix_jobs"], 24)
        self.assertTrue(plan["post_merge_validation"]["required"])
        self.assertEqual(git(self.root, "status", "--porcelain=v1"), before)
        self.assertEqual(self.validator.validate_schema(load_json(self.task_path), self.schema["$defs"]["external_task_reference"], root_schema=self.schema), [])
        self.assertEqual(self.validator.validate_schema(plan, self.schema["$defs"]["source_plan"], root_schema=self.schema), [])
        plan_path = self.area / "reviewed-source-plan.json"
        write_json(plan_path, plan)
        loaded, _transaction, _completion = RUNNER.load_current_plan(self.root, plan_path)
        self.assertEqual(loaded, plan)
        changed = json.loads(json.dumps(plan))
        changed["limitations"].append("Changed after review.")
        changed_path = self.area / "changed-source-plan.json"
        write_json(changed_path, changed)
        with self.assertRaisesRegex(RUNNER.SourceCompletionError, "absent or malformed"):
            RUNNER.load_current_plan(self.root, changed_path)
        receipt = self.completion.new_receipt(plan, self.authorization(plan))
        self.assertEqual(self.validator.validate_schema(receipt, self.schema["$defs"]["source_receipt"], root_schema=self.schema), [])
        malformed = json.loads(json.dumps(plan))
        malformed["cleanup"]["remote_task_branch"] = False
        self.assertTrue(self.validator.validate_schema(malformed, self.schema["$defs"]["source_plan"], root_schema=self.schema))

    def test_source_cli_requires_external_artifact_and_creates_no_task_lifecycle(self) -> None:
        before = git(self.root, "status", "--porcelain=v1")
        planned = subprocess.run(
            [
                sys.executable,
                "-B",
                str(RUNNER_PATH),
                "--target",
                str(self.root),
                "plan",
                "--task-reference",
                str(self.task_path),
                "--authorization-record",
                str(self.record_path),
            ],
            cwd=self.area,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
        self.assertEqual(json.loads(planned.stdout), RUNNER.build_plan(self.root, self.task_path, self.record_path))
        self.assertEqual(git(self.root, "status", "--porcelain=v1"), before)
        self.assertFalse((self.root / ".agent/tasks").exists())
        denied = subprocess.run(
            [
                sys.executable,
                "-B",
                str(RUNNER_PATH),
                "--target",
                str(self.root),
                "plan",
                "--task-ref",
                "raw-inline-task",
                "--authorization-record",
                str(self.record_path),
            ],
            cwd=self.area,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(denied.returncode, 0)
        self.assertEqual(git(self.root, "status", "--porcelain=v1"), before)

    def test_changed_task_reference_and_wrong_branch_fail_closed(self) -> None:
        plan = RUNNER.build_plan(self.root, self.task_path, self.record_path)
        task = load_json(self.task_path)
        task["scope"] = "Changed after planning"
        write_json(self.task_path, task)
        with self.assertRaisesRegex(self.completion.FinishBlocked, "task-reference bytes changed"):
            self.completion.source_repository_fingerprint(self.root, plan)
        task["branch"] = "main"
        task["task_reference_digest"] = RUNNER.digest({key: value for key, value in task.items() if key != "task_reference_digest"})
        write_json(self.task_path, task)
        with self.assertRaisesRegex(RUNNER.SourceCompletionError, "branch"):
            RUNNER.build_plan(self.root, self.task_path, self.record_path)

    def test_expired_in_repository_and_changed_candidate_bindings_fail_closed(self) -> None:
        task = load_json(self.task_path)
        task["valid_until"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        task["task_reference_digest"] = RUNNER.digest({key: value for key, value in task.items() if key != "task_reference_digest"})
        write_json(self.task_path, task)
        with self.assertRaisesRegex(RUNNER.SourceCompletionError, "expired"):
            RUNNER.build_plan(self.root, self.task_path, self.record_path)
        task["valid_until"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
        task["task_reference_digest"] = RUNNER.digest({key: value for key, value in task.items() if key != "task_reference_digest"})
        write_json(self.task_path, task)
        in_repository = self.root / "codex-task.json"
        write_json(in_repository, task)
        with self.assertRaisesRegex(RUNNER.SourceCompletionError, "outside the repository"):
            RUNNER.build_plan(self.root, in_repository, self.record_path)
        in_repository.unlink()
        plan = RUNNER.build_plan(self.root, self.task_path, self.record_path)
        (self.root / "subject.txt").write_text("candidate changed\n", encoding="utf-8")
        git(self.root, "add", "subject.txt")
        git(self.root, "commit", "-m", "fix: mutate reviewed candidate")
        with self.assertRaisesRegex(self.completion.FinishBlocked, "task branch changed"):
            self.completion.source_repository_fingerprint(self.root, plan)

    def test_every_source_external_effect_requires_fresh_subscription_status(self) -> None:
        plan = RUNNER.build_plan(self.root, self.task_path, self.record_path)
        plan_path = self.area / "source-plan.json"
        write_json(plan_path, plan)
        observed = self.autonomous.utc_now()
        contract = self.record["contract"]
        compute = {
            "schema_version": self.autonomous.COMPUTE_SCHEMA,
            "artifact_kind": "external_host_compute_enforcement_evidence",
            "compute_mode": "included_subscription",
            "host_enforced": True,
            "observed_at": self.autonomous.utc_text(observed),
            "valid_until": self.autonomous.utc_text(observed + timedelta(minutes=10)),
            "metered_api": None,
            "included_subscription": {
                "plan_ref": contract["compute_control"]["included_subscription"]["plan_ref"],
                "usage_status_readable": True,
                "allowance_status": "available",
                "all_applicable_windows_reported": True,
                "included_allowance_only": True,
                "separately_purchased_credits_in_use": False,
                "api_billing_in_use": False,
                "pay_as_you_go_in_use": False,
                "add_ons_in_use": False,
                "plan_upgrade_in_progress": False,
                "billing_mode_changed": False,
                "quota_windows": [{
                    "id": "synthetic-weekly-window",
                    "used_percent": 25.0,
                    "status": "available",
                    "resets_at": self.autonomous.utc_text(observed + timedelta(hours=1)),
                }],
            },
        }
        compute["evidence_fingerprint"] = self.autonomous.digest(compute)
        compute_path = self.area / "subscription-status.json"
        write_json(compute_path, compute)
        usage = {
            "schema_version": self.autonomous.USAGE_SCHEMA,
            "artifact_kind": "autonomous_delivery_usage_state",
            "permission_grant": False,
            "authorization_record_digest": self.record["accepted_record_digest"],
            "run_id": "synthetic-source-effect",
            "counts": {key: 0 for key in self.autonomous.USAGE_KEYS},
            "compute_mode": "included_subscription",
            "compute_evidence_fingerprint": compute["evidence_fingerprint"],
            "metered_api_usage": None,
            "included_subscription_usage": {
                "maximum_used_percent": 25.0,
                "quota_window_ids": ["synthetic-weekly-window"],
            },
            "warnings": [],
            "exhausted": False,
            "observed_at": self.autonomous.utc_text(observed),
        }
        usage["usage_digest"] = self.autonomous.digest(usage)
        usage_path = self.area / "usage.json"
        write_json(usage_path, usage)
        projection = self.autonomous.work_completion_authorization(
            argparse.Namespace(
                authorization_record=str(self.record_path),
                confirmation_artifact=str(self.confirmation_path),
                cost_enforcement_artifact=str(compute_path),
                usage=str(usage_path),
                work_plan=str(plan_path),
                output=None,
            ),
            self.root,
        )
        receipt = self.completion.new_receipt(plan, projection)
        self.completion.authority_still_current(self.root, receipt, "fetch_remote")
        compute["valid_until"] = self.autonomous.utc_text(self.autonomous.utc_now() - timedelta(minutes=1))
        compute["evidence_fingerprint"] = self.autonomous.digest({key: value for key, value in compute.items() if key != "evidence_fingerprint"})
        write_json(compute_path, compute)
        with self.assertRaisesRegex(self.completion.FinishBlocked, "standing authorization is not current"):
            self.completion.authority_still_current(self.root, receipt, "fetch_remote")

    def test_source_integration_stops_until_candidate_matrix_is_recorded(self) -> None:
        plan = RUNNER.build_plan(self.root, self.task_path, self.record_path)
        receipt = self.completion.new_receipt(plan, self.authorization(plan))
        candidate = plan["expected_revisions"]["candidate_head"]
        receipt["revisions"]["commit"] = candidate
        receipt["pull_request"] = {
            "number": 91,
            "url": "https://example.invalid/pull/91",
            "state": "OPEN",
            "isDraft": False,
            "headRefName": plan["branches"]["task"],
            "baseRefName": plan["branches"]["default"],
            "headRefOid": candidate,
            "mergeStateStatus": "CLEAN",
            "reviewDecision": "",
            "mergedAt": None,
            "mergeCommit": None,
        }
        receipt["completed_operations"] = [
            "create_commit", "push_task_branch", "locate_or_open_pull_request",
            "observe_hosted_checks", "record_self_review",
        ]
        self.transaction.write_work_completion_receipt(self.root, receipt, create=True)
        with (
            mock.patch.object(self.completion, "ensure_plan_sources"),
            mock.patch.object(self.completion, "git_hook_observation", return_value=plan["git_hook_observation"]),
            mock.patch.object(self.completion, "dirty_state", return_value=([], [])),
            mock.patch.object(self.completion, "merge_pr") as merge_pr,
        ):
            with self.assertRaisesRegex(self.completion.FinishBlocked, "candidate full-matrix"):
                self.completion.execute(self.root, receipt)
        merge_pr.assert_not_called()
        now = datetime.now(timezone.utc)
        evidence = {
            "schema_version": "harness.source-candidate-matrix-validation.v1",
            "artifact_kind": "source_candidate_hosted_validation_evidence",
            "permission_grant": False,
            "receipt_id": receipt["receipt_id"],
            "plan_digest": receipt["plan_digest"],
            "candidate_revision": candidate,
            "pull_request_number": 91,
            "pull_request_head": candidate,
            "required_check": {"status": "pass", "run_ref": "external:synthetic-required-check"},
            "full_matrix": {"status": "pass", "run_ref": "external:synthetic-candidate-matrix", "expected_jobs": 24, "successful_jobs": 24},
            "observed_at": now.isoformat().replace("+00:00", "Z"),
            "evidence_refs": ["external:synthetic-required-check", "external:synthetic-candidate-matrix"],
            "limitations": ["Synthetic fixture only."],
        }
        evidence["evidence_digest"] = self.completion.digest(evidence)
        evidence_path = self.area / "candidate-matrix.json"
        write_json(evidence_path, evidence)
        self.assertEqual(self.validator.validate_schema(evidence, self.schema["$defs"]["source_candidate_matrix_validation"], root_schema=self.schema), [])
        result = self.completion.record_source_candidate_validation(self.root.resolve(), receipt, evidence_path.resolve())
        self.assertIn("record_candidate_matrix_validation", result["completed_operations"])
        incomplete = json.loads(json.dumps(evidence))
        incomplete["full_matrix"]["successful_jobs"] = 23
        incomplete["evidence_digest"] = self.completion.digest({key: value for key, value in incomplete.items() if key != "evidence_digest"})
        incomplete_path = self.area / "candidate-matrix-incomplete.json"
        write_json(incomplete_path, incomplete)
        with self.assertRaisesRegex(self.completion.FinishBlocked, "accounting is incomplete"):
            self.completion.record_source_candidate_validation(self.root.resolve(), receipt, incomplete_path.resolve())

    def test_source_cleanup_stops_until_post_merge_validation_is_recorded(self) -> None:
        plan = RUNNER.build_plan(self.root, self.task_path, self.record_path)
        receipt = self.completion.new_receipt(plan, self.authorization(plan))
        receipt["revisions"] = {"commit": plan["expected_revisions"]["candidate_head"], "integrated": "a" * 40, "synchronized_default": "a" * 40}
        receipt["completed_operations"] = ["create_commit", "push_task_branch", "locate_or_open_pull_request", "observe_hosted_checks", "record_self_review", "record_candidate_matrix_validation", "merge_pull_request", "synchronize_local_default_branch"]
        with (
            mock.patch.object(self.completion, "ensure_plan_sources"),
            mock.patch.object(self.completion, "git_hook_observation", return_value=plan["git_hook_observation"]),
            mock.patch.object(self.completion, "dirty_state", return_value=([], [])),
        ):
            with self.assertRaisesRegex(self.completion.FinishBlocked, "integrated-main validation"):
                self.completion.execute(self.root, receipt)
        receipt["completed_operations"].append("record_post_merge_validation")
        with (
            mock.patch.object(self.completion, "ensure_plan_sources"),
            mock.patch.object(self.completion, "git_hook_observation", return_value=plan["git_hook_observation"]),
            mock.patch.object(self.completion, "dirty_state", return_value=([], [])),
            mock.patch.object(self.completion, "delete_remote") as delete_remote,
            mock.patch.object(self.completion, "delete_local") as delete_local,
            mock.patch.object(self.completion, "record") as record,
        ):
            self.completion.execute(self.root, receipt)
        delete_remote.assert_called_once()
        delete_local.assert_called_once()
        record.assert_called_once()

    def test_default_sync_fetches_before_switching_to_a_predecessor_main(self) -> None:
        events: list[str] = []
        current_branch = ["chore/autonomous-source-test"]
        integrated = "a" * 40
        receipt = {
            "plan": {"branches": {"default": "main"}},
            "revisions": {"integrated": integrated},
        }

        def fake_git(_root: Path, *arguments: str) -> str:
            if arguments == ("symbolic-ref", "--short", "HEAD"):
                return current_branch[0]
            raise AssertionError(arguments)

        def fake_fetch(_root: Path, _receipt: dict[str, object], *, expected: str | None) -> str:
            self.assertIsNone(expected)
            self.assertEqual(current_branch[0], "chore/autonomous-source-test")
            events.append("fetch")
            return integrated

        def fake_run(_root: Path, argv: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
            del check, env
            if argv == ["git", "switch", "main"]:
                current_branch[0] = "main"
                events.append("switch")
                return subprocess.CompletedProcess(argv, 0, b"", b"")
            if argv[:3] == ["git", "merge-base", "--is-ancestor"]:
                return subprocess.CompletedProcess(argv, 0, b"", b"")
            raise AssertionError(argv)

        with (
            mock.patch.object(self.completion, "git", side_effect=fake_git),
            mock.patch.object(self.completion, "fetch_default", side_effect=fake_fetch),
            mock.patch.object(self.completion, "dirty_state", return_value=([], [])),
            mock.patch.object(self.completion, "run", side_effect=fake_run),
            mock.patch.object(self.completion, "revision", return_value=integrated),
            mock.patch.object(self.completion, "record"),
        ):
            self.completion.sync_default(self.root, receipt)
        self.assertEqual(events, ["fetch", "switch"])

    def test_post_merge_evidence_binds_exact_integrated_main_before_cleanup(self) -> None:
        plan = RUNNER.build_plan(self.root, self.task_path, self.record_path)
        now = datetime.now(timezone.utc)
        receipt = self.completion.new_receipt(plan, self.authorization(plan))
        git(self.root, "switch", "main")
        git(self.root, "merge", "--no-ff", "chore/autonomous-source-test", "-m", "merge: synthetic source candidate")
        integrated = git(self.root, "rev-parse", "HEAD")
        receipt["state"] = "default_branch_synchronized"
        receipt["revisions"] = {"commit": plan["expected_revisions"]["candidate_head"], "integrated": integrated, "synchronized_default": integrated}
        receipt["completed_operations"] = ["create_commit", "push_task_branch", "locate_or_open_pull_request", "observe_hosted_checks", "record_self_review", "record_candidate_matrix_validation", "merge_pull_request", "synchronize_local_default_branch"]
        self.transaction.write_work_completion_receipt(self.root, receipt, create=True)
        evidence = {
            "schema_version": "harness.source-post-merge-validation.v1",
            "artifact_kind": "source_integrated_main_validation_evidence",
            "permission_grant": False,
            "receipt_id": receipt["receipt_id"],
            "plan_digest": receipt["plan_digest"],
            "integrated_revision": integrated,
            "tested_main_revision": integrated,
            "automatic_main_check": {"status": "pass", "run_ref": "external:synthetic-main-check"},
            "full_matrix": {"status": "pass", "run_ref": "external:synthetic-full-matrix", "expected_jobs": 24, "successful_jobs": 24},
            "observed_at": now.isoformat().replace("+00:00", "Z"),
            "evidence_refs": ["external:synthetic-main-check", "external:synthetic-full-matrix"],
            "limitations": ["Synthetic fixture only."],
        }
        evidence["evidence_digest"] = self.completion.digest(evidence)
        evidence_path = self.area / "post-merge.json"
        write_json(evidence_path, evidence)
        self.assertEqual(self.validator.validate_schema(evidence, self.schema["$defs"]["source_post_merge_validation"], root_schema=self.schema), [])
        result = self.completion.record_source_post_merge_validation(self.root.resolve(), receipt, evidence_path.resolve())
        self.assertIn("record_post_merge_validation", result["completed_operations"])
        corrupted = dict(evidence)
        corrupted["tested_main_revision"] = "f" * 40
        corrupted["evidence_digest"] = self.completion.digest({key: value for key, value in corrupted.items() if key != "evidence_digest"})
        corrupted_path = self.area / "post-merge-corrupt.json"
        write_json(corrupted_path, corrupted)
        with self.assertRaisesRegex(self.completion.FinishBlocked, "another receipt or integrated revision"):
            self.completion.record_source_post_merge_validation(self.root.resolve(), result, corrupted_path.resolve())
        incomplete = json.loads(json.dumps(evidence))
        incomplete["full_matrix"]["successful_jobs"] = 23
        incomplete["evidence_digest"] = self.completion.digest({key: value for key, value in incomplete.items() if key != "evidence_digest"})
        incomplete_path = self.area / "post-merge-incomplete.json"
        write_json(incomplete_path, incomplete)
        with self.assertRaisesRegex(self.completion.FinishBlocked, "accounting is incomplete"):
            self.completion.record_source_post_merge_validation(self.root.resolve(), result, incomplete_path.resolve())


if __name__ == "__main__":
    unittest.main(verbosity=2)
