#!/usr/bin/env python3
"""Installation, adoption, disable, update, tamper, and removal coverage."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import test_long_running_work as functional


class LongRunningWorkPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = functional.LongRunningWorkTests("test_absent_package_refuses_with_continuation_and_no_change")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    @property
    def target(self) -> Path:
        return self.fixture.target

    def install_only(self) -> tuple[str, Path]:
        functional.accepted_decision(self.target, "DEC-9001")
        plan_path = self.target / ".agent/transactions/plans/long-work-package.json"
        result = functional.run(
            [
                sys.executable, "-B", str(functional.PACKAGE), "plan",
                "--target", str(self.target), "--package", "long-running-work",
                "--owner", "synthetic-program-operator", "--trust-decision-ref", "DEC-9001",
                "--assess-applicable", "--output", str(plan_path),
            ],
            functional.REPO_ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        result = functional.run(
            [sys.executable, "-B", str(functional.PACKAGE), "apply", "--target", str(self.target), "--plan", str(plan_path), "--accept-digest", plan["canonical_plan_digest"]],
            functional.REPO_ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return plan["canonical_plan_digest"], plan_path

    def test_exact_pristine_update_receipt_remains_valid(self) -> None:
        self.install_only()
        registry_path = self.target / ".agent/packages.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        installed = next(item for item in registry["packages"] if item["id"] == "long-running-work")
        installed["version"] = "0.9.0"
        installed["sha256"] = "0" * 64
        functional.write_json(registry_path, registry)
        update_path = self.target / ".agent/transactions/plans/long-work-update.json"
        planned = functional.run(
            [
                sys.executable, "-B", str(functional.PACKAGE), "plan", "--target", str(self.target),
                "--package", "long-running-work", "--owner", "synthetic-program-operator",
                "--trust-decision-ref", "DEC-9001", "--update", "--output", str(update_path),
            ],
            functional.REPO_ROOT,
        )
        self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
        update = json.loads(update_path.read_text(encoding="utf-8"))
        applied = functional.run(
            [sys.executable, "-B", str(functional.PACKAGE), "apply", "--target", str(self.target), "--plan", str(update_path), "--accept-digest", update["canonical_plan_digest"]],
            functional.REPO_ROOT,
        )
        self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
        checked = self.fixture.octon("check")
        self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)

    def test_installed_but_unadopted_package_cannot_compile_task_context(self) -> None:
        self.install_only()
        functional.task_and_evidence(self.target)
        context = self.fixture.octon(
            "work", "run", "context", "--task-id", "TASK-0001",
            "--max-bytes", "65536", "--max-items", "16", "--json",
        )
        self.assertEqual(context.returncode, 2)
        self.assertIn("no project-owned adoption record", context.stderr)

    def test_tampered_payload_blocks_update(self) -> None:
        self.install_only()
        entrypoint = self.target / ".agent/capabilities/long-running-work/long_work.py"
        entrypoint.write_text(entrypoint.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
        plan_path = self.target / ".agent/transactions/plans/tampered-update.json"
        planned = functional.run(
            [
                sys.executable, "-B", str(functional.PACKAGE), "plan", "--target", str(self.target),
                "--package", "long-running-work", "--owner", "synthetic-program-operator",
                "--trust-decision-ref", "DEC-9001", "--update", "--output", str(plan_path),
            ],
            functional.REPO_ROOT,
        )
        self.assertNotEqual(planned.returncode, 0)
        self.assertIn("differs from its recorded baseline", planned.stderr)

    def test_unregistered_payload_and_run_state_paths_are_rejected(self) -> None:
        self.install_only()
        extra_payload = self.target / ".agent/capabilities/long-running-work/extra.py"
        extra_payload.write_text("raise SystemExit('must not execute')\n", encoding="utf-8")
        checked = self.fixture.octon("check")
        self.assertNotEqual(checked.returncode, 0)
        self.assertIn("unregistered capability payload path", checked.stdout + checked.stderr)
        extra_payload.unlink()
        # Installation remains unadopted here; an unregistered state path must still fail.
        state_root = self.target / ".agent/work-runs"
        state_root.mkdir(exist_ok=True)
        extra_state = state_root / "mutable-summary.json"
        extra_state.write_text("{}\n", encoding="utf-8")
        checked = self.fixture.octon("check")
        self.assertNotEqual(checked.returncode, 0)
        self.assertIn("unregistered work-run state path", checked.stdout + checked.stderr)

    def test_unused_package_can_be_removed_and_dispatch_returns_to_dormant(self) -> None:
        self.install_only()
        remove_path = self.target / ".agent/transactions/plans/long-work-remove.json"
        planned = functional.run(
            [
                sys.executable, "-B", str(functional.PACKAGE), "plan", "--target", str(self.target),
                "--package", "long-running-work", "--owner", "synthetic-program-operator",
                "--trust-decision-ref", "DEC-9001", "--remove", "--output", str(remove_path),
            ],
            functional.REPO_ROOT,
        )
        self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
        plan = json.loads(remove_path.read_text(encoding="utf-8"))
        applied = functional.run(
            [sys.executable, "-B", str(functional.PACKAGE), "apply", "--target", str(self.target), "--plan", str(remove_path), "--accept-digest", plan["canonical_plan_digest"]],
            functional.REPO_ROOT,
        )
        self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
        checked = self.fixture.octon("check")
        self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)
        absent = self.fixture.octon("work", "run", "status", "--json")
        self.assertEqual(absent.returncode, 2)
        self.assertIn("OCTON-LRW-1000", absent.stderr)

    def test_active_run_blocks_disable(self) -> None:
        self.fixture.install_and_enable()
        self.fixture.start()
        planned = self.fixture.octon(
            "work", "run", "configure", "plan", "--status", "disabled",
            "--decision-ref", "DEC-9001", "--owner", "synthetic-program-operator",
            "--output", ".agent/transactions/plans/disable.json",
        )
        self.assertEqual(planned.returncode, 2)
        self.assertIn("disable refuses", planned.stderr)

    def test_paused_run_can_be_disabled_without_erasing_recovery_state(self) -> None:
        self.fixture.install_and_enable()
        run_id = str(self.fixture.start()["run_id"])
        paused = self.fixture.octon(
            "work", "run", "pause", "--run-id", run_id,
            "--reason", "synthetic safe deactivation",
        )
        self.assertEqual(paused.returncode, 0, paused.stderr or paused.stdout)
        plan_path = ".agent/transactions/plans/disable.json"
        planned = self.fixture.octon(
            "work", "run", "configure", "plan", "--status", "disabled",
            "--decision-ref", "DEC-9001", "--owner", "synthetic-program-operator",
            "--output", plan_path,
        )
        self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
        plan = json.loads((self.target / plan_path).read_text(encoding="utf-8"))
        applied = self.fixture.octon(
            "work", "run", "configure", "apply", "--plan", plan_path,
            "--accept-digest", plan["canonical_plan_digest"],
        )
        self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
        adoption = json.loads((self.target / ".agent/work-runs/adoption.json").read_text(encoding="utf-8"))
        self.assertEqual(adoption["status"], "disabled")
        self.assertTrue((self.target / f".agent/work-runs/runs/{run_id}/run.json").is_file())

    def test_install_is_supported_but_inactive_in_all_profiles(self) -> None:
        area = self.target.parent
        for number, profile in enumerate(("minimal", "standard", "high-assurance"), 9100):
            with self.subTest(profile=profile):
                target = area / f"profile-{profile}"
                generated = functional.run(
                    [sys.executable, "-B", str(functional.SCAFFOLDER), "--target", str(target), "--project-name", f"{profile} fixture", "--profile", profile],
                    functional.REPO_ROOT,
                )
                self.assertEqual(generated.returncode, 0, generated.stderr or generated.stdout)
                decision = f"DEC-{number}"
                functional.accepted_decision(target, decision)
                plan_path = target / ".agent/transactions/plans/package.json"
                planned = functional.run(
                    [sys.executable, "-B", str(functional.PACKAGE), "plan", "--target", str(target), "--package", "long-running-work", "--owner", "synthetic-program-operator", "--trust-decision-ref", decision, "--assess-applicable", "--output", str(plan_path)],
                    functional.REPO_ROOT,
                )
                self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                applied = functional.run(
                    [sys.executable, "-B", str(functional.PACKAGE), "apply", "--target", str(target), "--plan", str(plan_path), "--accept-digest", plan["canonical_plan_digest"]],
                    functional.REPO_ROOT,
                )
                self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
                self.assertFalse((target / ".agent/work-runs/adoption.json").exists())
                checked = functional.run([sys.executable, "-I", "-B", "octon", "check"], target)
                self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
