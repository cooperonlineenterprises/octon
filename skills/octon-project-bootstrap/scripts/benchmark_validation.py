#!/usr/bin/env python3
"""Run content-free, non-authorizing Octon validation benchmarks."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path


sys.dont_write_bytecode = True

SCHEMA_VERSION = "octon-mini.project.validation-benchmark.v2"
DOCUMENT_ROLE = "local_content_free_non_authorizing_measurement"
CHECK_TARGET_SECONDS = 2.0
MUTATION_TARGET_SECONDS = 10.0
SCAFFOLD_TARGET_SECONDS = 10.0
DEFAULT_SIZES = (0, 2_000, 10_000, 20_000)
DEFAULT_WARM_SAMPLES = 10
MIN_ENFORCED_WARM_SAMPLES = 10
PROFILES = ("minimal", "standard", "high-assurance")
COLD_CLASSIFICATION = "operational_cold_start_proxy"
WARM_CLASSIFICATION = "warm_steady_state"
PREPARATION_CLASSIFICATION = "preparation"
Sample = dict[str, object]
CommandFactory = Callable[[int], list[str]]


@dataclass(frozen=True)
class BenchmarkConfiguration:
    sizes: tuple[int, ...] = DEFAULT_SIZES
    warm_samples: int = DEFAULT_WARM_SAMPLES
    enforce: bool = False
    output: Path | None = None


class SequenceCounter:
    def __init__(self) -> None:
        self.value = 0

    def next(self) -> int:
        self.value += 1
        return self.value


def current_load_average() -> list[float] | None:
    try:
        return [round(value, 6) for value in os.getloadavg()]
    except (AttributeError, OSError):
        return None


def child_environment() -> dict[str, str]:
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def timed(
    argv: list[str],
    cwd: Path,
    *,
    classification: str,
    sequence: int,
) -> tuple[Sample, subprocess.CompletedProcess[str]]:
    load_before = current_load_average()
    started = time.perf_counter()
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            env=child_environment(),
        )
    except OSError:
        result = subprocess.CompletedProcess(argv, 126, stdout="", stderr="")
    elapsed = time.perf_counter() - started
    return (
        {
            "sequence": sequence,
            "classification": classification,
            "seconds": elapsed,
            "exit_code": result.returncode,
            "load_average_before": load_before,
            "load_average_after": current_load_average(),
        },
        result,
    )


def percentile_90(values: list[float]) -> float:
    """Return the nearest-rank p90: sorted(values)[ceil(0.90*n)-1]."""
    if not values:
        raise ValueError("p90 requires at least one sample")
    ordered = sorted(values)
    rank = math.ceil(0.90 * len(ordered))
    return ordered[rank - 1]


def configuration_errors(configuration: BenchmarkConfiguration) -> list[str]:
    errors: list[str] = []
    sizes = list(configuration.sizes)
    if not sizes:
        errors.append("sizes must contain at least one value")
    if any(not isinstance(size, int) or isinstance(size, bool) or size < 0 for size in sizes):
        errors.append("sizes must contain nonnegative integers")
    if sizes != sorted(set(sizes)):
        errors.append("sizes must be unique and ascending")
    if configuration.warm_samples < 1:
        errors.append("warm samples must be at least 1")
    if configuration.enforce and configuration.warm_samples < MIN_ENFORCED_WARM_SAMPLES:
        errors.append(
            f"enforced runs require at least {MIN_ENFORCED_WARM_SAMPLES} warm samples"
        )
    if configuration.enforce and 10_000 not in configuration.sizes:
        errors.append("enforced runs must include the 10,000-file check target")
    return errors


def write_payload(root: Path, target: int) -> None:
    payload = root / "benchmark-payload"
    payload.mkdir(exist_ok=True)
    for index in range(target):
        bucket = payload / f"b{index // 1000:03d}"
        bucket.mkdir(exist_ok=True)
        (bucket / f"f{index:05d}.txt").write_text(
            f"bounded benchmark payload {index}\n",
            encoding="utf-8",
        )


def filesystem_context(root: Path) -> dict[str, object]:
    case_sensitive: bool | None = None
    probe = root / "octon-mini-case-probe"
    alternate = root / "OCTON-MINI-CASE-PROBE"
    try:
        probe.write_bytes(b"probe\n")
        case_sensitive = not alternate.exists()
    except OSError:
        case_sensitive = None
    finally:
        try:
            probe.unlink()
        except OSError:
            pass

    block_size: int | None = None
    fragment_size: int | None = None
    statvfs = getattr(os, "statvfs", None)
    if statvfs is not None:
        try:
            details = statvfs(root)
            block_size = int(details.f_bsize)
            fragment_size = int(details.f_frsize)
        except OSError:
            pass
    return {
        "temporary_root_policy": "fresh_system_temporary_directory",
        "fresh_temporary_root": True,
        "cache_eviction_attempted": False,
        "case_sensitive": case_sensitive,
        "block_size_bytes": block_size,
        "fragment_size_bytes": fragment_size,
        "filesystem_encoding": sys.getfilesystemencoding(),
    }


def host_context(root: Path) -> dict[str, object]:
    clock = time.get_clock_info("perf_counter")
    return {
        "operating_system": platform.system() or "unknown",
        "operating_system_release": platform.release() or "unknown",
        "architecture": platform.machine() or "unknown",
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "logical_cpu_count": os.cpu_count(),
        "perf_counter": {
            "implementation": clock.implementation,
            "resolution_seconds": clock.resolution,
            "monotonic": clock.monotonic,
        },
        "load_average_at_start": current_load_average(),
        "load_average_at_end": None,
        "filesystem": filesystem_context(root),
    }


def empty_series() -> dict[str, object]:
    return {
        "samples": [],
        "combined_p90_seconds": None,
        "warm_p90_seconds": None,
    }


def initial_report(
    configuration: BenchmarkConfiguration,
    temporary_root: Path,
) -> dict[str, object]:
    samples_per_series = 1 + configuration.warm_samples
    expected_samples = (
        len(PROFILES) * samples_per_series
        + len(configuration.sizes) * (2 + 2 * samples_per_series)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "document_role": DOCUMENT_ROLE,
        "permission_grant": False,
        "benchmark_configuration": {
            "synthetic_payload_file_counts": list(configuration.sizes),
            "profiles": list(PROFILES),
            "layout": "compact",
            "cold_start_proxy_samples_per_series": 1,
            "warm_samples_per_series": configuration.warm_samples,
            "independent_target_per_payload_size": True,
            "child_python_bytecode_disabled": True,
            "percentile": {
                "name": "nearest_rank",
                "percentile": 90,
                "rank_formula": "ceil(0.90 * sample_count)",
            },
            "cache_policy": {
                "operational_cold_start_proxy": (
                    "first measured invocation in each operation or profile series"
                ),
                "warm_steady_state": (
                    "subsequent measured invocations; check and mutation series reuse "
                    "their target while scaffold samples use independent destinations"
                ),
                "kernel_cache_eviction": "not_attempted",
            },
        },
        "host_context": host_context(temporary_root),
        "scaffold_profiles": [],
        "measurements": [],
        "thresholds": {
            "scaffold_combined_p90_seconds": SCAFFOLD_TARGET_SECONDS,
            "check_combined_p90_seconds_at_10000_files": CHECK_TARGET_SECONDS,
            "check_warm_p90_seconds_at_10000_files": CHECK_TARGET_SECONDS,
            "fast_mutation_combined_p90_seconds": MUTATION_TARGET_SECONDS,
            "fast_mutation_warm_p90_seconds": MUTATION_TARGET_SECONDS,
        },
        "sample_accounting": {
            "expected_samples": expected_samples,
            "observed_samples": 0,
            "successful_samples": 0,
            "failed_samples": 0,
            "by_classification": {
                COLD_CLASSIFICATION: 0,
                WARM_CLASSIFICATION: 0,
                PREPARATION_CLASSIFICATION: 0,
            },
            "complete": False,
        },
        "execution_failures": [],
        "enforcement": {
            "enabled": configuration.enforce,
            "status": "not_evaluated",
            "failures": [],
        },
        "limitations": [
            "Synthetic small files do not represent every filesystem or repository shape.",
            "The cold-start value is an operational first-invocation proxy; the benchmark does not claim or attempt kernel cache eviction.",
            "Wall-clock and load-average results are host-specific and are never readiness evidence.",
            "Unavailable platform metadata is reported as null rather than inferred.",
        ],
    }


def record_command(
    report: dict[str, object],
    *,
    stage: str,
    argv: list[str],
    cwd: Path,
    classification: str,
    counter: SequenceCounter,
) -> tuple[Sample, bool]:
    sample, result = timed(
        argv,
        cwd,
        classification=classification,
        sequence=counter.next(),
    )
    if result.returncode:
        failures = report["execution_failures"]
        assert isinstance(failures, list)
        failures.append(
            {
                "stage": stage,
                "sequence": sample["sequence"],
                "exit_code": result.returncode,
            }
        )
    return sample, result.returncode == 0


def summarize_series(series: dict[str, object]) -> None:
    samples = series["samples"]
    assert isinstance(samples, list)
    successful = [
        sample
        for sample in samples
        if isinstance(sample, dict) and sample.get("exit_code") == 0
    ]
    combined = [float(sample["seconds"]) for sample in successful]
    warm = [
        float(sample["seconds"])
        for sample in successful
        if sample.get("classification") == WARM_CLASSIFICATION
    ]
    series["combined_p90_seconds"] = percentile_90(combined) if combined else None
    series["warm_p90_seconds"] = percentile_90(warm) if warm else None


def measure_series(
    report: dict[str, object],
    series: dict[str, object],
    *,
    stage: str,
    command: CommandFactory,
    cwd: Path,
    warm_samples: int,
    counter: SequenceCounter,
) -> bool:
    samples = series["samples"]
    assert isinstance(samples, list)
    classifications = [COLD_CLASSIFICATION] + [WARM_CLASSIFICATION] * warm_samples
    for index, classification in enumerate(classifications):
        sample, success = record_command(
            report,
            stage=stage,
            argv=command(index),
            cwd=cwd,
            classification=classification,
            counter=counter,
        )
        samples.append(sample)
        if not success:
            summarize_series(series)
            return False
    summarize_series(series)
    return True


def report_samples(report: dict[str, object]) -> Iterator[Sample]:
    scaffold_profiles = report.get("scaffold_profiles", [])
    if isinstance(scaffold_profiles, list):
        for row in scaffold_profiles:
            if not isinstance(row, dict):
                continue
            for sample in row.get("samples", []):
                if isinstance(sample, dict):
                    yield sample
    measurements = report.get("measurements", [])
    if isinstance(measurements, list):
        for row in measurements:
            if not isinstance(row, dict):
                continue
            for sample in row.get("preparation_samples", []):
                if isinstance(sample, dict):
                    yield sample
            for name in ("check", "fast_mutation"):
                series = row.get(name, {})
                if not isinstance(series, dict):
                    continue
                for sample in series.get("samples", []):
                    if isinstance(sample, dict):
                        yield sample


def update_sample_accounting(report: dict[str, object]) -> None:
    samples = list(report_samples(report))
    successful = [sample for sample in samples if sample.get("exit_code") == 0]
    failed = [sample for sample in samples if sample.get("exit_code") != 0]
    counts = {
        classification: sum(
            sample.get("classification") == classification for sample in samples
        )
        for classification in (
            COLD_CLASSIFICATION,
            WARM_CLASSIFICATION,
            PREPARATION_CLASSIFICATION,
        )
    }
    accounting = report["sample_accounting"]
    assert isinstance(accounting, dict)
    accounting.update(
        observed_samples=len(samples),
        successful_samples=len(successful),
        failed_samples=len(failed),
        by_classification=counts,
        complete=(
            len(samples) == accounting["expected_samples"]
            and not failed
            and not report["execution_failures"]
        ),
    )


def threshold_failures(report: dict[str, object]) -> list[str]:
    failures: list[str] = []
    scaffold_profiles = report["scaffold_profiles"]
    assert isinstance(scaffold_profiles, list)
    for row in scaffold_profiles:
        assert isinstance(row, dict)
        value = row.get("combined_p90_seconds")
        if isinstance(value, (int, float)) and value >= SCAFFOLD_TARGET_SECONDS:
            failures.append(f"{row['profile']} scaffold combined p90 threshold exceeded")

    measurements = report["measurements"]
    assert isinstance(measurements, list)
    for row in measurements:
        assert isinstance(row, dict)
        size = row["synthetic_payload_files"]
        mutation = row["fast_mutation"]
        check = row["check"]
        assert isinstance(mutation, dict) and isinstance(check, dict)
        for key, label in (
            ("combined_p90_seconds", "combined"),
            ("warm_p90_seconds", "warm"),
        ):
            value = mutation.get(key)
            if isinstance(value, (int, float)) and value >= MUTATION_TARGET_SECONDS:
                failures.append(
                    f"fast mutation {label} p90 threshold exceeded at {size} files"
                )
        if size == 10_000:
            for key, label in (
                ("combined_p90_seconds", "combined"),
                ("warm_p90_seconds", "warm"),
            ):
                value = check.get(key)
                if isinstance(value, (int, float)) and value >= CHECK_TARGET_SECONDS:
                    failures.append(f"10,000-file check {label} p90 threshold exceeded")
    return failures


def finalize_report(report: dict[str, object]) -> int:
    update_sample_accounting(report)
    context = report["host_context"]
    assert isinstance(context, dict)
    context["load_average_at_end"] = current_load_average()
    enforcement = report["enforcement"]
    accounting = report["sample_accounting"]
    assert isinstance(enforcement, dict) and isinstance(accounting, dict)
    if report["execution_failures"] or not accounting["complete"]:
        enforcement["status"] = "measurement_failed"
        enforcement["failures"] = ["benchmark sample accounting is incomplete"]
        return 1
    if not enforcement["enabled"]:
        enforcement["status"] = "not_enforced"
        enforcement["failures"] = []
        return 0
    failures = threshold_failures(report)
    enforcement["failures"] = failures
    enforcement["status"] = "failed" if failures else "passed"
    return 1 if failures else 0


def run_benchmark(
    configuration: BenchmarkConfiguration,
) -> tuple[dict[str, object], int]:
    errors = configuration_errors(configuration)
    if errors:
        raise ValueError("; ".join(errors))
    script_root = Path(__file__).resolve().parent
    scaffold = script_root / "scaffold_project.py"
    counter = SequenceCounter()

    with tempfile.TemporaryDirectory(prefix="octon-mini-validation-scale-") as temporary:
        area = Path(temporary)
        report = initial_report(configuration, area)
        scaffold_profiles = report["scaffold_profiles"]
        measurements = report["measurements"]
        assert isinstance(scaffold_profiles, list) and isinstance(measurements, list)

        for profile in PROFILES:
            row: dict[str, object] = {
                "profile": profile,
                "layout": "compact",
                **empty_series(),
            }
            scaffold_profiles.append(row)

            def scaffold_command(index: int, *, selected_profile: str = profile) -> list[str]:
                destination = area / f"scaffold-{selected_profile}-sample-{index}"
                return [
                    sys.executable,
                    "-B",
                    str(scaffold),
                    "--project-name",
                    f"{selected_profile.title()} Validation Benchmark",
                    "--profile",
                    selected_profile,
                    "--layout",
                    "compact",
                    "--target",
                    str(destination),
                ]

            if not measure_series(
                report,
                row,
                stage=f"scaffold_profile.{profile}",
                command=scaffold_command,
                cwd=script_root,
                warm_samples=configuration.warm_samples,
                counter=counter,
            ):
                return report, finalize_report(report)

        for size in configuration.sizes:
            target = area / f"payload-size-{size}"
            row = {
                "synthetic_payload_files": size,
                "preparation_samples": [],
                "check": empty_series(),
                "fast_mutation": empty_series(),
            }
            measurements.append(row)
            preparation = row["preparation_samples"]
            assert isinstance(preparation, list)

            sample, success = record_command(
                report,
                stage=f"payload.{size}.scaffold_preparation",
                argv=[
                    sys.executable,
                    "-B",
                    str(scaffold),
                    "--project-name",
                    f"Validation Benchmark {size}",
                    "--profile",
                    "minimal",
                    "--layout",
                    "compact",
                    "--target",
                    str(target),
                ],
                cwd=script_root,
                classification=PREPARATION_CLASSIFICATION,
                counter=counter,
            )
            preparation.append(sample)
            if not success:
                return report, finalize_report(report)
            try:
                write_payload(target, size)
            except OSError:
                failures = report["execution_failures"]
                assert isinstance(failures, list)
                failures.append(
                    {
                        "stage": f"payload.{size}.synthetic_file_preparation",
                        "sequence": None,
                        "exit_code": None,
                    }
                )
                return report, finalize_report(report)

            sample, success = record_command(
                report,
                stage=f"payload.{size}.refresh_preparation",
                argv=[
                    sys.executable,
                    "-B",
                    ".agent/scripts/refresh.py",
                    "--refresh",
                ],
                cwd=target,
                classification=PREPARATION_CLASSIFICATION,
                counter=counter,
            )
            preparation.append(sample)
            if not success:
                return report, finalize_report(report)

            check = row["check"]
            assert isinstance(check, dict)
            if not measure_series(
                report,
                check,
                stage=f"payload.{size}.check",
                command=lambda _index: [
                    sys.executable,
                    "-B",
                    ".agent/scripts/validate.py",
                    "--check",
                ],
                cwd=target,
                warm_samples=configuration.warm_samples,
                counter=counter,
            ):
                return report, finalize_report(report)

            mutation = row["fast_mutation"]
            assert isinstance(mutation, dict)
            if not measure_series(
                report,
                mutation,
                stage=f"payload.{size}.fast_mutation",
                command=lambda _index: [
                    sys.executable,
                    "-B",
                    ".agent/tests/test_validate.py",
                    "--tier",
                    "fast",
                ],
                cwd=target,
                warm_samples=configuration.warm_samples,
                counter=counter,
            ):
                return report, finalize_report(report)

        return report, finalize_report(report)


def parse_args(argv: list[str] | None = None) -> BenchmarkConfiguration:
    parser = argparse.ArgumentParser(
        description="Run local, content-free validation scale benchmarks."
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=list(DEFAULT_SIZES),
        help="independent synthetic repository file counts",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=DEFAULT_WARM_SAMPLES,
        help=(
            "warm steady-state samples per series; one additional operational "
            "cold-start proxy is always recorded"
        ),
    )
    parser.add_argument("--enforce", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        help="write the complete report to a new explicit path instead of stdout",
    )
    args = parser.parse_args(argv)
    configuration = BenchmarkConfiguration(
        sizes=tuple(args.sizes),
        warm_samples=args.samples,
        enforce=args.enforce,
        output=args.output,
    )
    errors = configuration_errors(configuration)
    if errors:
        parser.error("; ".join(errors))
    return configuration


def main(argv: list[str] | None = None) -> int:
    configuration = parse_args(argv)
    report, status = run_benchmark(configuration)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    output_path = getattr(configuration, "output", None)
    if output_path is None:
        print(rendered, end="")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(
                output_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError as error:
            raise SystemExit(
                f"refusing to overwrite benchmark report: {output_path}"
            ) from error
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
    enforcement = report["enforcement"]
    assert isinstance(enforcement, dict)
    for failure in enforcement["failures"]:
        print(f"[FAIL] {failure}", file=sys.stderr)
    execution_failures = report["execution_failures"]
    assert isinstance(execution_failures, list)
    for failure in execution_failures:
        assert isinstance(failure, dict)
        print(
            f"[FAIL] benchmark stage {failure['stage']} exited {failure['exit_code']}",
            file=sys.stderr,
        )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
