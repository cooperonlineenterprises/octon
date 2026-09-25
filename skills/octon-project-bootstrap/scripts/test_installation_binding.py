#!/usr/bin/env python3
"""Focused current/target installation binding and path refusal fixtures."""

from __future__ import annotations

import copy
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCAFFOLD_PATH = Path(__file__).resolve().parent / "scaffold_project.py"
ADOPTION_PATH = Path(__file__).resolve().parent / "plan_adoption.py"
SPEC = importlib.util.spec_from_file_location("octon_binding_scaffold", SCAFFOLD_PATH)
assert SPEC is not None and SPEC.loader is not None
scaffolder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scaffolder)


class InstallationBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = scaffolder.load_generation_policy()

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
            binding = scaffolder.InstallationBinding.target(root)
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
                scaffolder.InstallationBinding.target(old)
            (old / ".OCTON").rmdir()
            (old / ".octon").write_text("unclassified occupant\n")
            with self.assertRaisesRegex(ValueError, "reserved-path disposition"):
                scaffolder.InstallationBinding.target(old)
            (old / ".octon").unlink()
            (old / ".agent").mkdir()
            with self.assertRaisesRegex(ValueError, "reserved-path disposition"):
                scaffolder.InstallationBinding.target(old)
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

    def test_live_state_has_one_explicit_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-state-binding-") as temporary:
            area = Path(temporary).resolve()
            root = area / "project"
            root.mkdir()
            external = area / "state"
            external.mkdir()
            binding = scaffolder.InstallationBinding.target(
                root, state_owner="external", external_state_root=external
            )
            self.assertEqual(binding.state_root, external)
            with self.assertRaisesRegex(ValueError, "conflicts with the external owner"):
                binding.project_source_path(".octon/agent/state/focus.json", "fixture")
            with self.assertRaisesRegex(ValueError, "conflicts with the external owner"):
                binding.derived_path(".octon/agent/state/current.json", "fixture")
            with self.assertRaises(ValueError):
                scaffolder.InstallationBinding.target(root, state_owner="external")
            with self.assertRaises(ValueError):
                scaffolder.InstallationBinding.target(root, external_state_root=external)
            with self.assertRaises(ValueError):
                scaffolder.InstallationBinding.target(
                    root, state_owner="external", external_state_root=root / "local-state"
                )
            with self.assertRaises(ValueError):
                scaffolder.InstallationBinding(
                    "current", root, state_owner="external", external_state_root=external
                )


if __name__ == "__main__":
    unittest.main()
