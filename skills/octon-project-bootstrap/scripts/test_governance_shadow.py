#!/usr/bin/env python3
"""Adverse binding, narrowing, budget, and compatibility qualification."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("governance_shadow_tests_subject", SCRIPTS / "governance_shadow.py")
assert SPEC and SPEC.loader
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)
FIXTURE = SCRIPTS.parent / "fixtures/governance-shadow/covered.json"


def reseal(value: dict, *, parents: bool = True, budgets: bool = True) -> dict:
    value["intent"]["digest"] = G.record_digest(value["intent"])
    for index, grant in enumerate(value["delegations"]):
        if parents and index:
            grant["parent_ref"] = G.delegation_reference(value["delegations"][index - 1])
        grant["digest"] = G.record_digest(grant)
        if budgets and index < len(value["controls"]["budget_snapshots"]):
            value["controls"]["budget_snapshots"][index]["delegation_ref"] = G.delegation_reference(grant)
    for key in ("action", "controls"):
        value[key]["digest"] = G.record_digest(value[key])
    return value


class GovernanceShadowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = G.load_input(FIXTURE)

    def assert_reason(self, reason: str, *, status: str = "uncovered", **kwargs) -> dict:
        result = G.evaluate(reseal(self.value, **kwargs))
        self.assertEqual(result["coverage"], status)
        self.assertIn(reason, result["reasons"])
        self.assertFalse(result["execution_authorized"])
        return result

    def test_covered_technical_decision_never_becomes_execution_authority(self) -> None:
        before = copy.deepcopy(self.value)
        result = G.evaluate(self.value)
        self.assertEqual(result["coverage"], "covered")
        self.assertFalse(result["permission_grant"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["reservations_created"])
        self.assertEqual(result["authority_authentication"], "not_performed")
        self.assertEqual(self.value, before)
        self.assertEqual(G.evaluate(self.value), result)
        self.assertEqual(result["result_digest"], G.digest({k: v for k, v in result.items() if k != "result_digest"}))

    def test_changed_plan_bytes_invalidate_action_binding(self) -> None:
        self.value["action"]["plan_digest"] = "0" * 64
        result = G.evaluate(self.value)
        self.assertEqual(result["coverage"], "uncovered")
        self.assertIn("action_digest_mismatch", result["reasons"])

    def test_intent_revision_and_work_contract_must_match(self) -> None:
        for mutation, reason in (
            (lambda v: v["action"]["intent_ref"].update(revision=2), "intent_lineage_mismatch"),
            (lambda v: v["work_binding"]["intent_ref"].update(digest="0" * 64), "intent_lineage_mismatch"),
            (lambda v: v["action"].update(work_contract_digest="0" * 64), "work_binding_mismatch"),
            (lambda v: v["action"].update(resources=["resource:unrelated"]), "action_exceeds_work_scope"),
        ):
            with self.subTest(reason=reason):
                self.setUp(); mutation(self.value); self.assert_reason(reason)

    def test_same_intent_identity_cannot_silently_change_bound_meaning(self) -> None:
        self.value["intent"]["interpretation"] = "Replace the principal's objective."
        self.assert_reason("intent_lineage_mismatch")

    def test_intent_supersession_requires_same_identity_and_older_revision(self) -> None:
        self.value["intent"]["supersedes"] = G.intent_reference(self.value["intent"])
        self.assert_reason("invalid_intent_supersession")

    def test_root_and_actor_identity_must_bind(self) -> None:
        for path, key, value, reason in (
            ("root", "issuer_ref", "principal:other", "root_delegation_binding_mismatch"),
            ("action", "actor_ref", "agent:other", "actor_not_delegated_subject"),
            ("action", "project_id", "other-project", "project_identity_mismatch"),
        ):
            with self.subTest(reason=reason):
                self.setUp(); target = self.value["delegations"][0] if path == "root" else self.value[path]
                target[key] = value; self.assert_reason(reason)

    def test_child_cannot_widen_any_scope_dimension(self) -> None:
        for key in G.SCOPE_SETS:
            with self.subTest(dimension=key):
                self.setUp(); self.value["delegations"][1]["scope"][key].append("extra:scope")
                self.assert_reason("child_scope_widening")

    def test_child_cannot_widen_limits_or_change_budget_unit(self) -> None:
        for limit in ("period_limits", "per_run_limits"):
            for unit in G.BUDGET_UNITS:
                with self.subTest(limit=limit, unit=unit):
                    self.setUp(); self.value["delegations"][1][limit][unit] = self.value["delegations"][0][limit][unit] + 1
                    self.assert_reason("child_limit_widening")
        self.setUp(); self.value["delegations"][1]["concurrency_limit"] = 3
        self.assert_reason("child_limit_widening")
        self.setUp(); self.value["delegations"][1]["compute_unit_ref"] = "unit:different"
        self.assert_reason("child_budget_unit_change")

    def test_child_cannot_extend_validity_or_subdelegation(self) -> None:
        self.value["delegations"][1]["valid_until"] = "2030-03-01T00:00:00Z"
        self.assert_reason("child_validity_widening")
        self.setUp(); self.value["delegations"][1]["remaining_delegation_depth"] = 1
        self.assert_reason("subdelegation_not_covered")
        self.setUp(); self.value["delegations"][0]["remaining_delegation_depth"] = 0
        self.assert_reason("subdelegation_not_covered")

    def test_child_cannot_remove_obligations_or_reservations(self) -> None:
        self.value["delegations"][1]["required_obligations"] = []
        self.assert_reason("child_obligation_weakening")
        self.setUp(); self.value["delegations"][1]["reserved_decision_classes"] = []
        self.assert_reason("child_reservation_weakening")

    def test_parent_digest_issuer_duplicates_and_cycles_fail_closed(self) -> None:
        self.value["delegations"][1]["parent_ref"]["digest"] = "0" * 64
        self.assert_reason("delegation_parent_or_issuer_mismatch", parents=False)
        self.setUp(); self.value["delegations"][1]["issuer_ref"] = "role:other"
        self.assert_reason("delegation_parent_or_issuer_mismatch")
        self.setUp(); self.value["delegations"][1]["id"] = self.value["delegations"][0]["id"]
        self.assert_reason("duplicate_delegation_identity")
        self.setUp(); self.value["delegations"][0]["parent_ref"] = G.delegation_reference(self.value["delegations"][1])
        self.assert_reason("root_delegation_binding_mismatch", parents=False)

    def test_revoking_any_ancestor_or_stopping_blocks_coverage(self) -> None:
        for grant in self.value["delegations"]:
            with self.subTest(grant=grant["id"]):
                self.value["controls"]["revoked_delegation_ids"] = [grant["id"]]
                self.assert_reason("delegation_revoked")
        self.setUp(); self.value["controls"]["emergency_stop"] = True
        self.assert_reason("emergency_stop")

    def test_expiry_is_half_open_and_future_grants_fail(self) -> None:
        self.value["delegations"][1]["valid_until"] = self.value["evaluation_time"]
        self.assert_reason("delegation_not_current")
        self.setUp(); self.value["delegations"][1]["valid_from"] = "2030-01-02T00:02:00Z"
        self.assert_reason("delegation_not_current")

    def test_stale_or_future_control_observation_is_indeterminate(self) -> None:
        self.value["controls"]["fresh_until"] = self.value["evaluation_time"]
        self.assert_reason("control_snapshot_stale_or_future", status="indeterminate")
        self.setUp(); self.value["controls"]["observed_at"] = "2030-01-02T00:02:00Z"
        self.assert_reason("control_snapshot_stale_or_future", status="indeterminate")

    def test_policy_and_expected_state_changes_invalidate_binding(self) -> None:
        for key, reason in (("policy_digest", "policy_digest_mismatch"), ("state_digest", "expected_state_mismatch")):
            with self.subTest(key=key):
                self.setUp(); self.value["controls"][key] = "0" * 64
                self.assert_reason(reason)

    def test_current_policy_intersects_grants(self) -> None:
        self.value["controls"]["policy_scope"]["operations"] = ["work.plan"]
        self.assert_reason("uncovered_operations")

    def test_control_source_and_changed_epoch_invalidate_old_action(self) -> None:
        self.value["controls"]["authority_controls_ref"] = "control:other-project"
        self.assert_reason("authority_control_source_mismatch")
        self.setUp(); self.value["controls"]["authority_epoch"] = 2
        self.assert_reason("authority_epoch_mismatch")

    def test_environment_data_destination_and_credentials_cannot_expand(self) -> None:
        for field, wanted, reason in (
            ("environment", "production", "uncovered_environments"),
            ("data_class", "private", "uncovered_data_classes"),
            ("destinations", ["destination:uncovered"], "uncovered_destinations"),
            ("credential_classes", ["credential:trunk-write"], "uncovered_credential_classes"),
        ):
            with self.subTest(field=field):
                self.setUp(); self.value["action"][field] = wanted; self.assert_reason(reason)

    def test_parent_period_usage_is_shared_even_when_child_has_capacity(self) -> None:
        self.value["controls"]["budget_snapshots"][0]["reserved"]["actions"] = 10
        self.assert_reason("shared_period_limit_exceeded")

    def test_per_run_limit_accounts_for_existing_committed_and_reserved_usage(self) -> None:
        self.value["action"].update(starts_run=False)
        for budget in self.value["controls"]["budget_snapshots"]:
            budget["committed"]["actions"] = 1
            budget["run_committed"]["actions"] = 1
            budget["reserved"]["actions"] = 1
            budget["run_reserved"]["actions"] = 1
            budget["active_runs"] = 1
        self.assert_reason("per_run_limit_exceeded")

    def test_unknown_usage_is_not_zero(self) -> None:
        for field, reason in (("committed", "budget_usage_unknown"), ("run_committed", "run_budget_usage_unknown")):
            with self.subTest(field=field):
                self.setUp(); self.value["controls"]["budget_snapshots"][0][field]["compute_units"] = None
                self.assert_reason(reason, status="indeterminate")

    def test_budget_snapshot_must_bind_exact_grant_and_run(self) -> None:
        self.value["controls"]["budget_snapshots"][0]["delegation_ref"]["digest"] = "0" * 64
        self.assert_reason("missing_exact_delegation_budget", status="indeterminate", budgets=False)
        self.setUp(); self.value["controls"]["budget_snapshots"][0]["run_ref"] = "run:other"
        self.assert_reason("run_budget_binding_mismatch", status="indeterminate")

    def test_active_run_ceiling_and_unknown_count(self) -> None:
        self.value["controls"]["budget_snapshots"][0]["active_runs"] = 2
        self.assert_reason("concurrency_limit_exceeded")
        self.setUp(); self.value["controls"]["budget_snapshots"][0]["active_runs"] = None
        self.assert_reason("active_run_count_unknown", status="indeterminate")

    def test_missing_failed_or_duplicate_obligations_never_pass(self) -> None:
        self.value["controls"]["obligation_results"] = []
        self.assert_reason("obligation_evidence_missing", status="indeterminate")
        self.setUp(); self.value["controls"]["obligation_results"][0]["outcome"] = "failed"
        self.assert_reason("mandatory_obligation_failed")
        self.setUp(); observation = copy.deepcopy(self.value["controls"]["obligation_results"][0])
        observation["outcome"] = "failed"; self.value["controls"]["obligation_results"].append(observation)
        self.assert_reason("duplicate_obligation_observation")

    def test_qualified_human_obligation_is_not_replaced_by_agent_claim(self) -> None:
        first = self.value["controls"]["obligation_results"][0]
        self.value["controls"]["qualified_human_obligations"] = [first["id"]]
        first["actor_kind"] = "agent"
        self.assert_reason("qualified_human_obligation_not_satisfied")
        first["actor_kind"] = "qualified_human"
        result = G.evaluate(reseal(self.value))
        self.assertEqual(result["coverage"], "covered")
        self.assertEqual(result["authority_authentication"], "not_performed")

    def test_wrong_action_or_stale_evidence_does_not_satisfy_obligation(self) -> None:
        self.value["controls"]["obligation_results"][0]["action_digest"] = "0" * 64
        self.assert_reason("obligation_action_binding_mismatch", status="indeterminate")
        self.setUp(); self.value["controls"]["obligation_results"][0]["fresh_until"] = self.value["evaluation_time"]
        self.assert_reason("obligation_evidence_stale_or_future", status="indeterminate")

    def test_material_plan_successor_needs_new_evidence_binding(self) -> None:
        self.value["action"]["plan_digest"] = G.digest({"different_plan": True})
        self.assert_reason("obligation_action_binding_mismatch", status="indeterminate")

    def test_capability_result_cannot_be_relabelled_as_canonical_work(self) -> None:
        self.value["work_binding"]["record_ref"] = "result:suite-completed"
        self.value["action"]["work_ref"] = "result:suite-completed"
        with self.assertRaises(G.GovernanceError): G.evaluate(reseal(self.value))

    def test_reserved_decision_or_sovereign_change_never_passes_technical_route(self) -> None:
        self.value["action"]["changes_sovereign_boundary"] = True
        self.assert_reason("sovereign_change_requires_principal_channel")
        self.setUp(); self.value["action"]["decision_class"] = "sovereign.intent"
        self.assert_reason("reserved_decision_class")

    def test_unknown_fields_versions_null_class_bool_count_and_wildcards_refuse(self) -> None:
        for mutate in (
            lambda v: v.update(schema_version="octon.governance-shadow-input.v99"),
            lambda v: v["action"].update(model_confidence=1),
            lambda v: v["action"].update(decision_class=None),
            lambda v: v["action"]["proposed_usage"].update(actions=True),
            lambda v: v["action"]["proposed_usage"].update(actions=0),
            lambda v: v["delegations"][0]["scope"].update(resources=["resource:*"]),
        ):
            with self.subTest(mutation=mutate):
                self.setUp(); mutate(self.value)
                with self.assertRaises(G.GovernanceError): G.evaluate(reseal(self.value))

    def test_duplicate_keys_nonfinite_and_large_inputs_refuse(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            path = Path(area) / "input.json"
            for data in ('{"x":1,"x":2}', '{"x":NaN}', ' ' * (G.MAX_BYTES + 1)):
                path.write_text(data)
                with self.assertRaises(G.GovernanceError): G.load_input(path)

    def test_symlink_input_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            path = Path(area) / "input.json"; path.write_text("{}")
            link = Path(area) / "link.json"
            try: link.symlink_to(path)
            except OSError as error:
                self.skipTest("Host cannot create the symlink fixture: " + str(error))
            with self.assertRaises(G.GovernanceError): G.load_input(link)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "Host has no FIFO fixture support")
    def test_fifo_input_refuses_without_waiting_for_a_writer(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            path = Path(area) / "pipe"; os.mkfifo(path)
            result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPTS / "governance_shadow.py"), "--input", str(path)], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(json.loads(result.stdout)["execution_authorized"])

    def test_cli_is_read_only_and_never_resolves_input_references(self) -> None:
        def source_hashes():
            return {
                str(path.relative_to(G.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in G.ROOT.rglob("*")
                if ".git" not in path.relative_to(G.ROOT).parts
                and "__pycache__" not in path.parts and path.name != ".DS_Store"
                and path.is_file() and not path.is_symlink()
            }
        with tempfile.TemporaryDirectory() as area:
            path = Path(area) / "input.json"; path.write_text(json.dumps(self.value))
            before = path.read_bytes()
            source_before = source_hashes()
            result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPTS / "governance_shadow.py"), "--input", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertFalse(value["execution_authorized"])
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual([p.name for p in Path(area).iterdir()], ["input.json"])
            self.assertEqual(source_hashes(), source_before)

    def test_source_registration_cannot_advertise_live_activation(self) -> None:
        metadata = G.CONTRACTS.load_json(G.ROOT / "octon.json")
        with tempfile.TemporaryDirectory() as area:
            root = Path(area); (root / "shared/source-contracts").mkdir(parents=True)
            (root / G.SCHEMA_PATH).write_bytes((G.ROOT / G.SCHEMA_PATH).read_bytes())
            for flag in ("generated", "runtime_authorization"):
                bad = copy.deepcopy(metadata)
                bad["source_governance"]["intent_delegation_foundation"][flag] = True
                (root / "octon.json").write_text(json.dumps(bad))
                self.assertTrue(G.validate_contract_source(root))

    def test_full_source_metadata_gate_accepts_the_explicit_registration(self) -> None:
        spec = importlib.util.spec_from_file_location("governance_full_metadata_gate", SCRIPTS / "validate_octon_mini.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        issues = []
        module.validate_config_and_schemas(issues, module.load_scaffolder())
        self.assertEqual(issues, [])

    def test_cli_diagnostics_do_not_echo_rejected_input_values(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            path = Path(area) / "input.json"
            self.value["information_role"] = "fixture-sensitive-material"
            path.write_text(json.dumps(self.value))
            result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPTS / "governance_shadow.py"), "--input", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("fixture-sensitive-material", result.stdout + result.stderr)
            self.assertFalse(json.loads(result.stdout)["execution_authorized"])

    def test_legacy_activation_rejects_shadow_records(self) -> None:
        path = SCRIPTS.parent / "assets/templates/core/.agent/scripts/octon_autonomous_delivery.py.tmpl"
        module = types.ModuleType("legacy_delivery_shadow_boundary")
        module.__file__ = str(path)
        exec(compile(path.read_text(), str(path), "exec"), module.__dict__)
        for value in (G.evaluate(self.value), self.value["delegations"][0]):
            with self.subTest(schema=value["schema_version"]):
                with self.assertRaises(module.DeliveryError): module.validate_record(value)

    def test_blueprint_1_origin_is_not_silently_upgraded(self) -> None:
        spec = importlib.util.spec_from_file_location("governance_legacy_upgrade_probe", SCRIPTS / "upgrade_project.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as area:
            target = Path(area); origin = target / ".project-blueprint-origin.json"
            original = b'{"schema_version":"project-blueprint.origin.v1","blueprint_version":"1.0.0","harness_kernel_version":"1.0.0","profile":"high-assurance"}\n'
            origin.write_bytes(original)
            with self.assertRaisesRegex(module.UpgradeError, "older snapshots through"):
                module.load_upgrade_origin(target)
            self.assertEqual(origin.read_bytes(), original)
            self.assertEqual([p.name for p in target.iterdir()], [origin.name])

    def test_generation_does_not_ship_shadow_contracts_or_authority(self) -> None:
        with tempfile.TemporaryDirectory() as area:
            target = Path(area) / "project"
            command = [sys.executable, "-B", str(SCRIPTS / "scaffold_project.py"), "--target", str(target), "--project-name", "Shadow Compatibility Fixture", "--profile", "minimal", "--layout", "compact"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for path in target.rglob("*"):
                if path.is_file():
                    data = path.read_bytes()
                    self.assertNotIn(b"harness.intent-revision.v1", data, str(path))
                    self.assertNotIn(b"octon.governance-shadow", data, str(path))
            checked = subprocess.run([sys.executable, "-B", str(target / "octon"), "check"], cwd=target, capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            policy = json.loads((target / ".agent/policy.json").read_text())
            self.assertFalse(policy["permission_grant"])
            project = json.loads((target / ".agent/project.json").read_text())
            delivery = project["autonomous_delivery"]
            self.assertEqual(delivery["status"], "available_not_activated")
            self.assertEqual(delivery["write_capability"], "locked")
            self.assertEqual(delivery["external_effects"], "locked")
            self.assertIsNone(delivery["authorization_record_ref"])
            self.assertIsNone(delivery["activation_receipt_ref"])


if __name__ == "__main__":
    unittest.main()
