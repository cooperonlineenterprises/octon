#!/usr/bin/env python3
"""Validate this skill package without third-party runtime dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---(?:\n|\Z)", re.DOTALL)
OPENAI_FIELD_RE = re.compile(r'^  ([a-z_]+): ("(?:[^"\\]|\\.)*")$')
EXPECTED_SKILL_ID = "octon-project-bootstrap"
EXPECTED_DISPLAY_NAME = "Octon Project Bootstrap"
EXPECTED_DESCRIPTION_PREFIX = (
    "Create, adopt, configure, operate, recover, or upgrade a project-local "
    "Octon agent harness and project dossier."
)


def parse_simple_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("SKILL.md must begin with closed YAML frontmatter")
    result: dict[str, str] = {}
    for number, line in enumerate(match.group("body").splitlines(), 1):
        if not line or line.startswith((" ", "\t", "#")):
            raise ValueError(
                f"SKILL.md frontmatter line {number} is not a simple mapping entry"
            )
        if ":" not in line:
            raise ValueError(f"SKILL.md frontmatter line {number} lacks ':'")
        key, value = line.split(":", 1)
        if key in result:
            raise ValueError(f"SKILL.md frontmatter duplicates {key!r}")
        result[key] = value.strip()
    return result


def validate_skill_md(skill_root: Path) -> list[str]:
    issues: list[str] = []
    path = skill_root / "SKILL.md"
    if not path.is_file():
        return ["SKILL.md is missing"]
    try:
        frontmatter = parse_simple_frontmatter(path)
    except (OSError, UnicodeError, ValueError) as error:
        return [str(error)]

    allowed = {"name", "description"}
    unexpected = sorted(set(frontmatter) - allowed)
    if unexpected:
        issues.append(f"SKILL.md has unexpected keys: {', '.join(unexpected)}")
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if not NAME_RE.fullmatch(name) or len(name) > 64:
        issues.append("SKILL.md name must be 1-64 lowercase hyphen-case characters")
    elif name != EXPECTED_SKILL_ID:
        issues.append(f"SKILL.md name must be {EXPECTED_SKILL_ID!r}")
    if not description:
        issues.append("SKILL.md description is required")
    elif len(description) > 1024:
        issues.append("SKILL.md description exceeds 1024 characters")
    elif "<" in description or ">" in description:
        issues.append("SKILL.md description must not contain angle brackets")
    elif not description.startswith(EXPECTED_DESCRIPTION_PREFIX):
        issues.append("SKILL.md description must begin with the canonical bootstrap capability description")
    required_discovery_terms = (
        "project bootstrap",
        "new-project initialization",
        "established-project adoption",
        "guided setup",
        "harness and dossier creation",
        "profile and layout selection",
        "work lifecycle",
        "validation and recovery",
        "collaboration assessment",
        "package installation",
        "deliberate upgrades",
    )
    for term in required_discovery_terms:
        if term not in description:
            issues.append(f"SKILL.md description lacks discovery term {term!r}")
    return issues


def validate_openai_yaml(skill_root: Path) -> list[str]:
    issues: list[str] = []
    path = skill_root / "agents/openai.yaml"
    if not path.is_file():
        return ["agents/openai.yaml is missing"]
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        return [f"cannot read agents/openai.yaml: {error}"]
    if not lines or lines[0] != "interface:":
        return ["agents/openai.yaml must begin with the interface mapping"]

    fields: dict[str, str] = {}
    for number, line in enumerate(lines[1:], 2):
        if not line:
            continue
        match = OPENAI_FIELD_RE.fullmatch(line)
        if not match:
            issues.append(
                f"agents/openai.yaml line {number} must be a quoted interface scalar"
            )
            continue
        key, encoded = match.groups()
        if key in fields:
            issues.append(f"agents/openai.yaml duplicates interface.{key}")
            continue
        try:
            fields[key] = json.loads(encoded)
        except json.JSONDecodeError as error:
            issues.append(f"agents/openai.yaml line {number} is not valid quoted text: {error}")

    allowed = {
        "display_name",
        "short_description",
        "icon_small",
        "icon_large",
        "brand_color",
        "default_prompt",
    }
    unexpected = sorted(set(fields) - allowed)
    if unexpected:
        issues.append(
            "agents/openai.yaml has unsupported interface fields: "
            + ", ".join(unexpected)
        )
    for required in ("display_name", "short_description", "default_prompt"):
        if not fields.get(required):
            issues.append(f"agents/openai.yaml requires interface.{required}")
    if fields.get("display_name") != EXPECTED_DISPLAY_NAME:
        issues.append(f"interface.display_name must be {EXPECTED_DISPLAY_NAME!r}")
    short = fields.get("short_description", "")
    if short and not 25 <= len(short) <= 64:
        issues.append("interface.short_description must be 25-64 characters")

    skill_name = ""
    try:
        skill_name = parse_simple_frontmatter(skill_root / "SKILL.md").get("name", "")
    except (OSError, UnicodeError, ValueError):
        pass
    prompt = fields.get("default_prompt", "")
    if skill_name and f"${skill_name}" not in prompt:
        issues.append(
            f"interface.default_prompt must explicitly mention ${skill_name}"
        )
    for icon_key in ("icon_small", "icon_large"):
        icon = fields.get(icon_key)
        if icon:
            candidate = (skill_root / icon).resolve()
            try:
                candidate.relative_to(skill_root.resolve())
            except ValueError:
                issues.append(f"interface.{icon_key} escapes the skill directory")
            else:
                if not candidate.is_file():
                    issues.append(f"interface.{icon_key} does not resolve to a file")
    return issues


def validate_package_structure(skill_root: Path) -> list[str]:
    issues: list[str] = []
    if skill_root.name != EXPECTED_SKILL_ID:
        issues.append(
            f"skill directory basename must be {EXPECTED_SKILL_ID!r}, found {skill_root.name!r}"
        )
    legacy_command = "p" + "b"
    forbidden_exact = {
        legacy_command,
        f"{legacy_command}.py",
        f"{legacy_command}_doctor.py",
        f"{legacy_command}_finish.py",
        f"{legacy_command}_transaction.py",
        f"{legacy_command}.tmpl",
        f"{legacy_command}.py.tmpl",
        f"{legacy_command}_doctor.py.tmpl",
        f"{legacy_command}_finish.py.tmpl",
        f"{legacy_command}_transaction.py.tmpl",
    }
    for path in skill_root.rglob("*"):
        if path.is_symlink():
            issues.append(f"skill package contains a symlink: {path.relative_to(skill_root)}")
        if path.name in forbidden_exact:
            issues.append(
                "skill package contains an obsolete legacy command path: "
                f"{path.relative_to(skill_root)}"
            )
    legacy_source_bundle = "blueprint" + "-source"
    if (skill_root / "assets" / legacy_source_bundle).exists():
        issues.append("skill package contains an obsolete legacy source bundle")
    bundled = skill_root / "assets/octon-source"
    if bundled.exists():
        license_path = bundled / "LICENSE"
        if not license_path.is_file() or license_path.is_symlink():
            issues.append("bundled source lacks a regular MIT-0 LICENSE file")
        else:
            license_text = license_path.read_text(encoding="utf-8")
            if not license_text.startswith(
                "MIT No Attribution\n\nCopyright 2026 Cooper Online Enterprises\n"
            ):
                issues.append("bundled source LICENSE identity differs from MIT-0 policy")
        pyproject_path = bundled / "pyproject.toml"
        if pyproject_path.is_file():
            metadata = pyproject_path.read_text(encoding="utf-8")
            if (
                'license = "MIT-0"' not in metadata
                or 'license-files = ["LICENSE"]' not in metadata
            ):
                issues.append("bundled source package metadata lacks MIT-0 and LICENSE")
        legacy_product_config = "blueprint" + ".json"
        legacy_spec_name = "BLUE" + "PRINT.md"
        legacy_skill_path = "skills/project-" + "bootstrap"
        for obsolete in (
            legacy_product_config,
            f"dossier/{legacy_spec_name}",
            f"harness/{legacy_spec_name}",
            legacy_skill_path,
        ):
            if (bundled / obsolete).exists():
                issues.append(f"bundled source contains obsolete current path: {obsolete}")
        if any(
            path.name in {"LICENSE.tmpl", "LICENSE.md.tmpl", "LICENSE.txt.tmpl"}
            for path in (skill_root / "assets/templates").rglob("*")
        ):
            issues.append("generated templates must not project the source LICENSE")
    return issues


def main() -> int:
    if len(sys.argv) > 2:
        print("usage: validate_skill_package.py [skill-directory]", file=sys.stderr)
        return 2
    skill_root = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) == 2
        else Path(__file__).resolve().parents[1]
    )
    issues = (
        validate_skill_md(skill_root)
        + validate_openai_yaml(skill_root)
        + validate_package_structure(skill_root)
    )
    if issues:
        print("Skill package validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print(f"Skill package validation passed: {skill_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
