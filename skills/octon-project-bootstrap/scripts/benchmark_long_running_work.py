#!/usr/bin/env python3
"""Measure read-only long-running-work surfaces without changing benchmark-v2."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import test_long_running_work as fixture_support


ROOT = fixture_support.REPO_ROOT


def nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("percentile requires samples")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def revision() -> tuple[str, bool]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
        check=False, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True,
        check=False, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    return (head.stdout.strip() or "unavailable", bool(status.stdout.strip()))


def sample(target: Path, argv: list[str]) -> dict[str, object]:
    started = time.perf_counter()
    result = fixture_support.run(
        [sys.executable, "-I", "-B", "octon", *argv], target
    )
    elapsed = time.perf_counter() - started
    return {
        "seconds": round(elapsed, 9),
        "exit_code": result.returncode,
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
    }


def build_report(payload_files: int, warm_samples: int) -> dict[str, object]:
    fixture = fixture_support.LongRunningWorkTests(
        "test_absent_package_refuses_with_continuation_and_no_change"
    )
    fixture.setUp()
    try:
        fixture.install_and_enable()
        payload = fixture.target / "payload"
        payload.mkdir()
        for index in range(payload_files):
            (payload / f"file-{index:06d}.txt").write_text("synthetic payload\n", encoding="utf-8")
        refreshed = fixture_support.run(
            [sys.executable, "-I", "-B", ".agent/scripts/refresh.py", "--refresh"],
            fixture.target,
        )
        if refreshed.returncode:
            raise RuntimeError(refreshed.stderr or refreshed.stdout)
        run_id = str(fixture.start()["run_id"])
        commands = {
            "context": ["work", "run", "context", "--run-id", run_id, "--json"],
            "status": ["work", "run", "status", "--run-id", run_id, "--json"],
            "resume": ["work", "run", "resume", "--run-id", run_id, "--json"],
            "explain": ["work", "run", "explain", "--run-id", run_id, "--json"],
        }
        series: list[dict[str, object]] = []
        for name, argv in commands.items():
            samples = [sample(fixture.target, argv) for _ in range(warm_samples + 1)]
            warm = samples[1:]
            series.append({
                "name": name,
                "samples": samples,
                "cold_seconds": samples[0]["seconds"],
                "warm_p90_seconds": round(nearest_rank([float(item["seconds"]) for item in warm], 0.9), 9),
                "deterministic_output": len({item["stdout_sha256"] for item in samples}) == 1,
                "all_exit_zero": all(item["exit_code"] == 0 for item in samples),
            })
        head, dirty = revision()
        passed = all(
            item["warm_p90_seconds"] < 2.0
            and item["deterministic_output"]
            and item["all_exit_zero"]
            for item in series
        )
        return {
            "schema_version": "octon-mini.long-running-work-benchmark.v1",
            "permission_grant": False,
            "subject": {
                "source_revision": head,
                "source_dirty": dirty,
                "profile": "standard",
                "payload_files": payload_files,
            },
            "host": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "architecture": platform.machine(),
            },
            "method": {
                "cold_samples": 1,
                "warm_samples": warm_samples,
                "percentile_method": "nearest_rank",
                "read_only": True,
            },
            "series": series,
            "thresholds": {"warm_p90_seconds": 2.0},
            "result": "pass" if passed else "fail",
            "limitations": [
                "Synthetic disposable-project measurement on one host.",
                "Dirty source evidence is not final-candidate or real-project maturity evidence.",
                "Benchmark-v2 thresholds and accounting remain separate and unchanged.",
            ],
        }
    finally:
        fixture.tearDown()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-files", type=int, default=10000)
    parser.add_argument("--warm-samples", type=int, default=10)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    if args.payload_files < 0 or args.warm_samples < 1:
        parser.error("payload files must be nonnegative and warm samples must be positive")
    report = build_report(args.payload_files, args.warm_samples)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(
                args.output,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError as error:
            raise SystemExit(
                f"refusing to overwrite benchmark report: {args.output}"
            ) from error
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
    else:
        print(text, end="")
    return 1 if args.enforce and report["result"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
