#!/usr/bin/env python3
"""Produce content-free, non-enforcing large-project phase measurements."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any


sys.dont_write_bytecode = True
SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
SOURCE_ROOT = next(
    candidate
    for candidate in (
        Path(__file__).resolve().parents[3],
        SKILL_ROOT / "assets/octon-source",
    )
    if (candidate / "shared/source-contracts").is_dir()
)
SCAFFOLD = SCRIPT_ROOT / "scaffold_project.py"
SCHEMA_VERSION = "octon-mini.source.large-project-phase-profile.v1"
DOCUMENT_ROLE = "local_content_free_non_authorizing_informational_phase_measurement"
DEFAULT_SIZES = (0, 2_000, 10_000, 20_000)
PHASE_IDS = (
    "validator.tree_traversal",
    "validator.hash_inventory",
    "validator.schema_semantic_validation",
    "validator.text_json_scan",
    "validator.integrity_validation",
    "transaction.staging_copy",
    "transaction.tree_state",
    "transaction.staged_refresh_validation",
    "transaction.live_apply",
    "transaction.post_apply_validation",
    "transaction.receipt_creation",
    "transaction.total_apply",
)


def child_environment() -> dict[str, str]:
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            env=child_environment(),
        )
    except OSError:
        return subprocess.CompletedProcess(argv, 126, stdout="", stderr="")


def elapsed(action: Callable[[], Any]) -> tuple[Any, float]:
    started = time.perf_counter()
    result = action()
    return result, time.perf_counter() - started


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("phase target module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_git_state() -> tuple[str | None, bool | None]:
    if not (SOURCE_ROOT / ".git").exists():
        return None, None
    revision = run(["git", "rev-parse", "HEAD"], SOURCE_ROOT)
    status = run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        SOURCE_ROOT,
    )
    return (
        revision.stdout.strip() if revision.returncode == 0 else None,
        bool(status.stdout) if status.returncode == 0 else None,
    )


def host_context() -> dict[str, object]:
    return {
        "operating_system": platform.system() or "unknown",
        "operating_system_release": platform.release() or "unknown",
        "architecture": platform.machine() or "unknown",
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "logical_cpu_count": os.cpu_count(),
        "filesystem_encoding": sys.getfilesystemencoding(),
    }


def empty_phase(*limitations: str) -> dict[str, object]:
    return {
        "status": "not_run",
        "seconds": None,
        "invocations": None,
        "observed_file_count": None,
        "overlaps_other_phases": False,
        "limitations": list(limitations),
    }


def measured_phase(
    seconds: float,
    *,
    invocations: int = 1,
    observed_file_count: int | None = None,
    overlaps: bool = False,
    limitations: list[str] | None = None,
) -> dict[str, object]:
    return {
        "status": "measured",
        "seconds": seconds,
        "invocations": invocations,
        "observed_file_count": observed_file_count,
        "overlaps_other_phases": overlaps,
        "limitations": limitations or [],
    }


def failed_phase(seconds: float | None = None, *limitations: str) -> dict[str, object]:
    return {
        "status": "failed",
        "seconds": seconds,
        "invocations": 1 if seconds is not None else None,
        "observed_file_count": None,
        "overlaps_other_phases": False,
        "limitations": list(limitations),
    }


def initial_report(sizes: tuple[int, ...]) -> dict[str, object]:
    revision, dirty = source_git_state()
    version = (SOURCE_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    return {
        "schema_version": SCHEMA_VERSION,
        "document_role": DOCUMENT_ROLE,
        "permission_grant": False,
        "octon_mini_version": version,
        "source_revision": revision,
        "source_dirty": dirty,
        "configuration": {
            "synthetic_payload_file_counts": list(sizes),
            "profile": "minimal",
            "layout": "compact",
            "samples_per_size": 1,
            "phase_ids": list(PHASE_IDS),
            "threshold_policy": "informational_only_no_thresholds",
            "child_python_bytecode_disabled": True,
        },
        "host_context": host_context(),
        "measurements": [],
        "execution_failures": [],
        "enforcement": "informational_only_no_thresholds_or_release_claim",
        "limitations": [
            "Each phase is a single host-specific diagnostic observation, not benchmark-v2 evidence or a percentile.",
            "Inclusive phases overlap where marked and must not be added together.",
            "Synthetic small files do not represent every real repository or filesystem shape.",
            "No path, project content, subprocess output, exception text, identity, or credential is retained.",
            "A measured phase grants no authority and establishes no project or release readiness claim.",
        ],
    }


def write_payload(root: Path, target: int) -> None:
    payload = root / "benchmark-payload"
    payload.mkdir(exist_ok=True)
    for index in range(target):
        bucket = payload / f"b{index // 1000:03d}"
        bucket.mkdir(exist_ok=True)
        (bucket / f"f{index:05d}.txt").write_text(
            f"bounded phase-profile payload {index}\n",
            encoding="utf-8",
        )


def record_failure(
    report: dict[str, object],
    size: int,
    phase: str,
    exit_code: int | None,
) -> None:
    failures = report["execution_failures"]
    assert isinstance(failures, list)
    failures.append(
        {
            "synthetic_payload_files": size,
            "phase": phase,
            "exit_code": exit_code,
        }
    )


def profile_validator(target: Path) -> tuple[dict[str, dict[str, object]], str | None]:
    phases = {phase: empty_phase("Phase was not reached.") for phase in PHASE_IDS}
    try:
        validator = load_module(
            target / ".agent/scripts/validate.py",
            f"octon_mini_phase_validator_{time.time_ns()}",
        )

        files, seconds = elapsed(
            lambda: validator.repository_files(target, source_only=True)
        )
        phases["validator.tree_traversal"] = measured_phase(
            seconds,
            observed_file_count=len(files),
            limitations=["Traversal excludes configured source-only paths before descent."],
        )

        inventory, seconds = elapsed(lambda: validator.source_inventory(target))
        file_map, _fingerprint = inventory
        phases["validator.hash_inventory"] = measured_phase(
            seconds,
            observed_file_count=len(file_map),
            limitations=["Includes deterministic traversal and byte hashing."],
        )

        errors, seconds = elapsed(
            lambda: validator.check_sources(target, scan_repository_files=False)
        )
        phases["validator.schema_semantic_validation"] = (
            measured_phase(
                seconds,
                limitations=[
                    "Excludes the repository text/JSON scan but may perform bounded integrity-dependent semantic work."
                ],
            )
            if not errors
            else failed_phase(seconds, "Generated source checks returned findings.")
        )
        if errors:
            return phases, "validator.schema_semantic_validation"

        errors, seconds = elapsed(
            lambda: validator.check_files_and_json(target, include_derived=True)
        )
        phases["validator.text_json_scan"] = (
            measured_phase(
                seconds,
                overlaps=True,
                limitations=["Includes its own full repository enumeration and text reads."],
            )
            if not errors
            else failed_phase(seconds, "Generated text/JSON scan returned findings.")
        )
        if errors:
            return phases, "validator.text_json_scan"

        errors, seconds = elapsed(
            lambda: validator.check_integrity(target, include_generated=True)
        )
        phases["validator.integrity_validation"] = (
            measured_phase(
                seconds,
                overlaps=True,
                limitations=["Includes source inventory and generated-integrity comparisons."],
            )
            if not errors
            else failed_phase(seconds, "Generated integrity validation returned findings.")
        )
        return phases, None
    except Exception:
        return phases, "validator.phase_setup"


def octon_command(root: Path, *arguments: str) -> list[str]:
    command = [str(root / "octon")]
    if os.name == "nt":
        command = [sys.executable, "-B", *command]
    return [*command, *arguments]


def native_transaction_phase_records(
    receipt: object,
    process_timings: object,
    *,
    tree_seconds: float,
    tree_invocations: int,
) -> tuple[dict[str, dict[str, object]], str | None]:
    records: dict[str, dict[str, object]] = {}
    native_failure = False
    tree_failure = False
    invalid_phases: set[str] = set()

    def fail_native(phase: str, limitation: str) -> None:
        nonlocal native_failure
        records[phase] = failed_phase(None, limitation)
        invalid_phases.add(phase)
        native_failure = True

    if (
        not isinstance(receipt, dict)
        or receipt.get("schema_version") != "harness.transaction-receipt.v3"
        or not isinstance(receipt.get("timings"), dict)
        or not isinstance(process_timings, dict)
    ):
        for phase in PHASE_IDS:
            if phase.startswith("transaction."):
                fail_native(
                    phase,
                    "Transaction-v3 native timing sources were unavailable or invalid.",
                )
        return records, "transaction.native_timings"

    receipt_timings = receipt["timings"]

    def number(value: object) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        result = float(value)
        return result if result >= 0 and math.isfinite(result) else None

    required_embedded = {
        "staging_seconds": "transaction.staging_copy",
        "refresh_seconds": "transaction.staged_refresh_validation",
        "staged_validation_seconds": "transaction.staged_refresh_validation",
        "apply_seconds": "transaction.live_apply",
        "post_apply_validation_seconds": "transaction.post_apply_validation",
        "receipt_preparation_seconds": "transaction.receipt_creation",
        "total_before_receipt_persist_seconds": "transaction.total_apply",
    }
    shared: dict[str, float] = {}
    for key, phase in required_embedded.items():
        receipt_value = number(receipt_timings.get(key))
        process_value = number(process_timings.get(key))
        if receipt_value is None or process_value is None or receipt_value != process_value:
            fail_native(
                phase,
                f"Transaction-v3 native timing {key} was unavailable, invalid, or inconsistent.",
            )
        else:
            shared[key] = process_value

    native_map = {
        "transaction.staging_copy": (
            "staging_seconds",
            [
                "Native receipt-v3 staging time measures the complete portable copy; staged static writes occur afterward, and no hardlink, reflink, or partial staging is used."
            ],
        ),
        "transaction.staged_refresh_validation": (
            "staged_validation_seconds",
            [
                "Native receipt-v3 staged validation includes refresh and before/after tree-state observations; refresh_seconds remains in the receipt but is not projected as a separate phase."
            ],
        ),
        "transaction.live_apply": (
            "apply_seconds",
            [
                "Native receipt-v3 apply time begins after pending-journal creation and covers live static and declared derived writes plus exact postimage checks before post-apply validation."
            ],
        ),
        "transaction.post_apply_validation": (
            "post_apply_validation_seconds",
            [
                "Native receipt-v3 post-apply validation includes its second isolated full clone, command execution, and before/after tree-state observations."
            ],
        ),
    }
    for phase, (key, limitations) in native_map.items():
        value = shared.get(key)
        if value is not None and phase not in invalid_phases:
            records[phase] = measured_phase(
                value,
                overlaps=True,
                limitations=limitations,
            )

    if tree_invocations < 1 or tree_seconds < 0 or not math.isfinite(tree_seconds):
        records["transaction.tree_state"] = failed_phase(
            None,
            "Invocation-local transaction tree-state timing was unavailable or invalid.",
        )
        tree_failure = True
    else:
        records["transaction.tree_state"] = measured_phase(
            tree_seconds,
            invocations=tree_invocations,
            overlaps=True,
            limitations=[
                "Invocation-local tree-state observations overlap native staged and post-apply validation timings and do not intercept command semantics."
            ],
        )

    preparation = shared.get("receipt_preparation_seconds")
    persistence = number(process_timings.get("receipt_persist_seconds"))
    if preparation is None or persistence is None:
        if "transaction.receipt_creation" not in invalid_phases:
            fail_native(
                "transaction.receipt_creation",
                "Transaction-v3 receipt preparation or post-write persistence timing was unavailable or invalid.",
            )
    elif "transaction.receipt_creation" not in invalid_phases:
        records["transaction.receipt_creation"] = measured_phase(
            round(preparation + persistence, 9),
            overlaps=True,
            limitations=[
                "One composed phase observation equal to receipt-v3 receipt_preparation_seconds plus process-local receipt_persist_seconds; it excludes path confinement and pending-journal deletion, and the post-write persistence observation is not inserted back into the immutable receipt."
            ],
        )

    total = number(process_timings.get("total_seconds"))
    if total is None:
        fail_native(
            "transaction.total_apply",
            "Transaction-v3 process-local total_seconds was unavailable or invalid.",
        )
    elif "transaction.total_apply" not in invalid_phases:
        records["transaction.total_apply"] = measured_phase(
            total,
            overlaps=True,
            limitations=[
                "Uses process-local transaction-v3 total_seconds from apply entry through receipt persistence and timing publication, before pending-journal unlink; it does not substitute total_before_receipt_persist_seconds."
            ],
        )

    return (
        records,
        "transaction.native_timings"
        if native_failure
        else "transaction.tree_state"
        if tree_failure
        else None,
    )


def profile_transaction(
    source: Path,
    phases: dict[str, dict[str, object]],
) -> str | None:
    with tempfile.TemporaryDirectory(prefix="octon-mini-phase-transaction-") as temporary:
        target = Path(temporary) / "project"
        shutil.copytree(source, target, symlinks=True, copy_function=shutil.copy2)
        plan_path = target / ".agent/transactions/plans/phase-profile.json"
        planned = run(
            octon_command(
                target,
                "work",
                "start",
                "--title",
                "Synthetic phase profile",
                "--scope",
                "Measure transaction phases in a disposable synthetic project",
                "--authority-basis",
                "authority:synthetic-phase-profile",
                "--owner",
                "phase_profiler",
                "--operator",
                "phase_profiler",
                "--acceptance",
                "The disposable transaction completes with exact recovery metadata",
                "--validation",
                "Run the generated structural validation contract",
                "--next-action",
                "Discard the disposable phase subject",
                "--output",
                str(plan_path),
            ),
            target,
        )
        if planned.returncode:
            return "transaction.plan_preparation"

        try:
            transaction = load_module(
                target / ".agent/scripts/octon_transaction.py",
                f"octon_mini_phase_transaction_{time.time_ns()}",
            )
            plan = transaction.load_plan(plan_path)
            original_tree = transaction._tree_state
            tree_seconds = 0.0
            tree_invocations = 0

            def tree_wrapper(root: Path) -> dict[str, tuple[str, int, str]]:
                nonlocal tree_seconds, tree_invocations
                started = time.perf_counter()
                try:
                    return original_tree(root)
                finally:
                    tree_seconds += time.perf_counter() - started
                    tree_invocations += 1

            transaction._tree_state = tree_wrapper
            try:
                receipt, _receipt_path = transaction.apply_plan(
                    target,
                    plan,
                    plan["canonical_plan_digest"],
                )
            finally:
                transaction._tree_state = original_tree

            native_records, timing_failure = native_transaction_phase_records(
                receipt,
                dict(transaction.LAST_PHASE_TIMINGS),
                tree_seconds=tree_seconds,
                tree_invocations=tree_invocations,
            )
            phases.update(native_records)
            return timing_failure
        except Exception:
            phases["transaction.total_apply"] = failed_phase(
                None,
                "Disposable transaction-v3 apply failed; exception content and partial native timings were not retained.",
            )
            return "transaction.apply"


def run_profile(sizes: tuple[int, ...]) -> tuple[dict[str, object], int]:
    report = initial_report(sizes)
    measurements = report["measurements"]
    assert isinstance(measurements, list)

    with tempfile.TemporaryDirectory(prefix="octon-mini-large-project-phase-") as temporary:
        area = Path(temporary)
        for size in sizes:
            target = area / f"payload-{size}"
            preparation = {
                "status": "completed",
                "scaffold_seconds": None,
                "payload_seconds": None,
                "refresh_seconds": None,
            }
            phases = {phase: empty_phase("Preparation did not complete.") for phase in PHASE_IDS}
            row = {
                "synthetic_payload_files": size,
                "preparation": preparation,
                "phases": phases,
                "limitations": [
                    "One informational observation per phase; no percentile or threshold applies.",
                    "Transaction phase timings overlap where marked and use a disposable routine work-start transaction.",
                ],
            }
            measurements.append(row)

            scaffold_result, scaffold_seconds = elapsed(
                lambda: run(
                    [
                        sys.executable,
                        "-B",
                        str(SCAFFOLD),
                        "--project-name",
                        f"Large Project Phase Profile {size}",
                        "--profile",
                        "minimal",
                        "--layout",
                        "compact",
                        "--target",
                        str(target),
                    ],
                    SCRIPT_ROOT,
                )
            )
            preparation["scaffold_seconds"] = scaffold_seconds
            if scaffold_result.returncode:
                preparation["status"] = "failed"
                record_failure(report, size, "preparation.scaffold", scaffold_result.returncode)
                continue

            try:
                _, payload_seconds = elapsed(lambda: write_payload(target, size))
                preparation["payload_seconds"] = payload_seconds
            except OSError:
                preparation["status"] = "failed"
                record_failure(report, size, "preparation.payload", None)
                continue

            refresh_result, refresh_seconds = elapsed(
                lambda: run(
                    [
                        sys.executable,
                        "-B",
                        ".agent/scripts/refresh.py",
                        "--refresh",
                    ],
                    target,
                )
            )
            preparation["refresh_seconds"] = refresh_seconds
            if refresh_result.returncode:
                preparation["status"] = "failed"
                record_failure(report, size, "preparation.refresh", refresh_result.returncode)
                continue

            phases, validator_failure = profile_validator(target)
            row["phases"] = phases
            if validator_failure is not None:
                record_failure(report, size, validator_failure, None)
                continue
            transaction_failure = profile_transaction(target, phases)
            if transaction_failure is not None:
                record_failure(report, size, transaction_failure, None)

    failures = report["execution_failures"]
    assert isinstance(failures, list)
    return report, 1 if failures else 0


def parse_args(argv: list[str] | None = None) -> tuple[int, ...]:
    parser = argparse.ArgumentParser(
        description=(
            "Run content-free, non-enforcing phase measurements on disposable "
            "synthetic Octon projects."
        )
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=list(DEFAULT_SIZES),
        help="unique ascending synthetic payload file counts",
    )
    args = parser.parse_args(argv)
    sizes = tuple(args.sizes)
    if not sizes or any(size < 0 for size in sizes) or list(sizes) != sorted(set(sizes)):
        parser.error("sizes must be unique ascending nonnegative integers")
    return sizes


def main(argv: list[str] | None = None) -> int:
    sizes = parse_args(argv)
    report, status = run_profile(sizes)
    print(json.dumps(report, indent=2, sort_keys=True))
    failures = report["execution_failures"]
    assert isinstance(failures, list)
    for failure in failures:
        print(
            "[FAIL] phase profile did not complete "
            f"size={failure['synthetic_payload_files']} phase={failure['phase']} "
            f"exit={failure['exit_code']}",
            file=sys.stderr,
        )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
