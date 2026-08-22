#!/usr/bin/env python3
"""Offline payload, profile, and package-boundary coverage."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import test_autonomous_delivery as functional


class AutonomousDeliveryPackageTests(unittest.TestCase):
    def test_setup_catalog_advertises_delivery_in_every_mode_without_collecting_authority(self) -> None:
        catalog = json.loads((functional.REPO_ROOT / "shared/source-contracts/setup-questions.json").read_text(encoding="utf-8"))
        by_id = {item["id"]: item for item in catalog["questions"]}
        profile = by_id["setup.autonomous-delivery-profile"]
        self.assertEqual(set(profile["modes"]), {"initialization", "adoption", "upgrade"})
        self.assertIn("available but externally locked", profile["prompt"])
        self.assertEqual(profile["recommendation"]["rule"], "recommend fast_delivery for most solo developers without selecting it")
        authorization = by_id["setup.autonomous-delivery-authorization"]
        self.assertEqual(authorization["information_role"], "runtime_authorization_forbidden")
        self.assertIn("a command-line flag cannot confirm authority", authorization["validation_rules"])

    def test_all_profiles_include_locked_network_free_activation_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-autonomous-profiles-") as temporary:
            area = Path(temporary)
            for profile in ("minimal", "standard", "high-assurance"):
                with self.subTest(profile=profile):
                    target = area / profile
                    generated = functional.run(
                        [sys.executable, "-B", str(functional.SCAFFOLDER), "--target", str(target), "--project-name", f"{profile} autonomous fixture", "--profile", profile],
                        functional.REPO_ROOT,
                    )
                    self.assertEqual(generated.returncode, 0, generated.stderr or generated.stdout)
                    project = json.loads((target / ".agent/project.json").read_text(encoding="utf-8"))
                    registry = json.loads((target / ".agent/packages.json").read_text(encoding="utf-8"))
                    self.assertEqual(project["autonomous_delivery"]["status"], "available_not_activated")
                    self.assertEqual(project["autonomous_delivery"]["write_capability"], "locked")
                    self.assertEqual(project["autonomous_delivery"]["external_effects"], "locked")
                    self.assertIsNone(project["autonomous_delivery"]["delivery_profile"])
                    self.assertEqual(project["packages"]["trigger_assessments"]["autonomous_delivery"], "not_assessed")
                    self.assertFalse(registry["packages"])
                    self.assertTrue((target / ".agent/available-packages/autonomous-delivery/payload/.agent/capabilities/autonomous-delivery/delivery_runtime.py").is_file())
                    self.assertTrue((target / ".agent/available-packages/long-running-work/payload/.agent/capabilities/long-running-work/long_work.py").is_file())

    def test_payload_tamper_after_plan_blocks_activation(self) -> None:
        fixture = functional.AutonomousDeliveryTests("test_pre_activation_surfaces_are_read_only_and_hook_free")
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        record_path, confirmation_path, cost_path, _ = fixture.accepted_records()
        planned = fixture.octon(
            "delivery", "activate", "plan",
            "--authorization-record", str(record_path),
            "--confirmation-artifact", str(confirmation_path),
            "--cost-enforcement-artifact", str(cost_path),
            "--adoption-decision-ref", "DEC-9100",
        )
        self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
        plan = json.loads(planned.stdout)
        plan_path = fixture.area / "activation-plan.json"
        functional.write_json(plan_path, plan)
        payload = fixture.target / ".agent/available-packages/autonomous-delivery/payload/.agent/capabilities/autonomous-delivery/README.md"
        payload.write_text(payload.read_text(encoding="utf-8") + "\nTampered.\n", encoding="utf-8")
        applied = fixture.octon(
            "delivery", "activate", "apply",
            "--plan", str(plan_path), "--accept-digest", plan["canonical_plan_digest"],
            "--authorization-record", str(record_path),
            "--confirmation-artifact", str(confirmation_path),
            "--cost-enforcement-artifact", str(cost_path),
        )
        self.assertEqual(applied.returncode, 2)
        self.assertIn("offline package payload digest differs", applied.stderr)

    def test_delivery_profile_is_independent_from_assurance_and_collaboration(self) -> None:
        fixture = functional.AutonomousDeliveryTests("test_profile_recommendation_never_selects_or_activates")
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        project = json.loads((fixture.target / ".agent/project.json").read_text(encoding="utf-8"))
        before_profile = project["project"]["profile"]
        before_collaboration = project["collaboration_profile"]
        for delivery_profile in ("review_first", "balanced_autonomous", "fast_delivery", "custom"):
            result = fixture.octon("delivery", "activation-preview", "--profile", delivery_profile)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        after = json.loads((fixture.target / ".agent/project.json").read_text(encoding="utf-8"))
        self.assertEqual(after["project"]["profile"], before_profile)
        self.assertEqual(after["collaboration_profile"], before_collaboration)


if __name__ == "__main__":
    unittest.main(verbosity=2)
