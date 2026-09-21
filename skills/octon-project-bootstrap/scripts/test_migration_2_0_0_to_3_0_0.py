#!/usr/bin/env python3
"""Executable coverage for the Project Blueprint 2.0.0 to 3.0.0 migration."""

from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
MIGRATOR_PATH = SCRIPT_DIR / "migrate_2_0_0_to_3_0_0.py"
FIXTURE_ROOT = SCRIPT_DIR.parent / "fixtures/migrations/2.0.0-to-3.0.0"
VALID_PATH = FIXTURE_ROOT / "valid/v2-minimal.json"
EXPECTATIONS_PATH = FIXTURE_ROOT / "valid/expectations.json"
INVALID_ROOT = FIXTURE_ROOT / "invalid"


def load_migrator() -> Any:
    spec = importlib.util.spec_from_file_location("blueprint_v3_migrator", MIGRATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load migration module: {MIGRATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATOR = load_migrator()


def load_json(path: Path) -> dict[str, Any]:
    value, _ = MIGRATOR.load_json_document(path)
    return value


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def apply_operations(
    document: dict[str, Any], operations: list[dict[str, Any]]
) -> dict[str, Any]:
    result = copy.deepcopy(document)
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict) or set(operation) not in (
            {"op", "path"},
            {"op", "path", "value"},
        ):
            raise AssertionError(f"operation {index} has an invalid shape")
        path = operation["path"]
        if not isinstance(path, list) or not path:
            raise AssertionError(f"operation {index} path must be nonempty")
        parent: Any = result
        for segment in path[:-1]:
            parent = parent[segment]
        final = path[-1]
        if operation["op"] in {"add", "replace"}:
            parent[final] = copy.deepcopy(operation["value"])
        elif operation["op"] == "remove":
            del parent[final]
        else:
            raise AssertionError(f"operation {index} has unknown op")
    return result


def not_applicable_hook() -> dict[str, Any]:
    return {
        "status": "not_applicable",
        "owner": "fixture_owner",
        "rationale": "Synthetic adopted-harness preservation fixture.",
        "tool_name": None,
        "argv": None,
        "version_argv": None,
        "timeout_seconds": None,
        "evidence_freshness_days": None,
        "side_effects": {
            "classification": "not_applicable",
            "repository_write_paths": [],
            "external_effects": [],
        },
    }


class MigrationFixtureTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.source, self.source_bytes = MIGRATOR.load_json_document(VALID_PATH)
        self.expectations = load_json(EXPECTATIONS_PATH)
        self.result = MIGRATOR.migrate_document(self.source, self.source_bytes)

    def test_valid_fixture_migrates_against_current_v3_schemas(self) -> None:
        MIGRATOR.validate_migrated_result(self.result, replay=True)
        live = self.result["live"]
        self.assertEqual(live["project"]["schema_version"], "harness.project.v3")
        self.assertEqual(live["tools"]["schema_version"], "harness.tools.v2")
        self.assertEqual(
            live["validators"]["schema_version"], "harness.validators.v3"
        )
        self.assertEqual(
            live["git_workflows"]["schema_version"], "harness.git-workflows.v1"
        )
        self.assertEqual(live["origin"]["blueprint_version"], "3.0.0")
        self.assertEqual(live["origin"]["harness_kernel_version"], "3.0.0")

    def test_collaboration_and_workflow_are_never_inferred_or_adopted(self) -> None:
        profile = self.result["live"]["project"]["collaboration_profile"]
        self.assertEqual(profile, MIGRATOR.unknown_collaboration_profile())
        self.assertIs(profile["permission_grant"], False)
        self.assertEqual(profile["confidence"], "unknown")
        self.assertEqual(profile["workflow_selection"]["status"], "not_assessed")
        self.assertIsNone(profile["workflow_selection"]["base_workflow"])
        self.assertEqual(
            self.result["transformation"],
            {
                "project_commands_executed": False,
                "network_accessed": False,
                "collaborators_inferred": False,
                "workflow_recommended": False,
                "workflow_adopted": False,
                "hosted_state_assumed": False,
            },
        )

    def test_exact_operation_and_workflow_portfolio_is_installed(self) -> None:
        live = self.result["live"]
        self.assertEqual(
            len(live["tools"]["tools"]["git"]["operations"]),
            self.expectations["git_operation_count"],
        )
        self.assertEqual(
            len(live["tools"]["tools"]["hosted_change"]["operations"]),
            self.expectations["hosted_change_operation_count"],
        )
        self.assertEqual(
            live["git_workflows"]["supported_base_workflows"],
            self.expectations["supported_base_workflows"],
        )
        self.assertEqual(
            live["git_workflows"]["unsupported_state"],
            {
                "result": "unsupported_team_size",
                "threshold": 5,
                "enterprise_fallback": False,
            },
        )

    def test_stable_identity_authority_and_whole_harness_adoption_are_preserved(self) -> None:
        source_project = self.source["live"]["project"]
        result_project = self.result["live"]["project"]
        for field in (
            "id",
            "name",
            "repository_root",
            "profile",
            "adoption_status",
            "adoption_decision_ref",
        ):
            self.assertEqual(result_project["project"][field], source_project["project"][field])
        self.assertEqual(result_project["commands"], source_project["commands"])
        self.assertEqual(
            self.result["live"]["origin"]["authority"],
            self.source["live"]["origin"]["authority"],
        )
        self.assertEqual(
            self.result["live"]["origin"]["initial_generation"],
            self.source["live"]["origin"]["initial_generation"],
        )

        adopted = copy.deepcopy(self.source)
        adopted["live"]["project"]["project"]["adoption_status"] = "adopted"
        adopted["live"]["project"]["project"]["adoption_decision_ref"] = "DEC-3000"
        adopted["live"]["project"]["commands"] = {
            hook: not_applicable_hook() for hook in MIGRATOR.PROJECT_HOOKS
        }
        adopted_bytes = MIGRATOR.canonical_bytes(adopted)
        adopted_result = MIGRATOR.migrate_document(adopted, adopted_bytes)
        self.assertEqual(
            adopted_result["live"]["project"]["project"]["adoption_status"],
            "adopted",
        )
        self.assertEqual(
            adopted_result["live"]["project"]["project"]["adoption_decision_ref"],
            "DEC-3000",
        )
        self.assertEqual(
            adopted_result["live"]["project"]["collaboration_profile"]
            ["workflow_selection"]["status"],
            "not_assessed",
        )

    def test_origin_history_and_generated_inventory_are_advanced(self) -> None:
        origin = self.result["live"]["origin"]
        self.assertEqual(
            [item["id"] for item in origin["migration_history"]],
            self.expectations["migration_ids"],
        )
        for path in (
            ".agent/schemas/harness-git-workflows.schema.json",
            ".agent/templates/pull-request.md",
            ".agent/workflows/README.md",
            ".agent/workflows/github-adapter.md",
            ".agent/workflows/small-team-git.json",
        ):
            self.assertIn(path, origin["generated_paths"])

    def test_exact_rollback_bytes_and_idempotence_are_preserved(self) -> None:
        rollback = self.result["rollback_evidence"]
        self.assertEqual(
            base64.b64decode(rollback["source_bytes_base64"]), self.source_bytes
        )
        self.assertEqual(
            rollback["source_sha256"], hashlib.sha256(self.source_bytes).hexdigest()
        )
        self.assertEqual(rollback["live_state"], self.source["live"])
        reapplied = MIGRATOR.migrate_document(
            copy.deepcopy(self.result), MIGRATOR.canonical_bytes(self.result)
        )
        self.assertEqual(reapplied, self.result)

    def test_every_fail_closed_mutation_fixture_is_rejected(self) -> None:
        fixture_names = []
        for path in sorted(INVALID_ROOT.glob("*.json")):
            fixture_names.append(path.name)
            mutation = load_json(path)
            self.assertEqual(
                mutation["schema_version"],
                "project-blueprint.migration-invalid-mutation.2.0.0-to-3.0.0.v1",
            )
            candidate = apply_operations(self.source, mutation["operations"])
            with self.assertRaisesRegex(
                MIGRATOR.MigrationError, mutation["expected_error"]
            ):
                MIGRATOR.migrate_document(candidate, MIGRATOR.canonical_bytes(candidate))
        self.assertEqual(
            fixture_names,
            [
                "adopted-legacy-git-policy.json",
                "divergent-legacy-tools.json",
                "fabricated-collaboration-evidence.json",
                "fabricated-workflow-adoption.json",
                "mixed-live-project-version.json",
                "mixed-live-validator-version.json",
                "nonexternal-migration-authority.json",
            ],
        )

    def test_cli_check_is_read_only_and_output_is_collision_safe(self) -> None:
        before = snapshot(FIXTURE_ROOT)
        checked = subprocess.run(
            [sys.executable, "-B", str(MIGRATOR_PATH), "--input", str(VALID_PATH), "--check"],
            cwd=SCRIPT_DIR.parents[2],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)
        self.assertEqual(snapshot(FIXTURE_ROOT), before)
        summary = json.loads(checked.stdout)
        self.assertIs(summary["permission_grant"], False)
        self.assertIs(summary["network_accessed"], False)
        self.assertIs(summary["workflow_adopted"], False)

        with tempfile.TemporaryDirectory(prefix="blueprint-v3-migration-") as temp:
            output = Path(temp) / "result.json"
            materialized = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(MIGRATOR_PATH),
                    "--input",
                    str(VALID_PATH),
                    "--output",
                    str(output),
                ],
                cwd=SCRIPT_DIR.parents[2],
                capture_output=True,
                text=True,
                check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            self.assertEqual(
                materialized.returncode, 0, materialized.stderr or materialized.stdout
            )
            self.assertTrue(output.is_file())
            second = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(MIGRATOR_PATH),
                    "--input",
                    str(VALID_PATH),
                    "--output",
                    str(output),
                ],
                cwd=SCRIPT_DIR.parents[2],
                capture_output=True,
                text=True,
                check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to replace", second.stderr)

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
            cwd=SCRIPT_DIR.parents[2],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertNotEqual(in_place.returncode, 0)
        self.assertIn("in-place", in_place.stderr)
        self.assertEqual(snapshot(FIXTURE_ROOT), before)


if __name__ == "__main__":
    unittest.main()
