#!/usr/bin/env python3
"""Shared, non-authorizing guided setup sessions for init, adopt, and upgrade."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import secrets
import subprocess
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
SESSION_SCHEMA = "octon-mini.bootstrap.setup-session.v2"
LEGACY_SESSION_SCHEMA = "octon-mini.bootstrap.setup-session.v1"
ANSWER_SCHEMA = "octon-mini.bootstrap.setup-answers.v1"
SESSION_VERSION = "2.0.0"
MODES = ("initialization", "adoption", "upgrade")
STATES = ("answered", "unknown", "deferred", "not_applicable")
AUTHORITY_PREFIXES = ("authority:", "external:")
SETUP_EVIDENCE_KIND = "guided_setup_session"
CATALOG_TOP_KEYS = {
    "schema_version",
    "document_role",
    "permission_grant",
    "catalog_version",
    "modes",
    "information_roles",
    "validity_policy",
    "questions",
    "limitations",
}
QUESTION_KEYS = {
    "id",
    "version",
    "family",
    "modes",
    "dependencies",
    "trigger_conditions",
    "prompt",
    "importance",
    "answer",
    "blocking",
    "recommendation",
    "authoritative_destination",
    "information_role",
    "evidence",
    "sensitivity",
    "validation_rules",
    "migration_behavior",
    "change_consequences",
}
ANSWER_KEYS = {
    "type",
    "valid_values",
    "allow_unknown",
    "allow_deferred",
    "allow_not_applicable",
}
EVIDENCE_KEYS = {"required", "freshness_days", "allowed_sources", "requirements"}
SENSITIVITY_KEYS = {"classification", "collection_restrictions"}
RECOMMENDATION_KEYS = {"rule", "rationale"}
CONDITION_KEYS = {"question_id", "operator", "values"}
ANSWER_INPUT_KEYS = {"question_id", "state", "value", "supplied_by", "evidence"}
ANSWER_EVIDENCE_KEYS = {"source", "observed_at", "expires_at", "confidence", "limitations"}
VALIDITY_CLASSES = {
    "re_observe_every_run",
    "source_fingerprint_bound",
    "dependency_bound",
    "expiry_bound",
    "decision_successor_or_revocation_bound",
    "runtime_only_never_reusable",
}
INFORMATION_ROLES = {
    "observation",
    "inference",
    "initialization_input",
    "recommendation",
    "owner_selection",
    "accepted_authority_reference",
    "runtime_authorization_forbidden",
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|github_pat|sk_live|xox[baprs])_[A-Za-z0-9_-]{12,}\b"),
)
SHELL_EXECUTABLES = {
    "sh",
    "bash",
    "zsh",
    "fish",
    "cmd",
    "cmd.exe",
    "powershell",
    "powershell.exe",
    "pwsh",
}
INLINE_SHELL_FLAGS = {"-c", "/c", "-command", "--command"}
FINGERPRINT_EXCLUSIONS = (
    PurePosixPath(".git"),
    PurePosixPath(".agent/transactions"),
)


class SetupError(ValueError):
    """The setup session is malformed, stale, ambiguous, or incomplete."""


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        module = types.ModuleType(name)
        module.__file__ = str(path)
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
        return module
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTINUATION = load_module(
    "octon_setup_continuation",
    SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_continuation.py.tmpl",
)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise SetupError(f"{label} must be a timezone-aware ISO date-time") from error
    if parsed.tzinfo is None:
        raise SetupError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SetupError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def reject_constant(value: str) -> None:
    raise SetupError(f"non-finite JSON number is prohibited: {value}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SetupError(f"cannot load strict JSON {path}: {error}") from error


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def record_digest(value: dict[str, Any], key: str) -> str:
    unsigned = dict(value)
    unsigned.pop(key, None)
    return sha256(canonical_bytes(unsigned))


def octon_mini_root() -> Path:
    candidates = (
        Path(__file__).resolve().parents[3],
        SKILL_ROOT / "assets/octon-source",
    )
    for candidate in candidates:
        if (
            (candidate / "VERSION").is_file()
            and (candidate / "shared/source-contracts/setup-questions.json").is_file()
        ):
            return candidate
    raise SetupError("Octon source with the setup question catalog is unavailable")


def source_version() -> str:
    value = (octon_mini_root() / "VERSION").read_text(encoding="utf-8").strip()
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value) is None:
        raise SetupError("Octon source VERSION is malformed")
    return value


def catalog_path() -> Path:
    return octon_mini_root() / "shared/source-contracts/setup-questions.json"


def catalog_digest(value: dict[str, Any]) -> str:
    return sha256(canonical_bytes(value))


def question_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in catalog["questions"]}


def validate_catalog(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != CATALOG_TOP_KEYS:
        raise SetupError("setup question catalog uses an invalid closed top-level contract")
    if (
        value.get("schema_version") != "octon-mini.bootstrap.setup-question-catalog.v2"
        or value.get("document_role") != "authoritative_guided_setup_question_catalog"
        or value.get("permission_grant") is not False
        or value.get("modes") != list(MODES)
        or set(value.get("information_roles", [])) != INFORMATION_ROLES
        or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", str(value.get("catalog_version", "")))
        or not isinstance(value.get("questions"), list)
        or not value["questions"]
        or not isinstance(value.get("limitations"), list)
    ):
        raise SetupError("setup question catalog metadata is malformed or authorizing")
    validity = value.get("validity_policy")
    if (
        not isinstance(validity, dict)
        or validity.get("schema_version") != "octon-mini.setup-validity.v1"
        or set(validity.get("classes", [])) != VALIDITY_CLASSES
        or set(validity.get("reinspection_classifications", []))
        != {"preserved", "reobserved", "needs_confirmation", "invalidated", "newly_introduced"}
        or not isinstance(validity.get("role_defaults"), dict)
        or set(validity["role_defaults"]) != INFORMATION_ROLES
        or any(
            not isinstance(classes, list)
            or not classes
            or not set(classes) <= VALIDITY_CLASSES
            for classes in validity["role_defaults"].values()
        )
        or not isinstance(validity.get("rules"), list)
        or any(not isinstance(item, str) or not item for item in validity["rules"])
    ):
        raise SetupError("setup validity policy is malformed or incomplete")
    seen: set[str] = set()
    positions: dict[str, int] = {}
    for index, question in enumerate(value["questions"]):
        if not isinstance(question, dict) or set(question) != QUESTION_KEYS:
            raise SetupError(f"setup question {index} uses an invalid closed contract")
        identifier = question.get("id")
        if (
            not isinstance(identifier, str)
            or re.fullmatch(r"setup\.[a-z0-9]+(?:[.-][a-z0-9]+)*", identifier) is None
            or identifier in seen
        ):
            raise SetupError(f"duplicate or malformed setup question ID: {identifier!r}")
        seen.add(identifier)
        positions[identifier] = index
        if not isinstance(question.get("version"), int) or question["version"] < 1:
            raise SetupError(f"{identifier}: version must be a positive integer")
        if (
            not isinstance(question.get("modes"), list)
            or not question["modes"]
            or not set(question["modes"]) <= set(MODES)
            or len(question["modes"]) != len(set(question["modes"]))
        ):
            raise SetupError(f"{identifier}: modes are malformed")
        if not isinstance(question.get("dependencies"), list) or len(question["dependencies"]) != len(set(question["dependencies"])):
            raise SetupError(f"{identifier}: dependencies must be unique question IDs")
        if not isinstance(question.get("trigger_conditions"), list):
            raise SetupError(f"{identifier}: trigger conditions must be an array")
        for condition in question["trigger_conditions"]:
            if (
                not isinstance(condition, dict)
                or set(condition) != CONDITION_KEYS
                or condition.get("operator") not in {"answered", "equals", "in", "not_in"}
                or not isinstance(condition.get("values"), list)
            ):
                raise SetupError(f"{identifier}: trigger condition is malformed")
        answer = question.get("answer")
        if not isinstance(answer, dict) or set(answer) != ANSWER_KEYS:
            raise SetupError(f"{identifier}: answer contract is malformed")
        if answer.get("type") not in {"string", "integer", "boolean", "enum", "string_list", "object", "object_list"}:
            raise SetupError(f"{identifier}: answer type is unsupported")
        if not isinstance(answer.get("valid_values"), list):
            raise SetupError(f"{identifier}: valid values must be an array")
        if answer["type"] == "enum" and not answer["valid_values"]:
            raise SetupError(f"{identifier}: enum requires valid values")
        if any(not isinstance(answer.get(key), bool) for key in ("allow_unknown", "allow_deferred", "allow_not_applicable")):
            raise SetupError(f"{identifier}: answer state flags must be booleans")
        if not isinstance(question.get("blocking"), bool):
            raise SetupError(f"{identifier}: blocking must be boolean")
        if not isinstance(question.get("recommendation"), dict) or set(question["recommendation"]) != RECOMMENDATION_KEYS:
            raise SetupError(f"{identifier}: recommendation contract is malformed")
        if question.get("information_role") not in INFORMATION_ROLES:
            raise SetupError(f"{identifier}: information role is invalid")
        if not isinstance(question.get("evidence"), dict) or set(question["evidence"]) != EVIDENCE_KEYS:
            raise SetupError(f"{identifier}: evidence contract is malformed")
        if not isinstance(question.get("sensitivity"), dict) or set(question["sensitivity"]) != SENSITIVITY_KEYS:
            raise SetupError(f"{identifier}: sensitivity contract is malformed")
        if question["information_role"] == "runtime_authorization_forbidden" and "never_collect" not in question["sensitivity"]["collection_restrictions"]:
            raise SetupError(f"{identifier}: runtime authorization must be marked never_collect")
    for question in value["questions"]:
        identifier = question["id"]
        references = [*question["dependencies"], *[item["question_id"] for item in question["trigger_conditions"]]]
        for reference in references:
            if reference not in seen:
                raise SetupError(f"{identifier}: unknown dependency or trigger question {reference}")
            if positions[reference] >= positions[identifier]:
                raise SetupError(f"{identifier}: dependency order is circular or forward-referencing at {reference}")
    work_finish = next((item for item in value["questions"] if item["id"] == "setup.work-finish-mode"), None)
    if work_finish is None or work_finish["answer"]["valid_values"] != [
        "disabled",
        "on_demand",
        "on_demand_plus_plan_only_event",
    ]:
        raise SetupError("work-completion setup choices differ from the closed three-choice contract")
    return value


def load_catalog() -> dict[str, Any]:
    return validate_catalog(load_json(catalog_path()))


def excluded(relative: PurePosixPath) -> bool:
    return any(relative == root or root in relative.parents for root in FINGERPRINT_EXCLUSIONS)


def fingerprint(root: Path, *, instructions_only: bool = False) -> dict[str, Any]:
    root = root.resolve()
    digest = hashlib.sha256()
    paths: list[str] = []
    if not root.exists():
        candidates: list[Path] = []
    elif instructions_only:
        candidates = sorted(
            path for path in root.rglob("AGENTS.md") if path.is_file() and not path.is_symlink()
        )
    else:
        candidates = sorted(path for path in root.rglob("*") if path.is_file() or path.is_symlink())
    for path in candidates:
        relative = PurePosixPath(path.relative_to(root).as_posix())
        if excluded(relative):
            continue
        kind = "symlink" if path.is_symlink() else "file"
        identity = os.readlink(path).encode("utf-8", errors="surrogateescape") if path.is_symlink() else path.read_bytes()
        rendered = relative.as_posix()
        paths.append(rendered)
        digest.update(rendered.encode("utf-8"))
        digest.update(b"\0")
        digest.update(kind.encode("ascii"))
        digest.update(b"\0")
        digest.update(identity)
        digest.update(b"\0")
    return {
        "algorithm": "sha256_path_type_nul_content_nul_v1",
        "paths": paths,
        "digest": digest.hexdigest(),
    }


def git_read(target: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *argv],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def target_revision(target: Path) -> dict[str, Any]:
    if not (target / ".git").exists():
        return {"scm": "none", "revision": None, "dirty_state_observed": "not_applicable"}
    revision = git_read(target, ["rev-parse", "--verify", "HEAD"])
    if revision.returncode:
        return {"scm": "git", "revision": None, "dirty_state_observed": "unborn"}
    status = git_read(target, ["status", "--porcelain=v1", "--untracked-files=all"])
    dirty = "unknown" if status.returncode else ("dirty" if status.stdout.strip() else "clean")
    return {"scm": "git", "revision": revision.stdout.strip(), "dirty_state_observed": dirty}


def relevant_top_level(target: Path) -> list[str]:
    if not target.exists():
        return []
    result: list[str] = []
    for child in target.iterdir():
        if child.name == ".git":
            continue
        if child.name == ".agent" and child.is_dir() and not child.is_symlink():
            contents = [item for item in child.rglob("*") if item.is_file() or item.is_symlink()]
            if contents and all(PurePosixPath(item.relative_to(target).as_posix()).parts[:2] == (".agent", "transactions") for item in contents):
                continue
        result.append(child.name)
    return sorted(result)


def origin_observation(target: Path) -> tuple[str, str | None, list[str], list[str]]:
    names = (".octon-origin.json", ".octon-mini-origin.json", ".project-blueprint-origin.json")
    present = [name for name in names if (target / name).exists() or (target / name).is_symlink()]
    if (target / ".octon").exists() or (target / ".octon").is_symlink():
        return "invalid", None, [], ["original Octon runtime installation requires separate disposition"]
    if len(present) > 1:
        return "invalid", None, [], ["conflicting origin records require explicit reconciliation"]
    origin_path = target / (present[0] if present else ".octon-origin.json")
    if not origin_path.exists():
        legacy_path = target / ".project-blueprint-origin.json"
        if legacy_path.exists():
            if legacy_path.is_symlink() or not legacy_path.is_file():
                return "invalid", None, [], ["legacy origin provenance is not a regular file"]
            try:
                legacy = load_json(legacy_path)
            except SetupError:
                return "invalid", None, [], ["legacy origin provenance is malformed strict JSON"]
            legacy_version = legacy.get("blueprint_version") if isinstance(legacy, dict) else None
            if (
                not isinstance(legacy, dict)
                or legacy.get("schema_version") != "project-blueprint.origin.v1"
                or legacy.get("blueprint") != "project-blueprint"
                or not isinstance(legacy_version, str)
                or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", legacy_version) is None
            ):
                return "invalid", None, [], ["legacy origin lacks the reviewed Project Blueprint product, schema, or version"]
            return "valid", legacy_version, [], [
                f"valid legacy migration input records Project Blueprint {legacy_version}; no compatibility runtime is enabled"
            ]
        return "absent", None, [], ["no .octon-origin.json was observed"]
    if origin_path.is_symlink() or not origin_path.is_file():
        return "invalid", None, [], ["origin provenance is not a regular file"]
    try:
        value = load_json(origin_path)
    except SetupError:
        return "invalid", None, [], ["origin provenance is malformed strict JSON"]
    version = value.get("octon_mini_version") if isinstance(value, dict) else None
    schema = value.get("schema_version") if isinstance(value, dict) else None
    product = value.get("product") if isinstance(value, dict) else None
    if (
        not isinstance(version, str)
        or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None
        or not isinstance(schema, str)
        or (schema, product, origin_path.name) not in {
            ("octon.project.origin.v1", "octon", ".octon-origin.json"),
            ("octon-mini.project.origin.v1", "octon-mini", ".octon-mini-origin.json"),
        }
    ):
        return "invalid", None, [], [
            "origin provenance lacks the current Octon product, schema, or version"
        ]
    installed: list[str] = []
    packages_path = target / ".agent/packages.json"
    if packages_path.is_file() and not packages_path.is_symlink():
        try:
            packages = load_json(packages_path)
            installed = sorted(
                str(item["id"])
                for item in packages.get("packages", [])
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            )
        except SetupError:
            installed = []
    if product == "octon-mini" and version != "4.2.0":
        return "invalid", version, installed, ["upgrade through the released Mini 4.2.0 baseline first"]
    return "valid", version, installed, [f"valid {schema} provenance records {product} {version}"]


def detect_mode(target: Path) -> tuple[str, list[str], dict[str, Any]]:
    target = target.resolve()
    provenance, installed_version, installed_packages, evidence = origin_observation(target)
    relevant = relevant_top_level(target)
    if provenance == "valid":
        mode = "upgrade"
    elif provenance == "invalid":
        mode = "ambiguous"
    elif not relevant:
        mode = "initialization"
        evidence.append("no established-project content was observed outside allowed transaction artifacts")
    elif any(name in {"octon", ".agent", "project-dossier"} for name in relevant):
        mode = "ambiguous"
        evidence.append("Octon-like generated markers exist without valid origin provenance")
    else:
        mode = "adoption"
        evidence.append("established content exists without Octon origin provenance")
    return mode, evidence, {
        "source_version": source_version(),
        "candidate_version": source_version(),
        "installed_version": installed_version,
        "provenance_status": provenance if mode != "ambiguous" else "ambiguous",
        "installed_packages": installed_packages,
    }


def observed_evidence(source: str, *, limitations: list[str] | None = None) -> dict[str, Any]:
    return {
        "source": source,
        "observed_at": utc_timestamp(),
        "expires_at": None,
        "confidence": "deterministic",
        "limitations": limitations or [],
    }


def question_validity_classes(
    catalog: dict[str, Any],
    question: dict[str, Any],
    evidence: dict[str, Any],
) -> list[str]:
    classes = set(catalog["validity_policy"]["role_defaults"][question["information_role"]])
    if evidence.get("expires_at") is not None:
        classes.add("expiry_bound")
    return sorted(classes)


def binding(
    kind: str,
    reference: str,
    *,
    digest_value: str | None,
    expires_at: str | None = None,
    subject_type: str = "metadata",
) -> dict[str, Any]:
    return {
        "kind": kind,
        "reference": reference,
        "subject_type": subject_type,
        "digest": digest_value,
        "expires_at": expires_at,
    }


def dependency_digest(
    question: dict[str, Any],
    states: dict[str, dict[str, Any]],
) -> str:
    values = []
    for identifier in question["dependencies"]:
        item = states.get(identifier)
        values.append(
            {
                "question_id": identifier,
                "question_version": item.get("question_version") if item else None,
                "state": item.get("state") if item else None,
                "value": item.get("value") if item else None,
            }
        )
    return sha256(canonical_bytes(values))


def evidence_binding_state(target: Path, evidence: dict[str, Any]) -> tuple[str, str]:
    source = str(evidence.get("source", ""))
    for prefix in ("filesystem:", "repo:"):
        if not source.startswith(prefix):
            continue
        raw = source[len(prefix):]
        candidate = Path(raw)
        if candidate.is_absolute():
            path = candidate
        else:
            path = target / candidate
        try:
            path.resolve(strict=False).relative_to(target.resolve())
        except (OSError, ValueError) as error:
            raise SetupError(f"evidence source path escapes the target: {source}") from error
        if path.is_symlink():
            raise SetupError(f"evidence source path is a symlink and cannot be reused: {source}")
        if path.is_file():
            return "file", sha256(path.read_bytes())
        if not path.exists():
            return "absent", sha256(b"absent")
        raise SetupError(f"evidence source path is not a regular file or explicit absence: {source}")
    return "metadata", sha256(canonical_bytes(evidence))


def state_validity(
    catalog: dict[str, Any],
    question: dict[str, Any],
    states: dict[str, dict[str, Any]],
    target: Path,
    evidence: dict[str, Any],
    *,
    reuse_status: str = "current",
    reason: str = "Collected against the current declared dependencies.",
) -> dict[str, Any]:
    classes = question_validity_classes(catalog, question, evidence)
    records = [
        binding(
            "catalog_question",
            question["id"],
            digest_value=sha256(canonical_bytes(question)),
        ),
        binding(
            "question_dependencies",
            question["id"],
            digest_value=dependency_digest(question, states),
        ),
    ]
    if question["information_role"] != "runtime_authorization_forbidden":
        records.append(
            binding(
                "governing_instructions",
                "AGENTS.md",
                digest_value=fingerprint(target, instructions_only=True)["digest"],
            )
        )
    evidence_subject_type, evidence_digest = evidence_binding_state(target, evidence)
    records.append(
        binding(
            "evidence_source",
            evidence["source"],
            digest_value=evidence_digest,
            expires_at=evidence.get("expires_at"),
            subject_type=evidence_subject_type,
        )
    )
    return {
        "classes": classes,
        "bindings": records,
        "reuse_status": reuse_status,
        "reason": reason,
    }


def state_record(
    question: dict[str, Any],
    state: str,
    value: Any,
    supplied_by: str,
    evidence: dict[str, Any],
    *,
    validity: dict[str, Any],
) -> dict[str, Any]:
    return {
        "question_id": question["id"],
        "question_version": question["version"],
        "state": state,
        "information_role": question["information_role"],
        "value": value,
        "supplied_by": supplied_by,
        "evidence": evidence,
        "validity": validity,
    }


def initial_observations(
    catalog: dict[str, Any],
    target: Path,
    mode: str,
    mode_evidence: list[str],
    octon_mini: dict[str, Any],
) -> list[dict[str, Any]]:
    questions = question_map(catalog)
    instruction = fingerprint(target, instructions_only=True)
    provenance_value = dict(octon_mini)
    provenance_value.pop("installed_packages", None)
    rows = [
        (questions["setup.target-identity"], str(target), observed_evidence("inspection:canonical-target")),
        (questions["setup.detected-mode"], mode, observed_evidence("inspection:mode-detection", limitations=mode_evidence)),
        (questions["setup.governing-instructions"], instruction["paths"], observed_evidence("inspection:governing-instructions")),
        (
            questions["setup.octon-mini-provenance"],
            provenance_value,
            observed_evidence(
                "filesystem:.octon-origin.json"
                if (target / ".octon-origin.json").exists()
                else "filesystem:.octon-mini-origin.json"
                if (target / ".octon-mini-origin.json").exists()
                else "filesystem:.project-blueprint-origin.json"
                if (target / ".project-blueprint-origin.json").exists()
                else "inspection:origin-absent"
            ),
        ),
    ]
    states: dict[str, dict[str, Any]] = {}
    result = []
    for question, value, evidence_record in rows:
        record = state_record(
            question,
            "answered",
            value,
            "inspection",
            evidence_record,
            validity=state_validity(
                catalog,
                question,
                states,
                target,
                evidence_record,
                reuse_status="reobserved",
                reason="Direct observation was recomputed for this session.",
            ),
        )
        result.append(record)
        states[question["id"]] = record
    return result


def recommendation_records(target: Path, mode: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if mode in {"initialization", "adoption"}:
        records.extend(
            [
                {
                    "question_id": "setup.project-name",
                    "value": target.name or "Project",
                    "rationale": "Candidate derived from the target directory name; it is not selected.",
                    "evidence_refs": ["filesystem:canonical-target"],
                },
                {
                    "question_id": "setup.layout",
                    "value": "compact",
                    "rationale": "Compact is the documented representation default unless separation materially improves ownership or review.",
                    "evidence_refs": ["octon-mini:profile-manifest"],
                },
            ]
        )
    if (target / ".git").exists():
        records.append(
            {
                "question_id": "setup.scm-selection",
                "value": "git",
                "rationale": "A local Git repository was observed; this is a recommendation, not adoption.",
                "evidence_refs": ["filesystem:.git"],
            }
        )
    return records


def decision_frontmatter(path: Path) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
        value = json.loads("".join(lines[1:end]), object_pairs_hook=strict_object)
    except (StopIteration, json.JSONDecodeError, SetupError):
        return None
    return value if isinstance(value, dict) else None


def decision_path(target: Path, decision_ref: str) -> Path | None:
    root = target / ".agent/decisions"
    if not root.is_dir() or root.is_symlink():
        return None
    matches = [
        path
        for path in sorted(root.glob(f"{decision_ref}*.md"))
        if path.is_file() and not path.is_symlink()
    ]
    return matches[0] if len(matches) == 1 else None


def reusable_decision_states(
    target: Path,
    mode: str,
    catalog: dict[str, Any],
    states: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    registry_path = target / ".agent/decisions/reuse-policy.json"
    if not registry_path.is_file() or registry_path.is_symlink():
        return [], [], []
    registry = load_json(registry_path)
    if (
        not isinstance(registry, dict)
        or set(registry) != {
            "schema_version",
            "document_role",
            "permission_grant",
            "runtime_authorization",
            "records",
            "limitations",
        }
        or registry.get("schema_version") != "harness.decision-reuse-registry.v1"
        or registry.get("permission_grant") is not False
        or registry.get("runtime_authorization") is not False
        or not isinstance(registry.get("records"), list)
    ):
        raise SetupError("project decision-reuse registry is malformed or authorizing")
    questions = question_map(catalog)
    now = datetime.now(timezone.utc)
    instruction_digest = fingerprint(target, instructions_only=True)["digest"]
    reused_states: list[dict[str, Any]] = []
    reused_records: list[dict[str, Any]] = []
    invalid: list[dict[str, str]] = []
    for policy in registry["records"]:
        policy_id = str(policy.get("id", "unknown")) if isinstance(policy, dict) else "unknown"
        if not isinstance(policy, dict):
            invalid.append({"question_id": "setup.decision-reuse", "reason": "Decision-reuse record is not an object."})
            continue
        classification_id = next(
            (
                identifier
                for identifier in policy.get("question_ids", [])
                if isinstance(identifier, str)
                and re.fullmatch(r"setup\.[a-z0-9]+(?:[.-][a-z0-9]+)*", identifier)
            ),
            "setup.decision-reuse",
        )
        expected_policy_fields = {
            "id",
            "status",
            "decision_ref",
            "decision_sha256",
            "authority_source",
            "question_ids",
            "operations",
            "value",
            "applicability",
            "governing_instruction_digest",
            "evidence_refs",
            "valid_from",
            "expires_at",
            "successor",
            "runtime_authorization",
            "external_action_authority",
            "limitations",
        }
        if (
            set(policy) != expected_policy_fields
            or re.fullmatch(r"DRP-[0-9]{4}", policy_id) is None
            or not isinstance(policy.get("question_ids"), list)
            or not isinstance(policy.get("operations"), list)
            or not isinstance(policy.get("limitations"), list)
        ):
            invalid.append({"question_id": classification_id, "reason": "Decision-reuse record does not use the closed v1 contract."})
            continue
        if policy.get("runtime_authorization") is not False or policy.get("external_action_authority") is not False:
            invalid.append({"question_id": classification_id, "reason": "Runtime or external-action authority can never be remembered."})
            continue
        if policy.get("status") != "active" or policy.get("successor") is not None:
            invalid.append({"question_id": classification_id, "reason": "Decision-reuse record is revoked or superseded."})
            continue
        expiry = policy.get("expires_at")
        valid_from = policy.get("valid_from")
        if (
            not isinstance(valid_from, str)
            or parse_time(valid_from, f"{policy_id} valid_from") > now
        ):
            invalid.append({"question_id": classification_id, "reason": "Decision-reuse record is not yet valid."})
            continue
        if expiry is not None and parse_time(expiry, f"{policy_id} expires_at") <= now:
            invalid.append({"question_id": classification_id, "reason": "Decision-reuse record is expired."})
            continue
        applicability = policy.get("applicability", {})
        modes = applicability.get("modes", []) if isinstance(applicability, dict) else []
        if modes and mode not in modes:
            continue
        if "setup.answer" not in policy.get("operations", []):
            continue
        configured_profiles = applicability.get("profiles", []) if isinstance(applicability, dict) else []
        project_profile = None
        project_path = target / ".agent/project.json"
        if project_path.is_file() and not project_path.is_symlink():
            try:
                project_profile = load_json(project_path).get("project", {}).get("profile")
            except SetupError:
                project_profile = None
        if configured_profiles and project_profile not in configured_profiles:
            continue
        path_prefixes = applicability.get("path_prefixes", []) if isinstance(applicability, dict) else []
        if path_prefixes and "." not in path_prefixes:
            continue
        dependency_fingerprints = applicability.get("dependency_fingerprints", []) if isinstance(applicability, dict) else []
        dependency_changed = False
        dependency_items = (
            dependency_fingerprints
            if isinstance(dependency_fingerprints, list)
            else []
        )
        for dependency in dependency_items:
            if not isinstance(dependency, dict):
                dependency_changed = True
                break
            relative = dependency.get("path")
            expected_type = dependency.get("type")
            expected_digest = dependency.get("sha256")
            if (
                not isinstance(relative, str)
                or expected_type not in {"absent", "file"}
                or not isinstance(expected_digest, str)
            ):
                dependency_changed = True
                break
            normalized = PurePosixPath(relative)
            if normalized.is_absolute() or any(part in {"", ".", ".."} for part in normalized.parts):
                dependency_changed = True
                break
            dependency_path = target.joinpath(*normalized.parts)
            if dependency_path.is_symlink():
                dependency_changed = True
                break
            if dependency_path.is_file():
                current_type = "file"
                current_digest = sha256(dependency_path.read_bytes())
            elif not dependency_path.exists():
                current_type = "absent"
                current_digest = sha256(b"absent")
            else:
                dependency_changed = True
                break
            if current_type != expected_type or current_digest != expected_digest:
                dependency_changed = True
                break
        if dependency_changed:
            invalid.append({"question_id": classification_id, "reason": "Decision-reuse applicability dependency fingerprint changed."})
            continue
        if policy.get("governing_instruction_digest") != instruction_digest:
            invalid.append({"question_id": classification_id, "reason": "Governing instructions differ from the accepted reuse boundary."})
            continue
        decision_ref = policy.get("decision_ref")
        if not isinstance(decision_ref, str):
            invalid.append({"question_id": classification_id, "reason": "Decision reference is malformed."})
            continue
        path = decision_path(target, decision_ref)
        record = decision_frontmatter(path) if path is not None else None
        if (
            path is None
            or record is None
            or record.get("schema_version") != "harness.decision.v1"
            or record.get("id") != decision_ref
            or record.get("status") != "accepted"
            or record.get("successor") is not None
            or record.get("authority_source") != policy.get("authority_source")
            or not isinstance(record.get("scope"), str)
            or not record["scope"].strip()
            or sha256(path.read_bytes()) != policy.get("decision_sha256")
        ):
            invalid.append({"question_id": classification_id, "reason": "Accepted decision no longer resolves exactly or was superseded."})
            continue
        applied_questions: list[str] = []
        for identifier in policy.get("question_ids", []):
            question = questions.get(identifier)
            if question is None or identifier in states or not question_eligible(question, mode, states):
                continue
            evidence_record = {
                "source": f"authority:{decision_ref}",
                "observed_at": policy["valid_from"],
                "expires_at": expiry,
                "confidence": "deterministic",
                "limitations": list(policy.get("limitations", []))
                + ["The accepted decision is reused as a policy input, not runtime authorization."],
            }
            validate_answer_type(question, "answered", policy.get("value"))
            validate_answer_evidence(question, evidence_record, "answered")
            validity = state_validity(
                catalog,
                question,
                states,
                target,
                evidence_record,
                reuse_status="preserved",
                reason="Current accepted project-owned decision and reuse applicability remain exact.",
            )
            validity["classes"] = sorted(
                set(validity["classes"])
                | {"decision_successor_or_revocation_bound", "dependency_bound"}
            )
            validity["bindings"].append(
                binding(
                    "decision_record",
                    decision_ref,
                    digest_value=policy["decision_sha256"],
                    expires_at=expiry,
                    subject_type="file",
                )
            )
            state = state_record(
                question,
                "answered",
                policy.get("value"),
                "accepted_decision",
                evidence_record,
                validity=validity,
            )
            reused_states.append(state)
            states[identifier] = state
            applied_questions.append(identifier)
        if applied_questions:
            reused_records.append(
                {
                    "reuse_policy_id": policy_id,
                    "decision_ref": decision_ref,
                    "question_ids": applied_questions,
                    "valid_until": expiry,
                    "limitations": list(policy.get("limitations", [])),
                }
            )
    return reused_states, reused_records, invalid


def session_question_state(session: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["question_id"]: item for item in session["question_states"]}


def accepted_decision_identity(item: dict[str, Any]) -> tuple[Any, ...]:
    bindings = tuple(
        sorted(
            (
                binding_item.get("kind"),
                binding_item.get("reference"),
                binding_item.get("digest"),
                binding_item.get("expires_at"),
            )
            for binding_item in item.get("validity", {}).get("bindings", [])
            if binding_item.get("kind") == "decision_record"
        )
    )
    return (
        item.get("value"),
        item.get("evidence", {}).get("source"),
        bindings,
    )


def condition_matches(condition: dict[str, Any], states: dict[str, dict[str, Any]]) -> bool:
    state = states.get(condition["question_id"])
    if state is None:
        return False
    operator = condition["operator"]
    if operator == "answered":
        return state["state"] == "answered"
    if state["state"] != "answered":
        return False
    value = state["value"]
    values = condition["values"]
    if operator == "equals":
        return len(values) == 1 and value == values[0]
    if operator == "in":
        return value in values
    if operator == "not_in":
        return value not in values
    return False


def question_applicable(question: dict[str, Any], mode: str, states: dict[str, dict[str, Any]]) -> bool:
    if mode not in question["modes"] or question["information_role"] == "runtime_authorization_forbidden":
        return False
    return all(condition_matches(item, states) for item in question["trigger_conditions"])


def question_eligible(question: dict[str, Any], mode: str, states: dict[str, dict[str, Any]]) -> bool:
    if not question_applicable(question, mode, states) or question["id"] in states:
        return False
    return all(dependency in states for dependency in question["dependencies"])


def validate_answer_type(question: dict[str, Any], state: str, value: Any) -> None:
    answer = question["answer"]
    if state != "answered":
        allowed_key = {
            "unknown": "allow_unknown",
            "deferred": "allow_deferred",
            "not_applicable": "allow_not_applicable",
        }[state]
        if not answer[allowed_key]:
            raise SetupError(f"{question['id']}: state {state} is not allowed")
        if value is not None:
            raise SetupError(f"{question['id']}: unresolved or inapplicable state must use null value")
        return
    expected = answer["type"]
    valid = (
        (expected == "string" and isinstance(value, str) and bool(value.strip()))
        or (expected == "integer" and isinstance(value, int) and not isinstance(value, bool))
        or (expected == "boolean" and isinstance(value, bool))
        or (expected == "enum" and value in answer["valid_values"])
        or (expected == "string_list" and isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value) and len(value) == len(set(value)))
        or (expected == "object" and isinstance(value, dict))
        or (expected == "object_list" and isinstance(value, list) and all(isinstance(item, dict) for item in value))
    )
    if not valid:
        raise SetupError(f"{question['id']}: value does not match answer type {expected}")


def contains_secret(value: Any) -> bool:
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in SECRET_PATTERNS)
    if isinstance(value, list):
        return any(contains_secret(item) for item in value)
    if isinstance(value, dict):
        return any(
            str(key).casefold() in {"password", "secret", "token", "private_key", "credential"}
            or contains_secret(item)
            for key, item in value.items()
        )
    return False


def exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise SetupError(f"{label} requires exactly: {', '.join(sorted(expected))}")
    return value


def shell_free_argv(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or any(not isinstance(item, str) or not item or "\x00" in item for item in value)
    ):
        raise SetupError(f"{label}: argv must be a shell-free string array")
    if not value:
        return value
    if Path(value[0]).name.casefold() in SHELL_EXECUTABLES or any(
        item.casefold() in INLINE_SHELL_FLAGS for item in value[1:]
    ):
        raise SetupError(f"{label}: shell executables and inline shell flags are prohibited")
    return value


def validate_special_answer(identifier: str, value: Any, states: dict[str, dict[str, Any]]) -> None:
    if identifier == "setup.project-name":
        if (
            len(value.strip()) > 200
            or any(ord(character) < 32 or ord(character) == 127 for character in value)
            or "{{" in value
            or "}}" in value
        ):
            raise SetupError(f"{identifier}: project name is unsafe or longer than 200 characters")
    elif identifier == "setup.project-slug" and re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", value
    ) is None:
        raise SetupError(f"{identifier}: project slug is not portable")
    elif identifier == "setup.assurance-profile" and "setup.write-capable-humans" in states:
        # The two values are intentionally never compared or derived.
        pass
    elif identifier == "setup.write-capable-humans" and value < 0:
        raise SetupError("setup.write-capable-humans: count must be non-negative")
    elif identifier == "setup.collaboration-concurrency":
        exact_keys(value, {"human_writers", "agents_or_automation"}, identifier)
        if any(not isinstance(value[key], int) or isinstance(value[key], bool) or value[key] < 0 for key in value):
            raise SetupError(f"{identifier}: concurrency values must be non-negative integers")
    elif identifier == "setup.first-task":
        required = {"title", "scope", "authority_basis", "owner", "operator", "acceptance", "validation", "next_action"}
        exact_keys(value, required, identifier)
        if any(not value[key] for key in required):
            raise SetupError(f"{identifier}: every first-task semantic field is required")
        if not isinstance(value["acceptance"], list) or not isinstance(value["validation"], list):
            raise SetupError(f"{identifier}: acceptance and validation must be arrays")
    elif identifier.startswith("setup.hook-"):
        required = {"status", "owner", "argv", "version_argv", "timeout_seconds", "evidence_freshness_days", "repository_write_paths", "external_effects", "limitations", "rationale"}
        exact_keys(value, required, identifier)
        if value["status"] not in {"configured", "not_applicable"}:
            raise SetupError(f"{identifier}: status must be configured or not_applicable")
        for key in ("repository_write_paths", "external_effects", "limitations"):
            if (
                not isinstance(value[key], list)
                or any(not isinstance(item, str) or not item for item in value[key])
                or len(value[key]) != len(set(value[key]))
            ):
                raise SetupError(f"{identifier}: {key} must be a string array")
        if (
            not isinstance(value["owner"], str)
            or not value["owner"].strip()
            or not isinstance(value["rationale"], str)
            or not value["rationale"].strip()
            or not isinstance(value["timeout_seconds"], int)
            or isinstance(value["timeout_seconds"], bool)
            or value["timeout_seconds"] <= 0
            or not isinstance(value["evidence_freshness_days"], int)
            or isinstance(value["evidence_freshness_days"], bool)
            or value["evidence_freshness_days"] <= 0
        ):
            raise SetupError(f"{identifier}: owner, rationale, timeout, and freshness are required")
        shell_free_argv(
            value["argv"],
            f"{identifier}.argv",
            allow_empty=value["status"] == "not_applicable",
        )
        shell_free_argv(
            value["version_argv"],
            f"{identifier}.version_argv",
            allow_empty=value["status"] == "not_applicable",
        )
        if value["status"] == "configured" and (
            not value["argv"] or not value["version_argv"]
        ):
            raise SetupError(f"{identifier}: configured hooks require argv and version argv")
        for path in value["repository_write_paths"]:
            relative = PurePosixPath(path)
            if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
                raise SetupError(f"{identifier}: repository write paths must be safe relative paths")
    elif identifier in {"setup.adoption-review", "setup.upgrade-review"}:
        required = {"proposal", "review", "proposal_digest"}
        if identifier == "setup.upgrade-review":
            required.add("legacy_seed")
        exact_keys(value, required, identifier)
        for key in ("proposal", "review"):
            if not isinstance(value[key], str) or not Path(value[key]).is_absolute():
                raise SetupError(f"{identifier}: {key} must be an absolute artifact path")
        if (
            identifier == "setup.upgrade-review"
            and value["legacy_seed"] is not None
            and (
                not isinstance(value["legacy_seed"], str)
                or not Path(value["legacy_seed"]).is_absolute()
            )
        ):
            raise SetupError(f"{identifier}: legacy_seed must be null or an absolute path")
        if re.fullmatch(r"[a-f0-9]{64}", str(value["proposal_digest"])) is None:
            raise SetupError(f"{identifier}: proposal_digest must be exact lowercase SHA-256")
    elif identifier == "setup.optional-package-assessments":
        families = {
            "operations_observability",
            "security_supply_chain",
            "context_packages",
            "domain_extensions",
            "high_assurance_conditional_controls",
        }
        if not value or any(key not in families for key in value):
            raise SetupError(f"{identifier}: assessment must name one or more supported trigger families")
        for family, assessment in value.items():
            exact_keys(assessment, {"status", "rationale", "evidence_refs"}, f"{identifier}.{family}")
            if assessment["status"] not in {"applicable", "not_applicable", "unknown", "deferred"}:
                raise SetupError(f"{identifier}.{family}: invalid assessment status")
            if not isinstance(assessment["rationale"], str) or not assessment["rationale"].strip():
                raise SetupError(f"{identifier}.{family}: rationale is required")
            if (
                not isinstance(assessment["evidence_refs"], list)
                or any(not isinstance(item, str) or not item for item in assessment["evidence_refs"])
                or len(assessment["evidence_refs"]) != len(set(assessment["evidence_refs"]))
            ):
                raise SetupError(f"{identifier}.{family}: evidence_refs must be a unique string array")
    elif identifier == "setup.repository-contract":
        exact_keys(value, {"identity", "remote", "default_branch"}, identifier)
        if any(not isinstance(value[key], str) or not value[key].strip() for key in value):
            raise SetupError(f"{identifier}: every repository field must be exact and non-empty")
    elif identifier == "setup.provider-assessment":
        exact_keys(
            value,
            {"adapter", "hosted_repository", "configuration_is_authority"},
            identifier,
        )
        if value["adapter"] not in {"none", "github_cli"}:
            raise SetupError(f"{identifier}: adapter must be none or github_cli")
        if value["configuration_is_authority"] is not False:
            raise SetupError(f"{identifier}: provider configuration is never authority")
        if value["adapter"] == "none" and value["hosted_repository"] is not None:
            raise SetupError(f"{identifier}: adapter none requires a null hosted repository")
        if value["adapter"] == "github_cli" and (
            not isinstance(value["hosted_repository"], str)
            or not value["hosted_repository"].strip()
        ):
            raise SetupError(f"{identifier}: github_cli requires an exact hosted repository")
    elif identifier == "setup.upgrade-evidence" and not value:
        raise SetupError(f"{identifier}: at least one exact evidence reference is required")
    elif identifier == "setup.workflow-selection":
        writers = states.get("setup.write-capable-humans")
        if writers and writers["state"] == "answered":
            count = writers["value"]
            if count not in {1, 2, 3, 4, 5}:
                raise SetupError(f"{identifier}: no supported workflow exists for {count} write-capable humans")
            allowed = {1: {"solo_direct", "solo_hybrid"}, 2: {"pair_pr"}, 3: {"tiny_pr"}, 4: {"tiny_pr"}, 5: {"tiny_pr"}}[count]
            if value not in allowed:
                raise SetupError(f"{identifier}: {value} conflicts with current write-capable-human evidence")
    elif identifier == "setup.concurrent-work-modifier" and value is True:
        concurrency = states.get("setup.collaboration-concurrency")
        if not concurrency or concurrency["state"] != "answered" or not any(concurrency["value"].values()):
            raise SetupError(f"{identifier}: true requires positive concurrency evidence")
    elif identifier == "setup.integration-and-checks":
        required = {
            "integration_method",
            "required_hosted_checks",
            "eligible_peer_reviewers",
            "solo_hybrid_pull_request",
            "remote_cleanup",
            "local_cleanup",
        }
        exact_keys(value, required, identifier)
        workflow = states.get("setup.workflow-selection")
        if workflow is None or workflow.get("state") != "answered":
            raise SetupError(f"{identifier}: an exact workflow selection is required")
        workflow_id = workflow["value"]
        allowed_methods = {
            "solo_direct": {"not_applicable"},
            "solo_hybrid": {"merge_commit", "squash_merge", "rebase_then_fast_forward"},
            "pair_pr": {"merge_commit", "squash_merge", "rebase_then_fast_forward"},
            "tiny_pr": {"merge_commit", "squash_merge", "rebase_then_fast_forward"},
        }[workflow_id]
        if value["integration_method"] not in allowed_methods:
            raise SetupError(f"{identifier}: integration method is unsupported by {workflow_id}")
        checks = value["required_hosted_checks"]
        exact_keys(checks, {"status", "names"}, f"{identifier}.required_hosted_checks")
        if (
            checks["status"] != "configured"
            or not isinstance(checks["names"], list)
            or any(not isinstance(item, str) or not item for item in checks["names"])
            or len(checks["names"]) != len(set(checks["names"]))
        ):
            raise SetupError(f"{identifier}: hosted checks require configured status and an explicit list")
        reviewers = value["eligible_peer_reviewers"]
        if (
            not isinstance(reviewers, list)
            or any(not isinstance(item, str) or not item for item in reviewers)
            or len(reviewers) != len(set(reviewers))
        ):
            raise SetupError(f"{identifier}: eligible reviewers must be an explicit list")
        if workflow_id in {"pair_pr", "tiny_pr"}:
            provider = states.get("setup.provider-assessment")
            if (
                not reviewers
                or provider is None
                or provider.get("state") != "answered"
                or provider["value"].get("adapter") == "none"
            ):
                raise SetupError(f"{identifier}: peer-review workflows require an assessed provider and eligible peer reviewers")
        elif reviewers:
            raise SetupError(f"{identifier}: solo workflows must not invent peer-review capacity")
        expected_self_pr = {"enabled", "disabled"} if workflow_id == "solo_hybrid" else {"not_applicable"}
        if value["solo_hybrid_pull_request"] not in expected_self_pr:
            raise SetupError(f"{identifier}: solo self-PR choice conflicts with {workflow_id}")
        cleanup_values = {"required", "disabled"}
        if value["remote_cleanup"] not in cleanup_values or value["local_cleanup"] not in cleanup_values:
            raise SetupError(f"{identifier}: cleanup choices must be required or disabled")
        if workflow_id == "solo_direct" and (
            value["remote_cleanup"] != "disabled" or value["local_cleanup"] != "disabled"
        ):
            raise SetupError(f"{identifier}: solo_direct has no task-branch cleanup")
    elif identifier == "setup.work-finish-local-controls":
        required = {"validation_hooks", "git_hooks", "core_fsmonitor", "assurance_control_refs", "completion_hook"}
        exact_keys(value, required, identifier)
        if value["git_hooks"] != "require_none" or value["core_fsmonitor"] != "inactive":
            raise SetupError(f"{identifier}: v1 requires no active Git hooks and inactive core.fsmonitor")
        if not isinstance(value["validation_hooks"], list) or not isinstance(value["assurance_control_refs"], list):
            raise SetupError(f"{identifier}: hooks and assurance references must be explicit arrays")
        hook_questions = {
            "project_test": "setup.hook-test",
            "project_lint": "setup.hook-lint",
            "project_build": "setup.hook-build",
            "project_closure": "setup.hook-closure",
        }
        if (
            not value["validation_hooks"]
            or len(value["validation_hooks"]) != len(set(value["validation_hooks"]))
            or any(item not in hook_questions for item in value["validation_hooks"])
        ):
            raise SetupError(f"{identifier}: at least one unique supported validation hook is required")
        for hook_id in value["validation_hooks"]:
            hook = states.get(hook_questions[hook_id])
            if (
                hook is None
                or hook.get("state") != "answered"
                or hook["value"].get("status") != "configured"
                or hook["value"].get("repository_write_paths")
                or hook["value"].get("external_effects")
            ):
                raise SetupError(f"{identifier}: validation hooks must be configured and read-only")
        if (
            any(not isinstance(item, str) or not item for item in value["assurance_control_refs"])
            or len(value["assurance_control_refs"]) != len(set(value["assurance_control_refs"]))
        ):
            raise SetupError(f"{identifier}: assurance references must be a unique string array")
        if value["completion_hook"] not in {"disabled", "plan_only_on_completion_event"}:
            raise SetupError(f"{identifier}: completion hook may be disabled or plan-only")
        finish_mode = states.get("setup.work-finish-mode", {}).get("value")
        expected_completion_hook = (
            "plan_only_on_completion_event"
            if finish_mode == "on_demand_plus_plan_only_event"
            else "disabled"
        )
        if value["completion_hook"] != expected_completion_hook:
            raise SetupError(f"{identifier}: completion hook conflicts with the selected work-finish mode")


def validate_answer_evidence(question: dict[str, Any], evidence: Any, state: str) -> dict[str, Any]:
    if not isinstance(evidence, dict) or set(evidence) != ANSWER_EVIDENCE_KEYS:
        raise SetupError(f"{question['id']}: answer evidence uses an invalid closed contract")
    if (
        not isinstance(evidence.get("source"), str)
        or not evidence["source"].strip()
        or evidence.get("confidence") not in {"low", "medium", "high", "deterministic"}
        or not isinstance(evidence.get("limitations"), list)
        or any(not isinstance(item, str) or not item for item in evidence["limitations"])
    ):
        raise SetupError(f"{question['id']}: answer evidence is malformed")
    observed = parse_time(evidence.get("observed_at"), f"{question['id']} observed_at")
    expiry = evidence.get("expires_at")
    if expiry is not None:
        expires = parse_time(expiry, f"{question['id']} expires_at")
        if expires <= observed:
            raise SetupError(f"{question['id']}: evidence expiry must follow observation")
        if expires <= datetime.now(timezone.utc):
            raise SetupError(f"{question['id']}: evidence is already stale")
    if state == "answered" and question["evidence"]["freshness_days"] is not None and expiry is None:
        raise SetupError(f"{question['id']}: current evidence requires an explicit expiry")
    return evidence


def apply_answer_batch(session: dict[str, Any], payload: Any, catalog: dict[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema_version", "permission_grant", "session_digest", "answers", "limitations"}
        or payload.get("schema_version") != ANSWER_SCHEMA
        or payload.get("permission_grant") is not False
        or payload.get("session_digest") != session["canonical_session_digest"]
        or not isinstance(payload.get("answers"), list)
        or not payload["answers"]
        or not isinstance(payload.get("limitations"), list)
    ):
        raise SetupError("answer batch is malformed, authorizing, or bound to a stale session digest")
    questions = question_map(catalog)
    states = session_question_state(session)
    observed_ids: set[str] = set()
    successor = copy.deepcopy(session)
    for raw in payload["answers"]:
        if not isinstance(raw, dict) or set(raw) != ANSWER_INPUT_KEYS:
            raise SetupError("answer batch entries use an invalid closed contract")
        identifier = raw.get("question_id")
        if identifier in observed_ids:
            raise SetupError(f"duplicate answer question ID: {identifier}")
        observed_ids.add(identifier)
        question = questions.get(identifier)
        if question is None:
            raise SetupError(f"unknown setup question ID: {identifier}")
        if question["information_role"] == "runtime_authorization_forbidden":
            raise SetupError(f"{identifier}: runtime authorization is forbidden during setup")
        if identifier in states:
            raise SetupError(f"{identifier}: an answered question cannot be silently overwritten; reinspection or successor review is required")
        if not question_eligible(question, session["mode"], states):
            raise SetupError(f"{identifier}: dependencies or trigger conditions are not yet satisfied")
        state = raw.get("state")
        if state not in STATES:
            raise SetupError(f"{identifier}: invalid answer state")
        validate_answer_type(question, state, raw.get("value"))
        if state == "answered":
            validate_special_answer(identifier, raw["value"], states)
            if contains_secret(raw["value"]):
                raise SetupError(f"{identifier}: answer appears to contain secret material")
            if question["information_role"] == "accepted_authority_reference" and isinstance(raw["value"], str) and not raw["value"].startswith(AUTHORITY_PREFIXES):
                raise SetupError(f"{identifier}: accepted authority references must start authority: or external:")
        evidence = validate_answer_evidence(question, raw.get("evidence"), state)
        if raw.get("supplied_by") not in {"user", "agent", "tty", "cli", "review_artifact"}:
            raise SetupError(f"{identifier}: invalid answer source")
        record = state_record(
            question,
            state,
            raw.get("value"),
            raw["supplied_by"],
            evidence,
            validity=state_validity(
                catalog,
                question,
                states,
                Path(session["target_identity"]["canonical_path"]),
                evidence,
            ),
        )
        successor["question_states"].append(record)
        states[identifier] = record
        for bucket in ("needs_confirmation", "invalidated", "newly_introduced"):
            successor["reinspection"][bucket] = [
                item
                for item in successor["reinspection"][bucket]
                if item.get("question_id") != identifier
            ]
    successor["sequence"] += 1
    successor["updated_at"] = utc_timestamp()
    successor["successor_of"] = {
        "session_id": session["session_id"],
        "canonical_session_digest": session["canonical_session_digest"],
        "reason": "reviewed answer batch",
    }
    successor["session_id"] = "SETUP-" + secrets.token_hex(12)
    successor["limitations"] = sorted(set(successor["limitations"] + payload["limitations"]))
    return finalize_session(successor, catalog)


def work_completion_assessment(session: dict[str, Any], states: dict[str, dict[str, Any]]) -> dict[str, Any]:
    selection = states.get("setup.work-finish-mode")
    if selection is None or selection["state"] not in {"answered", "deferred"}:
        return {"selected_mode": None, "status": "unanswered", "missing_prerequisites": [], "closure_sequence": [], "external_action_authorization": False}
    if selection["state"] == "deferred":
        return {
            "selected_mode": None,
            "status": "deferred",
            "missing_prerequisites": [],
            "closure_sequence": [],
            "external_action_authorization": False,
        }
    if selection["value"] == "disabled":
        return {
            "selected_mode": "disabled",
            "status": "disabled",
            "missing_prerequisites": [],
            "closure_sequence": [],
            "external_action_authorization": False,
        }
    pending: list[tuple[int, str, str, bool]] = []
    octon_mini = session.get("octon_mini", {})
    scm = states.get("setup.scm-selection")
    if scm is None or scm.get("state") != "answered" or scm.get("value") != "git":
        pending.append((1, "decision", "select Git through project-owned SCM authority", False))
    workflow = states.get("setup.workflow-selection")
    if workflow is None or workflow.get("state") != "answered":
        pending.append((2, "decision", "select a supported workflow from current collaboration evidence", False))
    authority = states.get("setup.workflow-authority")
    if authority is None or authority.get("state") != "answered":
        pending.append((3, "decision", "accept the exact workflow through the project ADR or approval process", False))
    if "small-team-git-portfolio" not in octon_mini.get("installed_packages", []):
        pending.append((4, "package", "install the content-addressed small-team Git portfolio through its existing package transaction", True))
    for identifier, stage, description, parallel in (
        ("setup.repository-contract", 4, "record exact repository identity, remote, and default branch", True),
        ("setup.work-finish-local-controls", 4, "configure reviewed read-only hooks and required local safety controls", True),
        ("setup.provider-assessment", 5, "complete the provider adapter assessment, including an explicit not-applicable result when valid", False),
        ("setup.integration-and-checks", 6, "select the supported integration method, exact check set, reviewers, and cleanup policy", False),
    ):
        item = states.get(identifier)
        if item is None or item.get("state") not in {"answered", "not_applicable"}:
            pending.append((stage, "configuration", description, parallel))
    pending.sort(key=lambda item: item[0])
    missing = [description for _, _, description, _ in pending]
    closure = [
        {
            "order": index,
            "kind": kind,
            "description": description,
            "can_run_in_parallel": parallel,
            "blocks_enablement": True,
        }
        for index, (_, kind, description, parallel) in enumerate(pending, 1)
    ]
    return {
        "selected_mode": selection["value"],
        "status": "pending_prerequisites" if missing else "eligible_for_separate_configuration",
        "missing_prerequisites": missing,
        "closure_sequence": closure,
        "external_action_authorization": False,
    }


def setup_closure_sequence(
    catalog: dict[str, Any],
    states: dict[str, dict[str, Any]],
    blockers: list[dict[str, str]],
    work_completion: dict[str, Any],
) -> list[dict[str, Any]]:
    blocker_ids = {item["question_id"] for item in blockers}
    unresolved_ids = {
        identifier
        for identifier, item in states.items()
        if item["state"] in {"unknown", "deferred"}
    }
    candidate_ids = blocker_ids | unresolved_ids
    rows: list[dict[str, Any]] = []
    for question in catalog["questions"]:
        identifier = question["id"]
        if identifier not in candidate_ids:
            continue
        if identifier not in blocker_ids and question["family"] == "project_generation":
            continue
        if question["information_role"] == "accepted_authority_reference":
            kind = "approval"
        elif question["family"] == "commands_hooks":
            kind = "configuration"
        elif question["family"] == "optional_packages":
            kind = "package"
        elif question["family"] in {"collaboration", "scm_workflow"}:
            kind = "evidence" if question["evidence"]["required"] else "decision"
        elif question["family"] in {"existing_authority", "upgrade"}:
            kind = "specialist_review"
        else:
            kind = "decision"
        rows.append(
            {
                "question_id": identifier,
                "kind": kind,
                "description": f"Resolve {identifier}: {question['change_consequences']}",
                "can_run_in_parallel": not any(
                    dependency in candidate_ids for dependency in question["dependencies"]
                ),
                "blocks_plan": identifier in blocker_ids,
                "blocks_adoption_or_feature": True,
            }
        )
    package_assessments = states.get("setup.optional-package-assessments")
    if package_assessments and package_assessments.get("state") == "answered":
        for family, assessment in sorted(package_assessments["value"].items()):
            status = assessment["status"]
            if status == "not_applicable":
                continue
            family_label = family.replace("_", " ")
            if status == "applicable":
                kind = "package"
                description = (
                    f"Plan the applicable {family_label} package or control through its "
                    "existing reviewed transaction"
                )
            else:
                kind = "evidence"
                description = (
                    f"Resolve the {status} {family_label} applicability assessment "
                    "from current project-risk evidence"
                )
            rows.append(
                {
                    "question_id": "setup.optional-package-assessments",
                    "kind": kind,
                    "description": description,
                    "can_run_in_parallel": True,
                    "blocks_plan": False,
                    "blocks_adoption_or_feature": True,
                }
            )
    descriptions = {item["description"] for item in rows}
    for item in work_completion["closure_sequence"]:
        if item["description"] in descriptions:
            continue
        rows.append(
            {
                "question_id": None,
                "kind": item["kind"],
                "description": item["description"],
                "can_run_in_parallel": item["can_run_in_parallel"],
                "blocks_plan": False,
                "blocks_adoption_or_feature": item["blocks_enablement"],
            }
        )
    for index, item in enumerate(rows, 1):
        item["order"] = index
    return rows


def finalize_session(session: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    questions = question_map(catalog)
    states = session_question_state(session)
    if len(states) != len(session["question_states"]):
        raise SetupError("setup session contains duplicate question IDs")
    inventories = {state: sorted(item["question_id"] for item in session["question_states"] if item["state"] == state) for state in STATES}
    inventories["needs_confirmation"] = sorted(
        item["question_id"] for item in session["reinspection"]["needs_confirmation"]
    )
    inventories["invalidated"] = sorted(
        item["question_id"] for item in session["reinspection"]["invalidated"]
    )
    session["inventories"] = inventories
    session["selected_profile"] = states.get("setup.assurance-profile", {}).get("value") if states.get("setup.assurance-profile", {}).get("state") == "answered" else None
    session["selected_layout"] = states.get("setup.layout", {}).get("value") if states.get("setup.layout", {}).get("state") == "answered" else None
    session["user_selections"] = [
        {"question_id": item["question_id"], "value": item["value"], "accepted_authority": False}
        for item in session["question_states"]
        if item["state"] == "answered"
        and item["supplied_by"] in {"user", "agent", "tty", "cli", "review_artifact"}
        and item["information_role"] in {"owner_selection", "initialization_input"}
    ]
    session["accepted_authority_references"] = [
        {
            "question_id": item["question_id"],
            "reference": item["value"],
            "setup_validation": "reference_syntax_valid_project_resolution_required",
        }
        for item in session["question_states"]
        if item["state"] == "answered" and item["information_role"] == "accepted_authority_reference" and isinstance(item["value"], str) and item["value"].startswith(AUTHORITY_PREFIXES)
    ]
    blockers: list[dict[str, str]] = []
    eligible: list[str] = []
    for question in catalog["questions"]:
        identifier = question["id"]
        if question_eligible(question, session["mode"], states):
            eligible.append(identifier)
        if not question["blocking"] or not question_applicable(question, session["mode"], states):
            continue
        state = states.get(identifier)
        if state is None or state["state"] == "unknown":
            blockers.append({
                "question_id": identifier,
                "consequence": question["change_consequences"],
                "required_action": "provide a reviewed answer or use an allowed deferred state",
            })
    session["unresolved_blockers"] = blockers
    session["next_eligible_questions"] = eligible
    assessment = work_completion_assessment(session, states)
    session["work_completion_assessment"] = assessment
    session["minimum_closure_sequence"] = setup_closure_sequence(
        catalog, states, blockers, assessment
    )
    session["session_status"] = "ready_for_plan" if not blockers else "collecting"
    session["canonical_session_digest"] = record_digest(session, "canonical_session_digest")
    return session


def create_session(
    mode: str,
    target: Path,
    *,
    catalog_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if mode not in MODES:
        raise SetupError(f"unsupported setup mode: {mode}")
    target = target.expanduser().resolve()
    if not target.exists():
        if mode != "initialization" or not target.parent.is_dir():
            raise SetupError("setup target must exist, except an initialization target with an existing parent")
        observed_target = target
    elif target.is_symlink() or not target.is_dir():
        raise SetupError("setup target must be a real directory")
    else:
        observed_target = target
    detected, evidence, octon_mini = detect_mode(observed_target)
    if detected == "ambiguous":
        raise SetupError("target mode is ambiguous: " + "; ".join(evidence))
    if detected != mode:
        raise SetupError(f"target evidence supports {detected}, not requested {mode}")
    catalog = (
        validate_catalog(copy.deepcopy(catalog_override))
        if catalog_override is not None
        else load_catalog()
    )
    now = utc_timestamp()
    instruction = fingerprint(observed_target, instructions_only=True)
    observations = initial_observations(
        catalog, observed_target, detected, evidence, octon_mini
    )
    observed_states = {item["question_id"]: item for item in observations}
    reused_states, reused_decisions, invalid_reuse = reusable_decision_states(
        observed_target,
        mode,
        catalog,
        observed_states,
    )
    observations.extend(reused_states)
    session: dict[str, Any] = {
        "schema_version": SESSION_SCHEMA,
        "artifact_kind": "setup_session",
        "artifact_version": SESSION_VERSION,
        "permission_grant": False,
        "session_id": "SETUP-" + secrets.token_hex(12),
        "sequence": 1,
        "created_at": now,
        "updated_at": now,
        "mode": mode,
        "target_identity": {
            "requested_path": str(target),
            "canonical_path": str(observed_target),
            "detected_mode": detected,
            "mode_evidence": evidence,
        },
        "target_revision": target_revision(observed_target),
        "target_fingerprint": fingerprint(observed_target),
        "governing_instruction_fingerprint": instruction,
        "octon_mini": octon_mini,
        "question_catalog": {
            "schema_version": catalog["schema_version"],
            "catalog_version": catalog["catalog_version"],
            "sha256": catalog_digest(catalog),
        },
        "validity_policy_version": catalog["validity_policy"]["schema_version"],
        "selected_profile": None,
        "selected_layout": None,
        "question_states": observations,
        "reinspection": {
            "preserved": [
                {
                    "question_id": item["question_id"],
                    "reason": "Current accepted project-owned decision was reused within its exact validity boundary.",
                }
                for item in reused_states
            ],
            "reobserved": [
                {
                    "question_id": item["question_id"],
                    "reason": "Direct observation was computed for this new session.",
                }
                for item in observations
                if item["supplied_by"] == "inspection"
            ],
            "needs_confirmation": [],
            "invalidated": invalid_reuse,
            "newly_introduced": [],
        },
        "inventories": {**{state: [] for state in STATES}, "needs_confirmation": [], "invalidated": []},
        "recommendations": recommendation_records(observed_target, mode),
        "user_selections": [],
        "accepted_authority_references": [],
        "reused_decisions": reused_decisions,
        "unresolved_blockers": [],
        "next_eligible_questions": [],
        "generated_plan_references": [],
        "work_completion_assessment": {"selected_mode": None, "status": "unanswered", "missing_prerequisites": [], "closure_sequence": [], "external_action_authorization": False},
        "minimum_closure_sequence": [],
        "session_status": "collecting",
        "successor_of": None,
        "limitations": [
            "The session grants no permission and creates no accepted project authority.",
            "Recommendations, user selections, accepted-authority references, and runtime authorization remain separate.",
            "Inspection did not execute hooks, refresh generated artifacts, query hosted providers, install packages, or modify the target.",
            "Structural setup evidence does not establish implementation, specialist approval, release, production, efficacy, or commercial readiness.",
        ],
        "canonical_session_digest": "",
    }
    return finalize_session(session, catalog)


def validate_session_shape(value: Any, catalog: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "artifact_kind", "artifact_version", "permission_grant", "session_id", "sequence", "created_at", "updated_at", "mode",
        "target_identity", "target_revision", "target_fingerprint", "governing_instruction_fingerprint", "octon_mini", "question_catalog", "selected_profile",
        "selected_layout", "validity_policy_version", "question_states", "reinspection", "inventories", "recommendations", "user_selections", "accepted_authority_references", "reused_decisions", "unresolved_blockers",
        "next_eligible_questions", "generated_plan_references", "work_completion_assessment", "minimum_closure_sequence", "session_status", "successor_of", "limitations", "canonical_session_digest",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise SetupError("setup session uses an invalid closed top-level contract")
    if (
        value.get("schema_version") != SESSION_SCHEMA
        or value.get("artifact_kind") != "setup_session"
        or value.get("artifact_version") != SESSION_VERSION
        or value.get("validity_policy_version")
        != catalog["validity_policy"]["schema_version"]
        or value.get("permission_grant") is not False
        or value.get("mode") not in MODES
        or re.fullmatch(r"SETUP-[a-f0-9]{24}", str(value.get("session_id", ""))) is None
        or not isinstance(value.get("question_states"), list)
        or record_digest(value, "canonical_session_digest") != value.get("canonical_session_digest")
    ):
        raise SetupError("setup session metadata or canonical digest is invalid")
    reinspection = value.get("reinspection")
    if (
        not isinstance(reinspection, dict)
        or set(reinspection)
        != {"preserved", "reobserved", "needs_confirmation", "invalidated", "newly_introduced"}
        or any(not isinstance(reinspection[key], list) for key in reinspection)
        or not isinstance(value.get("reused_decisions"), list)
    ):
        raise SetupError("setup session reinspection or reused-decision contract is malformed")
    catalog_ref = value.get("question_catalog")
    if not isinstance(catalog_ref, dict) or catalog_ref != {
        "schema_version": catalog["schema_version"],
        "catalog_version": catalog["catalog_version"],
        "sha256": catalog_digest(catalog),
    }:
        raise SetupError("setup question catalog definitions changed; reinspection is required")
    questions = question_map(catalog)
    seen: set[str] = set()
    validated_states: dict[str, dict[str, Any]] = {}
    for item in value["question_states"]:
        if not isinstance(item, dict) or set(item) != {"question_id", "question_version", "state", "information_role", "value", "supplied_by", "evidence", "validity"}:
            raise SetupError("setup question state uses an invalid closed contract")
        identifier = item.get("question_id")
        question = questions.get(identifier)
        if question is None or identifier in seen:
            raise SetupError(f"setup session contains unknown or duplicate question ID: {identifier}")
        seen.add(identifier)
        if item.get("question_version") != question["version"] or item.get("information_role") != question["information_role"]:
            raise SetupError(f"{identifier}: question definition changed; re-answering is required")
        if not question_eligible(question, value["mode"], validated_states):
            raise SetupError(f"{identifier}: stored dependencies or trigger conditions are not satisfied")
        if item.get("state") not in STATES:
            raise SetupError(f"{identifier}: invalid stored state")
        if item.get("supplied_by") not in {
            "inspection",
            "user",
            "agent",
            "tty",
            "cli",
            "review_artifact",
            "accepted_decision",
        }:
            raise SetupError(f"{identifier}: invalid stored answer source")
        validate_answer_type(question, item["state"], item.get("value"))
        validate_answer_evidence(question, item.get("evidence"), item["state"])
        validity = item.get("validity")
        if (
            not isinstance(validity, dict)
            or set(validity) != {"classes", "bindings", "reuse_status", "reason"}
            or not isinstance(validity.get("classes"), list)
            or not validity["classes"]
            or not set(validity["classes"]) <= VALIDITY_CLASSES
            or validity.get("reuse_status") not in {"current", "preserved", "reobserved"}
            or not isinstance(validity.get("bindings"), list)
            or not isinstance(validity.get("reason"), str)
        ):
            raise SetupError(f"{identifier}: validity binding is malformed")
        if item["state"] == "answered":
            validate_special_answer(identifier, item["value"], {row["question_id"]: row for row in value["question_states"]})
            if contains_secret(item["value"]):
                raise SetupError(f"{identifier}: stored answer appears to contain secret material")
            if (
                question["information_role"] == "accepted_authority_reference"
                and (
                    not isinstance(item["value"], str)
                    or not item["value"].startswith(AUTHORITY_PREFIXES)
                )
            ):
                raise SetupError(f"{identifier}: stored accepted authority reference is malformed")
        validated_states[identifier] = item
    expected = copy.deepcopy(value)
    expected["canonical_session_digest"] = ""
    expected = finalize_session(expected, catalog)
    for key in ("inventories", "selected_profile", "selected_layout", "user_selections", "accepted_authority_references", "unresolved_blockers", "next_eligible_questions", "work_completion_assessment", "minimum_closure_sequence", "session_status"):
        if expected[key] != value[key]:
            raise SetupError(f"setup session derived field is inconsistent: {key}")
    return value


def validate_predecessor_session_shape(value: Any) -> dict[str, Any]:
    required = {
        "schema_version", "artifact_kind", "artifact_version", "permission_grant", "session_id", "sequence", "created_at", "updated_at", "mode",
        "target_identity", "target_revision", "target_fingerprint", "governing_instruction_fingerprint", "octon_mini", "question_catalog", "selected_profile",
        "selected_layout", "validity_policy_version", "question_states", "reinspection", "inventories", "recommendations", "user_selections", "accepted_authority_references", "reused_decisions", "unresolved_blockers",
        "next_eligible_questions", "generated_plan_references", "work_completion_assessment", "minimum_closure_sequence", "session_status", "successor_of", "limitations", "canonical_session_digest",
    }
    if (
        not isinstance(value, dict)
        or set(value) != required
        or value.get("schema_version") != SESSION_SCHEMA
        or value.get("artifact_kind") != "setup_session"
        or value.get("artifact_version") != SESSION_VERSION
        or value.get("permission_grant") is not False
        or value.get("mode") not in MODES
        or re.fullmatch(r"SETUP-[a-f0-9]{24}", str(value.get("session_id", ""))) is None
        or record_digest(value, "canonical_session_digest")
        != value.get("canonical_session_digest")
        or not isinstance(value.get("question_states"), list)
    ):
        raise SetupError("predecessor setup session metadata or canonical digest is invalid")
    seen: set[str] = set()
    required_state_keys = {
        "question_id", "question_version", "state", "information_role",
        "value", "supplied_by", "evidence", "validity",
    }
    for item in value["question_states"]:
        identifier = item.get("question_id") if isinstance(item, dict) else None
        if (
            not isinstance(item, dict)
            or set(item) != required_state_keys
            or not isinstance(identifier, str)
            or re.fullmatch(r"setup\.[a-z0-9]+(?:[.-][a-z0-9]+)*", identifier) is None
            or identifier in seen
            or item.get("state") not in STATES
            or contains_secret(item.get("value"))
        ):
            raise SetupError("predecessor setup session contains malformed or unsafe question state")
        seen.add(identifier)
    return value


def current_state_mismatches(session: dict[str, Any]) -> list[str]:
    target = Path(session["target_identity"]["canonical_path"])
    mismatches: list[str] = []
    catalog = load_catalog()
    detected, mode_evidence, octon_mini = detect_mode(target)
    if detected != session["mode"]:
        mismatches.append("target mode")
    if fingerprint(target, instructions_only=True) != session["governing_instruction_fingerprint"]:
        mismatches.append("governing instruction fingerprint")
    for key in ("source_version", "candidate_version", "installed_version", "provenance_status", "installed_packages"):
        if octon_mini.get(key) != session["octon_mini"].get(key):
            mismatches.append(f"Octon {key}")
    current_observations = {
        item["question_id"]: item
        for item in initial_observations(catalog, target, detected, mode_evidence, octon_mini)
    }
    stored_states = session_question_state(session)
    for identifier, current in current_observations.items():
        stored = stored_states.get(identifier)
        if stored is None or stored.get("value") != current.get("value"):
            mismatches.append(f"observation {identifier}")
    current_states = dict(current_observations)
    current_reused, _, _ = reusable_decision_states(
        target, session["mode"], catalog, current_states
    )
    current_reused_by_id = {item["question_id"]: item for item in current_reused}
    questions = question_map(catalog)
    now = datetime.now(timezone.utc)
    for identifier, item in stored_states.items():
        if item.get("supplied_by") == "inspection":
            continue
        if item.get("supplied_by") == "accepted_decision":
            current = current_reused_by_id.get(identifier)
            if current is None or accepted_decision_identity(current) != accepted_decision_identity(item):
                mismatches.append(f"accepted decision {identifier}")
            continue
        question = questions[identifier]
        for stored_binding in item.get("validity", {}).get("bindings", []):
            kind = stored_binding.get("kind")
            expected = stored_binding.get("digest")
            if kind == "catalog_question":
                current = sha256(canonical_bytes(question))
                current_type = "metadata"
            elif kind == "question_dependencies":
                current = dependency_digest(question, stored_states)
                current_type = "metadata"
            elif kind == "governing_instructions":
                current = fingerprint(target, instructions_only=True)["digest"]
                current_type = "metadata"
            elif kind == "evidence_source":
                current_type, current = evidence_binding_state(
                    target, item["evidence"]
                )
            else:
                continue
            if expected != current or stored_binding.get("subject_type") != current_type:
                mismatches.append(f"{identifier} {kind}")
            expiry = stored_binding.get("expires_at")
            if expiry is not None and parse_time(expiry, f"{identifier} expires_at") <= now:
                mismatches.append(f"{identifier} expiry")
    return sorted(set(mismatches))


def convert_legacy_session(value: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    if (
        value.get("schema_version") != LEGACY_SESSION_SCHEMA
        or value.get("artifact_version") != "1.0.0"
        or value.get("permission_grant") is not False
        or record_digest(value, "canonical_session_digest") != value.get("canonical_session_digest")
    ):
        raise SetupError("legacy setup session is malformed or has an invalid digest")
    target = Path(value["target_identity"]["canonical_path"])
    questions = question_map(catalog)
    states: dict[str, dict[str, Any]] = {}
    converted_states: list[dict[str, Any]] = []
    for item in value.get("question_states", []):
        question = questions.get(item.get("question_id"))
        if question is None or question["version"] != item.get("question_version"):
            continue
        copied = dict(item)
        copied["validity"] = state_validity(
            catalog,
            question,
            states,
            target,
            copied["evidence"],
            reason="Legacy v1 state awaits explicit dependency-scoped reinspection.",
        )
        converted_states.append(copied)
        states[question["id"]] = copied
    converted = copy.deepcopy(value)
    legacy_digest = value["canonical_session_digest"]
    converted.update(
        {
            "schema_version": SESSION_SCHEMA,
            "artifact_version": SESSION_VERSION,
            "question_catalog": {
                "schema_version": catalog["schema_version"],
                "catalog_version": catalog["catalog_version"],
                "sha256": catalog_digest(catalog),
            },
            "validity_policy_version": catalog["validity_policy"]["schema_version"],
            "question_states": converted_states,
            "reinspection": {
                "preserved": [],
                "reobserved": [],
                "needs_confirmation": [],
                "invalidated": [],
                "newly_introduced": [],
            },
            "reused_decisions": [],
            "inventories": {**{state: [] for state in STATES}, "needs_confirmation": [], "invalidated": []},
        }
    )
    converted["limitations"] = sorted(
        set(converted.get("limitations", []))
        | {f"Converted legacy session {legacy_digest} in memory; write only an immutable v2 successor."}
    )
    converted["canonical_session_digest"] = ""
    return finalize_session(converted, catalog)


def load_session(path: Path, *, require_current: bool = True) -> dict[str, Any]:
    catalog = load_catalog()
    raw = load_json(path)
    if isinstance(raw, dict) and raw.get("schema_version") == LEGACY_SESSION_SCHEMA:
        value = convert_legacy_session(raw, catalog)
        if require_current:
            raise CONTINUATION.ContinuationError(
                CONTINUATION.finding(
                    failure_code="OCTON-SETUP-1004",
                    blocked_operation="setup.session",
                    phase="revalidate",
                    root_cause="A setup-session v1 artifact requires an explicit immutable v2 reinspection successor.",
                    authority_source="setup_session_and_current_question_catalog",
                    repair_class="replan_required",
                    next_action=CONTINUATION.action(
                        "Reinspect the legacy session and write a new external successor.",
                        ["./octon", {"initialization": "init", "adoption": "adopt", "upgrade": "upgrade"}[value["mode"]], "setup", "--target", value["target_identity"]["canonical_path"], "--session", str(path), "--reinspect", "--output", str(path.with_name(path.stem + "-v2-successor.json"))],
                        read_only=False,
                        requires_confirmation=True,
                    ),
                    invalidated=[CONTINUATION.proof_state("answer", "setup-session-v1", "The predecessor lacks dependency-scoped validity bindings.", ["dependency_bound"])],
                    preserved=[CONTINUATION.proof_state("plan", raw["canonical_session_digest"], "The immutable v1 artifact remains predecessor evidence.", ["source_fingerprint_bound"])],
                    successor_session=True,
                    successor_reason="A v2 successor can classify every prior state without rewriting the v1 artifact.",
                )
            )
    else:
        if (
            not require_current
            and isinstance(raw, dict)
            and raw.get("question_catalog")
            != {
                "schema_version": catalog["schema_version"],
                "catalog_version": catalog["catalog_version"],
                "sha256": catalog_digest(catalog),
            }
        ):
            value = validate_predecessor_session_shape(raw)
        else:
            value = validate_session_shape(raw, catalog)
    if require_current:
        mismatches = current_state_mismatches(value)
        if mismatches:
            raise CONTINUATION.ContinuationError(
                CONTINUATION.finding(
                    failure_code="OCTON-SETUP-1002",
                    blocked_operation="setup.session",
                    phase="revalidate",
                    root_cause="Setup-session dependencies are stale: " + ", ".join(mismatches),
                    authority_source="setup_session_current_dependencies_and_project_authority",
                    repair_class="replan_required",
                    next_action=CONTINUATION.action(
                        "Create an immutable reinspection successor and review only its invalidated inputs.",
                        ["./octon", {"initialization": "init", "adoption": "adopt", "upgrade": "upgrade"}[value["mode"]], "setup", "--target", value["target_identity"]["canonical_path"], "--session", str(path), "--reinspect", "--output", str(path.with_name(path.stem + "-successor.json"))],
                        read_only=False,
                        requires_confirmation=True,
                    ),
                    invalidated=[CONTINUATION.proof_state("answer", item, "The declared current binding no longer matches.", ["dependency_bound"]) for item in mismatches],
                    preserved=[CONTINUATION.proof_state("plan", value["canonical_session_digest"], "The immutable predecessor remains comparison evidence.", ["source_fingerprint_bound"])],
                    successor_session=True,
                    successor_reason="Reinspection can preserve every state whose exact declared bindings still match.",
                )
            )
    return value


def reinspect_session(
    session: dict[str, Any],
    *,
    catalog_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog = (
        validate_catalog(copy.deepcopy(catalog_override))
        if catalog_override is not None
        else load_catalog()
    )
    fresh = create_session(
        session["mode"],
        Path(session["target_identity"]["canonical_path"]),
        catalog_override=catalog,
    )
    questions = question_map(catalog)
    current_states = session_question_state(fresh)
    prior_states = session_question_state(session)
    classifications = {
        "preserved": list(fresh["reinspection"]["preserved"]),
        "reobserved": list(fresh["reinspection"]["reobserved"]),
        "needs_confirmation": [],
        "invalidated": list(fresh["reinspection"]["invalidated"]),
        "newly_introduced": [],
    }
    appended: list[dict[str, Any]] = []
    current_instruction = fingerprint(
        Path(fresh["target_identity"]["canonical_path"]), instructions_only=True
    )["digest"]
    target = Path(fresh["target_identity"]["canonical_path"])
    for item in session["question_states"]:
        question = questions.get(item["question_id"])
        identifier = item["question_id"]
        if item["supplied_by"] == "inspection":
            continue
        if item["supplied_by"] == "accepted_decision":
            if (
                identifier in current_states
                and current_states[identifier].get("supplied_by") == "accepted_decision"
                and accepted_decision_identity(current_states[identifier])
                == accepted_decision_identity(item)
            ):
                continue
            classifications["invalidated"].append(
                {"question_id": identifier, "reason": "Accepted decision is expired, revoked, superseded, inapplicable, or no longer exact."}
            )
            continue
        if question is None or question["version"] != item["question_version"]:
            classifications["invalidated"].append(
                {"question_id": identifier, "reason": "Question definition changed or was removed."}
            )
            continue
        if "runtime_only_never_reusable" in item.get("validity", {}).get("classes", []):
            classifications["invalidated"].append(
                {"question_id": identifier, "reason": "Runtime-only values are never reusable."}
            )
            continue
        if not question_eligible(question, fresh["mode"], current_states):
            classifications["invalidated"].append(
                {"question_id": identifier, "reason": "Current dependencies or trigger conditions are not eligible."}
            )
            continue
        changed_bindings: list[str] = []
        expired = False
        for stored_binding in item.get("validity", {}).get("bindings", []):
            kind = stored_binding.get("kind")
            if kind == "catalog_question":
                current = sha256(canonical_bytes(question))
                current_type = "metadata"
            elif kind == "question_dependencies":
                current = dependency_digest(question, current_states)
                current_type = "metadata"
            elif kind == "governing_instructions":
                current = current_instruction
                current_type = "metadata"
            elif kind == "evidence_source":
                current_type, current = evidence_binding_state(
                    target, item["evidence"]
                )
            else:
                current = stored_binding.get("digest")
                current_type = stored_binding.get("subject_type")
            if (
                current != stored_binding.get("digest")
                or current_type != stored_binding.get("subject_type")
            ):
                changed_bindings.append(str(kind))
            expiry = stored_binding.get("expires_at")
            if expiry is not None and parse_time(expiry, f"{identifier} expires_at") <= datetime.now(timezone.utc):
                expired = True
        if expired:
            classifications["invalidated"].append(
                {"question_id": identifier, "reason": "Evidence or policy freshness expired."}
            )
            continue
        if changed_bindings:
            bucket = (
                "needs_confirmation"
                if item["information_role"] in {"initialization_input", "owner_selection", "accepted_authority_reference"}
                else "invalidated"
            )
            classifications[bucket].append(
                {"question_id": identifier, "reason": "Relevant bindings changed: " + ", ".join(sorted(set(changed_bindings)))}
            )
            continue
        copied = copy.deepcopy(item)
        copied["validity"] = state_validity(
            catalog,
            question,
            current_states,
            target,
            copied["evidence"],
            reuse_status="preserved",
            reason="All exact declared dependencies remain current.",
        )
        appended.append(copied)
        current_states[identifier] = copied
        classifications["preserved"].append(
            {"question_id": identifier, "reason": "All exact declared dependencies remain current."}
        )
    prior_ids = set(prior_states)
    current_ids = set(current_states)
    for question in catalog["questions"]:
        identifier = question["id"]
        if identifier not in prior_ids and identifier not in current_ids and question_applicable(question, fresh["mode"], current_states):
            classifications["newly_introduced"].append(
                {"question_id": identifier, "reason": "The current catalog introduced an unresolved applicable question."}
            )
    fresh["question_states"].extend(appended)
    fresh["reinspection"] = classifications
    fresh["sequence"] = session["sequence"] + 1
    fresh["session_id"] = "SETUP-" + secrets.token_hex(12)
    fresh["updated_at"] = utc_timestamp()
    fresh["successor_of"] = {
        "session_id": session["session_id"],
        "canonical_session_digest": session["canonical_session_digest"],
        "reason": "dependency-scoped reinspection preserving only exact current validity bindings",
    }
    fresh["limitations"].append(
        "Reinspection preserved exact current bindings, reobserved volatile facts, and returned changed selections for confirmation without rewriting the predecessor."
    )
    return finalize_session(fresh, catalog)


def write_new_json(path: Path, value: object) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise SetupError(f"refusing to overwrite existing setup artifact: {path}")
    temporary = path.with_name(f".{path.name}.tmp-{secrets.token_hex(8)}")
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def ensure_output_outside_target(output: Path, target: Path) -> None:
    candidate = output.expanduser().resolve()
    target = target.expanduser().resolve()
    try:
        candidate.relative_to(target)
    except ValueError:
        return
    raise SetupError("setup-session output must be outside the target so setup inspection remains read-only")


def question_batch(session: dict[str, Any], catalog: dict[str, Any], limit: int) -> dict[str, Any]:
    questions = question_map(catalog)
    selected = session["next_eligible_questions"][:limit]
    return {
        "schema_version": "octon-mini.bootstrap.setup-question-batch.v2",
        "permission_grant": False,
        "session_id": session["session_id"],
        "session_digest": session["canonical_session_digest"],
        "mode": session["mode"],
        "status": session["session_status"],
        "questions": [questions[identifier] for identifier in selected],
        "reinspection": session["reinspection"],
        "reused_decisions": session["reused_decisions"],
        "unresolved_blockers": session["unresolved_blockers"],
        "work_completion_assessment": session["work_completion_assessment"],
        "minimum_closure_sequence": session["minimum_closure_sequence"],
        "limitations": ["Ask normally one to three questions; no answer is preselected."],
    }


def render_question_batch(value: dict[str, Any]) -> str:
    lines = [
        f"Setup: {value['mode']} — {value['status']}",
        f"Session digest: {value['session_digest']}",
    ]
    reinspection = value.get("reinspection", {})
    if any(reinspection.get(key) for key in reinspection):
        lines.append(
            "Reinspection: "
            + ", ".join(
                f"{key.replace('_', ' ')}={len(reinspection.get(key, []))}"
                for key in ("preserved", "reobserved", "needs_confirmation", "invalidated", "newly_introduced")
            )
        )
    if value.get("reused_decisions"):
        lines.append(
            "Reused accepted decisions: "
            + ", ".join(item["decision_ref"] for item in value["reused_decisions"])
        )
    questions = value.get("questions", [])
    if questions:
        lines.append("Next unresolved questions:")
        for question in questions:
            lines.append(f"  - {question['id']}: {question['prompt']}")
    else:
        lines.append("No currently eligible unanswered question remains.")
    blockers = value.get("unresolved_blockers", [])
    if blockers:
        lines.append("Blocking inputs: " + ", ".join(item["question_id"] for item in blockers))
    return "\n".join(lines)


def tty_value(question: dict[str, Any]) -> tuple[str, Any]:
    print(f"\n{question['prompt']}")
    print(f"Why it matters: {question['importance']}")
    print(f"Recommendation rule: {question['recommendation']['rule']} — {question['recommendation']['rationale']}")
    answer = question["answer"]
    if answer["valid_values"]:
        print("Choices: " + ", ".join(str(item) for item in answer["valid_values"]))
    states = []
    if answer["allow_unknown"]:
        states.append("unknown")
    if answer["allow_deferred"]:
        states.append("defer")
    if answer["allow_not_applicable"]:
        states.append("n/a")
    if states:
        print("Also allowed: " + ", ".join(states))
        print(f"If unresolved: {question['change_consequences']}")
    raw = input("Answer (no default): ").strip()
    if raw == "unknown":
        return "unknown", None
    if raw == "defer":
        return "deferred", None
    if raw == "n/a":
        return "not_applicable", None
    expected = answer["type"]
    if expected in {"object", "object_list", "string_list"}:
        try:
            return "answered", json.loads(raw)
        except json.JSONDecodeError as error:
            raise SetupError(f"{question['id']}: expected JSON input: {error}") from error
    if expected == "integer":
        try:
            return "answered", int(raw)
        except ValueError as error:
            raise SetupError(f"{question['id']}: expected an integer") from error
    if expected == "boolean":
        if raw.casefold() not in {"yes", "no", "true", "false"}:
            raise SetupError(f"{question['id']}: expected yes or no")
        return "answered", raw.casefold() in {"yes", "true"}
    return "answered", raw


def tty_answer_batch(
    session: dict[str, Any],
    catalog: dict[str, Any],
    limit: int,
    *,
    require_tty: bool = True,
) -> dict[str, Any]:
    if require_tty and not sys.stdin.isatty():
        raise SetupError("TTY setup requires a terminal; conversational agents should use an answer batch")
    questions = question_map(catalog)
    answers = []
    observed = datetime.now(timezone.utc)
    now = observed.isoformat().replace("+00:00", "Z")
    for identifier in session["next_eligible_questions"][:limit]:
        question = questions[identifier]
        state, value = tty_value(question)
        freshness_days = question["evidence"]["freshness_days"]
        expires_at = (
            (observed + timedelta(days=freshness_days))
            .isoformat()
            .replace("+00:00", "Z")
            if state == "answered" and freshness_days is not None
            else None
        )
        answers.append(
            {
                "question_id": identifier,
                "state": state,
                "value": value,
                "supplied_by": "tty",
                "evidence": {
                    "source": "user:tty-interview",
                    "observed_at": now,
                    "expires_at": expires_at,
                    "confidence": "low",
                    "limitations": ["User-supplied TTY answer observed now; underlying project evidence was not independently verified by setup."],
                },
            }
        )
    return {
        "schema_version": ANSWER_SCHEMA,
        "permission_grant": False,
        "session_digest": session["canonical_session_digest"],
        "answers": answers,
        "limitations": ["TTY collection used the canonical question catalog and grants no permission."],
    }


FLAG_QUESTION_MAP: dict[str, dict[str, str]] = {
    "initialization": {
        "target": "setup.target-identity", "project_name": "setup.project-name", "project_slug": "setup.project-slug", "profile": "setup.assurance-profile", "layout": "setup.layout",
        "writer_count": "setup.write-capable-humans", "collaboration_source": "setup.write-capable-humans", "collaboration_observed_at": "setup.write-capable-humans",
        "collaboration_expires_at": "setup.write-capable-humans", "collaboration_limitation": "setup.write-capable-humans", "solo_integration_preference": "setup.solo-integration-preference",
        "independent_review_capacity": "setup.independent-review-capacity", "concurrent_humans": "setup.collaboration-concurrency", "concurrent_agents": "setup.collaboration-concurrency",
        "external_contribution_mode": "setup.external-contribution-mode", "first_task_title": "setup.first-task", "first_task_scope": "setup.first-task",
        "first_task_authority_basis": "setup.first-task", "first_task_owner": "setup.first-task", "first_task_operator": "setup.first-task",
        "first_task_acceptance": "setup.first-task", "first_task_validation": "setup.first-task", "first_task_next_action": "setup.first-task",
    },
    "adoption": {
        "target": "setup.target-identity", "project_name": "setup.project-name", "project_slug": "setup.project-slug", "profile": "setup.assurance-profile", "layout": "setup.layout",
        "authority_source": "setup.adoption-authority", "proposal": "setup.adoption-review", "review": "setup.adoption-review", "max_files": "setup.adoption-review",
        "max_file_bytes": "setup.adoption-review", "max_total_bytes": "setup.adoption-review", "include_sensitive_path": "setup.preserved-project-paths",
    },
    "upgrade": {
        "target": "setup.target-identity", "authority_source": "setup.upgrade-authority", "evidence_ref": "setup.upgrade-evidence", "legacy_seed": "setup.upgrade-review",
        "proposal": "setup.upgrade-review", "review": "setup.upgrade-review",
    },
}


def mapped_flag_ids(mode: str) -> dict[str, str]:
    return dict(FLAG_QUESTION_MAP[mode])


def answer_value(session: dict[str, Any], identifier: str) -> Any:
    item = session_question_state(session).get(identifier)
    return item["value"] if item and item["state"] == "answered" else None


def set_or_compare(args: argparse.Namespace, attribute: str, value: Any, identifier: str) -> None:
    if value is None:
        return
    current = getattr(args, attribute, None)
    if current not in (None, [], "") and current != value:
        raise SetupError(f"CLI input {attribute} conflicts with setup answer {identifier}")
    setattr(args, attribute, value)


def apply_session_to_args(mode: str, args: argparse.Namespace, session: dict[str, Any]) -> None:
    if session["mode"] != mode:
        raise SetupError(f"setup session mode {session['mode']} cannot drive {mode}")
    if session["session_status"] != "ready_for_plan":
        names = ", ".join(item["question_id"] for item in session["unresolved_blockers"])
        raise SetupError("setup session is not ready for planning; unresolved: " + names)
    set_or_compare(args, "project_name", answer_value(session, "setup.project-name"), "setup.project-name")
    set_or_compare(args, "project_slug", answer_value(session, "setup.project-slug"), "setup.project-slug")
    set_or_compare(args, "profile", answer_value(session, "setup.assurance-profile"), "setup.assurance-profile")
    set_or_compare(args, "layout", answer_value(session, "setup.layout"), "setup.layout")
    if mode == "initialization":
        writer = session_question_state(session).get("setup.write-capable-humans")
        if writer and writer["state"] == "answered":
            set_or_compare(args, "writer_count", writer["value"], writer["question_id"])
            set_or_compare(args, "collaboration_source", writer["evidence"]["source"], writer["question_id"])
            set_or_compare(args, "collaboration_observed_at", writer["evidence"]["observed_at"], writer["question_id"])
            set_or_compare(args, "collaboration_expires_at", writer["evidence"]["expires_at"], writer["question_id"])
            if not getattr(args, "collaboration_limitation", []):
                args.collaboration_limitation = writer["evidence"]["limitations"]
        for attribute, identifier in (
            ("solo_integration_preference", "setup.solo-integration-preference"),
            ("independent_review_capacity", "setup.independent-review-capacity"),
            ("external_contribution_mode", "setup.external-contribution-mode"),
        ):
            set_or_compare(args, attribute, answer_value(session, identifier), identifier)
        concurrency = answer_value(session, "setup.collaboration-concurrency")
        if concurrency:
            set_or_compare(args, "concurrent_humans", concurrency["human_writers"], "setup.collaboration-concurrency")
            set_or_compare(args, "concurrent_agents", concurrency["agents_or_automation"], "setup.collaboration-concurrency")
        first = answer_value(session, "setup.first-task")
        if first:
            for attribute, key in (
                ("first_task_title", "title"), ("first_task_scope", "scope"), ("first_task_authority_basis", "authority_basis"), ("first_task_owner", "owner"),
                ("first_task_operator", "operator"), ("first_task_acceptance", "acceptance"), ("first_task_validation", "validation"), ("first_task_next_action", "next_action"),
            ):
                set_or_compare(args, attribute, first[key], "setup.first-task")
    elif mode == "adoption":
        set_or_compare(args, "authority_source", answer_value(session, "setup.adoption-authority"), "setup.adoption-authority")
        review = answer_value(session, "setup.adoption-review")
        if review:
            if "proposal" in review:
                set_or_compare(args, "proposal", Path(review["proposal"]), "setup.adoption-review")
            if "review" in review:
                set_or_compare(args, "review", Path(review["review"]), "setup.adoption-review")
    else:
        set_or_compare(args, "authority_source", answer_value(session, "setup.upgrade-authority"), "setup.upgrade-authority")
        set_or_compare(args, "evidence_ref", answer_value(session, "setup.upgrade-evidence"), "setup.upgrade-evidence")
        review = answer_value(session, "setup.upgrade-review")
        if review:
            for attribute in ("legacy_seed", "proposal", "review"):
                if attribute in review and review[attribute] is not None:
                    set_or_compare(args, attribute, Path(review[attribute]), "setup.upgrade-review")


def prepare_plan_session(mode: str, args: argparse.Namespace) -> tuple[dict[str, Any], Path] | None:
    path = getattr(args, "setup_session", None)
    if path is None:
        return None
    session_path = path.expanduser().resolve()
    session = load_session(session_path, require_current=True)
    target = args.target.expanduser().resolve()
    ensure_output_outside_target(session_path, target)
    if session["target_identity"]["canonical_path"] != str(target):
        raise SetupError("setup session target differs from the planning target")
    apply_session_to_args(mode, args, session)
    return session, session_path


def transaction_evidence(binding: tuple[dict[str, Any], Path] | None, transaction: Any) -> list[dict[str, Any]]:
    if binding is None:
        return []
    session, path = binding
    result = [
        transaction.source_evidence(
            SETUP_EVIDENCE_KIND,
            f"setup-session:{session['canonical_session_digest']}:{path}",
            content=path.read_bytes(),
            limitations=[
                "The setup session is non-authorizing and records selections separately from accepted authority.",
                "The session does not establish implementation or readiness evidence.",
            ],
        )
    ]
    for item in session.get("reused_decisions", []):
        result.append(
            transaction.source_evidence(
                "accepted_decision_reuse",
                f"{item['decision_ref']}:{item['reuse_policy_id']}",
                limitations=list(item.get("limitations", []))
                + [
                    "Reused only within the setup session's exact decision, applicability, instruction, dependency, and freshness bindings.",
                    "The decision does not supply operation confirmation or runtime authorization.",
                ],
            )
        )
    return result


def verify_plan_binding(target: Path, plan: dict[str, Any]) -> None:
    matches = [item for item in plan.get("source_evidence", []) if item.get("kind") == SETUP_EVIDENCE_KIND]
    if not matches:
        return
    if len(matches) != 1:
        raise SetupError("transaction plan must bind exactly one setup session")
    evidence = matches[0]
    reference = evidence.get("reference", "")
    if not isinstance(reference, str) or not reference.startswith("setup-session:"):
        raise SetupError("setup-session evidence reference is malformed")
    try:
        _, digest, raw_path = reference.split(":", 2)
    except ValueError as error:
        raise SetupError("setup-session evidence reference is malformed") from error
    path = Path(raw_path)
    if path.is_symlink() or not path.is_file():
        raise SetupError("bound setup session is unavailable or unsafe")
    content = path.read_bytes()
    if sha256(content) != evidence.get("sha256"):
        raise SetupError("bound setup-session bytes changed after planning")
    session = load_session(path, require_current=True)
    if session["canonical_session_digest"] != digest:
        raise SetupError("bound setup-session digest differs from the reviewed plan")
    if session["target_identity"]["canonical_path"] != str(target.expanduser().resolve()):
        raise SetupError("bound setup-session target differs from apply target")
    expected_operation = {"initialization": "init.project", "adoption": "adopt.install", "upgrade": "upgrade.project"}[session["mode"]]
    if plan.get("operation") != expected_operation:
        raise SetupError("bound setup-session mode differs from transaction operation")


def record_plan_reference(
    session: dict[str, Any],
    plan_path: Path,
    target: Path,
    catalog: dict[str, Any],
) -> dict[str, Any]:
    plan_path = plan_path.expanduser().resolve()
    if plan_path.is_symlink() or not plan_path.is_file():
        raise SetupError("generated plan reference must be an existing regular file")
    plan = load_json(plan_path)
    if (
        not isinstance(plan, dict)
        or plan.get("artifact_kind") != "transaction_plan"
        or plan.get("permission_grant") is not False
        or plan.get("canonical_plan_digest") != record_digest(plan, "canonical_plan_digest")
    ):
        raise SetupError("generated plan reference is malformed, authorizing, or has an invalid digest")
    verify_plan_binding(target, plan)
    expected = {
        "initialization": "init.project",
        "adoption": "adopt.install",
        "upgrade": "upgrade.project",
    }[session["mode"]]
    if plan.get("operation") != expected:
        raise SetupError("generated plan operation differs from the setup session mode")
    reference = {
        "operation": expected,
        "canonical_plan_digest": plan["canonical_plan_digest"],
        "path": str(plan_path),
        "created_at": plan["created_at"],
    }
    if reference in session["generated_plan_references"]:
        raise SetupError("generated plan reference is already recorded")
    successor = copy.deepcopy(session)
    successor["sequence"] += 1
    successor["updated_at"] = utc_timestamp()
    successor["successor_of"] = {
        "session_id": session["session_id"],
        "canonical_session_digest": session["canonical_session_digest"],
        "reason": "record exact generated transaction plan reference",
    }
    successor["session_id"] = "SETUP-" + secrets.token_hex(12)
    successor["generated_plan_references"].append(reference)
    return finalize_session(successor, catalog)


def add_setup_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser], mode: str) -> None:
    setup = commands.add_parser(
        "setup",
        help="run Octon Guided Setup for this bootstrap workflow",
        description=(
            "Inspect the target read-only, ask unresolved questions, and optionally write "
            "one explicit external non-authorizing setup session"
        ),
    )
    setup.add_argument("--target", type=Path, required=True)
    setup.add_argument("--session", type=Path)
    setup.add_argument("--answers", type=Path)
    setup.add_argument("--record-plan", type=Path)
    setup.add_argument("--output", type=Path)
    setup.add_argument("--reinspect", action="store_true")
    setup.add_argument("--tty", action="store_true")
    setup.add_argument("--batch-size", type=int, choices=(1, 2, 3), default=3)
    setup.add_argument("--json", action="store_true")
    setup.set_defaults(setup_mode=mode)


def run_setup(args: argparse.Namespace) -> int:
    mode = args.setup_mode
    catalog = load_catalog()
    target = args.target.expanduser().resolve()
    if args.answers and args.tty:
        raise SetupError("use either --answers or --tty, not both")
    if args.record_plan and (not args.session or not args.output):
        raise SetupError("--record-plan requires an existing --session and a new --output successor")
    if args.record_plan and (args.answers or args.tty or args.reinspect):
        raise SetupError("record a plan in its own immutable successor operation")
    if args.reinspect and not args.session:
        raise SetupError("--reinspect requires --session")
    if args.session:
        ensure_output_outside_target(args.session, target)
        stored = load_session(args.session, require_current=not args.reinspect)
        if stored["target_identity"]["canonical_path"] != str(target):
            raise SetupError("stored setup session target differs from --target")
        session = reinspect_session(stored) if args.reinspect else stored
    else:
        session = create_session(mode, target)
    if session["mode"] != mode:
        raise SetupError(f"session mode {session['mode']} differs from requested {mode}")
    if args.answers:
        session = apply_answer_batch(session, load_json(args.answers), catalog)
    elif args.tty:
        session = apply_answer_batch(session, tty_answer_batch(session, catalog, args.batch_size), catalog)
    elif args.record_plan:
        session = record_plan_reference(session, args.record_plan, target, catalog)
    if args.output:
        ensure_output_outside_target(args.output, target)
        if args.session and args.output.expanduser().resolve() == args.session.expanduser().resolve():
            raise SetupError("resumed sessions are immutable; write a successor path")
        write_new_json(args.output, session)
        if not args.json:
            print(f"[SESSION] {args.output.expanduser().resolve()}")
    batch = question_batch(session, catalog, args.batch_size)
    print(
        json.dumps(batch, indent=2, sort_keys=True, allow_nan=False)
        if args.json
        else render_question_batch(batch)
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Shared Octon guided setup session engine")
    parser.add_argument("mode", choices=MODES)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--session", type=Path)
    parser.add_argument("--answers", type=Path)
    parser.add_argument("--record-plan", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reinspect", action="store_true")
    parser.add_argument("--tty", action="store_true")
    parser.add_argument("--batch-size", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    args.setup_mode = args.mode
    try:
        return run_setup(args)
    except (OSError, RuntimeError, SetupError, ValueError) as error:
        report = getattr(error, "report", None)
        if not isinstance(report, dict):
            report = CONTINUATION.fallback(
                error,
                blocked_operation="setup.session",
                phase="questions",
                next_argv=["./octon", {"initialization": "init", "adoption": "adopt", "upgrade": "upgrade"}[args.mode], "setup", "--help"],
            )
        print(CONTINUATION.render_finding(report, json_output=args.json), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
