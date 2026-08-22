#!/usr/bin/env python3
"""Interruption and monotonic-effect safety coverage for autonomous delivery."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_ROOT = Path(__file__).resolve().parent
RUNTIME_SOURCE = SCRIPT_ROOT.parent / "assets/packages/autonomous-delivery/templates/.agent/capabilities/autonomous-delivery/delivery_runtime.py.tmpl"
MUTATIONS = SCRIPT_ROOT.parent / "fixtures/autonomous-delivery/invalid-mutations.json"


def load_runtime(name: str):
    import types
    module = types.ModuleType(name)
    module.__file__ = str(RUNTIME_SOURCE)
    exec(compile(RUNTIME_SOURCE.read_text(encoding="utf-8"), str(RUNTIME_SOURCE), "exec"), module.__dict__)
    return module


class AutonomousDeliveryFaultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="octon-autonomous-effects-")
        self.area = Path(self.temporary.name)
        self.root = self.area / "project"
        self.root.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, capture_output=True, check=True)
        (self.root / ".agent").mkdir()
        self.runtime = load_runtime("octon_autonomous_delivery_fault_runtime")
        self.projection = {
            "projection_digest": "a" * 64,
            "action": "push_tag",
        }
        self.plan = {
            "schema_version": self.runtime.PLAN_SCHEMA,
            "artifact_kind": "autonomous_delivery_effect_plan",
            "permission_grant": False,
            "read_only": True,
            "action": "push_tag",
            "projection_digest": "a" * 64,
            "delivery_plan_digest": "b" * 64,
            "repository_identity": "synthetic/repository",
            "default_branch": "main",
            "remote": "origin",
            "expected_commit": "c" * 40,
            "tag": "v9.9.9",
            "workflow": None,
            "operation_argv": ["git", "push", "--no-follow-tags", "origin", "refs/tags/v9.9.9:refs/tags/v9.9.9"],
            "external_effect": True,
            "unknown_outcome_retries": 0,
            "rollback": "local_tag_may_be_deleted_only_before_publication_other_effects_are_monotonic_fix_forward",
            "limitations": [
                "This exact plan is non-authorizing and must be revalidated against current standing authorization.",
                "An attempted effect without decisive read-back becomes outcome_unknown and is never replayed automatically.",
            ],
        }
        self.plan["canonical_plan_digest"] = self.runtime.digest(self.plan)
        self.plan_path = self.area / "plan.json"
        self.plan_path.write_text(json.dumps(self.plan, sort_keys=True) + "\n", encoding="utf-8")
        self.base_args = argparse.Namespace(
            plan=str(self.plan_path),
            accept_digest=self.plan["canonical_plan_digest"],
            projection=str(self.area / "projection.json"),
            authorization_record=str(self.area / "record.json"),
            confirmation_artifact=str(self.area / "confirmation.json"),
            cost_enforcement_artifact=str(self.area / "cost.json"),
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def completed_process(self, returncode: int = 0) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(self.plan["operation_argv"], returncode, b"", b"")

    def receipt_id(self) -> str:
        receipt_root = self.runtime.receipt_root(self.root)
        values = sorted(path.name for path in receipt_root.iterdir() if path.is_dir())
        self.assertEqual(len(values), 1)
        return values[0]

    def test_interruption_after_effect_never_replays_and_resume_uses_readback(self) -> None:
        observations = [
            {"observation": "known", "refs": {}},
        ]
        calls = 0

        def invoke(_root, _argv, check=True):
            nonlocal calls
            if _argv == self.plan["operation_argv"]:
                calls += 1
                return self.completed_process()
            return subprocess.CompletedProcess(_argv, 0, b".git\n", b"")

        def interrupt(phase: str) -> None:
            if phase == "after_external_effect_before_readback":
                raise RuntimeError("synthetic interruption after external effect")

        with (
            mock.patch.object(self.runtime, "validate_runtime_authority", return_value=(object(), self.projection)),
            mock.patch.object(self.runtime, "require_clean_main"),
            mock.patch.object(self.runtime, "observe", side_effect=observations),
            mock.patch.object(self.runtime, "run", side_effect=invoke),
            mock.patch.object(self.runtime, "INTERRUPTION_HOOK", side_effect=interrupt),
        ):
            with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                self.runtime.apply_effect(self.base_args, self.root)
        self.assertEqual(calls, 1)
        receipt_id = self.receipt_id()
        history = self.runtime.receipt_sequence(self.root, receipt_id)
        self.assertEqual(history[-1]["state"], "attempted")

        resume_args = argparse.Namespace(**vars(self.base_args), receipt_id=receipt_id)
        satisfied = {"observation": "known", "refs": {"refs/tags/v9.9.9^{}": "c" * 40}}
        replayed: list[list[str]] = []
        def resume_run(_root, argv, check=True):
            if argv == self.plan["operation_argv"]:
                replayed.append(argv)
            return subprocess.CompletedProcess(argv, 0, b".git\n", b"")
        with (
            mock.patch.object(self.runtime, "validate_runtime_authority", return_value=(object(), self.projection)),
            mock.patch.object(self.runtime, "observe", return_value=satisfied),
            mock.patch.object(self.runtime, "run", side_effect=resume_run),
        ):
            result = self.runtime.resume_effect(resume_args, self.root)
        self.assertFalse(replayed)
        self.assertEqual(result["state"], "completed")
        self.assertEqual(self.runtime.receipt_sequence(self.root, receipt_id)[-1]["outcome"], "completed")

    def test_unknown_readback_stops_with_zero_retry(self) -> None:
        observations = [
            {"observation": "known", "refs": {}},
            {"observation": "unknown"},
        ]
        effect_invocations: list[list[str]] = []
        def invoke(_root, argv, check=True):
            if argv == self.plan["operation_argv"]:
                effect_invocations.append(argv)
                return self.completed_process()
            return subprocess.CompletedProcess(argv, 0, b".git\n", b"")
        with (
            mock.patch.object(self.runtime, "validate_runtime_authority", return_value=(object(), self.projection)),
            mock.patch.object(self.runtime, "require_clean_main"),
            mock.patch.object(self.runtime, "observe", side_effect=observations),
            mock.patch.object(self.runtime, "run", side_effect=invoke),
        ):
            with self.assertRaisesRegex(self.runtime.RuntimeBlocked, "outcome is unknown"):
                self.runtime.apply_effect(self.base_args, self.root)
        self.assertEqual(len(effect_invocations), 1)
        receipt_id = self.receipt_id()
        self.assertEqual(self.runtime.receipt_sequence(self.root, receipt_id)[-1]["state"], "outcome_unknown")
        resume_args = argparse.Namespace(**vars(self.base_args), receipt_id=receipt_id)
        replayed: list[list[str]] = []
        def resume_run(_root, argv, check=True):
            if argv == self.plan["operation_argv"]:
                replayed.append(argv)
            return subprocess.CompletedProcess(argv, 0, b".git\n", b"")
        with (
            mock.patch.object(self.runtime, "validate_runtime_authority", return_value=(object(), self.projection)),
            mock.patch.object(self.runtime, "observe", return_value={"observation": "unknown"}),
            mock.patch.object(self.runtime, "run", side_effect=resume_run),
        ):
            with self.assertRaisesRegex(self.runtime.RuntimeBlocked, "zero automatic retries"):
                self.runtime.resume_effect(resume_args, self.root)
        self.assertFalse(replayed)

    def test_corrupt_or_noncontiguous_receipt_history_is_rejected(self) -> None:
        # Path arithmetic is kept explicit because a malformed receipt identity
        # must never be interpreted as a filesystem operation.
        root = self.runtime.receipt_root(self.root) / ("ADER-" + "a" * 24)
        root.mkdir()
        (root / "0002.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(self.runtime.RuntimeBlocked, "malformed or noncontiguous"):
            self.runtime.receipt_sequence(self.root, root.name)

    def test_closed_adapter_has_no_force_deploy_purchase_or_message_operation(self) -> None:
        forbidden = {
            "force_push", "push_default_branch", "deploy", "publish_package",
            "purchase", "message", "change_repository_settings", "move_tag",
        }
        self.assertFalse(forbidden & self.runtime.SUPPORTED)
        self.assertEqual(self.plan["unknown_outcome_retries"], 0)

    def test_source_release_requires_exact_remote_tag_target(self) -> None:
        release_plan = dict(self.plan)
        release_plan.update(action="create_github_release", tag="v9.9.9")
        wrong = {
            "observation": "known",
            "remote_refs": {"refs/tags/v9.9.9^{}": "d" * 40},
            "release": {"tagName": "v9.9.9", "isDraft": False, "isPrerelease": False},
        }
        exact = {
            **wrong,
            "remote_refs": {"refs/tags/v9.9.9^{}": "c" * 40},
        }
        self.assertFalse(self.runtime.effect_satisfied(release_plan, wrong))
        self.assertTrue(self.runtime.effect_satisfied(release_plan, exact))

    def test_invalid_mutation_inventory_covers_every_hard_deny(self) -> None:
        value = json.loads(MUTATIONS.read_text(encoding="utf-8"), object_pairs_hook=self.runtime.duplicate_pairs)
        ids = {item["id"] for item in value["cases"]}
        self.assertTrue({
            "profile-silent-selection", "flag-authority", "changed-contract",
            "worker-control-write", "expired-authority", "revoked-authority",
            "emergency-stop", "unknown-cost-zero", "direct-spending",
            "force-push", "direct-main-push", "threshold-weakening",
            "tag-movement", "credential-forwarding", "deployment",
            "package-publication", "external-project", "communication",
            "purchase", "ambiguous-replay",
        } <= ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
