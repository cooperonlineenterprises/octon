#!/usr/bin/env python3
"""Focused current/target installation binding and path refusal fixtures."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCAFFOLD_PATH = Path(__file__).resolve().parent / "scaffold_project.py"
ADOPTION_PATH = Path(__file__).resolve().parent / "plan_adoption.py"
UPGRADE_PATH = Path(__file__).resolve().parent / "upgrade_project.py"
SPEC = importlib.util.spec_from_file_location("octon_binding_scaffold", SCAFFOLD_PATH)
assert SPEC is not None and SPEC.loader is not None
scaffolder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scaffolder)


class InstallationBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = scaffolder.load_generation_policy()

    @staticmethod
    def rehash_target(manifest: dict[str, object]) -> None:
        target = manifest["installation_bindings"]["target"]
        inventory = target["file_inventory"]
        target["inventory_count"] = len(inventory)
        target["inventory_sha256"] = hashlib.sha256(
            json.dumps(inventory, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()

    def test_target_manifest_requires_version_and_complete_core_inventory(self) -> None:
        missing = copy.deepcopy(self.manifest)
        del missing["installation_bindings"]
        with self.assertRaises(ValueError):
            scaffolder.target_installation_contract(missing)
        wrong_version = copy.deepcopy(self.manifest)
        wrong_version["installation_bindings"]["target"]["schema_version"] = "unknown"
        with self.assertRaises(ValueError):
            scaffolder.target_installation_contract(wrong_version)
        wrong_count = copy.deepcopy(self.manifest)
        wrong_count["installation_bindings"]["target"]["inventory_count"] -= 1
        with self.assertRaises(ValueError):
            scaffolder.target_installation_contract(wrong_count)
        missing_root = copy.deepcopy(self.manifest)
        del missing_root["installation_bindings"]["target"]["root_bindings"]["agent"]
        with self.assertRaisesRegex(ValueError, "root inventory"):
            scaffolder.target_installation_contract(missing_root)
        missing_file = copy.deepcopy(self.manifest)
        inventory = missing_file["installation_bindings"]["target"]["file_inventory"]
        inventory[:] = [item for item in inventory if item["id"] != "harness.policy"]
        self.rehash_target(missing_file)
        with self.assertRaisesRegex(ValueError, "required identity"):
            scaffolder.target_installation_contract(missing_file)
        premature_generation = copy.deepcopy(self.manifest)
        premature_generation["installation_bindings"]["target"]["generation_status"] = "active"
        with self.assertRaises(ValueError):
            scaffolder.target_installation_contract(premature_generation)
        unqualified_rule = copy.deepcopy(self.manifest)
        unqualified_rule["installation_bindings"]["target"]["file_inventory"][0]["source_rule_id"] = "templates-core"
        self.rehash_target(unqualified_rule)
        with self.assertRaisesRegex(ValueError, "unqualified"):
            scaffolder.target_installation_contract(unqualified_rule)

    def test_target_manifest_rejects_escape_ownership_and_duplicate_state(self) -> None:
        escaped_root = copy.deepcopy(self.manifest)
        escaped_root["installation_bindings"]["target"]["root_bindings"]["agent"]["path"] = "../escape"
        with self.assertRaises(ValueError):
            scaffolder.target_installation_contract(escaped_root)
        escaped_file = copy.deepcopy(self.manifest)
        escaped_file["installation_bindings"]["target"]["file_inventory"][0]["path"] = "../escape"
        self.rehash_target(escaped_file)
        with self.assertRaises(ValueError):
            scaffolder.target_installation_contract(escaped_file)
        wrong_owner = copy.deepcopy(self.manifest)
        wrong_owner["installation_bindings"]["target"]["file_inventory"][6]["owner"] = "runtime_release"
        self.rehash_target(wrong_owner)
        with self.assertRaisesRegex(ValueError, "ownership"):
            scaffolder.target_installation_contract(wrong_owner)
        duplicate_state = copy.deepcopy(self.manifest)
        duplicate_state["installation_bindings"]["target"]["file_inventory"].append({
            "id": "harness.state.second-focus",
            "path": ".octon/agent/state/second-focus.json",
            "root_id": "agent",
            "owner": "project",
            "information_class": "authored",
            "tracking": "versioned",
            "minimum_profile": "minimal",
            "source_rule_id": None,
        })
        self.rehash_target(duplicate_state)
        with self.assertRaisesRegex(ValueError, "second live state"):
            scaffolder.target_installation_contract(duplicate_state)

    def test_current_manifest_and_recovery_paths_remain_exact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-current-binding-") as temporary:
            root = Path(temporary).resolve() / "project"
            root.mkdir()
            binding = scaffolder.InstallationBinding.current(root)
            with self.assertRaises(ValueError):
                scaffolder.InstallationBinding.current(Path("relative-project"))
            self.assertEqual(binding.layout_id, "current")
            self.assertEqual(binding.state_root, root / ".agent/state")
            self.assertEqual(binding.transaction_root, root / ".agent/transactions")
            self.assertEqual(
                scaffolder.origin_path(self.manifest, installation=binding),
                Path(".octon-origin.json"),
            )
            self.assertEqual(
                scaffolder.project_local_source_paths("minimal", self.manifest, installation=binding),
                scaffolder.project_local_source_paths("minimal", self.manifest),
            )
            self.assertIn(
                Path(".agent/state/current.json"),
                scaffolder.derived_output_paths("minimal", self.manifest, installation=binding),
            )
            self.assertIn(
                Path(".agent/policy.json"),
                scaffolder.kernel_paths(self.manifest, installation=binding),
            )
            records = {
                ".octon-origin.json": b"historical origin\n",
                ".agent/tasks/TASK-0001.md": b"project-owned task\n",
                ".agent/transactions/receipts/RCPT-0001.json": b"historical receipt\n",
            }
            for relative, content in records.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            self.assertEqual({key: (root / key).read_bytes() for key in records}, records)

    def test_target_layout_is_explicit_and_old_origin_is_not_an_alias(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-target-binding-") as temporary:
            root = Path(temporary).resolve() / "project"
            root.mkdir()
            binding = scaffolder.InstallationBinding.target(root, self.manifest)
            self.assertEqual(binding.layout_id, "oep1_target")
            self.assertEqual(binding.manifest_relative, Path(".octon/manifest.json"))
            self.assertEqual(binding.state_root, root / ".octon/agent/state")
            with self.assertRaises(ValueError):
                scaffolder.project_local_source_paths("minimal", self.manifest, installation=binding)
            with self.assertRaises(ValueError):
                scaffolder.origin_path(self.manifest, installation=binding)
            with self.assertRaises(ValueError):
                scaffolder.InstallationBinding("compact", root)

            target_manifest = copy.deepcopy(self.manifest)
            target_manifest["project_paths"]["project_local_sources"] = [
                {"path": ".octon/agent/state/focus.json", "minimum_profile": "minimal", "ownership": "project_owned"},
                {"path": ".octon/dossier/machine-readable/artifact-registry.json", "minimum_profile": "minimal", "ownership": "project_owned"},
            ]
            target_manifest["project_paths"]["derived_outputs"] = [
                {"path": ".octon/generated/validation-report.json", "minimum_profile": "minimal", "writer": "refresh", "ownership": "derived"},
            ]
            self.assertEqual(
                scaffolder.project_local_source_paths("minimal", target_manifest, installation=binding),
                {
                    Path(".octon/agent/state/focus.json"),
                    Path(".octon/dossier/machine-readable/artifact-registry.json"),
                },
            )
            self.assertEqual(
                scaffolder.derived_output_paths("minimal", target_manifest, installation=binding),
                {Path(".octon/generated/validation-report.json")},
            )

    def test_portable_paths_and_symlink_escape_refuse(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-confinement-") as temporary:
            root = Path(temporary).resolve() / "project"
            root.mkdir()
            binding = scaffolder.InstallationBinding.current(root)
            self.assertEqual(
                binding.project_source_path(".agent/state/focus.json", "fixture"),
                Path(".agent/state/focus.json"),
            )
            for unsafe in (
                "../escape", "/absolute", "//server/share", "C:/project/state",
                "C:relative", "C:\\project\\state", "\\\\server\\share", ".agent//state",
                ".agent/./state", ".agent/../state", ".agent/CON.txt",
                ".agent/CON .txt", ".agent/LPT1", ".agent/state.", ".agent/state ",
            ):
                with self.subTest(path=unsafe), self.assertRaises(ValueError):
                    binding.relative_path(unsafe, "fixture")
            outside = Path(temporary).resolve() / "outside"
            outside.mkdir()
            try:
                (root / ".agent").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("host cannot create a directory symlink")
            with self.assertRaisesRegex(ValueError, "escapes the project root"):
                scaffolder.project_local_source_paths("minimal", self.manifest, installation=binding)
            with self.assertRaisesRegex(ValueError, "escapes the project root"):
                binding.relative_path(".agent/scripts/validate.py", "intended template")
            result = subprocess.run(
                [sys.executable, "-B", str(ADOPTION_PATH), "--target", str(root), "--profile", "minimal", "--format", "json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("path escapes the project root", result.stderr)
            self.assertEqual([path.name for path in root.iterdir()], [".agent"])

    def test_reserved_collision_and_moved_root_require_explicit_binding(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-moved-binding-") as temporary:
            area = Path(temporary).resolve()
            old = area / "old"
            old.mkdir()
            (old / ".OCTON").mkdir()
            with self.assertRaisesRegex(ValueError, "reserved-path disposition"):
                scaffolder.InstallationBinding.target(old, self.manifest)
            (old / ".OCTON").rmdir()
            (old / ".octon").write_text("unclassified occupant\n")
            with self.assertRaisesRegex(ValueError, "reserved-path disposition"):
                scaffolder.InstallationBinding.target(old, self.manifest)
            (old / ".octon").unlink()
            (old / ".agent").mkdir()
            with self.assertRaisesRegex(ValueError, "reserved-path disposition"):
                scaffolder.InstallationBinding.target(old, self.manifest)
            (old / ".agent/state").mkdir()
            (old / ".agent/state/focus.json").write_text("owner intent\n")
            before = scaffolder.InstallationBinding.current(old)
            moved = area / "moved"
            old.rename(moved)
            after = scaffolder.InstallationBinding.current(moved)
            self.assertEqual(before.state_root, old / ".agent/state")
            self.assertEqual(after.state_root, moved / ".agent/state")
            self.assertEqual(after.transaction_root, moved / ".agent/transactions")
            self.assertEqual((moved / ".agent/state/focus.json").read_text(), "owner intent\n")
            target_old = area / "target-old"
            target_old.mkdir()
            target_before = scaffolder.InstallationBinding.target(target_old, self.manifest)
            target_moved = area / "target-moved"
            target_old.rename(target_moved)
            target_after = scaffolder.InstallationBinding.target(target_moved, self.manifest)
            self.assertEqual(target_before.state_root, target_old / ".octon/agent/state")
            self.assertEqual(target_after.state_root, target_moved / ".octon/agent/state")

    def test_occupied_target_root_refuses_adoption_and_upgrade(self) -> None:
        for reserved_name in (".octon", ".OCTON", ".Octon"):
            with self.subTest(reserved_name=reserved_name):
                with tempfile.TemporaryDirectory(prefix="octon-entry-binding-") as temporary:
                    area = Path(temporary).resolve()
                    root = area / "project"
                    root.mkdir()
                    (root / reserved_name).mkdir()
                    adoption = subprocess.run(
                        [sys.executable, "-B", str(ADOPTION_PATH), "--target", str(root), "--profile", "minimal"],
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(adoption.returncode, 2)
                    self.assertIn("occupied target installation path", adoption.stderr)
                    upgrade = subprocess.run(
                        [
                            sys.executable, "-B", str(UPGRADE_PATH), "plan", "--target", str(root),
                            "--output", str(area / "upgrade-plan.json"),
                        ],
                        capture_output=True, text=True, check=False,
                    )
                    self.assertNotEqual(upgrade.returncode, 0)
                    self.assertIn("original Octon runtime installation conflicts", upgrade.stderr)
                    self.assertFalse((area / "upgrade-plan.json").exists())

    def test_live_state_has_one_explicit_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-state-binding-") as temporary:
            area = Path(temporary).resolve()
            root = area / "project"
            root.mkdir()
            external = area / "state"
            external.mkdir()
            binding = scaffolder.InstallationBinding.target(
                root, self.manifest, state_owner="external", external_state_root=external
            )
            self.assertEqual(binding.state_root, external)
            with self.assertRaisesRegex(ValueError, "conflicts with the external owner"):
                binding.project_source_path(".octon/agent/state/focus.json", "fixture")
            with self.assertRaisesRegex(ValueError, "conflicts with the external owner"):
                binding.derived_path(".octon/agent/state/current.json", "fixture")
            with self.assertRaises(ValueError):
                scaffolder.InstallationBinding.target(root, self.manifest, state_owner="external")
            with self.assertRaises(ValueError):
                scaffolder.InstallationBinding.target(root, self.manifest, external_state_root=external)
            with self.assertRaises(ValueError):
                scaffolder.InstallationBinding.target(
                    root, self.manifest, state_owner="external", external_state_root=root / "local-state"
                )
            with self.assertRaises(ValueError):
                scaffolder.InstallationBinding(
                    "current", root, state_owner="external", external_state_root=external
                )


if __name__ == "__main__":
    unittest.main()
