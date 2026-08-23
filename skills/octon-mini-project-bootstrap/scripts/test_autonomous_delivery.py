#!/usr/bin/env python3
"""Functional coverage for dormant and activated autonomous delivery."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import test_long_running_work as long_work_fixture


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
SOURCE_CANDIDATE = SKILL_ROOT.parents[1]
BUNDLED_CANDIDATE = SKILL_ROOT / "assets/octon-mini-source"
REPO_ROOT = SOURCE_CANDIDATE if (SOURCE_CANDIDATE / "octon-mini.json").is_file() else BUNDLED_CANDIDATE
SCAFFOLDER = SCRIPT_ROOT / "scaffold_project.py"


def run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def snapshot(root: Path) -> dict[str, tuple[str, int]]:
    return {
        path.relative_to(root).as_posix(): (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            path.stat().st_mode & 0o777,
        )
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def load_module(path: Path, name: str):
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


def accepted_decision(target: Path, identifier: str = "DEC-9100") -> None:
    record = {
        "schema_version": "harness.decision.v1",
        "id": identifier,
        "status": "accepted",
        "previous_status": "proposed",
        "title": "Adopt governed autonomous delivery",
        "created_at": "2026-08-22",
        "authority_source": "authority:synthetic-disposable-operator",
        "owner": "synthetic-disposable-operator",
        "scope": "Synthetic disposable autonomous-delivery adoption only",
        "supersedes": None,
        "successor": None,
        "governance_register_refs": [],
        "limitations": ["Synthetic fixture authority only; no live external effect."],
    }
    path = target / ".agent/decisions" / f"{identifier}-autonomous-delivery.md"
    path.write_text(
        "---\n" + json.dumps(record, indent=2, sort_keys=True) + "\n---\n\n# Decision\nSynthetic fixture.\n",
        encoding="utf-8",
    )


class AutonomousDeliveryTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="octon-autonomous-delivery-")
        self.area = Path(self.temporary.name)
        self.target = self.area / "project"
        generated = run(
            [
                sys.executable,
                "-B",
                str(SCAFFOLDER),
                "--target",
                str(self.target),
                "--project-name",
                "Autonomous Delivery Fixture",
                "--project-slug",
                "autonomous-delivery-fixture",
                "--profile",
                "standard",
            ],
            REPO_ROOT,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr or generated.stdout)
        self.control = self.area / "control"
        self.evidence = self.area / "evidence"
        self.control.mkdir()
        self.evidence.mkdir()
        accepted_decision(self.target)
        refreshed = run([sys.executable, "-I", "-B", ".agent/scripts/refresh.py", "--refresh"], self.target)
        self.assertEqual(refreshed.returncode, 0, refreshed.stderr or refreshed.stdout)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def octon(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, "-I", "-B", "octon", *arguments], self.target)

    def draft(
        self,
        profile: str = "fast_delivery",
        compute_mode: str = "metered_api",
        authorization_id: str = "SAC-01",
        supersedes_record: Path | None = None,
    ) -> dict[str, object]:
        arguments = [
            "delivery",
            "authorization",
            "draft",
            "--authorization-id",
            authorization_id,
            "--profile",
            profile,
            "--compute-mode",
            compute_mode,
            "--repository-root",
            str(self.target),
            "--repository-identity",
            "synthetic/autonomous-delivery",
            "--remote",
            "origin",
            "--default-branch",
            "main",
            "--task-branch-pattern",
            "chore/autonomous-*",
            "--authority-dir",
            str(self.control),
            "--evidence-root",
            str(self.evidence),
            "--valid-from",
            "2026-08-22T00:00:00Z",
            "--valid-until",
            "2099-01-01T00:00:00Z",
        ]
        if compute_mode == "included_subscription":
            arguments.extend(["--subscription-plan-ref", "authority:synthetic-included-subscription-plan"])
        if supersedes_record is not None:
            arguments.extend(["--supersedes-authorization-record", str(supersedes_record)])
        result = self.octon(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def confirmation(self, contract: dict[str, object]) -> dict[str, object]:
        module = load_module(
            self.target / ".agent/scripts/octon_autonomous_delivery.py",
            "octon_autonomous_delivery_test_confirmation",
        )
        value = {
            "schema_version": "harness.autonomous-delivery-confirmation.v1",
            "artifact_kind": "standing_authorization_confirmation_evidence",
            "permission_grant": False,
            "authorization_id": contract["authorization_id"],
            "contract_digest": contract["canonical_contract_digest"],
            "confirmation_method": "independent_exact_digest_statement",
            "confirmation_statement": module.expected_confirmation_statement(contract["canonical_contract_digest"], contract["authorization_id"]),
            "authority_source": "authority:synthetic-disposable-operator",
            "confirmed_by_role": "synthetic-disposable-operator",
            "confirmed_at": "2026-08-22T00:05:00Z",
        }
        value["confirmation_fingerprint"] = module.digest(value)
        return value

    def compute_evidence(self, contract: dict[str, object], used_percent: float = 25.0) -> dict[str, object]:
        module = load_module(
            self.target / ".agent/scripts/octon_autonomous_delivery.py",
            "octon_autonomous_delivery_test_cost",
        )
        observed = module.utc_now()
        mode = contract["compute_control"]["mode"]
        value = {
            "schema_version": "harness.autonomous-delivery-compute-enforcement.v2",
            "artifact_kind": "external_host_compute_enforcement_evidence",
            "compute_mode": mode,
            "host_enforced": True,
            "observed_at": module.utc_text(observed),
            "valid_until": module.utc_text(observed + timedelta(minutes=10)),
            "metered_api": {
                "unknown_cost": False,
                "per_run_usd": 250.0,
                "per_authorization_usd": 1000.0,
            } if mode == "metered_api" else None,
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
                    "id": "rolling-provider-window",
                    "used_percent": used_percent,
                    "status": "available",
                    "resets_at": module.utc_text(observed + timedelta(hours=1)),
                }],
            } if mode == "included_subscription" else None,
        }
        value["evidence_fingerprint"] = module.digest(value)
        return value

    def accepted_records(self, compute_mode: str = "metered_api") -> tuple[Path, Path, Path, dict[str, object]]:
        contract = self.draft(compute_mode=compute_mode)
        draft_path = self.area / "SAC-01.draft.json"
        confirmation_path = self.control / "SAC-01.confirmation.json"
        record_path = self.control / "SAC-01.json"
        cost_path = self.control / "cost.json"
        write_json(draft_path, contract)
        write_json(confirmation_path, self.confirmation(contract))
        write_json(cost_path, self.compute_evidence(contract))
        result = self.octon(
            "delivery",
            "authorization",
            "record",
            "--draft",
            str(draft_path),
            "--confirmation-artifact",
            str(confirmation_path),
            "--output",
            str(record_path),
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return record_path, confirmation_path, cost_path, contract

    def activate(self) -> dict[str, object]:
        record_path, confirmation_path, cost_path, _contract = self.accepted_records()
        plan_result = self.octon(
            "delivery",
            "activate",
            "plan",
            "--authorization-record",
            str(record_path),
            "--confirmation-artifact",
            str(confirmation_path),
            "--cost-enforcement-artifact",
            str(cost_path),
            "--adoption-decision-ref",
            "DEC-9100",
        )
        self.assertEqual(plan_result.returncode, 0, plan_result.stderr or plan_result.stdout)
        plan = json.loads(plan_result.stdout)
        plan_path = self.area / "activation-plan.json"
        write_json(plan_path, plan)
        applied = self.octon(
            "delivery",
            "activate",
            "apply",
            "--plan",
            str(plan_path),
            "--accept-digest",
            plan["canonical_plan_digest"],
            "--authorization-record",
            str(record_path),
            "--confirmation-artifact",
            str(confirmation_path),
            "--cost-enforcement-artifact",
            str(cost_path),
        )
        diagnostic = ""
        if applied.returncode:
            module = load_module(self.target / ".agent/scripts/octon_autonomous_delivery.py", "octon_activation_diagnostic")
            transaction = load_module(self.target / ".agent/scripts/octon_transaction.py", "octon_activation_transaction_diagnostic")
            receipt_id = transaction.new_receipt_id()
            operations, _ = module.activation_operations(self.target.resolve(), plan, str(record_path), receipt_id)
            record = json.loads(record_path.read_text(encoding="utf-8"))
            tx_plan = transaction.build_plan(
                self.target.resolve(),
                operation_name="delivery.activate",
                scope="Diagnostic activation stage",
                operations=operations,
                evidence=[transaction.source_evidence("standing_authorization", str(record_path), content=module.canonical_bytes(record))],
                assumptions=[],
                confidence="high",
                limitations=module.LIMITATIONS,
                validation_plan=[[sys.executable, "-B", ".agent/scripts/validate.py", "--check"]],
                evidence_paths=[".agent/project.json", ".agent/packages.json"],
                planned_receipt_id=receipt_id,
                bundle_authority_class="independently_confirmed_standing_authorization",
            )
            diagnostic = long_work_fixture.staged_diagnostic(self.target, tx_plan)
            registry_operation = next(item for item in operations if item["path"] == ".agent/packages.json")
            registry_value = json.loads(__import__("base64").b64decode(registry_operation["content_base64"]))
            diagnostic += "\nplanned_receipt=" + tx_plan["planned_receipt_id"] + " registry_receipts=" + repr([item["validation_receipt_ref"] for item in registry_value["packages"]])
            with tempfile.TemporaryDirectory(prefix="octon-activation-env-diagnostic-") as temporary:
                stage = Path(temporary) / "project"
                transaction._clone_for_staging(self.target.resolve(), stage)
                transaction._apply_static(stage, tx_plan, transaction._decode_operations(tx_plan))
                staged_check = subprocess.run(
                    [sys.executable, "-B", ".agent/scripts/validate.py", "--check"],
                    cwd=stage,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OCTON_MINI_ACTIVE_TRANSACTION_RECEIPT": tx_plan["planned_receipt_id"], "OCTON_MINI_ACTIVE_TRANSACTION_PLAN_DIGEST": tx_plan["canonical_plan_digest"]},
                    capture_output=True,
                    text=True,
                    check=False,
                )
                diagnostic += "\nWITH_ENV:\n" + staged_check.stdout + staged_check.stderr
        self.assertEqual(applied.returncode, 0, (applied.stderr or applied.stdout) + "\nSTAGED:\n" + diagnostic)
        return json.loads(applied.stdout)

    def test_pre_activation_surfaces_are_read_only_and_hook_free(self) -> None:
        before = snapshot(self.target)
        invocations = [
            ("status",),
            ("research", "--query", "safe autonomous delivery"),
            ("context", "--max-bytes", "65536"),
            ("assess",),
            ("plan",),
            ("explain",),
            ("activation-preview", "--profile", "fast_delivery"),
        ]
        for argv in invocations:
            with self.subTest(argv=argv):
                result = self.octon("delivery", *argv)
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
                value = json.loads(result.stdout)
                if argv[0] != "explain":
                    self.assertFalse(value.get("permission_grant"))
        self.assertEqual(snapshot(self.target), before)

    def test_draft_is_deterministic_non_authorizing_and_capped_at_ninety_days(self) -> None:
        first = self.draft()
        second = self.draft()
        self.assertEqual(first, second)
        self.assertFalse(first["permission_grant"])
        self.assertEqual(first["status"], "proposed_unconfirmed")
        self.assertEqual(first["compute_control"]["mode"], "metered_api")
        self.assertEqual(first["compute_control"]["direct_external_spending_usd"], 0)
        self.assertIsNotNone(first["compute_control"]["metered_api"])
        self.assertIsNone(first["compute_control"]["included_subscription"])
        self.assertEqual(first["valid_until"], "2026-11-20T00:00:00Z")
        self.assertEqual(first["limits"]["warning_percentages"], [70, 85, 95])
        self.assertIn("selected_compute_enforcement_or_usage_readback_unavailable", first["human_stop_conditions"])
        self.assertNotIn("host_cost_enforcement_unavailable", first["human_stop_conditions"])

    def test_compute_mode_is_explicit_and_subscription_never_overlaps_metered_api(self) -> None:
        missing = self.octon("delivery", "authorization", "draft", "--profile", "fast_delivery")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("--compute-mode", missing.stderr)
        subscription = self.draft(compute_mode="included_subscription")
        self.assertEqual(subscription["compute_control"]["mode"], "included_subscription")
        self.assertIsNone(subscription["compute_control"]["metered_api"])
        self.assertFalse(subscription["compute_control"]["included_subscription"]["separately_purchased_credits_allowed"])

    def test_included_subscription_activation_requires_readable_included_allowance_only(self) -> None:
        record_path, confirmation_path, compute_path, _contract = self.accepted_records("included_subscription")
        planned = self.octon(
            "delivery", "activate", "plan",
            "--authorization-record", str(record_path),
            "--confirmation-artifact", str(confirmation_path),
            "--compute-enforcement-artifact", str(compute_path),
            "--adoption-decision-ref", "DEC-9100",
        )
        self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
        plan = json.loads(planned.stdout)
        self.assertEqual(plan["compute_mode"], "included_subscription")
        validator = load_module(self.target / ".agent/scripts/validate.py", "octon_subscription_plan_schema")
        schema = json.loads((self.target / ".agent/schemas/harness-autonomous-delivery.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(validator.validate_schema(plan, schema["$defs"]["activation_plan"], root_schema=schema), [])
        compute = json.loads(compute_path.read_text(encoding="utf-8"))
        compute["included_subscription"]["separately_purchased_credits_in_use"] = True
        module = load_module(self.target / ".agent/scripts/octon_autonomous_delivery.py", "octon_subscription_rehash")
        compute["evidence_fingerprint"] = module.digest({key: value for key, value in compute.items() if key != "evidence_fingerprint"})
        write_json(compute_path, compute)
        blocked = self.octon(
            "delivery", "activate", "plan",
            "--authorization-record", str(record_path),
            "--confirmation-artifact", str(confirmation_path),
            "--compute-enforcement-artifact", str(compute_path),
            "--adoption-decision-ref", "DEC-9100",
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("paid capacity", blocked.stderr)

    def test_confirmed_v1_metered_record_remains_valid_legacy_evidence(self) -> None:
        module = load_module(self.target / ".agent/scripts/octon_autonomous_delivery.py", "octon_legacy_record")
        current = self.draft()
        legacy = dict(current)
        legacy["schema_version"] = module.CONTRACT_SCHEMA_V1
        legacy.pop("compute_control")
        legacy.pop("supersedes")
        legacy["costs"] = {
            "host_enforcement_required": True,
            "ai_provider_usd_per_run": 250.0,
            "ai_provider_usd_per_authorization": 1000.0,
            "unknown_cost_behavior": "block_activation_or_require_human_approved_custom_treatment",
            "direct_external_spending_usd": 0,
            "purchases_prohibited": module.PURCHASE_DENIES,
        }
        legacy["canonical_contract_digest"] = module.digest({key: value for key, value in legacy.items() if key != "canonical_contract_digest"})
        confirmation = self.confirmation(legacy)
        record = module.accepted_record(legacy, confirmation)
        self.assertEqual(record["schema_version"], module.RECORD_SCHEMA_V1)
        self.assertEqual(module.compute_mode(module.validate_record(record)["contract"]), "metered_api")

    def test_successor_uses_new_id_and_requires_exact_predecessor_revocation(self) -> None:
        predecessor_path, _predecessor_confirmation, _predecessor_compute, _ = self.accepted_records()
        predecessor = json.loads(predecessor_path.read_text(encoding="utf-8"))
        successor = self.draft(
            compute_mode="included_subscription",
            authorization_id="SAC-02",
            supersedes_record=predecessor_path,
        )
        self.assertEqual(successor["supersedes"]["authorization_id"], "SAC-01")
        self.assertEqual(successor["supersedes"]["accepted_record_digest"], predecessor["accepted_record_digest"])
        successor_draft = self.area / "SAC-02.draft.json"
        successor_confirmation = self.control / "SAC-02.confirmation.json"
        successor_record = self.control / "SAC-02.json"
        successor_compute = self.control / "SAC-02.compute.json"
        write_json(successor_draft, successor)
        write_json(successor_confirmation, self.confirmation(successor))
        write_json(successor_compute, self.compute_evidence(successor))
        recorded = self.octon(
            "delivery", "authorization", "record",
            "--draft", str(successor_draft),
            "--confirmation-artifact", str(successor_confirmation),
            "--output", str(successor_record),
        )
        self.assertEqual(recorded.returncode, 0, recorded.stderr or recorded.stdout)
        blocked = self.octon(
            "delivery", "activate", "plan",
            "--authorization-record", str(successor_record),
            "--confirmation-artifact", str(successor_confirmation),
            "--compute-enforcement-artifact", str(successor_compute),
            "--adoption-decision-ref", "DEC-9100",
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("required external record is absent", blocked.stderr)
        superseded = self.octon(
            "delivery", "authorization", "supersede",
            "--predecessor-record", str(predecessor_path),
            "--successor-record", str(successor_record),
            "--output", str(self.control / "SAC-01.revoked.json"),
        )
        self.assertEqual(superseded.returncode, 0, superseded.stderr or superseded.stdout)
        revocation = json.loads((self.control / "SAC-01.revoked.json").read_text(encoding="utf-8"))
        self.assertEqual(revocation["successor_authorization_id"], "SAC-02")
        planned = self.octon(
            "delivery", "activate", "plan",
            "--authorization-record", str(successor_record),
            "--confirmation-artifact", str(successor_confirmation),
            "--compute-enforcement-artifact", str(successor_compute),
            "--adoption-decision-ref", "DEC-9100",
        )
        self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)

    def test_profile_recommendation_never_selects_or_activates(self) -> None:
        result = self.octon("delivery", "activation-preview", "--profile", "fast_delivery")
        value = json.loads(result.stdout)
        self.assertTrue(value["preset"]["recommended_for_most_solo_developers"])
        self.assertFalse(value["preset"]["silently_selected"])
        self.assertEqual(value["current"]["status"], "available_not_activated")
        self.assertEqual(value["current"]["write_capability"], "locked")

    def test_command_line_flag_cannot_fabricate_confirmation(self) -> None:
        result = self.octon("delivery", "authorization", "record", "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required", result.stderr)

    def test_changed_digest_and_confirmation_statement_are_rejected(self) -> None:
        contract = self.draft()
        contract["limits"]["work_iterations"] = 501
        draft_path = self.area / "changed.json"
        confirmation_path = self.area / "confirmation.json"
        write_json(draft_path, contract)
        write_json(confirmation_path, self.confirmation(contract))
        result = self.octon(
            "delivery", "authorization", "record",
            "--draft", str(draft_path),
            "--confirmation-artifact", str(confirmation_path),
            "--output", str(self.area / "record.json"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("contract digest is invalid", result.stderr)

    def test_contract_schema_and_duplicate_keys_fail_closed(self) -> None:
        contract = self.draft()
        validator = load_module(self.target / ".agent/scripts/validate.py", "octon_autonomous_schema_validator")
        schema = json.loads((self.target / ".agent/schemas/harness-autonomous-delivery.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(validator.validate_schema(contract, schema["$defs"]["contract"], root_schema=schema), [])
        compute = self.compute_evidence(contract)
        self.assertEqual(validator.validate_schema(compute, schema["$defs"]["compute_enforcement"], root_schema=schema), [])
        duplicate = self.area / "duplicate-draft.json"
        duplicate.write_text('{"schema_version":"harness.autonomous-delivery-standing-authorization.v2","schema_version":"duplicate"}\n', encoding="utf-8")
        confirmation = self.area / "confirmation.json"
        write_json(confirmation, self.confirmation(contract))
        result = self.octon(
            "delivery", "authorization", "record",
            "--draft", str(duplicate),
            "--confirmation-artifact", str(confirmation),
            "--output", str(self.area / "record.json"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate JSON key", result.stderr)

    def test_unknown_or_unenforced_cost_blocks_activation(self) -> None:
        record_path, confirmation_path, cost_path, _contract = self.accepted_records()
        cost = json.loads(cost_path.read_text(encoding="utf-8"))
        cost["metered_api"]["unknown_cost"] = True
        module = load_module(self.target / ".agent/scripts/octon_autonomous_delivery.py", "octon_cost_rehash")
        cost["evidence_fingerprint"] = module.digest({key: value for key, value in cost.items() if key != "evidence_fingerprint"})
        write_json(cost_path, cost)
        result = self.octon(
            "delivery", "activate", "plan",
            "--authorization-record", str(record_path),
            "--confirmation-artifact", str(confirmation_path),
            "--cost-enforcement-artifact", str(cost_path),
            "--adoption-decision-ref", "DEC-9100",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("remain unknown", result.stderr)

    def test_revocation_and_emergency_stop_block_activation(self) -> None:
        for control_name in ["SAC-01.revoked.json", "STOP"]:
            with self.subTest(control_name=control_name):
                record_path, confirmation_path, cost_path, _contract = self.accepted_records()
                (self.control / control_name).write_text("{}\n", encoding="utf-8")
                result = self.octon(
                    "delivery", "activate", "plan",
                    "--authorization-record", str(record_path),
                    "--confirmation-artifact", str(confirmation_path),
                    "--cost-enforcement-artifact", str(cost_path),
                    "--adoption-decision-ref", "DEC-9100",
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("revoked" if "revoked" in control_name else "emergency stop", result.stderr)
                (self.control / control_name).unlink()
                for path in [record_path, confirmation_path, cost_path, self.area / "SAC-01.draft.json"]:
                    path.unlink(missing_ok=True)

    def test_exact_activation_installs_both_packages_and_preserves_external_authority(self) -> None:
        receipt = self.activate()
        self.assertEqual(receipt["status"], "active")
        project = json.loads((self.target / ".agent/project.json").read_text(encoding="utf-8"))
        self.assertEqual(project["autonomous_delivery"]["delivery_profile"], "fast_delivery")
        self.assertEqual(project["autonomous_delivery"]["adoption_decision_ref"], "DEC-9100")
        registry = json.loads((self.target / ".agent/packages.json").read_text(encoding="utf-8"))
        self.assertEqual({item["id"] for item in registry["packages"]}, {"autonomous-delivery", "long-running-work"})
        self.assertTrue((self.target / ".agent/capabilities/autonomous-delivery/delivery_runtime.py").is_file())
        self.assertTrue((self.target / ".agent/capabilities/long-running-work/long_work.py").is_file())
        self.assertFalse((self.target / ".agent" / "authorizations").exists())
        checked = self.octon("check")
        self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)

    def test_source_activation_exercise_writes_only_external_receipt(self) -> None:
        if not (REPO_ROOT / ".git").is_dir():
            self.skipTest("source repository Git metadata is unavailable in installed bundle")
        with tempfile.TemporaryDirectory(prefix="octon-source-delivery-exercise-") as temporary:
            area = Path(temporary)
            control = area / "control"
            evidence = area / "evidence"
            control.mkdir()
            evidence.mkdir()
            core = load_module(SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_autonomous_delivery.py.tmpl", "octon_source_delivery_exercise_core")
            tracked = run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], REPO_ROOT)
            self.assertEqual(tracked.returncode, 0, tracked.stderr)
            tracked_paths = [item for item in tracked.stdout.split("\0") if item]
            def tracked_digest() -> str:
                value = hashlib.sha256()
                for relative in tracked_paths:
                    path = REPO_ROOT / relative
                    value.update(relative.encode("utf-8")); value.update(b"\0")
                    if path.is_file():
                        value.update(path.read_bytes())
                    value.update(b"\0")
                return value.hexdigest()
            before = tracked_digest()
            draft_result = run(
                [
                    sys.executable, "-B", str(SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_autonomous_delivery.py.tmpl"),
                    "--target", str(REPO_ROOT), "authorization", "draft",
                    "--profile", "fast_delivery", "--compute-mode", "metered_api",
                    "--repository-root", str(REPO_ROOT),
                    "--repository-identity", "cooperonlineenterprises/octon-mini",
                    "--remote", "origin", "--default-branch", "main",
                    "--task-branch-pattern", "chore/autonomous-*",
                    "--authority-dir", str(control), "--evidence-root", str(evidence),
                    "--valid-from", "2026-08-22T00:00:00-05:00",
                    "--valid-until", "2026-09-10T23:59:59-05:00",
                ],
                REPO_ROOT,
            )
            self.assertEqual(draft_result.returncode, 0, draft_result.stderr or draft_result.stdout)
            contract = json.loads(draft_result.stdout)
            draft_path = area / "SAC-01.draft.json"
            write_json(draft_path, contract)
            confirmation = {
                "schema_version": "harness.autonomous-delivery-confirmation.v1",
                "artifact_kind": "standing_authorization_confirmation_evidence",
                "permission_grant": False,
                "authorization_id": "SAC-01",
                "contract_digest": contract["canonical_contract_digest"],
                "confirmation_method": "independent_exact_digest_statement",
                "confirmation_statement": core.expected_confirmation_statement(contract["canonical_contract_digest"]),
                "authority_source": "authority:synthetic-source-exercise-only",
                "confirmed_by_role": "synthetic-source-exercise-operator",
                "confirmed_at": "2026-08-22T00:05:00Z",
            }
            confirmation["confirmation_fingerprint"] = core.digest(confirmation)
            confirmation_path = control / "SAC-01.confirmation.json"
            write_json(confirmation_path, confirmation)
            record_path = control / "SAC-01.json"
            recorded = run(
                [sys.executable, "-B", str(SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_autonomous_delivery.py.tmpl"), "--target", str(REPO_ROOT), "authorization", "record", "--draft", str(draft_path), "--confirmation-artifact", str(confirmation_path), "--output", str(record_path)],
                REPO_ROOT,
            )
            self.assertEqual(recorded.returncode, 0, recorded.stderr or recorded.stdout)
            cost = {
                "schema_version": "harness.autonomous-delivery-compute-enforcement.v2",
                "artifact_kind": "external_host_compute_enforcement_evidence",
                "compute_mode": "metered_api",
                "host_enforced": True,
                "metered_api": {
                    "unknown_cost": False,
                    "per_run_usd": 250.0,
                    "per_authorization_usd": 1000.0,
                },
                "included_subscription": None,
                "observed_at": "2026-08-22T00:05:00Z",
                "valid_until": "2026-09-10T23:59:59-05:00",
            }
            cost["evidence_fingerprint"] = core.digest(cost)
            cost_path = control / "cost.json"
            write_json(cost_path, cost)
            plan_result = run(
                [sys.executable, "-B", str(SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_autonomous_delivery.py.tmpl"), "--target", str(REPO_ROOT), "activate", "plan", "--authorization-record", str(record_path), "--confirmation-artifact", str(confirmation_path), "--cost-enforcement-artifact", str(cost_path), "--adoption-decision-ref", "SRC-DEC-0019"],
                REPO_ROOT,
            )
            self.assertEqual(plan_result.returncode, 0, plan_result.stderr or plan_result.stdout)
            plan = json.loads(plan_result.stdout)
            self.assertEqual(plan["activation_target"], "octon_mini_source_repository")
            plan_path = area / "activation-plan.json"
            write_json(plan_path, plan)
            receipt_path = evidence / "activation-receipt.json"
            applied = run(
                [sys.executable, "-B", str(SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_autonomous_delivery.py.tmpl"), "--target", str(REPO_ROOT), "activate", "apply", "--plan", str(plan_path), "--accept-digest", plan["canonical_plan_digest"], "--authorization-record", str(record_path), "--confirmation-artifact", str(confirmation_path), "--cost-enforcement-artifact", str(cost_path), "--activation-receipt-output", str(receipt_path)],
                REPO_ROOT,
            )
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
            self.assertTrue(receipt_path.is_file())
            self.assertIsNone(json.loads(receipt_path.read_text(encoding="utf-8"))["transaction_receipt_ref"])
            active_status = run(
                [sys.executable, "-B", str(SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_autonomous_delivery.py.tmpl"), "--target", str(REPO_ROOT), "status", "--authorization-record", str(record_path), "--confirmation-artifact", str(confirmation_path), "--cost-enforcement-artifact", str(cost_path), "--activation-receipt", str(receipt_path)],
                REPO_ROOT,
            )
            self.assertEqual(active_status.returncode, 0, active_status.stderr or active_status.stdout)
            self.assertEqual(json.loads(active_status.stdout)["status"], "active")
            self.assertEqual(tracked_digest(), before)

    def test_warning_thresholds_and_exhaustion_are_exact(self) -> None:
        module = load_module(self.target / ".agent/scripts/octon_autonomous_delivery.py", "octon_usage_warning")
        self.assertIsNone(module.usage_warning(69, 100))
        self.assertEqual(module.usage_warning(70, 100), "warning_70_percent")
        self.assertEqual(module.usage_warning(85, 100), "warning_85_percent")
        self.assertEqual(module.usage_warning(95, 100), "warning_95_percent")
        self.assertEqual(module.usage_warning(100, 100), "exhausted")

    def test_usage_state_is_digest_bound_warned_and_stops_at_full_limit(self) -> None:
        record_path, _confirmation_path, cost_path, _contract = self.accepted_records()
        record = json.loads(record_path.read_text(encoding="utf-8"))
        compute = json.loads(cost_path.read_text(encoding="utf-8"))
        module = load_module(self.target / ".agent/scripts/octon_autonomous_delivery.py", "octon_usage_validation")
        counts = {key: 0 for key in module.USAGE_KEYS}
        counts["work_iterations"] = 350
        value = {
            "schema_version": "harness.autonomous-delivery-usage.v2",
            "artifact_kind": "autonomous_delivery_usage_state",
            "permission_grant": False,
            "authorization_record_digest": record["accepted_record_digest"],
            "run_id": "synthetic-run",
            "counts": counts,
            "compute_mode": "metered_api",
            "compute_evidence_fingerprint": compute["evidence_fingerprint"],
            "metered_api_usage": {"run_usd": 175.0, "authorization_usd": 175.0},
            "included_subscription_usage": None,
            "warnings": ["metered_api_run_usd:warning_70_percent", "work_iterations:warning_70_percent"],
            "exhausted": False,
            "observed_at": module.utc_text(),
        }
        value["usage_digest"] = module.digest(value)
        validator = load_module(self.target / ".agent/scripts/validate.py", "octon_metered_usage_schema")
        schema = json.loads((self.target / ".agent/schemas/harness-autonomous-delivery.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(validator.validate_schema(value, schema["$defs"]["usage"], root_schema=schema), [])
        self.assertEqual(module.validate_usage(value, record, compute), value)
        exhausted = json.loads(json.dumps(value))
        exhausted["counts"]["work_iterations"] = 500
        exhausted["warnings"] = ["metered_api_run_usd:warning_70_percent", "work_iterations:exhausted"]
        exhausted["exhausted"] = True
        exhausted["usage_digest"] = module.digest({key: item for key, item in exhausted.items() if key != "usage_digest"})
        with self.assertRaisesRegex(module.DeliveryError, "usage is exhausted"):
            module.validate_usage(exhausted, record, compute)

    def test_subscription_usage_is_bound_to_current_readable_quota_windows(self) -> None:
        record_path, _confirmation_path, compute_path, _contract = self.accepted_records("included_subscription")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        compute = json.loads(compute_path.read_text(encoding="utf-8"))
        module = load_module(self.target / ".agent/scripts/octon_autonomous_delivery.py", "octon_subscription_usage")
        compute["included_subscription"]["quota_windows"][0]["used_percent"] = 70.0
        compute["evidence_fingerprint"] = module.digest({key: item for key, item in compute.items() if key != "evidence_fingerprint"})
        write_json(compute_path, compute)
        counts = {key: 0 for key in module.USAGE_KEYS}
        value = {
            "schema_version": module.USAGE_SCHEMA,
            "artifact_kind": "autonomous_delivery_usage_state",
            "permission_grant": False,
            "authorization_record_digest": record["accepted_record_digest"],
            "run_id": "synthetic-subscription-run",
            "counts": counts,
            "compute_mode": "included_subscription",
            "compute_evidence_fingerprint": compute["evidence_fingerprint"],
            "metered_api_usage": None,
            "included_subscription_usage": {
                "maximum_used_percent": 70.0,
                "quota_window_ids": ["rolling-provider-window"],
            },
            "warnings": ["included_subscription_allowance:warning_70_percent"],
            "exhausted": False,
            "observed_at": module.utc_text(),
        }
        value["usage_digest"] = module.digest(value)
        validator = load_module(self.target / ".agent/scripts/validate.py", "octon_subscription_usage_schema")
        schema = json.loads((self.target / ".agent/schemas/harness-autonomous-delivery.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(validator.validate_schema(value, schema["$defs"]["usage"], root_schema=schema), [])
        self.assertEqual(module.validate_usage(value, record, compute), value)
        stale = dict(value)
        stale["compute_evidence_fingerprint"] = "0" * 64
        stale["usage_digest"] = module.digest({key: item for key, item in stale.items() if key != "usage_digest"})
        with self.assertRaisesRegex(module.DeliveryError, "stale compute observation"):
            module.validate_usage(stale, record, compute)

    def test_source_work_completion_projection_maps_existing_owner_operations(self) -> None:
        record_path, confirmation_path, compute_path, _contract = self.accepted_records("included_subscription")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        compute = json.loads(compute_path.read_text(encoding="utf-8"))
        module = load_module(self.target / ".agent/scripts/octon_autonomous_delivery.py", "octon_source_completion_projection")
        counts = {key: 0 for key in module.USAGE_KEYS}
        usage = {
            "schema_version": module.USAGE_SCHEMA,
            "artifact_kind": "autonomous_delivery_usage_state",
            "permission_grant": False,
            "authorization_record_digest": record["accepted_record_digest"],
            "run_id": "synthetic-source-completion",
            "counts": counts,
            "compute_mode": "included_subscription",
            "compute_evidence_fingerprint": compute["evidence_fingerprint"],
            "metered_api_usage": None,
            "included_subscription_usage": {
                "maximum_used_percent": 25.0,
                "quota_window_ids": ["rolling-provider-window"],
            },
            "warnings": [],
            "exhausted": False,
            "observed_at": module.utc_text(),
        }
        usage["usage_digest"] = module.digest(usage)
        usage_path = self.area / "source-usage.json"
        write_json(usage_path, usage)
        operations = ["fetch_remote", "push_branch", "locate_pull_request", "open_pull_request", "observe_change_checks", "merge_pull_request", "delete_remote_branch"]
        plan = {
            "schema_version": "harness.source-work-completion-plan.v1",
            "task_ref": "external:codex-task:11111111-2222-3333-4444-555555555555",
            "repository": {"identity": "synthetic/autonomous-delivery", "remote": "origin"},
            "branches": {"default": "main", "task": "chore/autonomous-source-test"},
            "external_operations": operations,
        }
        plan["canonical_plan_digest"] = module.work_completion_digest(plan)
        plan_path = self.area / "source-work-plan.json"
        write_json(plan_path, plan)
        args = argparse.Namespace(
            authorization_record=str(record_path),
            confirmation_artifact=str(confirmation_path),
            cost_enforcement_artifact=str(compute_path),
            usage=str(usage_path),
            work_plan=str(plan_path),
            output=None,
        )
        projection = module.work_completion_authorization(args, self.target)
        self.assertEqual(projection["task_ref"], plan["task_ref"])
        self.assertEqual(projection["operations"], operations)
        self.assertTrue(any(item.startswith("compute_enforcement_artifact_ref:") for item in projection["constraints"]))
        validator = load_module(self.target / ".agent/scripts/validate.py", "octon_source_completion_authorization_schema")
        schema = json.loads((self.target / ".agent/schemas/harness-work-completion.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(validator.validate_schema(projection, schema["$defs"]["authorization"], root_schema=schema), [])
        stale_compute = json.loads(json.dumps(compute))
        stale_compute["valid_until"] = module.utc_text(module.utc_now() - timedelta(minutes=1))
        stale_compute["evidence_fingerprint"] = module.digest({key: value for key, value in stale_compute.items() if key != "evidence_fingerprint"})
        write_json(compute_path, stale_compute)
        with self.assertRaisesRegex(module.DeliveryError, "stale, future-dated, or contradictory"):
            module.work_completion_authorization(args, self.target)
        write_json(compute_path, compute)
        plan["external_operations"].append("raw_git_bypass")
        write_json(plan_path, plan)
        with self.assertRaisesRegex(module.DeliveryError, "exact digest"):
            module.work_completion_authorization(args, self.target)

    def test_deactivate_and_remove_retains_dormant_surface_and_external_record(self) -> None:
        self.activate()
        planned = self.octon(
            "delivery", "deactivate", "plan",
            "--status", "disabled",
            "--authority-source", "authority:synthetic-disposable-operator",
        )
        self.assertEqual(planned.returncode, 0, planned.stderr or planned.stdout)
        plan = json.loads(planned.stdout)
        plan_path = self.area / "deactivation-plan.json"
        write_json(plan_path, plan)
        applied = self.octon(
            "delivery", "deactivate", "apply",
            "--plan", str(plan_path),
            "--accept-digest", plan["canonical_plan_digest"],
        )
        self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
        remove_path = self.target / ".agent/transactions/plans/autonomous-remove.json"
        removal = run(
            [
                sys.executable, "-B", str(SCRIPT_ROOT / "package_project.py"), "plan",
                "--target", str(self.target), "--package", "autonomous-delivery",
                "--owner", "synthetic-disposable-operator",
                "--trust-decision-ref", "DEC-9100", "--remove",
                "--output", str(remove_path),
            ],
            REPO_ROOT,
        )
        self.assertEqual(removal.returncode, 0, removal.stderr or removal.stdout)
        remove_plan = json.loads(remove_path.read_text(encoding="utf-8"))
        removed = run(
            [sys.executable, "-B", str(SCRIPT_ROOT / "package_project.py"), "apply", "--target", str(self.target), "--plan", str(remove_path), "--accept-digest", remove_plan["canonical_plan_digest"]],
            REPO_ROOT,
        )
        self.assertEqual(removed.returncode, 0, removed.stderr or removed.stdout)
        project = json.loads((self.target / ".agent/project.json").read_text(encoding="utf-8"))
        self.assertEqual(project["autonomous_delivery"]["status"], "available_not_activated")
        capability_root = self.target / ".agent/capabilities/autonomous-delivery"
        self.assertFalse(any(path.is_file() or path.is_symlink() for path in capability_root.rglob("*")))
        self.assertTrue((self.target / ".agent/scripts/octon_autonomous_delivery.py").is_file())
        self.assertTrue((self.control / "SAC-01.json").is_file())
        checked = self.octon("check")
        self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
