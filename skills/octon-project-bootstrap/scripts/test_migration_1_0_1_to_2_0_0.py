#!/usr/bin/env python3
"""Isolated executable coverage for the 1.0.1 to 2.0.0 migration."""

from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
MIGRATOR_PATH = SCRIPT_DIR / "migrate_1_0_1_to_2_0_0.py"
FIXTURE_ROOT = (
    SCRIPT_DIR.parent
    / "fixtures"
    / "migrations"
    / "1.0.1-to-2.0.0"
)
VALID_PATH = FIXTURE_ROOT / "valid" / "v1-standard.json"
EXPECTATIONS_PATH = FIXTURE_ROOT / "valid" / "expectations.json"
INVALID_ROOT = FIXTURE_ROOT / "invalid"


def load_migrator() -> Any:
    spec = importlib.util.spec_from_file_location("blueprint_v2_migrator", MIGRATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load migration module: {MIGRATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATOR = load_migrator()


def load_json(path: Path) -> dict[str, Any]:
    value, _ = MIGRATOR.load_json_document(path)
    return value


def fixture_tree_snapshot() -> dict[str, str]:
    return {
        path.relative_to(FIXTURE_ROOT).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(FIXTURE_ROOT.rglob("*"))
        if path.is_file()
    }


def apply_operations(
    document: dict[str, Any], operations: list[dict[str, Any]]
) -> dict[str, Any]:
    result = copy.deepcopy(document)
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise AssertionError(f"operation {index} must be an object")
        if set(operation) not in ({"op", "path"}, {"op", "path", "value"}):
            raise AssertionError(f"operation {index} has an invalid closed shape")
        path = operation["path"]
        if not isinstance(path, list) or not path:
            raise AssertionError(f"operation {index} path must be a nonempty array")
        parent: Any = result
        for segment in path[:-1]:
            if isinstance(parent, dict) and isinstance(segment, str):
                parent = parent[segment]
            elif isinstance(parent, list) and isinstance(segment, int):
                parent = parent[segment]
            else:
                raise AssertionError(
                    f"operation {index} cannot traverse segment {segment!r}"
                )
        final = path[-1]
        if operation["op"] == "remove":
            if isinstance(parent, dict) and isinstance(final, str):
                del parent[final]
            elif isinstance(parent, list) and isinstance(final, int):
                del parent[final]
            else:
                raise AssertionError(
                    f"operation {index} cannot remove segment {final!r}"
                )
        elif operation["op"] == "replace":
            if "value" not in operation:
                raise AssertionError(f"operation {index} replacement lacks a value")
            if isinstance(parent, dict) and isinstance(final, str) and final in parent:
                parent[final] = copy.deepcopy(operation["value"])
            elif (
                isinstance(parent, list)
                and isinstance(final, int)
                and 0 <= final < len(parent)
            ):
                parent[final] = copy.deepcopy(operation["value"])
            else:
                raise AssertionError(
                    f"operation {index} cannot replace segment {final!r}"
                )
        else:
            raise AssertionError(f"operation {index} has unknown op")
    return result


class MigrationFixtureTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.source, self.source_bytes = MIGRATOR.load_json_document(VALID_PATH)
        self.expectations = load_json(EXPECTATIONS_PATH)
        self.result = MIGRATOR.migrate_document(self.source, self.source_bytes)

    def test_valid_fixture_migrates_against_current_v2_schemas(self) -> None:
        MIGRATOR.validate_migrated_result(self.result, replay=True)
        live = self.result["live"]
        self.assertEqual(live["lifecycle"]["schema_version"], "harness.lifecycle.v2")
        self.assertEqual(live["plan"]["schema_version"], "project.dossier.plan.v2")
        self.assertEqual(live["project"]["schema_version"], "harness.project.v2")
        self.assertEqual(
            live["project"]["project"]["blueprint_version"], "2.0.0"
        )
        self.assertTrue(
            all(task["schema_version"] == "harness.task.v2" for task in live["tasks"])
        )
        self.assertEqual(
            live["validators"]["schema_version"], "harness.validators.v2"
        )
        self.assertEqual(live["validators"]["validator_version"], "2.0.0")
        self.assertEqual(live["origin"]["blueprint_version"], "2.0.0")
        self.assertEqual(live["origin"]["generator_version"], "2.0.0")
        self.assertEqual(live["origin"]["harness_kernel_version"], "2.0.0")

    def test_stable_ids_and_authority_are_preserved(self) -> None:
        source_tasks = {task["id"]: task for task in self.source["live"]["tasks"]}
        result_tasks = {task["id"]: task for task in self.result["live"]["tasks"]}
        self.assertEqual(sorted(source_tasks), self.expectations["task_ids"])
        self.assertEqual(sorted(result_tasks), self.expectations["task_ids"])
        self.assertEqual(
            {
                task_id: task["authority_basis"]
                for task_id, task in result_tasks.items()
            },
            self.expectations["preserved_task_authority"],
        )

        source_plan_ids = sorted(
            item["id"] for item in self.source["live"]["plan"]["plan_items"]
        )
        result_plan_ids = sorted(
            item["id"] for item in self.result["live"]["plan"]["plan_items"]
        )
        self.assertEqual(source_plan_ids, self.expectations["plan_ids"])
        self.assertEqual(result_plan_ids, self.expectations["plan_ids"])

        source_origin = self.source["live"]["origin"]
        result_origin = self.result["live"]["origin"]
        self.assertEqual(result_origin["authority"], source_origin["authority"])
        self.assertEqual(
            result_origin["initial_generation"], source_origin["initial_generation"]
        )
        self.assertEqual(
            result_origin["migration_history"][:-1],
            source_origin["migration_history"],
        )
        self.assertEqual(result_origin["migration_history"][-1], self.source["migration"])
        self.assertEqual(
            [item["id"] for item in result_origin["migration_history"]],
            self.expectations["origin_migration_ids"],
        )
        self.assertEqual(
            [item["authority_source"] for item in result_origin["migration_history"]],
            self.expectations["origin_authority_sources"],
        )
        source_project = self.source["live"]["project"]["project"]
        result_project = self.result["live"]["project"]["project"]
        for field in (
            "id",
            "name",
            "repository_root",
            "profile",
            "adoption_status",
            "adoption_decision_ref",
        ):
            self.assertEqual(result_project[field], source_project[field])
        self.assertEqual(
            result_project["adoption_status"],
            self.expectations["project_adoption_status"],
        )

    def test_project_command_contracts_are_explicit_but_never_executed(self) -> None:
        project = self.result["live"]["project"]
        commands = project["commands"]
        self.assertEqual(
            {hook: command["status"] for hook, command in commands.items()},
            self.expectations["project_command_statuses"],
        )
        self.assertNotIn("run", commands["project_test"])
        self.assertEqual(
            commands["project_test"]["argv"],
            ["python", "-B", "-m", "unittest", "discover", "-s", "tests"],
        )
        self.assertEqual(
            commands["project_test"]["side_effects"]["classification"],
            "read_only",
        )
        self.assertEqual(
            commands["project_lint"]["side_effects"]["classification"],
            "not_applicable",
        )
        self.assertEqual(project["project_checks"], MIGRATOR.PROJECT_CHECKS_CONTRACT)
        dispositions = self.result["project_command_dispositions"]
        self.assertEqual(
            {item["hook"]: item["action"] for item in dispositions},
            self.expectations["project_command_actions"],
        )
        for item in dispositions:
            self.assertFalse(item["legacy_run_interpreted"])
            self.assertFalse(item["check_executed"])
            self.assertFalse(item["evidence_created"])
        self.assertNotIn("project-checks", self.result["live"])

    def test_validator_contract_gains_v2_readiness_and_adoption_entry_points(self) -> None:
        validators = self.result["live"]["validators"]
        self.assertEqual(
            sorted(validators["commands"]),
            self.expectations["validator_command_names"],
        )
        self.assertEqual(
            validators["commands"]["ready_frontier"]["writes"], []
        )
        self.assertEqual(
            validators["commands"]["project_checks"]["writes"],
            [".agent/project-checks/evidence.json"],
        )
        self.assertEqual(
            validators["commands"]["adoption_verify"]["writes"],
            "project_check_evidence_and_profile_refresh_outputs",
        )
        self.assertEqual(
            validators["commands"]["refresh"],
            self.source["live"]["validators"]["commands"]["refresh"],
        )
        self.assertIn(
            "project_command_assessment_and_current_evidence",
            validators["required_core_checks"],
        )

    def test_hard_dependencies_links_and_advisories_remain_distinct(self) -> None:
        tasks = {task["id"]: task for task in self.result["live"]["tasks"]}
        plans = {
            item["id"]: item
            for item in self.result["live"]["plan"]["plan_items"]
        }
        self.assertEqual(
            {task_id: task["dependencies"] for task_id, task in tasks.items()},
            self.expectations["task_hard_dependencies"],
        )
        self.assertEqual(
            {task_id: task["plan_item_refs"] for task_id, task in tasks.items()},
            self.expectations["task_plan_item_refs"],
        )
        self.assertEqual(
            {plan_id: plan["depends_on"] for plan_id, plan in plans.items()},
            self.expectations["plan_hard_dependencies"],
        )
        self.assertEqual(
            {plan_id: plan["task_refs"] for plan_id, plan in plans.items()},
            self.expectations["plan_task_refs"],
        )
        self.assertEqual(
            self.result["advisory_relationships"],
            self.expectations["advisory_relationships"],
        )
        readiness_fields: list[str] = []
        for task in tasks.values():
            readiness_fields.extend(task["dependencies"])
            readiness_fields.extend(task["plan_item_refs"])
            readiness_fields.extend(task["gate_refs"])
            readiness_fields.extend(task["blocking_refs"])
        for plan in plans.values():
            readiness_fields.extend(plan["depends_on"])
            readiness_fields.extend(plan["task_refs"])
            readiness_fields.extend(plan["gate_refs"])
            readiness_fields.extend(plan["blocking_refs"])
        self.assertNotIn("REQ-0001", readiness_fields)
        self.assertNotIn("REQ-0002", readiness_fields)

    def test_second_application_is_an_exact_no_op(self) -> None:
        encoded = MIGRATOR.pretty_json_bytes(self.result)
        reapplied = MIGRATOR.migrate_document(self.result, encoded)
        self.assertEqual(reapplied, self.result)
        self.assertEqual(
            MIGRATOR.pretty_json_bytes(reapplied),
            MIGRATOR.pretty_json_bytes(self.result),
        )

    def test_rollback_retains_exact_source_bytes_and_live_state(self) -> None:
        rollback = self.result["rollback_evidence"]
        restored_bytes = base64.b64decode(
            rollback["source_bytes_base64"], validate=True
        )
        self.assertEqual(restored_bytes, self.source_bytes)
        self.assertEqual(
            hashlib.sha256(restored_bytes).hexdigest(), rollback["source_sha256"]
        )
        self.assertEqual(rollback["live_state"], self.source["live"])
        self.assertEqual(
            hashlib.sha256(
                MIGRATOR.canonical_json_bytes(self.source["live"])
            ).hexdigest(),
            rollback["live_state_sha256"],
        )
        self.assertEqual(rollback["live_state_role"], "noncurrent_rollback_evidence")
        self.assertFalse(rollback["permission_grant"])
        self.assertEqual(rollback["authority_effect"], "none")

    def test_live_authority_is_v2_only_while_rollback_is_explicitly_noncurrent(self) -> None:
        live = self.result["live"]
        self.assertEqual(live["lifecycle"]["schema_version"], "harness.lifecycle.v2")
        self.assertEqual(live["plan"]["schema_version"], "project.dossier.plan.v2")
        self.assertEqual(live["project"]["schema_version"], "harness.project.v2")
        self.assertEqual(
            live["validators"]["schema_version"], "harness.validators.v2"
        )
        self.assertEqual(
            {task["schema_version"] for task in live["tasks"]}, {"harness.task.v2"}
        )
        rollback_live = self.result["rollback_evidence"]["live_state"]
        self.assertEqual(
            rollback_live["lifecycle"]["schema_version"], "harness.lifecycle.v1"
        )
        self.assertEqual(
            rollback_live["plan"]["schema_version"], "project.dossier.plan.v1"
        )
        self.assertEqual(
            rollback_live["project"]["schema_version"], "harness.project.v1"
        )
        self.assertEqual(
            rollback_live["validators"]["schema_version"],
            "harness.validators.v1",
        )
        self.assertEqual(
            {task["schema_version"] for task in rollback_live["tasks"]},
            {"harness.task.v1"},
        )

    def test_lifecycle_routes_blocked_and_reopened_through_ready(self) -> None:
        task = self.result["live"]["lifecycle"]["task"]
        self.assertEqual(task["transitions"]["blocked"], ["ready", "cancelled"])
        self.assertEqual(task["transitions"]["reopened"], ["ready", "cancelled"])
        self.assertEqual(
            task["transitions"]["ready"],
            ["in_progress", "blocked", "cancelled"],
        )
        self.assertEqual(
            task["gates"]["ready"],
            [
                "scope",
                "authority_basis",
                "acceptance_criteria",
                "validation_plan",
                "dependencies_satisfied",
                "gates_satisfied",
                "blocking_refs_resolved",
                "plan_links_consistent",
            ],
        )

    def test_tampered_migrated_authority_fails_deterministic_replay(self) -> None:
        tampered = copy.deepcopy(self.result)
        tampered["live"]["tasks"][0]["authority_basis"] = "authority:DEC-9999"
        with self.assertRaisesRegex(
            MIGRATOR.MigrationError, "differs from deterministic replay"
        ):
            MIGRATOR.migrate_document(tampered, MIGRATOR.pretty_json_bytes(tampered))

    def test_invalid_and_ambiguous_fixture_cases_fail_closed(self) -> None:
        paths = sorted(INVALID_ROOT.glob("*.json"))
        self.assertGreaterEqual(len(paths), 6)
        for path in paths:
            with self.subTest(case=path.name):
                case = load_json(path)
                self.assertEqual(
                    case.get("schema_version"),
                    "project-blueprint.migration-invalid-case.v1",
                )
                self.assertEqual(case.get("base"), "../valid/v1-standard.json")
                mutated = apply_operations(self.source, case["operations"])
                raw = MIGRATOR.pretty_json_bytes(mutated)
                with self.assertRaisesRegex(
                    MIGRATOR.MigrationError,
                    re_escape(case["expected_error"]),
                ):
                    MIGRATOR.migrate_document(mutated, raw)

    def test_check_cli_is_read_only(self) -> None:
        before_bytes = VALID_PATH.read_bytes()
        before_tree = fixture_tree_snapshot()
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(MIGRATOR_PATH),
                "--input",
                str(VALID_PATH),
                "--check",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertFalse(report["would_write"])
        self.assertEqual(report["authority_effect"], "none")
        self.assertFalse(report["readiness_claim"])
        self.assertFalse(report["project_checks_executed"])
        self.assertFalse(report["legacy_project_command_strings_interpreted"])
        self.assertEqual(VALID_PATH.read_bytes(), before_bytes)
        self.assertEqual(fixture_tree_snapshot(), before_tree)

    def test_writer_refuses_in_place_and_existing_destinations(self) -> None:
        before = VALID_PATH.read_bytes()
        in_place = subprocess.run(
            [
                sys.executable,
                "-B",
                str(MIGRATOR_PATH),
                "--input",
                str(VALID_PATH),
                "--output",
                str(VALID_PATH),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(in_place.returncode, 0)
        self.assertIn("in-place migration is prohibited", in_place.stderr)
        self.assertEqual(VALID_PATH.read_bytes(), before)

        with tempfile.TemporaryDirectory(prefix="blueprint-migration-test-") as temporary:
            root = Path(temporary)
            first = root / "migrated.json"
            second = root / "migrated-again.json"
            first_run = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(MIGRATOR_PATH),
                    "--input",
                    str(VALID_PATH),
                    "--output",
                    str(first),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(first_run.returncode, 0, first_run.stderr)
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o600)
            second_run = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(MIGRATOR_PATH),
                    "--input",
                    str(first),
                    "--output",
                    str(second),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(second_run.returncode, 0, second_run.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            existing_before = first.read_bytes()
            overwrite = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(MIGRATOR_PATH),
                    "--input",
                    str(VALID_PATH),
                    "--output",
                    str(first),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(overwrite.returncode, 0)
            self.assertIn("refusing replacement", overwrite.stderr)
            self.assertEqual(first.read_bytes(), existing_before)


def re_escape(value: str) -> str:
    """Escape fixture-owned expected text for assertRaisesRegex."""

    import re

    return re.escape(value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
