#!/usr/bin/env python3
"""Benchmark dormant autonomous-delivery read-only commands."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
REPO_ROOT = SKILL_ROOT.parents[1] if (SKILL_ROOT.parents[1] / "octon.json").is_file() else SKILL_ROOT / "assets/octon-source"
SCAFFOLDER = SCRIPT_ROOT / "scaffold_project.py"


def percentile_nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def run(argv: list[str], cwd: Path) -> tuple[float, subprocess.CompletedProcess[bytes]]:
    started = time.perf_counter()
    result = subprocess.run(
        argv,
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        shell=False,
        timeout=120,
    )
    return time.perf_counter() - started, result


def measure(target: Path, argv: list[str], cold: int, warm: int, threshold: float) -> dict[str, object]:
    cold_values: list[float] = []
    warm_values: list[float] = []
    failures: list[dict[str, object]] = []
    for phase, count, values in (("cold", cold, cold_values), ("warm", warm, warm_values)):
        for sample in range(1, count + 1):
            elapsed, result = run(argv, target)
            values.append(elapsed)
            if result.returncode:
                failures.append({"phase": phase, "sample": sample, "returncode": result.returncode, "stdout_sha256": __import__("hashlib").sha256(result.stdout).hexdigest(), "stderr_sha256": __import__("hashlib").sha256(result.stderr).hexdigest()})
    p90 = percentile_nearest_rank(warm_values, 0.90)
    return {"argv": argv, "cold_seconds": cold_values, "warm_seconds": warm_values, "warm_p90_seconds": p90, "threshold_pass": not failures and p90 < threshold, "failures": failures}


def benchmark(payload_files: int, cold: int, warm: int, threshold: float) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="octon-autonomous-benchmark-") as temporary:
        target = Path(temporary) / "project"
        generated = subprocess.run([sys.executable, "-B", str(SCAFFOLDER), "--target", str(target), "--project-name", "Autonomous Benchmark", "--profile", "minimal"], cwd=REPO_ROOT, capture_output=True, check=False, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if generated.returncode:
            raise RuntimeError(generated.stderr.decode("utf-8", errors="replace"))
        payload = target / "payload"
        payload.mkdir()
        for index in range(payload_files):
            (payload / f"file-{index:05d}.txt").write_text("bounded synthetic payload\n", encoding="utf-8")
        commands = {
            "status": [sys.executable, "-I", "-B", "octon", "delivery", "status"],
            "context": [sys.executable, "-I", "-B", "octon", "delivery", "context", "--max-bytes", "65536"],
            "activation_preview": [sys.executable, "-I", "-B", "octon", "delivery", "activation-preview", "--profile", "fast_delivery"],
            "resume": [sys.executable, "-I", "-B", "octon", "delivery", "resume"],
            "explain": [sys.executable, "-I", "-B", "octon", "delivery", "explain"],
        }
        measurements = {name: measure(target, argv, cold, warm, threshold) for name, argv in commands.items()}
        sample_transition = {
            "schema_version": "harness.autonomous-delivery-effect-receipt.v1",
            "artifact_kind": "autonomous_delivery_monotonic_effect_receipt",
            "permission_grant": False,
            "receipt_id": "ADER-" + "0" * 24,
            "projection_digest": "0" * 64,
            "action": "dispatch_hosted_workflow",
            "state": "completed",
            "requested_at": "2030-01-01T00:00:00Z",
            "attempted_at": "2030-01-01T00:00:01Z",
            "observed_at": "2030-01-01T00:00:02Z",
            "before_evidence": {},
            "after_evidence": {"run_id": 1, "head_sha": "0" * 40},
            "outcome": "completed",
            "automatic_retry_safe": False,
            "limitations": ["Synthetic content-free storage measurement."],
            "receipt_digest": "0" * 64,
        }
        transition_bytes = len((json.dumps(sample_transition, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
    return {
        "schema_version": "octon-mini.autonomous-delivery-benchmark-report.v1",
        "subject": "generated_project_dormant_autonomous_delivery_read_only_surfaces",
        "payload_files": payload_files,
        "cold_samples": cold,
        "warm_samples": warm,
        "threshold_seconds": threshold,
        "measurements": measurements,
        "storage": {"sample_transition_bytes": transition_bytes, "projected_100_transition_bytes": transition_bytes * 100, "threshold": None, "informational": True},
        "result": "pass" if all(item["threshold_pass"] for item in measurements.values()) else "fail",
        "limitations": ["Synthetic files contain no project content.", "Timing is host-specific and is not human-usability evidence."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload-files", type=int, default=10000)
    parser.add_argument("--cold-samples", type=int, default=1)
    parser.add_argument("--warm-samples", type=int, default=10)
    parser.add_argument("--threshold", type=float, default=2.0)
    parser.add_argument("--output")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    if min(args.payload_files, args.cold_samples, args.warm_samples) < 0 or args.cold_samples < 1 or args.warm_samples < 1 or args.threshold <= 0:
        parser.error("sample counts and threshold must be positive; payload files must be nonnegative")
    report = benchmark(args.payload_files, args.cold_samples, args.warm_samples, args.threshold)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        path = Path(args.output)
        if path.exists():
            raise SystemExit("output already exists; benchmark evidence is not overwritten")
        path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if args.enforce and report["result"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
