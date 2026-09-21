#!/usr/bin/env python3
"""Source-repository coverage for the closed autonomous-delivery effect adapter."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
RUNNER_PATH = SCRIPT_ROOT / "source_delivery_effect.py"


def load_python(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SOURCE = load_python(RUNNER_PATH, "octon_source_delivery_effect_tests")


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class SourceDeliveryEffectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="octon-source-delivery-effect-")
        self.area = Path(self.temporary.name)
        self.root = self.area / "source"
        subprocess.run(["git", "init", "-b", "main", str(self.root)], capture_output=True, check=True)
        git(self.root, "config", "user.name", "Synthetic Source Worker")
        git(self.root, "config", "user.email", "synthetic@example.invalid")
        (self.root / "octon.json").write_text("{}\n", encoding="utf-8")
        (self.root / "VERSION").write_text("4.2.0\n", encoding="utf-8")
        (self.root / "subject.txt").write_text("base\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "chore: synthetic source base")
        self.main_revision = git(self.root, "rev-parse", "HEAD")
        git(self.root, "switch", "-c", "chore/autonomous-source-effect")
        (self.root / "subject.txt").write_text("candidate\n", encoding="utf-8")
        git(self.root, "add", "subject.txt")
        git(self.root, "commit", "-m", "feat: synthetic source candidate")
        self.candidate = git(self.root, "rev-parse", "HEAD")
        self.core, self.runtime = SOURCE.modules()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def projection(self, action: str) -> dict[str, object]:
        value = {
            "action": action,
            "plan_digest": "a" * 64,
            "repository_identity": "cooperonlineenterprises/octon-mini",
            "task_branch": "chore/autonomous-source-effect",
        }
        value["projection_digest"] = self.runtime.digest(value)
        return value

    def arguments(self, projection_path: Path, action: str, branch: str, commit: str) -> argparse.Namespace:
        return argparse.Namespace(
            projection=str(projection_path),
            action=action,
            delivery_plan_digest="a" * 64,
            default_branch=branch,
            remote="origin",
            commit=commit,
            tag=None,
            message=None,
            workflow="validate.yml" if action == "dispatch_hosted_workflow" else None,
            release_title=None,
            release_notes=None,
            output=None,
        )

    def test_source_adapter_is_closed_and_owns_no_work_completion_operation(self) -> None:
        self.assertEqual(
            self.runtime.SUPPORTED,
            {"dispatch_hosted_workflow", "create_annotated_tag", "push_tag", "create_github_release"},
        )
        forbidden = {"create_commit", "push_branch", "open_pull_request", "observe_change_checks", "merge_pull_request", "delete_remote_branch"}
        self.assertFalse(forbidden & self.runtime.SUPPORTED)

    def test_candidate_dispatch_binds_exact_task_branch_and_commit_read_only(self) -> None:
        projection_path = self.area / "projection.json"
        write_json(projection_path, self.projection("dispatch_hosted_workflow"))
        args = self.arguments(projection_path, "dispatch_hosted_workflow", "chore/autonomous-source-effect", self.candidate)
        before = git(self.root, "status", "--porcelain=v1")
        plan = SOURCE.source_plan(args, self.root, self.runtime)
        self.assertEqual(plan["default_branch"], "chore/autonomous-source-effect")
        self.assertEqual(plan["expected_commit"], self.candidate)
        self.assertEqual(plan["operation_argv"], ["gh", "workflow", "run", "validate.yml", "--ref", "chore/autonomous-source-effect"])
        self.assertFalse(self.runtime.effect_satisfied(plan, {"observation": "known", "runs": [{"event": "workflow_dispatch", "headSha": self.main_revision}]}))
        self.assertTrue(self.runtime.effect_satisfied(plan, {"observation": "known", "runs": [{"event": "workflow_dispatch", "headSha": self.candidate}]}))
        self.assertEqual(plan["canonical_plan_digest"], self.runtime.digest({key: value for key, value in plan.items() if key != "canonical_plan_digest"}))
        self.assertEqual(git(self.root, "status", "--porcelain=v1"), before)
        wrong_branch = self.arguments(projection_path, "dispatch_hosted_workflow", "main", self.candidate)
        with self.assertRaisesRegex(SOURCE.SourceEffectError, "differs from the exact execution branch"):
            SOURCE.source_plan(wrong_branch, self.root, self.runtime)
        wrong_commit = self.arguments(projection_path, "dispatch_hosted_workflow", "chore/autonomous-source-effect", self.main_revision)
        with self.assertRaisesRegex(SOURCE.SourceEffectError, "differs from the exact execution branch"):
            SOURCE.source_plan(wrong_commit, self.root, self.runtime)

    def test_post_merge_dispatch_requires_exact_integrated_receipt(self) -> None:
        git(self.root, "switch", "main")
        git(self.root, "merge", "--no-ff", "chore/autonomous-source-effect", "-m", "merge: synthetic candidate")
        integrated = git(self.root, "rev-parse", "HEAD")
        common = Path(git(self.root, "rev-parse", "--git-common-dir"))
        common = common if common.is_absolute() else self.root / common
        receipt_directory = common / "octon-mini/work-completion/receipts"
        receipt_directory.mkdir(parents=True)
        receipt = {
            "schema_version": "harness.work-completion-receipt.v1",
            "artifact_kind": "work_completion_receipt",
            "permission_grant": False,
            "receipt_id": "WCR-" + "a" * 24,
            "plan_digest": "a" * 64,
            "plan": {
                "schema_version": "harness.source-work-completion-plan.v1",
                "canonical_plan_digest": "a" * 64,
                "branches": {"default": "main"},
                "expected_revisions": {"candidate_head": self.candidate},
            },
            "revisions": {
                "commit": self.candidate,
                "integrated": integrated,
                "synchronized_default": integrated,
            },
            "completed_operations": [
                "record_candidate_matrix_validation",
                "merge_pull_request",
                "synchronize_local_default_branch",
            ],
        }
        receipt_path = receipt_directory / f"{receipt['receipt_id']}.json"
        write_json(receipt_path, receipt)
        projection_path = self.area / "post-merge-projection.json"
        write_json(projection_path, self.projection("dispatch_hosted_workflow"))
        args = self.arguments(projection_path, "dispatch_hosted_workflow", "main", integrated)
        plan = SOURCE.source_plan(args, self.root, self.runtime)
        self.assertEqual(plan["default_branch"], "main")
        self.assertEqual(plan["expected_commit"], integrated)
        self.assertEqual(plan["operation_argv"], ["gh", "workflow", "run", "validate.yml", "--ref", "main"])
        receipt["revisions"]["synchronized_default"] = self.main_revision
        write_json(receipt_path, receipt)
        with self.assertRaisesRegex(SOURCE.SourceEffectError, "integrated work-completion receipt"):
            SOURCE.source_plan(args, self.root, self.runtime)

    def test_release_effects_require_main(self) -> None:
        git(self.root, "switch", "main")
        projection_path = self.area / "tag-projection.json"
        projection = self.projection("create_annotated_tag")
        write_json(projection_path, projection)
        args = self.arguments(projection_path, "create_annotated_tag", "main", self.main_revision)
        args.tag = "v4.2.0"
        args.message = "Synthetic source release"
        plan = SOURCE.source_plan(args, self.root, self.runtime)
        self.assertEqual(plan["default_branch"], "main")
        self.assertEqual(plan["operation_argv"], ["git", "tag", "-a", "v4.2.0", self.main_revision, "-m", "Synthetic source release"])
        args.default_branch = "chore/autonomous-source-effect"
        with self.assertRaisesRegex(SOURCE.SourceEffectError, "wrong execution branch"):
            SOURCE.source_plan(args, self.root, self.runtime)

    def test_cli_plan_is_deterministic_and_target_read_only(self) -> None:
        projection_path = self.area / "cli-projection.json"
        output_path = self.area / "effect-plan.json"
        write_json(projection_path, self.projection("dispatch_hosted_workflow"))
        argv = [
            sys.executable, "-B", str(RUNNER_PATH), "--target", str(self.root), "plan",
            "--projection", str(projection_path), "--action", "dispatch_hosted_workflow",
            "--delivery-plan-digest", "a" * 64, "--default-branch", "chore/autonomous-source-effect",
            "--commit", self.candidate, "--workflow", "validate.yml", "--output", str(output_path),
        ]
        before = git(self.root, "status", "--porcelain=v1")
        result = subprocess.run(argv, cwd=self.area, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertTrue(output_path.is_file())
        self.assertEqual(git(self.root, "status", "--porcelain=v1"), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
