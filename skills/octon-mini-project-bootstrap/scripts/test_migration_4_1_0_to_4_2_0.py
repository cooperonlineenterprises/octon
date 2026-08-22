#!/usr/bin/env python3
"""Same-product 4.1.0 to 4.2.0 autonomous-delivery migration coverage."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import test_long_running_work as functional
import test_migration_4_0_0_to_4_1_0 as previous


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parents[2]
UPGRADER = SCRIPT_ROOT / "upgrade_project.py"


def tree_digest(root: Path) -> str:
    value = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            value.update(path.relative_to(root).as_posix().encode("utf-8"))
            value.update(b"\0")
            value.update(path.read_bytes())
            value.update(b"\0")
    return value.hexdigest()


class Migration410To420Tests(unittest.TestCase):
    def test_released_snapshot_gains_locked_offline_delivery_surface_only(self) -> None:
        if not (REPO_ROOT / ".git").exists():
            self.skipTest("annotated v4.1.0 source tag is unavailable in an installed source bundle")
        with tempfile.TemporaryDirectory(prefix="octon-mini-migration-410-420-") as temporary:
            area = Path(temporary)
            old_source = previous.extract_release(area, "v4.1.0")
            target = area / "project"
            generated = previous.run(
                [
                    sys.executable, "-B",
                    str(old_source / "skills/octon-mini-project-bootstrap/scripts/scaffold_project.py"),
                    "--target", str(target), "--project-name", "Autonomous Migration Fixture",
                    "--profile", "standard",
                ],
                old_source,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr or generated.stdout)
            functional.task_and_evidence(target)
            before = tree_digest(target)

            proposal_path = area / "proposal.json"
            proposal_result = previous.run(
                [
                    sys.executable, "-B", str(UPGRADER), "plan", "--target", str(target),
                    "--authority-source", "authority:synthetic-migration-operator",
                    "--evidence-ref", "EVD-0001", "--output", str(proposal_path),
                ],
                REPO_ROOT,
            )
            self.assertEqual(proposal_result.returncode, 3, proposal_result.stderr or proposal_result.stdout)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            self.assertEqual((proposal["from_version"], proposal["to_version"]), ("4.1.0", "4.2.0"))
            review_path = area / "review.json"
            dispositions = []
            for row in proposal["classifications"]:
                if row["automatic"]:
                    continue
                allowed = row["allowed_dispositions"]
                disposition = "accept_candidate" if "accept_candidate" in allowed else "delete" if "delete" in allowed else "preserve_current"
                dispositions.append({"id": row["id"], "disposition": disposition, "rationale": "Synthetic reviewed 4.1 to 4.2 migration."})
            previous.write_json(review_path, {
                "schema_version": "octon-mini.bootstrap.upgrade-review.v1",
                "permission_grant": False,
                "proposal_digest": proposal["canonical_proposal_digest"],
                "dispositions": dispositions,
                "limitations": ["Synthetic migration review only."],
            })
            plan_path = area / "plan.json"
            planned = previous.run(
                [
                    sys.executable, "-B", str(UPGRADER), "plan", "--target", str(target),
                    "--authority-source", "authority:synthetic-migration-operator",
                    "--evidence-ref", "EVD-0001", "--proposal", str(proposal_path),
                    "--review", str(review_path), "--output", str(plan_path),
                ],
                REPO_ROOT,
            )
            self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            applied = previous.run(
                [sys.executable, "-B", str(UPGRADER), "apply", "--target", str(target), "--plan", str(plan_path), "--accept-digest", plan["canonical_plan_digest"]],
                REPO_ROOT,
            )
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
            origin = json.loads((target / ".octon-mini-origin.json").read_text(encoding="utf-8"))
            project = json.loads((target / ".agent/project.json").read_text(encoding="utf-8"))
            packages = json.loads((target / ".agent/packages.json").read_text(encoding="utf-8"))
            self.assertEqual(origin["octon_mini_version"], "4.2.0")
            self.assertEqual(project["schema_version"], "harness.project.v8")
            self.assertEqual(project["autonomous_delivery"]["status"], "available_not_activated")
            self.assertEqual(project["autonomous_delivery"]["write_capability"], "locked")
            self.assertEqual(project["packages"]["trigger_assessments"]["autonomous_delivery"], "not_assessed")
            self.assertFalse(any(item["id"] == "autonomous-delivery" for item in packages["packages"]))
            available_catalog = json.loads((target / ".agent/available-packages/catalog.json").read_text(encoding="utf-8"))
            autonomous_payload = next(item for item in available_catalog["packages"] if item["id"] == "autonomous-delivery")
            self.assertIn(".agent/capabilities/autonomous-delivery/delivery_runtime.py", {item["path"] for item in autonomous_payload["payload_files"]})
            before_status = tree_digest(target)
            status = previous.run([sys.executable, "-I", "-B", "octon", "delivery", "status"], target)
            self.assertEqual(status.returncode, 0, status.stderr or status.stdout)
            self.assertEqual(json.loads(status.stdout)["status"], "available_not_activated")
            self.assertEqual(tree_digest(target), before_status)
            self.assertFalse((target / ".agent/authorizations").exists())

            receipts = [
                path for path in (target / ".agent/transactions/receipts").glob("RCPT-*.json")
                if json.loads(path.read_text(encoding="utf-8")).get("operation") == "upgrade.project"
            ]
            self.assertEqual(len(receipts), 1)
            rolled_back = previous.run([sys.executable, "-I", "-B", "octon", "transaction", "rollback", "--receipt", str(receipts[0])], target)
            self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr or rolled_back.stdout)
            self.assertEqual(json.loads((target / ".octon-mini-origin.json").read_text())["octon_mini_version"], "4.1.0")
            self.assertNotEqual(tree_digest(target), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
