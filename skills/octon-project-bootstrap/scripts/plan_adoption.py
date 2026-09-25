#!/usr/bin/env python3
"""Produce a read-only adoption plan for an established project."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IGNORED_DISCOVERY_PARTS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "node_modules",
    "vendor",
    "__pycache__",
    ".agent",
    ".agents",
    "build",
    "dist",
    "target",
    "coverage",
    ".coverage",
    ".next",
    ".cache",
}
DEFAULT_MAX_FILES = 200
DEFAULT_MAX_FILE_BYTES = 256 * 1024
DEFAULT_MAX_TOTAL_BYTES = 4 * 1024 * 1024
SENSITIVE_NAME = re.compile(
    r"(?i)(?:^|[._-])(?:secret|credential|private|sensitive|confidential|pii)(?:[._-]|$)"
)
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".kdbx"}
ALLOWLIST_NAMES = {
    "agents.md", "claude.md", "readme", "readme.md", "readme.rst",
    "package.json", "pyproject.toml", "cargo.toml", "go.mod", "makefile",
    "dockerfile", "pom.xml", "build.gradle", "build.gradle.kts",
    "citation.cff", "requirements.txt", "mkdocs.yml", "dvc.yaml",
    "dbt_project.yml",
}
ALLOWLIST_SUFFIXES = {".md", ".rst", ".txt", ".json", ".toml", ".yaml", ".yml"}
SEMANTIC_RULES = {
    "repository_instructions": ("permission", "authority", "instruction", "policy"),
    "decisions_and_work_state": ("decision", "status", "task", "plan", "owner"),
    "project_definition_and_requirements": ("objective", "scope", "requirement", "constraint"),
    "architecture_or_outcome_model": ("architecture", "component", "outcome", "system"),
    "current_state_and_conformance": ("current state", "finding", "conformance", "gap"),
    "plans_and_registers": ("roadmap", "risk", "assumption", "question", "milestone"),
    "provenance_validation_and_handoff": ("evidence", "source", "validation", "handoff", "resume"),
}
FUNCTIONAL_EQUIVALENT_PATTERNS = {
    "repository_instructions": (
        "AGENTS.md",
        "**/AGENTS.md",
        "CLAUDE.md",
        ".github/copilot-instructions.md",
    ),
    "agent_policy_and_context": (
        ".agent/policy.*",
        ".agent/policies.*",
        ".agent/context.*",
        ".agent/context-rules.*",
        "**/governance/**/policy*",
    ),
    "decisions_and_work_state": (
        ".agent/decisions/**/*",
        ".agent/tasks/**/*",
        "**/decisions/**/*",
        "**/adr/**/*",
        "**/ADRs/**/*",
    ),
    "project_definition_and_requirements": (
        "**/*project*definition*",
        "**/*problem*statement*",
        "**/*requirements*",
        "**/*brief*",
    ),
    "architecture_or_outcome_model": (
        "**/*architecture*",
        "**/*system*design*",
        "**/*operating*model*",
        "**/*outcome*model*",
    ),
    "current_state_and_conformance": (
        "**/*current*state*",
        "**/*project*status*",
        "**/*conformance*",
        "**/*gap*assessment*",
    ),
    "plans_and_registers": (
        "**/*implementation*plan*",
        "**/*roadmap*",
        "**/*risk*register*",
        "**/*open*question*",
        "**/*assumption*",
    ),
    "provenance_validation_and_handoff": (
        "**/*provenance*",
        "**/*evidence*",
        "**/*validation*report*",
        "**/*handoff*",
        "**/*resumption*",
    ),
}


def load_scaffolder():
    path = Path(__file__).with_name("scaffold_project.py")
    spec = importlib.util.spec_from_file_location("octon_mini_scaffold", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generator contracts: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_detector():
    path = Path(__file__).with_name("detect_project.py")
    spec = importlib.util.spec_from_file_location("octon_mini_detector", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load detector protocol: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def path_metadata_digest(path: Path, relative: str) -> str:
    try:
        metadata = path.lstat()
        payload = f"{relative}\0{metadata.st_mode & 0o7777}\0{metadata.st_size}".encode("utf-8")
    except OSError:
        payload = f"{relative}\0unreadable".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def content_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sensitive_path(relative: Path) -> bool:
    name = relative.name.casefold()
    return (
        name.startswith(".env")
        or relative.suffix.casefold() in SENSITIVE_SUFFIXES
        or name in {"id_rsa", "id_ed25519", "kubeconfig"}
        or any(SENSITIVE_NAME.search(part) for part in relative.parts)
    )


def allowlisted_text(relative: Path) -> bool:
    name = relative.name.casefold()
    return name in ALLOWLIST_NAMES or relative.suffix.casefold() in ALLOWLIST_SUFFIXES


def git_ignored_paths(target: Path, paths: list[Path]) -> set[str]:
    if not (target / ".git").exists() or not paths:
        return set()
    payload = "\0".join(path.as_posix() for path in paths) + "\0"
    try:
        result = subprocess.run(
            ["git", "check-ignore", "--stdin", "-z"],
            cwd=target,
            input=payload,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except OSError:
        return set()
    if result.returncode not in {0, 1}:
        return set()
    return {item for item in result.stdout.split("\0") if item}


def semantic_signals(text: str) -> dict[str, list[str]]:
    normalized = text.casefold()
    return {
        concern: sorted(token for token in tokens if token in normalized)
        for concern, tokens in SEMANTIC_RULES.items()
        if any(token in normalized for token in tokens)
    }


def semantic_inspection(
    target: Path,
    *,
    max_files: int = DEFAULT_MAX_FILES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    sensitive_opt_in: set[str] | None = None,
) -> dict[str, Any]:
    if max_files < 1 or max_file_bytes < 1 or max_total_bytes < 1:
        raise ValueError("semantic inspection limits must be positive")
    opt_in = sensitive_opt_in or set()
    candidate_paths: list[Path] = []
    exclusions: list[dict[str, Any]] = []
    for path in sorted(target.rglob("*")):
        try:
            relative = path.relative_to(target)
        except ValueError:
            continue
        relative_string = relative.as_posix()
        if any(part in IGNORED_DISCOVERY_PARTS for part in relative.parts):
            continue
        if path.is_symlink():
            exclusions.append(
                {
                    "path": relative_string,
                    "reason": "symlink_excluded",
                    "evidence_kind": "path_type_metadata",
                    "sha256": path_metadata_digest(path, relative_string),
                }
            )
            continue
        if not path.is_file():
            continue
        if sensitive_path(relative) and relative_string not in opt_in:
            exclusions.append(
                {
                    "path": relative_string,
                    "reason": "sensitive_path_requires_exact_opt_in",
                    "evidence_kind": "path_type_metadata_without_content_read",
                    "sha256": path_metadata_digest(path, relative_string),
                }
            )
            continue
        if not allowlisted_text(relative) and relative_string not in opt_in:
            continue
        candidate_paths.append(relative)

    ignored = git_ignored_paths(target, candidate_paths)
    inspected: list[dict[str, Any]] = []
    total = 0
    limited = False
    for relative in candidate_paths:
        relative_string = relative.as_posix()
        path = target / relative
        if relative_string in ignored:
            exclusions.append(
                {
                    "path": relative_string,
                    "reason": "ignored_artifact",
                    "evidence_kind": "path_type_metadata_without_content_read",
                    "sha256": path_metadata_digest(path, relative_string),
                }
            )
            continue
        try:
            size = path.stat().st_size
        except OSError:
            exclusions.append(
                {
                    "path": relative_string,
                    "reason": "unreadable_metadata",
                    "evidence_kind": "path_type_metadata",
                    "sha256": path_metadata_digest(path, relative_string),
                }
            )
            continue
        if size > max_file_bytes:
            exclusions.append(
                {
                    "path": relative_string,
                    "reason": "per_file_limit",
                    "evidence_kind": "content_hash_without_semantic_read",
                    "sha256": content_digest(path),
                    "size": size,
                }
            )
            continue
        if len(inspected) >= max_files or total + size > max_total_bytes:
            exclusions.append(
                {
                    "path": relative_string,
                    "reason": "aggregate_inspection_limit",
                    "evidence_kind": "content_hash_without_semantic_read",
                    "sha256": content_digest(path),
                    "size": size,
                }
            )
            limited = True
            continue
        try:
            data = path.read_bytes()
            if b"\0" in data:
                raise UnicodeDecodeError("utf-8", data, 0, 1, "NUL byte")
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            exclusions.append(
                {
                    "path": relative_string,
                    "reason": "binary_or_non_utf8",
                    "evidence_kind": "content_hash_without_semantic_read",
                    "sha256": content_digest(path),
                    "size": size,
                }
            )
            continue
        total += size
        inspected.append(
            {
                "path": relative_string,
                "size": size,
                "sha256": hashlib.sha256(data).hexdigest(),
                "signals": semantic_signals(text),
                "content_retained": False,
            }
        )
    return {
        "limits": {
            "max_files": max_files,
            "max_file_bytes": max_file_bytes,
            "max_total_bytes": max_total_bytes,
        },
        "files_inspected": len(inspected),
        "bytes_inspected": total,
        "limit_reached": limited,
        "inspected": inspected,
        "excluded": sorted(exclusions, key=lambda item: item["path"]),
        "sensitive_opt_in": sorted(opt_in),
        "content_retention": "none",
    }


def semantic_equivalents(inspection: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result = {concern: [] for concern in FUNCTIONAL_EQUIVALENT_PATTERNS}
    for item in inspection["inspected"]:
        for concern, matches in item["signals"].items():
            if concern not in result:
                continue
            confidence = "high" if len(matches) >= 3 else "medium" if len(matches) >= 2 else "low"
            result[concern].append(
                {
                    "path": item["path"],
                    "confidence": confidence,
                    "rule": "bounded case-insensitive concern vocabulary match",
                    "matched_terms": matches,
                    "sha256": item["sha256"],
                    "limitations": [
                        "Vocabulary matches do not establish functional equivalence, ownership, or authority."
                    ],
                }
            )
    return {key: sorted(value, key=lambda item: item["path"]) for key, value in result.items()}


def classify_existing(target: Path) -> dict[str, Any]:
    indicators = {
        "root_instructions": (target / "AGENTS.md").is_file(),
        "agent_harness": (target / ".agent").is_dir(),
        "capability_packages": (target / ".agents").is_dir(),
        "project_dossier": (target / "project-dossier").is_dir(),
        "octon_mini_origin": (target / ".octon-origin.json").is_file(),
        "legacy_project_blueprint_origin": (target / ".project-blueprint-origin.json").is_file(),
        "git_repository": (target / ".git").exists(),
    }
    technology_markers = [
        name
        for name in (
            "package.json",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "Gemfile",
            "pom.xml",
            "build.gradle",
            "Makefile",
            "Dockerfile",
        )
        if (target / name).exists()
    ]
    return {
        "indicators": indicators,
        "technology_markers": technology_markers,
    }


def origin_summary(target: Path, scaffolder: Any) -> dict[str, Any] | None:
    path = target / ".octon-origin.json"
    if not path.is_file():
        return None
    try:
        value = scaffolder.load_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {"status": "present_but_invalid"}
    if not isinstance(value, dict):
        return {"status": "present_but_invalid"}
    return {
        "status": "valid_shape_not_fully_validated",
        "product": value.get("product"),
        "octon_mini_version": value.get("octon_mini_version"),
        "profile": value.get("profile"),
        "layout": value.get("layout"),
        "harness_kernel_version": value.get("harness_kernel_version"),
    }


def functional_equivalent_candidates(target: Path) -> dict[str, list[str]]:
    """Find path/name candidates without reading project file contents."""
    discovered: dict[str, list[str]] = {}
    for concern, patterns in FUNCTIONAL_EQUIVALENT_PATTERNS.items():
        candidates: set[str] = set()
        for pattern in patterns:
            for path in target.glob(pattern):
                try:
                    relative = path.relative_to(target)
                except ValueError:
                    continue
                if any(part in IGNORED_DISCOVERY_PARTS for part in relative.parts):
                    continue
                if path.is_symlink() or not path.is_file():
                    continue
                candidates.add(relative.as_posix())
        discovered[concern] = sorted(candidates)
    return discovered


def build_plan(
    target: Path,
    profile: str,
    *,
    layout: str = "compact",
    max_files: int = DEFAULT_MAX_FILES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    sensitive_opt_in: set[str] | None = None,
) -> dict[str, Any]:
    scaffolder = load_scaffolder()
    scaffolder.require_runtime()
    if not target.is_absolute():
        raise ValueError("--target must be an absolute path")
    resolved = target.resolve()
    if not resolved.is_dir():
        raise ValueError("--target must be an existing directory")

    try:
        policy = scaffolder.load_generation_policy()
    except ValueError as error:
        raise ValueError(
            "authority_degradation: generation policy cannot be established: "
            f"{error}"
        ) from error
    diagnostics = scaffolder.generation_policy_diagnostics(policy, (profile,))
    mode = scaffolder.generation_profile_mode(diagnostics, profile)
    if mode == "blocked":
        raise ValueError(
            f"{profile} generation capability is blocked; run "
            "scaffold_project.py --diagnose-generation-policy "
            f"--profile {profile} for read-only recovery guidance"
        )
    templates, schemas = scaffolder.resolve_generation_inputs(profile, policy, layout)
    scaffolder.validate_generation_boundary(profile, templates, schemas, policy, layout)
    reserved_target = resolved / scaffolder.target_installation_root(policy)
    if reserved_target.exists() or reserved_target.is_symlink():
        raise ValueError("occupied target installation path requires lineage and ownership review")
    installation = scaffolder.InstallationBinding.current(resolved)
    intended = (
        set(templates)
        | set(schemas)
        | scaffolder.derived_output_paths(profile, policy, installation=installation)
        | scaffolder.project_local_source_paths(profile, policy, installation=installation)
        | {scaffolder.origin_path(policy, installation=installation)}
    )
    for relative in intended:
        installation.relative_path(relative.as_posix(), "adoption intended path")

    collisions = sorted(
        path.as_posix() for path in intended if (resolved / path).exists()
    )
    absent = sorted(
        path.as_posix() for path in intended if not (resolved / path).exists()
    )
    existing_top_level = sorted(
        path.name
        for path in resolved.iterdir()
        if path.name not in {".git", ".DS_Store"}
    )
    inspection = semantic_inspection(
        resolved,
        max_files=max_files,
        max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes,
        sensitive_opt_in=sensitive_opt_in,
    )
    path_candidates = functional_equivalent_candidates(resolved)
    semantic_candidates = semantic_equivalents(inspection)
    likely_equivalents: dict[str, list[dict[str, Any]]] = {}
    for concern in FUNCTIONAL_EQUIVALENT_PATTERNS:
        by_path: dict[str, dict[str, Any]] = {
            item["path"]: item for item in semantic_candidates.get(concern, [])
        }
        for path_value in path_candidates.get(concern, []):
            if path_value in by_path:
                by_path[path_value]["path_name_candidate"] = True
                if by_path[path_value]["confidence"] == "low":
                    by_path[path_value]["confidence"] = "medium"
            else:
                by_path[path_value] = {
                    "path": path_value,
                    "confidence": "low",
                    "rule": "path/name pattern only",
                    "matched_terms": [],
                    "sha256": path_metadata_digest(resolved / path_value, path_value),
                    "path_name_candidate": True,
                    "limitations": [
                        "Path/name evidence alone does not establish functional equivalence, ownership, or authority."
                    ],
                }
        likely_equivalents[concern] = sorted(by_path.values(), key=lambda item: item["path"])
    authority_conflicts = sorted(
        {
            item["path"]
            for concern in ("repository_instructions", "agent_policy_and_context")
            for item in likely_equivalents.get(concern, [])
        }
        | {
            item
            for item in collisions
            if item == "AGENTS.md" or item.startswith(".agent/")
        }
    )
    ambiguity = [
        {
            "id": f"FEQ-{index:04d}",
            "concern": concern,
            "path": item["path"],
            "confidence": item["confidence"],
            "required_disposition": [
                "add_parallel_after_review",
                "manual_reconcile_before_replan",
                "confirmed_equivalent_requires_project_specific_mapping",
            ],
        }
        for index, (concern, item) in enumerate(
            (
                (concern, item)
                for concern, items in likely_equivalents.items()
                for item in items
            ),
            1,
        )
    ]
    detector = load_detector()
    detection = detector.detect(resolved)
    always_review_prefixes = ("AGENTS.md", ".agent/", "project-dossier/")
    review_additions = sorted(
        item for item in absent if item == always_review_prefixes[0] or item.startswith(always_review_prefixes[1:])
    )
    safe_additions = sorted(set(absent) - set(review_additions))
    plan = {
        "schema_version": "octon-mini.bootstrap.adoption-proposal.v1",
        "authority": (
            "Read-only inventory and reconciliation guidance; not permission "
            "to modify, replace, or accept project content."
        ),
        "target": str(resolved),
        "requested_profile": profile,
        "requested_layout": layout,
        "octon_mini_version": scaffolder.octon_mini_version(),
        "generation_capability": {
            "mode": mode,
            "findings": scaffolder.generation_profile_findings(
                diagnostics, profile
            ),
            "effect": (
                "Unreviewed inputs are ignored and cannot expand this plan."
            ),
        },
        "existing": classify_existing(resolved),
        "origin": origin_summary(resolved, scaffolder),
        "existing_top_level_names": existing_top_level,
        "collisions": collisions,
        "candidate_new_paths": absent,
        "confirmed_collisions": [
            {
                "path": item,
                "type": "symlink" if (resolved / item).is_symlink() else "directory" if (resolved / item).is_dir() else "file",
                "authority_bearing": item in authority_conflicts,
            }
            for item in collisions
        ],
        "likely_functional_equivalents": likely_equivalents,
        "authority_bearing_conflicts": authority_conflicts,
        "safe_additions": safe_additions,
        "review_required_additions": review_additions,
        "project_owned_facts_required": [
            "adoption authority and accepted disposition",
            "collaboration writer count and only evidence used by the selected result",
            "project hook applicability, owner, argv, version probe, timeout, freshness, and side effects",
            "operations/observability and security/supply-chain trigger assessments",
            "SCM selection and any workflow adoption",
            "target-project readiness claims",
        ],
        "hook_and_archetype_proposals": detection,
        "semantic_inspection": inspection,
        "unresolved_ambiguity": ambiguity,
        "functional_equivalent_candidates": path_candidates,
        "functional_equivalence_limit": (
            "Bounded vocabulary and path/name evidence only. Content is not retained; "
            "functional equivalence, ownership, and authority always require review."
        ),
        "required_sequence": [
            "Read applicable target-project instructions root to leaf.",
            "Classify existing authority, governance, dossier, and handoff sources.",
            "Map direct and functional equivalents before proposing file changes.",
            "Preserve accepted target decisions and project facts.",
            "Resolve each collision through an authorized project-specific change.",
            "Add only controls justified by the selected profile triggers.",
            "Run target checks plus Octon mutation tests on the exact result.",
            "Record migration provenance, limitations, and a safe resumption point.",
        ],
        "non_transfer_rules": [
            "Do not copy permissions, accepted decisions, implementation claims, or readiness.",
            "Do not overwrite existing files or silently change authority.",
            "Do not treat absent Octon paths as proof of a project gap until functional equivalents are reviewed.",
        ],
    }
    unsigned = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode("utf-8")
    plan["canonical_proposal_digest"] = hashlib.sha256(unsigned).hexdigest()
    return plan


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Octon Adoption Plan",
        "",
        f"- Target: `{plan['target']}`",
        f"- Requested profile: `{plan['requested_profile']}`",
        f"- Requested layout: `{plan['requested_layout']}`",
        f"- Octon version: `{plan['octon_mini_version']}`",
        f"- Proposal digest: `{plan['canonical_proposal_digest']}`",
        f"- Authority: {plan['authority']}",
        f"- Generation capability: `{plan['generation_capability']['mode']}`",
        "",
        "## Generation boundary",
        "",
        f"- {plan['generation_capability']['effect']}",
    ]
    findings = plan["generation_capability"]["findings"]
    lines.extend(
        [
            f"- {item['failure_class']} ({item['rule_id']}): "
            + ", ".join(f"`{path}`" for path in item["paths"])
            for item in findings
        ]
        or ["- no selected-profile degradation observed"]
    )
    lines.extend(
        [
            "",
            "## Existing signals",
            "",
        ]
    )
    for key, value in plan["existing"]["indicators"].items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    markers = plan["existing"]["technology_markers"]
    lines.append(
        "- technology markers: "
        + (", ".join(f"`{item}`" for item in markers) if markers else "none observed")
    )
    origin = plan["origin"]
    lines.extend(["", "## Existing blueprint origin", ""])
    if origin is None:
        lines.append("- none observed")
    else:
        for key, value in origin.items():
            lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            f"## Exact path collisions ({len(plan['collisions'])})",
            "",
        ]
    )
    lines.extend(
        [f"- `{item}`" for item in plan["collisions"]]
        or ["- none"]
    )
    lines.extend(
        [
            "",
            f"## Candidate new paths ({len(plan['candidate_new_paths'])})",
            "",
        ]
    )
    lines.extend(
        [f"- `{item}`" for item in plan["candidate_new_paths"]]
        or ["- none"]
    )
    lines.extend(["", "## Functional-equivalent candidates", ""])
    lines.append(f"- Limitation: {plan['functional_equivalence_limit']}")
    for concern, candidates in plan["likely_functional_equivalents"].items():
        lines.append(f"- {concern}:")
        lines.extend(
            [f"  - `{item['path']}` ({item['confidence']}; {item['rule']})" for item in candidates]
            or ["  - none observed"]
        )
    inspection = plan["semantic_inspection"]
    lines.extend(
        [
            "",
            "## Bounded semantic inspection",
            "",
            f"- files inspected: `{inspection['files_inspected']}` / `{inspection['limits']['max_files']}`",
            f"- bytes inspected: `{inspection['bytes_inspected']}` / `{inspection['limits']['max_total_bytes']}`",
            f"- excluded paths: `{len(inspection['excluded'])}`",
            f"- aggregate limit reached: `{str(inspection['limit_reached']).lower()}`",
            "- inspected content retained: `false`",
            "",
            "## Mutation classification",
            "",
            f"- safe additions after plan review: `{len(plan['safe_additions'])}`",
            f"- authority/governance additions requiring explicit review: `{len(plan['review_required_additions'])}`",
            f"- authority-bearing conflicts: `{len(plan['authority_bearing_conflicts'])}`",
            f"- unresolved functional-equivalence dispositions: `{len(plan['unresolved_ambiguity'])}`",
        ]
    )
    lines.extend(["", "## Required reconciliation sequence", ""])
    for index, item in enumerate(plan["required_sequence"], 1):
        lines.append(f"{index}. {item}")
    lines.extend(["", "## Non-transfer rules", ""])
    lines.extend(f"- {item}" for item in plan["non_transfer_rules"])
    lines.extend(
        [
            "",
            "This plan is intentionally read-only. It identifies exact path "
            "collisions and path/name candidates for functional-equivalence "
            "review; it does not accept equivalence or authorize edits.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument(
        "--profile",
        required=True,
    )
    parser.add_argument("--layout", choices=("compact", "separated"), default="compact")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES)
    parser.add_argument(
        "--include-sensitive-path",
        action="append",
        default=[],
        help="exact target-relative path explicitly opted into bounded semantic inspection",
    )
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        opt_in: set[str] = set()
        for raw in args.include_sensitive_path:
            relative = Path(raw)
            if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
                raise ValueError(f"unsafe --include-sensitive-path: {raw!r}")
            opt_in.add(relative.as_posix())
        plan = build_plan(
            args.target.expanduser(),
            args.profile,
            layout=args.layout,
            max_files=args.max_files,
            max_file_bytes=args.max_file_bytes,
            max_total_bytes=args.max_total_bytes,
            sensitive_opt_in=opt_in,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(render_markdown(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
