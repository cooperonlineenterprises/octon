#!/usr/bin/env python3
"""Focused methodology tests for the v2 validation benchmark."""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().with_name("benchmark_validation.py")
PHASE_SCRIPT = Path(__file__).resolve().with_name("profile_large_project.py")
SOURCE_VALIDATOR_SCRIPT = Path(__file__).resolve().with_name(
    "validate_source_contracts.py"
)
SKILL_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = next(
    candidate
    for candidate in (
        Path(__file__).resolve().parents[3],
        SKILL_ROOT / "assets/octon-source",
    )
    if (candidate / "shared/source-contracts").is_dir()
)
BENCHMARK_SCHEMA = (
    SOURCE_ROOT / "shared/source-contracts/validation-benchmark-report.schema.json"
)
PHASE_SCHEMA = (
    SOURCE_ROOT / "shared/source-contracts/large-project-phase-profile.schema.json"
)


def load_benchmark() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("octon_mini_benchmark_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("benchmark module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


BENCHMARK = load_benchmark()


def load_phase_profiler() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "octon_mini_large_project_phase_test", PHASE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("large-project phase profiler cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


PHASE_PROFILER = load_phase_profiler()


def load_source_validator() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "octon_mini_benchmark_schema_test", SOURCE_VALIDATOR_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("source-contract validator cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SOURCE_VALIDATOR = load_source_validator()


def sample(
    sequence: int,
    classification: str,
    seconds: float,
    *,
    exit_code: int = 0,
) -> dict[str, object]:
    return {
        "sequence": sequence,
        "classification": classification,
        "seconds": seconds,
        "exit_code": exit_code,
        "load_average_before": None,
        "load_average_after": None,
    }


class BenchmarkMethodologyTests(unittest.TestCase):
    def test_nearest_rank_p90_is_explicit_and_deterministic(self) -> None:
        self.assertEqual(BENCHMARK.percentile_90([3.0]), 3.0)
        self.assertEqual(
            BENCHMARK.percentile_90([10.0, 1.0, 9.0, 2.0, 8.0, 3.0, 7.0, 4.0, 6.0, 5.0]),
            9.0,
        )
        self.assertEqual(BENCHMARK.percentile_90([float(value) for value in range(1, 12)]), 10.0)
        with self.assertRaises(ValueError):
            BENCHMARK.percentile_90([])

    def test_configuration_rejects_malformed_or_weak_enforced_runs(self) -> None:
        configuration = BENCHMARK.BenchmarkConfiguration
        cases = (
            configuration(sizes=(), warm_samples=10),
            configuration(sizes=(-1,), warm_samples=10),
            configuration(sizes=(0, 0), warm_samples=10),
            configuration(sizes=(10_000, 2_000), warm_samples=10),
            configuration(sizes=(10_000,), warm_samples=0),
            configuration(sizes=(10_000,), warm_samples=9, enforce=True),
            configuration(sizes=(0, 2_000), warm_samples=10, enforce=True),
        )
        for case in cases:
            with self.subTest(case=case):
                self.assertTrue(BENCHMARK.configuration_errors(case))
        self.assertEqual(
            BENCHMARK.configuration_errors(
                configuration(sizes=(0, 10_000), warm_samples=10, enforce=True)
            ),
            [],
        )

    def test_default_report_is_v2_content_free_and_non_authorizing(self) -> None:
        configuration = BENCHMARK.BenchmarkConfiguration(sizes=(10_000,))
        with tempfile.TemporaryDirectory(prefix="octon-mini benchmark report ") as temporary:
            report = BENCHMARK.initial_report(configuration, Path(temporary))
        self.assertEqual(
            report["schema_version"], "octon-mini.project.validation-benchmark.v2"
        )
        self.assertIs(report["permission_grant"], False)
        config = report["benchmark_configuration"]
        self.assertEqual(config["warm_samples_per_series"], 10)
        self.assertEqual(config["cold_start_proxy_samples_per_series"], 1)
        self.assertEqual(config["percentile"]["name"], "nearest_rank")
        self.assertIs(config["independent_target_per_payload_size"], True)
        self.assertIn("independent destinations", config["cache_policy"]["warm_steady_state"])
        encoded = json.dumps(report, sort_keys=True)
        self.assertNotIn(temporary, encoded)
        self.assertNotIn(str(Path.home()), encoded)
        self.assertNotIn("hostname", encoded.casefold())
        self.assertEqual(report["sample_accounting"]["expected_samples"], 57)

    def test_default_report_conforms_to_the_v2_source_schema(self) -> None:
        configuration = BENCHMARK.BenchmarkConfiguration(sizes=(10_000,))
        with tempfile.TemporaryDirectory(prefix="octon-mini benchmark schema ") as temporary:
            report = BENCHMARK.initial_report(configuration, Path(temporary))
        schema = json.loads(BENCHMARK_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            SOURCE_VALIDATOR.schema_issues(report, schema, "benchmark-report"),
            [],
        )

    def test_phase_profile_is_separate_content_free_and_non_enforcing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="octon-mini phase schema ") as temporary:
            with mock.patch.object(
                PHASE_PROFILER,
                "source_git_state",
                return_value=("a" * 40, False),
            ):
                report = PHASE_PROFILER.initial_report((0, 50_000))
        self.assertEqual(
            report["schema_version"],
            "octon-mini.source.large-project-phase-profile.v1",
        )
        self.assertIs(report["permission_grant"], False)
        self.assertEqual(
            report["enforcement"],
            "informational_only_no_thresholds_or_release_claim",
        )
        self.assertEqual(
            report["configuration"]["threshold_policy"],
            "informational_only_no_thresholds",
        )
        self.assertIn(50_000, report["configuration"]["synthetic_payload_file_counts"])
        self.assertEqual(
            report["configuration"]["phase_ids"],
            list(PHASE_PROFILER.PHASE_IDS),
        )
        encoded = json.dumps(report, sort_keys=True)
        self.assertNotIn(temporary, encoded)
        self.assertNotIn(str(Path.home()), encoded)
        schema = json.loads(PHASE_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            SOURCE_VALIDATOR.schema_issues(report, schema, "phase-profile"),
            [],
        )

    def test_phase_records_preserve_overlap_failure_and_non_run_state(self) -> None:
        measured = PHASE_PROFILER.measured_phase(
            1.25,
            invocations=4,
            observed_file_count=20_000,
            overlaps=True,
            limitations=["Inclusive observation."],
        )
        self.assertEqual(measured["status"], "measured")
        self.assertEqual(measured["invocations"], 4)
        self.assertIs(measured["overlaps_other_phases"], True)
        failed = PHASE_PROFILER.failed_phase(
            0.5,
            "Failure details are deliberately content-free.",
        )
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["seconds"], 0.5)
        not_run = PHASE_PROFILER.empty_phase("Prerequisite did not complete.")
        self.assertEqual(not_run["status"], "not_run")
        self.assertIsNone(not_run["seconds"])

    def test_transaction_v3_native_phase_mapping_is_exact_and_content_free(self) -> None:
        receipt_timings = {
            "staging_seconds": 1.0,
            "refresh_seconds": 2.0,
            "staged_validation_seconds": 3.0,
            "apply_seconds": 4.0,
            "post_apply_validation_seconds": 5.0,
            "receipt_preparation_seconds": 6.0,
            "total_before_receipt_persist_seconds": 7.0,
        }
        receipt = {
            "schema_version": "harness.transaction-receipt.v3",
            "timings": receipt_timings,
            "ignored_sensitive_value": "must-not-enter-phase-output",
        }
        process_timings = {
            **receipt_timings,
            "receipt_persist_seconds": 8.0,
            "total_seconds": 9.0,
        }
        records, failure = PHASE_PROFILER.native_transaction_phase_records(
            receipt,
            process_timings,
            tree_seconds=0.5,
            tree_invocations=4,
        )
        self.assertIsNone(failure)
        expected = {
            "transaction.staging_copy": 1.0,
            "transaction.staged_refresh_validation": 3.0,
            "transaction.live_apply": 4.0,
            "transaction.post_apply_validation": 5.0,
            "transaction.receipt_creation": 14.0,
            "transaction.total_apply": 9.0,
            "transaction.tree_state": 0.5,
        }
        self.assertEqual(
            {phase: record["seconds"] for phase, record in records.items()},
            expected,
        )
        self.assertTrue(
            all(record["overlaps_other_phases"] for record in records.values())
        )
        self.assertEqual(records["transaction.tree_state"]["invocations"], 4)
        self.assertEqual(records["transaction.receipt_creation"]["invocations"], 1)
        encoded = json.dumps(records, allow_nan=False, sort_keys=True)
        self.assertNotIn("must-not-enter-phase-output", encoded)
        self.assertNotEqual(
            records["transaction.staged_refresh_validation"]["seconds"],
            receipt_timings["refresh_seconds"],
        )
        self.assertNotEqual(
            records["transaction.total_apply"]["seconds"],
            receipt_timings["total_before_receipt_persist_seconds"],
        )
        profiler_source = PHASE_SCRIPT.read_text(encoding="utf-8")
        for prohibited in (
            "transaction._clone_for_staging =",
            "transaction._staged_result =",
            "transaction._run_commands =",
            "transaction.write_new_json =",
        ):
            self.assertNotIn(prohibited, profiler_source)
        self.assertIn("transaction._tree_state = tree_wrapper", profiler_source)

    def test_transaction_v3_native_phase_mapping_fails_closed(self) -> None:
        receipt_timings = {
            "staging_seconds": 1.0,
            "refresh_seconds": 2.0,
            "staged_validation_seconds": 3.0,
            "apply_seconds": 4.0,
            "post_apply_validation_seconds": 5.0,
            "receipt_preparation_seconds": 6.0,
            "total_before_receipt_persist_seconds": 7.0,
        }
        receipt = {
            "schema_version": "harness.transaction-receipt.v3",
            "timings": receipt_timings,
        }
        process_timings = {
            **receipt_timings,
            "receipt_persist_seconds": 8.0,
            "total_seconds": 9.0,
        }

        cases = (
            (
                "missing",
                lambda r, _p: r["timings"].pop("staging_seconds"),
                "transaction.staging_copy",
            ),
            (
                "mismatch",
                lambda _r, p: p.__setitem__("refresh_seconds", 20.0),
                "transaction.staged_refresh_validation",
            ),
            (
                "boolean",
                lambda r, p: (
                    r["timings"].__setitem__("apply_seconds", True),
                    p.__setitem__("apply_seconds", True),
                ),
                "transaction.live_apply",
            ),
            (
                "negative",
                lambda r, p: (
                    r["timings"].__setitem__("post_apply_validation_seconds", -1.0),
                    p.__setitem__("post_apply_validation_seconds", -1.0),
                ),
                "transaction.post_apply_validation",
            ),
            (
                "nan",
                lambda r, p: (
                    r["timings"].__setitem__("staging_seconds", float("nan")),
                    p.__setitem__("staging_seconds", float("nan")),
                ),
                "transaction.staging_copy",
            ),
            (
                "infinity",
                lambda r, p: (
                    r["timings"].__setitem__("receipt_preparation_seconds", float("inf")),
                    p.__setitem__("receipt_preparation_seconds", float("inf")),
                ),
                "transaction.receipt_creation",
            ),
            (
                "missing-persist",
                lambda _r, p: p.pop("receipt_persist_seconds"),
                "transaction.receipt_creation",
            ),
            (
                "missing-total",
                lambda _r, p: p.pop("total_seconds"),
                "transaction.total_apply",
            ),
        )
        for label, mutate, expected_phase in cases:
            with self.subTest(label=label):
                changed_receipt = copy.deepcopy(receipt)
                changed_process = copy.deepcopy(process_timings)
                mutate(changed_receipt, changed_process)
                records, failure = PHASE_PROFILER.native_transaction_phase_records(
                    changed_receipt,
                    changed_process,
                    tree_seconds=0.5,
                    tree_invocations=4,
                )
                self.assertEqual(failure, "transaction.native_timings")
                self.assertEqual(records[expected_phase]["status"], "failed")
                self.assertIsNone(records[expected_phase]["seconds"])
                json.dumps(records, allow_nan=False, sort_keys=True)

        records, failure = PHASE_PROFILER.native_transaction_phase_records(
            receipt,
            process_timings,
            tree_seconds=0.0,
            tree_invocations=0,
        )
        self.assertEqual(failure, "transaction.tree_state")
        self.assertEqual(records["transaction.tree_state"]["status"], "failed")

    def test_zero_file_phase_profile_uses_transaction_v3_native_timings(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", str(PHASE_SCRIPT), "--sizes", "0"],
            cwd=SOURCE_ROOT,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            env=PHASE_PROFILER.child_environment(),
            timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        schema = json.loads(PHASE_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            SOURCE_VALIDATOR.schema_issues(report, schema, "phase-profile"),
            [],
        )
        self.assertEqual(report["execution_failures"], [])
        phases = report["measurements"][0]["phases"]
        self.assertTrue(
            all(record["status"] == "measured" for record in phases.values())
        )

    def test_series_preserves_cold_and_warm_samples_and_both_p90_values(self) -> None:
        series = BENCHMARK.empty_series()
        series["samples"] = [
            sample(1, BENCHMARK.COLD_CLASSIFICATION, 99.0),
            *[
                sample(index + 2, BENCHMARK.WARM_CLASSIFICATION, float(index + 1))
                for index in range(10)
            ],
        ]
        BENCHMARK.summarize_series(series)
        self.assertEqual(series["combined_p90_seconds"], 10.0)
        self.assertEqual(series["warm_p90_seconds"], 9.0)
        self.assertEqual(len(series["samples"]), 11)
        self.assertEqual(series["samples"][0]["classification"], BENCHMARK.COLD_CLASSIFICATION)

    def test_sample_accounting_counts_every_classification(self) -> None:
        configuration = BENCHMARK.BenchmarkConfiguration(sizes=(10_000,))
        with tempfile.TemporaryDirectory() as temporary:
            report = BENCHMARK.initial_report(configuration, Path(temporary))
        sequence = 0
        for profile in BENCHMARK.PROFILES:
            samples = []
            for classification in [BENCHMARK.COLD_CLASSIFICATION] + [
                BENCHMARK.WARM_CLASSIFICATION
            ] * 10:
                sequence += 1
                samples.append(sample(sequence, classification, 0.1))
            report["scaffold_profiles"].append(
                {
                    "profile": profile,
                    "layout": "compact",
                    "samples": samples,
                    "combined_p90_seconds": 0.1,
                    "warm_p90_seconds": 0.1,
                }
            )
        preparation = []
        for _ in range(2):
            sequence += 1
            preparation.append(sample(sequence, BENCHMARK.PREPARATION_CLASSIFICATION, 0.1))
        check_samples = []
        mutation_samples = []
        for destination in (check_samples, mutation_samples):
            for classification in [BENCHMARK.COLD_CLASSIFICATION] + [
                BENCHMARK.WARM_CLASSIFICATION
            ] * 10:
                sequence += 1
                destination.append(sample(sequence, classification, 0.1))
        report["measurements"].append(
            {
                "synthetic_payload_files": 10_000,
                "preparation_samples": preparation,
                "check": {
                    "samples": check_samples,
                    "combined_p90_seconds": 0.1,
                    "warm_p90_seconds": 0.1,
                },
                "fast_mutation": {
                    "samples": mutation_samples,
                    "combined_p90_seconds": 0.1,
                    "warm_p90_seconds": 0.1,
                },
            }
        )
        BENCHMARK.update_sample_accounting(report)
        accounting = report["sample_accounting"]
        self.assertEqual(accounting["observed_samples"], 57)
        self.assertEqual(accounting["successful_samples"], 57)
        self.assertEqual(accounting["failed_samples"], 0)
        self.assertEqual(
            accounting["by_classification"],
            {
                BENCHMARK.COLD_CLASSIFICATION: 5,
                BENCHMARK.WARM_CLASSIFICATION: 50,
                BENCHMARK.PREPARATION_CLASSIFICATION: 2,
            },
        )
        self.assertIs(accounting["complete"], True)

    def test_enforcement_uses_unchanged_strict_thresholds(self) -> None:
        report = {
            "scaffold_profiles": [
                {
                    "profile": "minimal",
                    "combined_p90_seconds": BENCHMARK.SCAFFOLD_TARGET_SECONDS,
                }
            ],
            "measurements": [
                {
                    "synthetic_payload_files": 10_000,
                    "check": {
                        "combined_p90_seconds": BENCHMARK.CHECK_TARGET_SECONDS,
                        "warm_p90_seconds": BENCHMARK.CHECK_TARGET_SECONDS,
                    },
                    "fast_mutation": {
                        "combined_p90_seconds": BENCHMARK.MUTATION_TARGET_SECONDS,
                        "warm_p90_seconds": BENCHMARK.MUTATION_TARGET_SECONDS,
                    },
                }
            ],
        }
        failures = BENCHMARK.threshold_failures(report)
        self.assertEqual(len(failures), 5)
        report["scaffold_profiles"][0]["combined_p90_seconds"] -= 0.001
        for series in (report["measurements"][0]["check"], report["measurements"][0]["fast_mutation"]):
            series["combined_p90_seconds"] -= 0.001
            series["warm_p90_seconds"] -= 0.001
        self.assertEqual(BENCHMARK.threshold_failures(report), [])

    def test_command_failure_remains_in_partial_report(self) -> None:
        def failed_timed(
            _argv: list[str],
            _cwd: Path,
            *,
            classification: str,
            sequence: int,
        ) -> tuple[dict[str, object], subprocess.CompletedProcess[str]]:
            value = sample(sequence, classification, 0.25, exit_code=7)
            return value, subprocess.CompletedProcess([], 7, stdout="sensitive", stderr="detail")

        configuration = BENCHMARK.BenchmarkConfiguration(sizes=(0,), warm_samples=1)
        with mock.patch.object(BENCHMARK, "PROFILES", ("minimal",)), mock.patch.object(
            BENCHMARK, "timed", side_effect=failed_timed
        ):
            report, status = BENCHMARK.run_benchmark(configuration)
        self.assertEqual(status, 1)
        self.assertEqual(report["enforcement"]["status"], "measurement_failed")
        self.assertEqual(report["sample_accounting"]["observed_samples"], 1)
        self.assertEqual(report["sample_accounting"]["failed_samples"], 1)
        self.assertEqual(report["scaffold_profiles"][0]["samples"][0]["exit_code"], 7)
        self.assertEqual(report["execution_failures"][0]["sequence"], 1)
        encoded = json.dumps(report)
        self.assertNotIn('"sensitive"', encoded)
        self.assertNotIn('"detail"', encoded)

    def test_timed_command_forces_no_bytecode_environment(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with mock.patch.object(BENCHMARK.subprocess, "run", return_value=completed) as invoked:
            measured, result = BENCHMARK.timed(
                [sys.executable, "-B", "example.py"],
                Path.cwd(),
                classification=BENCHMARK.WARM_CLASSIFICATION,
                sequence=3,
            )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(measured["sequence"], 3)
        kwargs = invoked.call_args.kwargs
        self.assertEqual(kwargs["env"]["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertIs(kwargs["shell"], False)

    def test_main_prints_partial_report_before_failure_diagnostics(self) -> None:
        report = {
            "schema_version": BENCHMARK.SCHEMA_VERSION,
            "enforcement": {
                "enabled": False,
                "status": "measurement_failed",
                "failures": ["benchmark sample accounting is incomplete"],
            },
            "execution_failures": [
                {"stage": "scaffold_profile.minimal", "sequence": 1, "exit_code": 7}
            ],
        }
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(BENCHMARK, "parse_args", return_value=object()), mock.patch.object(
            BENCHMARK, "run_benchmark", return_value=(report, 1)
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            status = BENCHMARK.main([])
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout.getvalue())["schema_version"], BENCHMARK.SCHEMA_VERSION)
        self.assertIn("scaffold_profile.minimal", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
