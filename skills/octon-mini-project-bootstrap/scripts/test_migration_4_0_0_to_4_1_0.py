#!/usr/bin/env python3
"""Same-product 4.0.0 to 4.1.0 upgrade, refusal, and rollback coverage."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path, PurePosixPath

import test_long_running_work as functional


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parents[2]


def run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv, cwd=cwd, capture_output=True, text=True, check=False, shell=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GIT_OPTIONAL_LOCKS": "0"},
    )


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def extract_release(destination: Path, tag: str) -> Path:
    archive = destination / f"{tag}.tar"
    result = run(["git", "archive", "--format=tar", f"--output={archive}", tag], REPO_ROOT)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    source = destination / f"source-{tag.removeprefix('v')}"
    source.mkdir()
    with tarfile.open(archive) as stream:
        for member in stream.getmembers():
            pure = PurePosixPath(member.name)
            if (
                pure.is_absolute()
                or any(part in {"", ".", ".."} for part in pure.parts)
                or not (member.isdir() or member.isfile())
            ):
                raise RuntimeError(f"unsafe archived path: {member.name}")
            target = source.joinpath(*pure.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if member.isdir():
                target.mkdir(exist_ok=True)
                continue
            extracted = stream.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"archive member has no file content: {member.name}")
            with extracted, target.open("wb") as destination_stream:
                shutil.copyfileobj(extracted, destination_stream)
            target.chmod(member.mode & 0o777)
    return source


class Migration400To410Tests(unittest.TestCase):
    def test_released_snapshot_upgrades_without_installing_or_adopting_package(self) -> None:
        if not (REPO_ROOT / ".git").exists():
            self.skipTest("annotated v4.0.0 source tag is unavailable in an installed source bundle")
        with tempfile.TemporaryDirectory(prefix="octon-mini-migration-400-410-") as temporary:
            area = Path(temporary)
            old_source = extract_release(area, "v4.0.0")
            upgrade_source = extract_release(area, "v4.1.0")
            upgrader = upgrade_source / "skills/octon-mini-project-bootstrap/scripts/upgrade_project.py"
            target = area / "project"
            generated = run(
                [
                    sys.executable, "-B",
                    str(old_source / "skills/octon-mini-project-bootstrap/scripts/scaffold_project.py"),
                    "--target", str(target), "--project-name", "Migration Fixture",
                    "--profile", "standard",
                ],
                old_source,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr or generated.stdout)
            old_check = run([sys.executable, "-I", "-B", "octon", "check"], target)
            self.assertEqual(old_check.returncode, 0, old_check.stderr or old_check.stdout)
            self.assertEqual(json.loads((target / ".octon-mini-origin.json").read_text())["octon_mini_version"], "4.0.0")
            functional.task_and_evidence(target)

            proposal_path = area / "proposal.json"
            proposal_result = run(
                [
                    sys.executable, "-B", str(upgrader), "plan", "--target", str(target),
                    "--authority-source", "authority:synthetic-migration-operator",
                    "--evidence-ref", "EVD-0001",
                    "--output", str(proposal_path),
                ],
                upgrade_source,
            )
            self.assertEqual(proposal_result.returncode, 3, proposal_result.stderr or proposal_result.stdout)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            self.assertEqual((proposal["from_version"], proposal["to_version"]), ("4.0.0", "4.1.0"))
            review_path = area / "review.json"
            dispositions = []
            for row in proposal["classifications"]:
                if row["automatic"]:
                    continue
                allowed = row["allowed_dispositions"]
                disposition = "accept_candidate" if "accept_candidate" in allowed else "delete" if "delete" in allowed else "preserve_current"
                dispositions.append({"id": row["id"], "disposition": disposition, "rationale": "Synthetic exact-pristine migration review."})
            write_json(review_path, {
                "schema_version": "octon-mini.bootstrap.upgrade-review.v1",
                "permission_grant": False,
                "proposal_digest": proposal["canonical_proposal_digest"],
                "dispositions": dispositions,
                "limitations": ["Synthetic fixture review only."],
            })
            plan_path = area / "plan.json"
            planned = run(
                [
                    sys.executable, "-B", str(upgrader), "plan", "--target", str(target),
                    "--authority-source", "authority:synthetic-migration-operator",
                    "--evidence-ref", "EVD-0001",
                    "--proposal", str(proposal_path), "--review", str(review_path),
                    "--output", str(plan_path),
                ],
                upgrade_source,
            )
            self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            applied = run(
                [sys.executable, "-B", str(upgrader), "apply", "--target", str(target), "--plan", str(plan_path), "--accept-digest", plan["canonical_plan_digest"]],
                upgrade_source,
            )
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
            current_check = run([sys.executable, "-I", "-B", "octon", "check"], target)
            self.assertEqual(current_check.returncode, 0, current_check.stderr or current_check.stdout)
            origin = json.loads((target / ".octon-mini-origin.json").read_text(encoding="utf-8"))
            project = json.loads((target / ".agent/project.json").read_text(encoding="utf-8"))
            packages = json.loads((target / ".agent/packages.json").read_text(encoding="utf-8"))
            self.assertEqual(origin["octon_mini_version"], "4.1.0")
            self.assertEqual(project["packages"]["trigger_assessments"]["long_running_work"], "not_assessed")
            self.assertFalse(any(item["id"] == "long-running-work" for item in packages["packages"]))
            dormant = run([sys.executable, "-I", "-B", "octon", "work", "run", "status", "--json"], target)
            self.assertEqual(dormant.returncode, 2)
            self.assertIn("OCTON-LRW-1000", dormant.stderr)

            repeated = run(
                [sys.executable, "-B", str(upgrader), "apply", "--target", str(target), "--plan", str(plan_path), "--accept-digest", plan["canonical_plan_digest"]],
                upgrade_source,
            )
            self.assertNotEqual(repeated.returncode, 0)
            receipts = [
                path for path in (target / ".agent/transactions/receipts").glob("RCPT-*.json")
                if json.loads(path.read_text(encoding="utf-8")).get("operation") == "upgrade.project"
            ]
            self.assertEqual(len(receipts), 1)
            rolled_back = run([sys.executable, "-I", "-B", "octon", "transaction", "rollback", "--receipt", str(receipts[0])], target)
            self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr or rolled_back.stdout)
            self.assertEqual(json.loads((target / ".octon-mini-origin.json").read_text())["octon_mini_version"], "4.0.0")
            restored = run([sys.executable, "-I", "-B", "octon", "check"], target)
            self.assertEqual(restored.returncode, 0, restored.stderr or restored.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
