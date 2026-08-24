#!/usr/bin/env python3
"""Focused cross-platform tests for extensionless Octon launchers."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
REPOSITORY_ROOT = next(
    candidate
    for candidate in (
        SCRIPT_ROOT.parents[2],
        SKILL_ROOT / "assets/octon-mini-source",
    )
    if (candidate / "octon").is_file()
    and (candidate / "shared/source-contracts/commands.json").is_file()
)
SOURCE_LAUNCHER = REPOSITORY_ROOT / "octon"
SOURCE_DISPATCHER = SCRIPT_ROOT / "octon.py"
COMMAND_MANIFEST = REPOSITORY_ROOT / "shared/source-contracts/commands.json"
GENERATED_LAUNCHER_TEMPLATE = SKILL_ROOT / "assets/templates/core/octon.tmpl"
CONTINUATION_TEMPLATE = SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_continuation.py.tmpl"


def command(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
        timeout=10,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def cache_residue(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}
    )


def copy_executable(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    destination.chmod(0o755)


def make_checkout(root: Path) -> Path:
    launcher = root / "octon"
    dispatcher = root / "skills/octon-mini-project-bootstrap/scripts/octon.py"
    manifest = root / "shared/source-contracts/commands.json"
    copy_executable(SOURCE_LAUNCHER, launcher)
    dispatcher.parent.mkdir(parents=True)
    shutil.copy2(SOURCE_DISPATCHER, dispatcher)
    continuation = root / "skills/octon-mini-project-bootstrap/assets/templates/core/.agent/scripts/octon_continuation.py.tmpl"
    continuation.parent.mkdir(parents=True)
    shutil.copy2(CONTINUATION_TEMPLATE, continuation)
    manifest.parent.mkdir(parents=True)
    shutil.copy2(COMMAND_MANIFEST, manifest)
    return launcher


class OctonLauncherTests(unittest.TestCase):
    def test_source_delivery_status_is_locked_read_only_and_available(self) -> None:
        before = cache_residue(REPOSITORY_ROOT)
        result = command(
            [sys.executable, "-B", str(SOURCE_LAUNCHER), "delivery", "status"],
            REPOSITORY_ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        value = json.loads(result.stdout)
        self.assertEqual(value["status"], "available_not_activated")
        self.assertEqual(value["write_capability"], "locked")
        self.assertEqual(value["external_effects"], "locked")
        self.assertFalse(value["authority_created"])
        self.assertEqual(cache_residue(REPOSITORY_ROOT), before)

    def test_source_launcher_is_extensionless_python_and_executable(self) -> None:
        text = SOURCE_LAUNCHER.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/usr/bin/env python3\n"))
        self.assertIn("sys.dont_write_bytecode = True", text)
        self.assertNotIn("#!/bin/sh", text)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(SOURCE_LAUNCHER.stat().st_mode), 0o755)

    def test_checkout_resolution_and_windows_interpreter_form_support_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon launcher test ") as temporary:
            root = Path(temporary) / "source checkout with spaces"
            launcher = make_checkout(root)
            result = command([sys.executable, "-B", str(launcher), "--help"], root)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("Octon Mini workflow interface", result.stdout)
            self.assertIn("python -B octon", result.stdout)
            self.assertIn("py -3 -B octon", result.stdout)
            self.assertEqual(cache_residue(root), [])
            if os.name != "nt":
                direct = command([str(launcher), "--help"], root)
                self.assertEqual(direct.returncode, 0, direct.stderr or direct.stdout)
                self.assertEqual(cache_residue(root), [])

    def test_installed_bundle_falls_back_to_skill_dispatcher(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon installed launcher ") as temporary:
            skill = Path(temporary) / "installed skill with spaces"
            bundle = skill / "assets/octon-mini-source"
            launcher = bundle / "octon"
            copy_executable(SOURCE_LAUNCHER, launcher)
            dispatcher = skill / "scripts/octon.py"
            dispatcher.parent.mkdir(parents=True)
            shutil.copy2(SOURCE_DISPATCHER, dispatcher)
            continuation = skill / "assets/templates/core/.agent/scripts/octon_continuation.py.tmpl"
            continuation.parent.mkdir(parents=True)
            shutil.copy2(CONTINUATION_TEMPLATE, continuation)
            manifest = bundle / "shared/source-contracts/commands.json"
            manifest.parent.mkdir(parents=True)
            shutil.copy2(COMMAND_MANIFEST, manifest)
            result = command([sys.executable, "-B", str(launcher), "--help"], bundle)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("Octon Mini workflow interface", result.stdout)
            self.assertFalse((bundle / "skills").exists())
            self.assertEqual(cache_residue(skill), [])

    def test_unknown_workflow_has_typed_no_change_continuation_and_no_force_surface(self) -> None:
        help_result = command([sys.executable, "-B", str(SOURCE_LAUNCHER), "--help"], REPOSITORY_ROOT)
        self.assertEqual(help_result.returncode, 0, help_result.stderr or help_result.stdout)
        self.assertNotIn("--force", help_result.stdout)
        blocked = command(
            [sys.executable, "-B", str(SOURCE_LAUNCHER), "unsupported-workflow"],
            REPOSITORY_ROOT,
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("OCTON-CMD-1001", blocked.stderr)
        self.assertIn("Nothing changed", blocked.stderr)
        self.assertIn('Argv: ["./octon", "--help"]', blocked.stderr)

    def test_generated_launcher_resolves_dispatcher_in_path_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon generated launcher ") as temporary:
            project = Path(temporary) / "generated project with spaces"
            launcher = project / "octon"
            copy_executable(GENERATED_LAUNCHER_TEMPLATE, launcher)
            dispatcher = project / ".agent/scripts/octon.py"
            dispatcher.parent.mkdir(parents=True)
            dispatcher.write_text(
                "import json, sys\n"
                "print(json.dumps({'argv': sys.argv[1:], 'dispatch_count': 1}))\n",
                encoding="utf-8",
            )
            result = command(
                [sys.executable, "-B", str(launcher), "check", "--json"], project
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(
                json.loads(result.stdout),
                {"argv": ["check", "--json"], "dispatch_count": 1},
            )
            self.assertEqual(cache_residue(project), [])
            if os.name != "nt":
                direct = command([str(launcher), "check"], project)
                self.assertEqual(direct.returncode, 0, direct.stderr or direct.stdout)
                self.assertEqual(json.loads(direct.stdout)["dispatch_count"], 1)

    def test_root_launcher_delegates_to_generated_dispatcher_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon no recursion ") as temporary:
            area = Path(temporary)
            source = area / "source with spaces"
            project = area / "project with spaces"
            launcher = make_checkout(source)
            scripts = project / ".agent/scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(COMMAND_MANIFEST, project / ".agent/commands.json")
            (scripts / "octon.py").write_text(
                "import json, sys\n"
                "print(json.dumps({'argv': sys.argv[1:], 'dispatch_count': 1}))\n",
                encoding="utf-8",
            )
            result = command(
                [sys.executable, "-B", str(launcher), "check", "--json"], project
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(
                json.loads(result.stdout),
                {"argv": ["check", "--json"], "dispatch_count": 1},
            )
            self.assertFalse((project / "octon").exists())
            self.assertEqual(cache_residue(area), [])

    def test_missing_or_symlinked_dispatcher_fails_without_recursion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon unsafe dispatcher ") as temporary:
            area = Path(temporary)
            root = area / "nested/source"
            launcher = root / "octon"
            copy_executable(SOURCE_LAUNCHER, launcher)
            missing = command([sys.executable, "-B", str(launcher), "--help"], root)
            self.assertEqual(missing.returncode, 2)
            self.assertIn("source dispatcher is unavailable", missing.stderr)

            candidate = root / "skills/octon-mini-project-bootstrap/scripts/octon.py"
            candidate.parent.mkdir(parents=True)
            try:
                candidate.symlink_to(launcher)
            except OSError:
                self.skipTest("symlink creation is unavailable on this platform")
            refused = command([sys.executable, "-B", str(launcher), "--help"], root)
            self.assertEqual(refused.returncode, 2)
            self.assertIn("source dispatcher is unavailable", refused.stderr)
            self.assertEqual(cache_residue(area), [])


if __name__ == "__main__":
    unittest.main()
