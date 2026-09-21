#!/usr/bin/env python3
"""Run bounded, read-only archetype and hook-recipe detection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
RECIPE_ROOT = SKILL_ROOT / "assets/detectors/recipes"
MAX_RECIPE_READ = 256 * 1024
SHELL_EXECUTABLES = {
    "bash", "cmd", "cmd.exe", "dash", "fish", "ksh", "powershell",
    "powershell.exe", "pwsh", "pwsh.exe", "sh", "zsh",
}
INLINE_SHELL_FLAGS = {"-c", "/c", "-command", "-encodedcommand"}
HOOK_NAMES = {"project_test", "project_lint", "project_build", "project_closure"}


class DetectionError(ValueError):
    """The detector protocol or target boundary is invalid."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DetectionError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DetectionError(f"cannot read {path}: {error}") from error


def safe_marker(target: Path, raw: str) -> Path | None:
    relative = PurePosixPath(raw)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise DetectionError(f"unsafe detector marker: {raw!r}")
    candidate = target.joinpath(*relative.parts)
    if candidate.is_symlink() or not candidate.exists():
        return None
    try:
        candidate.resolve().relative_to(target.resolve())
    except ValueError as error:
        raise DetectionError(f"detector marker escapes target: {raw!r}") from error
    return candidate


def evidence(path: Path, target: Path, observed_at: str) -> dict[str, Any]:
    relative = path.relative_to(target).as_posix()
    if path.is_dir():
        payload = f"directory:{relative}".encode("utf-8")
        kind = "path"
        limitations = ["Directory presence only; descendants were not read by this evidence item."]
    elif path.is_file():
        size = path.stat().st_size
        if size > MAX_RECIPE_READ:
            payload = f"oversize-file:{relative}:{size}".encode("utf-8")
            kind = "path"
            limitations = ["File exceeds the 256 KiB detector content limit; only path and size were used."]
        else:
            payload = path.read_bytes()
            kind = "bounded_content"
            limitations = ["Content was read only to the bounded detector limit; no command was executed."]
    else:
        raise DetectionError(f"detector marker is not a file or directory: {relative}")
    return {
        "path": relative,
        "kind": kind,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "observed_at": observed_at,
        "limitations": limitations,
    }


def safe_argv(argv: Any, label: str) -> list[str]:
    if (
        not isinstance(argv, list)
        or not argv
        or any(not isinstance(item, str) or not item for item in argv)
    ):
        raise DetectionError(f"{label}: argv must be a nonempty string array")
    executable = Path(argv[0]).name.casefold()
    if executable in SHELL_EXECUTABLES:
        raise DetectionError(f"{label}: shell executables are prohibited")
    if any(item.casefold() in INLINE_SHELL_FLAGS for item in argv[1:]):
        raise DetectionError(f"{label}: inline shell flags are prohibited")
    for item in argv:
        normalized = item.replace("\\", "/")
        if ".." in PurePosixPath(normalized).parts:
            raise DetectionError(f"{label}: path traversal argument is prohibited")
    return argv


def load_recipes() -> list[dict[str, Any]]:
    recipes: list[dict[str, Any]] = []
    ids: set[str] = set()
    for path in sorted(RECIPE_ROOT.glob("*.json")):
        value = load_json(path)
        required = {"schema_version", "id", "markers", "archetypes", "hooks"}
        allowed = required | {"dynamic_strategy", "limitations"}
        if not isinstance(value, dict) or not required <= set(value) or set(value) - allowed:
            raise DetectionError(f"{path.name}: recipe uses an invalid closed contract")
        recipe_id = value.get("id")
        if (
            value.get("schema_version") != "octon-mini.bootstrap.detector-recipe.v1"
            or not isinstance(recipe_id, str)
            or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", recipe_id) is None
            or recipe_id in ids
            or not isinstance(value.get("markers"), list)
            or not value["markers"]
            or not isinstance(value.get("archetypes"), list)
            or not isinstance(value.get("hooks"), list)
            or ("limitations" in value and not isinstance(value.get("limitations"), list))
        ):
            raise DetectionError(f"{path.name}: invalid or duplicate recipe")
        value.setdefault(
            "limitations",
            ["Recipe-level limitations are supplemented by each proposed hook."],
        )
        for index, hook in enumerate(value["hooks"]):
            if (
                not isinstance(hook, dict)
                or hook.get("hook") not in HOOK_NAMES
                or hook.get("confidence") not in {"low", "medium", "high"}
                or not isinstance(hook.get("tool_name"), str)
                or not isinstance(hook.get("side_effects"), dict)
                or not isinstance(hook.get("limitations"), list)
            ):
                raise DetectionError(f"{path.name}: hook {index} is invalid")
            safe_argv(hook.get("argv"), f"{path.name} hook {index}")
            safe_argv(hook.get("version_argv"), f"{path.name} hook {index} version probe")
        ids.add(recipe_id)
        recipes.append(value)
    if not recipes:
        raise DetectionError("no detector recipes are installed")
    return recipes


def candidate_from_hook(
    recipe: dict[str, Any],
    hook: dict[str, Any],
    evidence_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "hook": hook["hook"],
        "recipe_id": recipe["id"],
        "tool_name": hook["tool_name"],
        "argv": hook["argv"],
        "version_argv": hook["version_argv"],
        "shell": False,
        "confidence": hook["confidence"],
        "side_effects": hook["side_effects"],
        "evidence": evidence_items,
        "override_required": True,
        "limitations": list(dict.fromkeys(recipe["limitations"] + hook["limitations"])),
    }


def dynamic_hooks(
    target: Path,
    recipe: dict[str, Any],
    marker_paths: list[Path],
    evidence_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    strategy = recipe.get("dynamic_strategy")
    hooks: list[dict[str, Any]] = []
    if strategy == "package_json_scripts":
        package = next((path for path in marker_paths if path.name == "package.json"), None)
        if package is None or package.stat().st_size > MAX_RECIPE_READ:
            return []
        value = load_json(package)
        scripts = value.get("scripts", {}) if isinstance(value, dict) else {}
        if not isinstance(scripts, dict):
            return []
        for hook_name, script_name in (
            ("project_test", "test"),
            ("project_lint", "lint"),
            ("project_build", "build"),
        ):
            if not isinstance(scripts.get(script_name), str):
                continue
            hooks.append(
                candidate_from_hook(
                    recipe,
                    {
                        "hook": hook_name,
                        "tool_name": "npm",
                        "argv": ["npm", "run", script_name],
                        "version_argv": ["npm", "--version"],
                        "confidence": "high",
                        "side_effects": {
                            "classification": "external_or_unknown",
                            "repository_write_paths": [],
                            "external_effects": ["package_script_effects_require_review"],
                        },
                        "limitations": ["The package script body may have arbitrary effects and was not interpreted as authorization."],
                    },
                    evidence_items,
                )
            )
    elif strategy == "java_build_marker":
        if any(path.name == "pom.xml" for path in marker_paths):
            tool, version, commands = "maven", ["mvn", "--version"], (
                ("project_test", ["mvn", "test"]),
                ("project_build", ["mvn", "verify"]),
            )
        else:
            tool, version, commands = "gradle", ["gradle", "--version"], (
                ("project_test", ["gradle", "test"]),
                ("project_build", ["gradle", "build"]),
            )
        for hook_name, argv in commands:
            hooks.append(candidate_from_hook(recipe, {
                "hook": hook_name, "tool_name": tool, "argv": argv,
                "version_argv": version, "confidence": "medium",
                "side_effects": {"classification": "external_or_unknown", "repository_write_paths": ["build", "target"], "external_effects": ["dependency_resolution_possible"]},
                "limitations": ["Build-tool availability, wrapper choice, and dependency effects require review."],
            }, evidence_items))
    elif strategy == "make_targets":
        makefile = next((path for path in marker_paths if path.is_file()), None)
        if makefile is None or makefile.stat().st_size > MAX_RECIPE_READ:
            return []
        try:
            text = makefile.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return []
        targets = set(re.findall(r"(?m)^([A-Za-z0-9_.-]+)\s*:(?![=])", text))
        for hook_name, names in (
            ("project_test", ("test", "check")),
            ("project_lint", ("lint",)),
            ("project_build", ("build",)),
            ("project_closure", ("closure",)),
        ):
            name = next((item for item in names if item in targets), None)
            if name is None:
                continue
            hooks.append(candidate_from_hook(recipe, {
                "hook": hook_name, "tool_name": "make", "argv": ["make", name],
                "version_argv": ["make", "--version"], "confidence": "medium",
                "side_effects": {"classification": "external_or_unknown", "repository_write_paths": [], "external_effects": ["make_recipe_effects_require_review"]},
                "limitations": ["The Make recipe body was not interpreted and may have arbitrary effects."],
            }, evidence_items))
    return hooks


def detect(target: Path) -> dict[str, Any]:
    if not target.is_absolute():
        raise DetectionError("--target must be an absolute path")
    target = target.resolve()
    if target.exists() and not target.is_dir():
        raise DetectionError("--target must be a directory")
    if not target.exists() and not target.parent.is_dir():
        raise DetectionError("a nonexistent target requires an existing parent directory")
    observed_at = now()
    archetypes: list[dict[str, Any]] = []
    hooks: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    fingerprint = hashlib.sha256()
    for recipe in load_recipes():
        marker_paths = [
            candidate
            for raw in recipe["markers"]
            if (candidate := safe_marker(target, raw)) is not None
        ]
        if not marker_paths:
            excluded.append({"recipe_id": recipe["id"], "reason": "no declared marker observed"})
            continue
        evidence_items = [evidence(path, target, observed_at) for path in marker_paths]
        for item in evidence_items:
            fingerprint.update(item["path"].encode("utf-8"))
            fingerprint.update(b"\0")
            fingerprint.update(item["sha256"].encode("ascii"))
            fingerprint.update(b"\0")
        confidence = "high" if any(item["kind"] == "bounded_content" for item in evidence_items) else "low"
        for archetype in recipe["archetypes"]:
            archetypes.append({
                "id": archetype,
                "recipe_id": recipe["id"],
                "confidence": confidence,
                "rule": "one or more recipe-declared root markers are present",
                "evidence": evidence_items,
                "limitations": recipe["limitations"],
            })
        hooks.extend(candidate_from_hook(recipe, hook, evidence_items) for hook in recipe["hooks"])
        hooks.extend(dynamic_hooks(target, recipe, marker_paths, evidence_items))
    return {
        "schema_version": "harness.hook-candidates.v1",
        "permission_grant": False,
        "observed_at": observed_at,
        "target_fingerprint": fingerprint.hexdigest(),
        "archetype_candidates": archetypes,
        "hook_candidates": hooks,
        "excluded_recipes": excluded,
        "limitations": [
            "Detection is read-only and executes no candidate or version probe.",
            "Candidates require explicit project-owned review; no hook, profile, collaboration mode, package, or authority is adopted.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="octon detect",
        description="Inspect a project read-only and propose Octon bootstrap inputs"
    )
    parser.add_argument("--target", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(detect(args.target.expanduser()), indent=2, sort_keys=True))
        return 0
    except (DetectionError, OSError, ValueError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
