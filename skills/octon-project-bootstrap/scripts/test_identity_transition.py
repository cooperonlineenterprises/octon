#!/usr/bin/env python3
"""Octon identity, real Mini baseline upgrades, refusal and recovery coverage."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import test_long_running_work as fixtures
from test_migration_4_0_0_to_4_1_0 import extract_release

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[2]
BASE = "5e2d3025aea6b1574ab984e5ebb89b5602a38535"
UPGRADE = SCRIPTS / "upgrade_project.py"


def run(argv, cwd=ROOT):
    return subprocess.run(
        [str(x) for x in argv], cwd=cwd, capture_output=True, text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GIT_OPTIONAL_LOCKS": "0"},
        check=False,
    )


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def snapshot(root, *, omit_transactions=False):
    result = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if omit_transactions and (rel.startswith(".agent/transactions/") or rel == ".agent/transactions"):
            continue
        if p.is_symlink():
            result[rel] = ("link", os.readlink(p))
        elif p.is_file():
            result[rel] = (p.stat().st_mode & 0o777, hashlib.sha256(p.read_bytes()).hexdigest())
    return result


class IdentityTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_area = tempfile.TemporaryDirectory(prefix="octon-identity-base-")
        cls.baseline = extract_release(Path(cls.base_area.name), BASE)
        cls.old_scaffold = cls.baseline / "skills/octon-mini-project-bootstrap/scripts/scaffold_project.py"

    @classmethod
    def tearDownClass(cls):
        cls.base_area.cleanup()

    def ok(self, argv, cwd=ROOT, code=0):
        result = run(argv, cwd)
        if result.returncode != code:
            print(result.stderr or result.stdout, flush=True)
        self.assertEqual(result.returncode, code, result.stderr or result.stdout)
        return result

    def generate(self, target, profile="minimal", layout="compact", *, old=False):
        script = self.old_scaffold if old else SCRIPTS / "scaffold_project.py"
        self.ok([sys.executable, "-B", script, "--target", target,
                 "--project-name", "Identity Fixture", "--profile", profile, "--layout", layout])

    def project_records(self, target):
        fixtures.accepted_decision(target, "DEC-0042")
        fixtures.task_and_evidence(target)
        for rel in ["AGENTS.md", "project-dossier/current-state/README.md"]:
            p = target / rel
            p.write_text(p.read_text() + "\nProject-owned synthetic note: preserve this exact text.\n")
        self.ok([sys.executable, "-I", "-B", ".agent/scripts/refresh.py", "--refresh"], target)
        paths = ["AGENTS.md", "project-dossier/current-state/README.md", ".agent/policy.json",
                 "project-dossier/machine-readable/artifact-registry.json",
                 ".agent/tasks/TASK-0001.md", ".agent/evidence/EVD-0001-validation.md"]
        paths += [str(p.relative_to(target)) for p in (target / ".agent/decisions").glob("DEC-0042*")]
        return {rel: (target / rel).read_bytes() for rel in paths}

    def plan(self, target, area):
        common = [sys.executable, "-B", UPGRADE, "plan", "--target", target,
                  "--authority-source", "authority:synthetic-identity-operator", "--evidence-ref", "EVD-0001"]
        proposal_path = area / "proposal.json"
        before = snapshot(target)
        self.ok([*common, "--output", proposal_path], code=3)
        self.assertEqual(snapshot(target), before)
        proposal = json.loads(proposal_path.read_text())
        self.assertEqual((proposal["from_product"], proposal["from_version"], proposal["to_product"], proposal["to_version"]),
                         ("octon-mini", "4.2.0", "octon", "5.0.0"))
        decisions = []
        for row in proposal["classifications"]:
            if row["automatic"]:
                continue
            choices = row["allowed_dispositions"]
            if row["path"] == ".agent/project.json" and "merge_version_only" in choices:
                choice = "merge_version_only"
            elif row["path"] == ".octon-mini-origin.json":
                choice = "delete"
            elif row["path"] == "project-dossier/machine-readable/artifact-registry.json":
                choice = "preserve_current"
            elif row["classification"] == "project_modified" and (
                row["current"]["sha256"] != (row["old_baseline"] or {}).get("sha256")
                or row["current"]["mode"] != (row["old_baseline"] or {}).get("mode")
            ):
                choice = "preserve_current"
            else:
                choice = "accept_candidate" if "accept_candidate" in choices else "preserve_current"
            self.assertIn(choice, choices)
            decisions.append({"id": row["id"], "disposition": choice, "rationale": "Explicit synthetic identity-upgrade review."})
        review = area / "review.json"
        write_json(review, {"schema_version": "octon.bootstrap.upgrade-review.v1", "permission_grant": False,
                            "proposal_digest": proposal["canonical_proposal_digest"], "dispositions": decisions,
                            "limitations": ["Disposable fixture only; no project authority supplied by this record."]})
        path = area / "plan.json"
        self.ok([*common, "--proposal", proposal_path, "--review", review, "--output", path])
        self.assertEqual(snapshot(target), before)
        return path, json.loads(path.read_text())

    def apply(self, target, path, plan):
        return self.ok([sys.executable, "-B", UPGRADE, "apply", "--target", target,
                        "--plan", path, "--accept-digest", plan["canonical_plan_digest"]])

    def test_published_schemas_unchanged(self):
        for name in ["octon-mini-project-origin.schema.json", "octon-mini-bootstrap-upgrade.schema.json", "harness-kernel.schema.json"]:
            self.assertEqual((ROOT / "shared/schemas" / name).read_bytes(), (self.baseline / "shared/schemas" / name).read_bytes())

    def test_all_profiles_layouts_fresh_and_released_upgrades(self):
        for profile in ["minimal", "standard", "high-assurance"]:
            for layout in ["compact", "separated"]:
                with self.subTest(profile=profile, layout=layout), tempfile.TemporaryDirectory(prefix="octon-identity-") as temp:
                    area = Path(temp)
                    fresh = area / "fresh"
                    self.generate(fresh, profile, layout)
                    origin = json.loads((fresh / ".octon-origin.json").read_text())
                    self.assertEqual((origin["schema_version"], origin["product"], origin["generator_version"]),
                                     ("octon.project.origin.v1", "octon", "5.0.0"))
                    self.assertFalse((fresh / ".octon-mini-origin.json").exists())
                    before = snapshot(fresh)
                    self.ok([sys.executable, "-I", "-B", "octon", "check"], fresh)
                    self.ok([sys.executable, "-I", "-B", "octon", "delivery", "status"], fresh)
                    self.assertEqual(snapshot(fresh), before)

                    target = area / "old"
                    self.generate(target, profile, layout, old=True)
                    records = self.project_records(target)
                    old_bytes = (target / ".octon-mini-origin.json").read_bytes()
                    old_origin = json.loads(old_bytes)
                    before = snapshot(target)
                    self.ok([sys.executable, "-I", "-B", "octon", "check"], target)
                    print(f"verified existing Mini snapshot: {profile}/{layout}", flush=True)
                    self.assertEqual(snapshot(target), before)
                    path, plan = self.plan(target, area)
                    self.apply(target, path, plan)
                    current = json.loads((target / ".octon-origin.json").read_text())
                    self.assertEqual(current["initial_generation"], old_origin["initial_generation"])
                    self.assertEqual(current["migration_history"][:-1], old_origin["migration_history"])
                    self.assertEqual(current["migration_history"][-1]["schema_version"], "octon.project.migration.v1")
                    self.assertEqual(current["migration_history"][-1]["from_product"], "octon-mini")
                    self.assertEqual(current["product"], "octon")
                    self.assertFalse((target / ".octon-mini-origin.json").exists())
                    for rel, data in records.items():
                        self.assertEqual((target / rel).read_bytes(), data, rel)
                    project = json.loads((target / ".agent/project.json").read_text())
                    self.assertEqual(project["autonomous_delivery"]["status"], "available_not_activated")
                    self.assertEqual(project["autonomous_delivery"]["write_capability"], "locked")
                    self.assertIsNone(project["autonomous_delivery"]["authorization_record_ref"])
                    self.assertEqual(project["autonomous_delivery"]["external_effects"], "locked")
                    self.ok([sys.executable, "-I", "-B", "octon", "check"], target)
                    receipt = next((target / ".agent/transactions/receipts").glob("RCPT-*.json"))
                    self.ok([sys.executable, "-I", "-B", "octon", "transaction", "rollback", "--receipt", receipt], target)
                    self.assertEqual((target / ".octon-mini-origin.json").read_bytes(), old_bytes)
                    self.assertFalse((target / ".octon-origin.json").exists())
                    self.ok([sys.executable, "-I", "-B", "octon", "check"], target)

    def test_conflicting_original_runtime_and_origin_refusals_are_read_only(self):
        with tempfile.TemporaryDirectory(prefix="octon-identity-refusal-") as temp:
            area = Path(temp); target = area / "project"
            self.generate(target, old=True)
            fixtures.task_and_evidence(target)
            for kind in ["runtime", "mixed", "wrong_producer", "duplicate_key", "origin_symlink", "internal_symlink"]:
                with self.subTest(kind=kind):
                    fixture = area / kind; shutil.copytree(target, fixture)
                    if kind == "runtime": (fixture / ".octon").mkdir()
                    elif kind == "mixed": shutil.copy2(fixture / ".octon-mini-origin.json", fixture / ".octon-origin.json")
                    elif kind == "wrong_producer":
                        p=fixture / ".octon-mini-origin.json"; v=json.loads(p.read_text());v["product"]="octon";write_json(p,v)
                    elif kind == "origin_symlink":
                        p=fixture / ".octon-mini-origin.json";p.rename(fixture/'retained-origin.json');p.symlink_to('retained-origin.json')
                    elif kind == "internal_symlink":
                        p=fixture/'.agent/scripts';p.rename(fixture/'.agent/retained-scripts');p.symlink_to('retained-scripts',target_is_directory=True)
                    else:
                        p=fixture / ".octon-mini-origin.json";p.write_text(p.read_text().replace('"product": "octon-mini"', '"product": "octon", "product": "octon-mini"', 1))
                    before=snapshot(fixture)
                    self.ok([sys.executable,"-B",UPGRADE,"plan","--target",fixture,"--authority-source","authority:synthetic",
                             "--evidence-ref","EVD-0001","--output",area/(kind+".json")],code=2)
                    self.assertEqual(snapshot(fixture),before)

    def test_interrupted_apply_recovers_old_snapshot_without_replay(self):
        for boundary in ["early", "before-origin", "after-origin"]:
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory(prefix="octon-identity-recovery-") as temp:
                area=Path(temp);target=area/"project";self.generate(target,old=True);self.project_records(target)
                path,plan=self.plan(target,area);before=snapshot(target,omit_transactions=True)
                program = "import json, os, sys\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\nimport upgrade_project\ntx=upgrade_project.TRANSACTION\nroot=Path(sys.argv[2]).resolve();plan=json.loads(Path(sys.argv[3]).read_text());boundary=sys.argv[4]\noriginal=tx._atomic_write\ndef crash(path, data, mode):\n    material=path.is_relative_to(root) and not path.is_relative_to(root/'.agent/transactions')\n    origin=path == root/'.octon-origin.json'\n    if material and origin and boundary == 'before-origin':\n        os._exit(73)\n    original(path,data,mode)\n    if material and (boundary == 'early' or origin and boundary == 'after-origin'):\n        os._exit(73)\ntx._atomic_write=crash\ntx.apply_plan(root,plan,plan['canonical_plan_digest'])\n"
                self.ok([sys.executable,"-B","-c",program,SCRIPTS,target,path,boundary],code=73)
                pending=list((target/".agent/transactions/pending").glob("*.json"));self.assertEqual(len(pending),1)
                if boundary != "early":
                    self.assertFalse((target/".octon-mini-origin.json").exists())
                    self.assertEqual((target/".octon-origin.json").exists(),boundary == "after-origin")
                self.ok([sys.executable,"-I","-B","octon","transaction","recover","--pending",pending[0].relative_to(target)],target)
                self.assertEqual(snapshot(target,omit_transactions=True),before)
                self.ok([sys.executable,"-I","-B","octon","check"],target)

    def test_snapshot_has_no_source_or_sibling_dependency(self):
        with tempfile.TemporaryDirectory(prefix="octon-identity-independent-") as temp:
            area=Path(temp); source=area/"source"
            shutil.copytree(ROOT,source,ignore=shutil.ignore_patterns('.git','__pycache__'))
            project=area/"project"
            self.ok([sys.executable,"-B",source/'skills/octon-project-bootstrap/scripts/scaffold_project.py',
                     '--target',project,'--project-name','Independent','--profile','high-assurance','--layout','separated'])
            source.rename(area/'source-unavailable')
            before=snapshot(project)
            self.ok([sys.executable,"-I","-B","octon","check"],project)
            self.ok([sys.executable,"-I","-B","octon","doctor"],project)
            self.ok([sys.executable,"-I","-B","octon","delivery","status"],project)
            self.assertEqual(snapshot(project),before)
            for p in project.rglob('*'):
                if p.is_file():
                    self.assertNotIn(str(ROOT).encode(),p.read_bytes())
                    self.assertNotIn(str(source).encode(),p.read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)
