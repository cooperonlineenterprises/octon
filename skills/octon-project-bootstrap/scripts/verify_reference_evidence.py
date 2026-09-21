#!/usr/bin/env python3
"""Verify Octon citations against the reference-evidence registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
READ_ONLY_GIT_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}


def octon_mini_source_root() -> Path:
    candidates = (
        Path(__file__).resolve().parents[3],
        SKILL_ROOT / "assets/octon-source",
    )
    for candidate in candidates:
        if (
            (candidate / "VERSION").is_file()
            and (candidate / "shared/reference-evidence.json").is_file()
        ):
            return candidate
    return candidates[0]


ROOT = octon_mini_source_root()
REGISTRY_PATH = ROOT / "shared/reference-evidence.json"
CITATION_SOURCES = (
    ROOT / "dossier/SPECIFICATION.md",
    ROOT / "dossier/artifact-types.json",
    ROOT / "dossier/references/REFERENCE_EVIDENCE.md",
    ROOT / "harness/SPECIFICATION.md",
    ROOT / "harness/references/REFERENCE_EVIDENCE.md",
)
CITATION_RE = re.compile(r"\b([A-Z][A-Z0-9_-]{1,15}):([A-Za-z0-9_.+@/-]+)")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_AUTHORITY_CLASSES = {
    "repository_instruction",
    "live_governance",
    "canonical_current",
    "current_state",
    "plan_or_register",
    "evidence_or_provenance",
    "navigation_or_handoff",
    "generated_integrity",
    "historical_or_baseline",
    "working_tree_uncommitted",
    "mixed_directory",
}
ALLOWED_OBSERVATIONS = {"commit", "working_tree"}


class DuplicateKeyError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=strict_object,
        parse_constant=reject_json_constant,
    )


def confined_relative_path(value: str, *, directory: bool) -> bool:
    if not value or value.startswith(("/", "\\")) or "\\" in value:
        return False
    parts = Path(value.rstrip("/")).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return False
    return value.endswith("/") if directory else not value.endswith("/")


def registry_index(registry: Any, issues: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(registry, dict):
        issues.append("reference registry root must be an object")
        return {}
    if registry.get("schema_version") != "octon-mini.source.reference-evidence.v1":
        issues.append("reference registry schema_version mismatch")
    if registry.get("document_role") != "reference_provenance_registry":
        issues.append("reference registry document_role mismatch")
    if registry.get("permission_grant") is not False:
        issues.append("reference registry must not grant permission")
    if set(registry) != {
        "schema_version",
        "document_role",
        "permission_grant",
        "inspected_on",
        "repositories",
    }:
        issues.append("reference registry root fields do not match the v1 contract")
    if not isinstance(registry.get("inspected_on"), str) or not DATE_RE.fullmatch(
        registry["inspected_on"]
    ):
        issues.append("reference registry inspected_on must be YYYY-MM-DD")
    repositories = registry.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        issues.append("reference registry repositories must be a nonempty array")
        return {}

    result: dict[str, dict[str, Any]] = {}
    for position, repository in enumerate(repositories):
        prefix = f"repositories[{position}]"
        if not isinstance(repository, dict):
            issues.append(f"{prefix} must be an object")
            continue
        if set(repository) != {
            "id",
            "label",
            "commit",
            "working_tree",
            "entries",
        }:
            issues.append(f"{prefix} fields do not match the repository contract")
        if not isinstance(repository.get("label"), str) or not repository["label"]:
            issues.append(f"{prefix}.label must be nonempty text")
        identifier = repository.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(
            r"[A-Z][A-Z0-9_-]{1,15}", identifier
        ):
            issues.append(f"{prefix}.id is invalid")
            continue
        if identifier in result:
            issues.append(f"duplicate reference repository id: {identifier}")
            continue
        commit = repository.get("commit")
        if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
            issues.append(f"{prefix}.commit must be a 40-character SHA")
        working_tree = repository.get("working_tree")
        if not isinstance(working_tree, dict):
            issues.append(f"{prefix}.working_tree must be an object")
        else:
            if set(working_tree) != {
                "status",
                "interpretation",
            }:
                issues.append(f"{prefix}.working_tree fields are invalid")
            status = working_tree.get("status")
            if status not in {"clean", "dirty"}:
                issues.append(f"{prefix}.working_tree.status is invalid")
            if (
                not isinstance(working_tree.get("interpretation"), str)
                or not working_tree["interpretation"]
            ):
                issues.append(f"{prefix}.working_tree.interpretation is required")
        entries = repository.get("entries")
        if not isinstance(entries, list) or not entries:
            issues.append(f"{prefix}.entries must be a nonempty array")
            continue
        seen_paths: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for entry_position, entry in enumerate(entries):
            entry_prefix = f"{prefix}.entries[{entry_position}]"
            if not isinstance(entry, dict):
                issues.append(f"{entry_prefix} must be an object")
                continue
            allowed_entry_fields = {
                "path",
                "path_kind",
                "authority_class",
                "observation",
                "content_sha256",
                "tree_sha256",
                "note",
            }
            if not set(entry) <= allowed_entry_fields:
                issues.append(f"{entry_prefix} has unsupported fields")
            path = entry.get("path")
            kind = entry.get("path_kind")
            if kind not in {"file", "directory"}:
                issues.append(f"{entry_prefix}.path_kind is invalid")
                continue
            if not isinstance(path, str) or not confined_relative_path(
                path, directory=kind == "directory"
            ):
                issues.append(f"{entry_prefix}.path is not repository-confined")
                continue
            if path in seen_paths:
                issues.append(f"{prefix} duplicates evidence path {path}")
                continue
            seen_paths.add(path)
            if entry.get("authority_class") not in ALLOWED_AUTHORITY_CLASSES:
                issues.append(f"{entry_prefix}.authority_class is invalid")
            if entry.get("observation") not in ALLOWED_OBSERVATIONS:
                issues.append(f"{entry_prefix}.observation is invalid")
            content_sha = entry.get("content_sha256")
            if content_sha is not None and (
                kind != "file"
                or not isinstance(content_sha, str)
                or not SHA256_RE.fullmatch(content_sha)
            ):
                issues.append(
                    f"{entry_prefix}.content_sha256 is valid only for exact files"
                )
            tree_sha = entry.get("tree_sha256")
            if tree_sha is not None and (
                kind != "directory"
                or not isinstance(tree_sha, str)
                or not SHA256_RE.fullmatch(tree_sha)
            ):
                issues.append(
                    f"{entry_prefix}.tree_sha256 is valid only for directories"
                )
            normalized.append(entry)
        result[identifier] = {
            "commit": commit,
            "working_tree": working_tree,
            "entries": normalized,
        }
    return result


def cited_paths(issues: list[str]) -> set[tuple[str, str]]:
    citations: set[tuple[str, str]] = set()
    for source in CITATION_SOURCES:
        if not source.is_file():
            issues.append(f"citation source is missing: {source.relative_to(ROOT)}")
            continue
        text = source.read_text(encoding="utf-8")
        for match in CITATION_RE.finditer(text):
            repository_id, path = match.groups()
            if not confined_relative_path(path, directory=path.endswith("/")):
                issues.append(
                    f"{source.relative_to(ROOT)} has unsafe citation "
                    f"{repository_id}:{path}"
                )
                continue
            citations.add((repository_id, path))
    return citations


def validate_crosswalk_aliases(issues: list[str]) -> None:
    path = ROOT / "dossier/SPECIFICATION.md"
    text = path.read_text(encoding="utf-8")
    start = text.find("## 3. Reference-dossier crosswalk")
    end = text.find("## 4. General artifact taxonomy")
    if start < 0 or end <= start:
        issues.append("dossier reference crosswalk section cannot be isolated")
        return
    for token in re.findall(r"`([^`\n]+)`", text[start:end]):
        if (
            "/" in token
            or token.endswith((".md", ".json", ".yaml", ".sha256"))
        ) and not token.startswith(("CF:", "COE:")):
            issues.append(
                "dossier crosswalk path lacks an explicit repository alias: "
                + token
            )


def entry_covers(entry: dict[str, Any], cited_path: str) -> bool:
    registered = entry["path"]
    if entry["path_kind"] == "file":
        return registered == cited_path
    return cited_path == registered or cited_path.startswith(registered)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(path.rglob("*")):
        if not child.is_file() or child.is_symlink():
            continue
        relative = child.relative_to(path).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256(child)))
        digest.update(b"\0")
    return digest.hexdigest()


def verify_external_root(
    identifier: str,
    root: Path,
    repository: dict[str, Any],
    issues: list[str],
) -> None:
    resolved = root.resolve()
    if not resolved.is_dir():
        issues.append(f"{identifier} reference root is not a directory: {resolved}")
        return
    try:
        head = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            env=READ_ONLY_GIT_ENV,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        issues.append(f"{identifier} cannot resolve reference commit: {error}")
    else:
        if head != repository["commit"]:
            issues.append(
                f"{identifier} commit drift: registry {repository['commit']}, "
                f"working copy {head}"
            )
    try:
        status_lines = subprocess.run(
            ["git", "-C", str(resolved), "status", "--porcelain=v1"],
            check=True,
            capture_output=True,
            text=True,
            env=READ_ONLY_GIT_ENV,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError) as error:
        issues.append(f"{identifier} cannot inspect reference working tree: {error}")
    else:
        observed_status = "dirty" if status_lines else "clean"
        expected_worktree = repository["working_tree"]
        if observed_status != expected_worktree.get("status"):
            issues.append(
                f"{identifier} working-tree status drift: registry "
                f"{expected_worktree.get('status')}, working copy {observed_status}"
            )

    for entry in repository["entries"]:
        candidate = (resolved / entry["path"].rstrip("/")).resolve()
        try:
            candidate.relative_to(resolved)
        except ValueError:
            issues.append(f"{identifier}:{entry['path']} escapes the reference root")
            continue
        expected_kind = entry["path_kind"]
        if expected_kind == "file" and not candidate.is_file():
            issues.append(f"{identifier}:{entry['path']} is not an existing file")
            continue
        if expected_kind == "directory" and not candidate.is_dir():
            issues.append(f"{identifier}:{entry['path']} is not an existing directory")
            continue
        expected_sha = entry.get("content_sha256")
        if expected_sha and sha256(candidate) != expected_sha:
            issues.append(f"{identifier}:{entry['path']} content hash drift")
        expected_tree_sha = entry.get("tree_sha256")
        if expected_tree_sha and tree_sha256(candidate) != expected_tree_sha:
            issues.append(f"{identifier}:{entry['path']} tree hash drift")


def parse_reference_roots(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--reference-root values must be ID=/absolute/path")
        identifier, raw_path = value.split("=", 1)
        path = Path(raw_path)
        if not identifier or not path.is_absolute():
            raise ValueError("--reference-root values must be ID=/absolute/path")
        if identifier in result:
            raise ValueError(f"duplicate --reference-root ID: {identifier}")
        result[identifier] = path
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reference-root",
        action="append",
        default=[],
        metavar="ID=/ABSOLUTE/PATH",
        help="optionally verify registered files against a local reference checkout",
    )
    args = parser.parse_args()
    issues: list[str] = []
    try:
        roots = parse_reference_roots(args.reference_root)
        registry = load_json(REGISTRY_PATH)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"Reference evidence validation failed: {error}", file=sys.stderr)
        return 1

    repositories = registry_index(registry, issues)
    validate_crosswalk_aliases(issues)
    for identifier, path in sorted(cited_paths(issues)):
        repository = repositories.get(identifier)
        if repository is None:
            issues.append(f"citation uses unregistered repository: {identifier}:{path}")
        elif not any(entry_covers(entry, path) for entry in repository["entries"]):
            issues.append(f"citation is absent from evidence registry: {identifier}:{path}")
    for identifier, root in roots.items():
        repository = repositories.get(identifier)
        if repository is None:
            issues.append(f"--reference-root uses unregistered repository: {identifier}")
        else:
            verify_external_root(identifier, root, repository, issues)
    if issues:
        print("Reference evidence validation failed:", file=sys.stderr)
        for issue in sorted(set(issues)):
            print(f"- {issue}", file=sys.stderr)
        return 1
    mode = "registry and citations"
    if roots:
        mode += " plus supplied reference roots"
    print(f"Reference evidence validation passed: {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
