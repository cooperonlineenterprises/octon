#!/usr/bin/env python3
"""Checkpoint commit-marker and recovery fault injection."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

import test_long_running_work as functional


class InjectedInterruption(RuntimeError):
    pass


def load_runtime(target: Path):
    path = target / ".agent/capabilities/long-running-work/long_work.py"
    spec = importlib.util.spec_from_file_location("octon_lrw_fault_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("installed runtime is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LongRunningWorkFaultTests(unittest.TestCase):
    def setUp(self) -> None:
        prior_clock = os.environ.get("OCTON_MINI_LONG_WORK_TEST_CLOCK")
        os.environ["OCTON_MINI_LONG_WORK_TEST_CLOCK"] = "1"
        self.addCleanup(
            lambda: os.environ.pop("OCTON_MINI_LONG_WORK_TEST_CLOCK", None)
            if prior_clock is None
            else os.environ.__setitem__("OCTON_MINI_LONG_WORK_TEST_CLOCK", prior_clock)
        )
        self.fixture = functional.LongRunningWorkTests("test_absent_package_refuses_with_continuation_and_no_change")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.install_and_enable()
        self.run_value = self.fixture.start()
        self.run_id = str(self.run_value["run_id"])
        self.runtime = load_runtime(self.fixture.target)

    def interrupt_on(self, phase: str):
        def hook(observed: str) -> None:
            if observed == phase:
                raise InjectedInterruption(phase)
        self.runtime.INTERRUPTION_HOOK = hook

    def pause_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            run_id=self.run_id,
            reason="synthetic fault boundary",
            observed_at=None,
        )

    def record_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            run_id=self.run_id,
            outcome="progress",
            transaction_receipt=None,
            work_completion_receipt=None,
            no_mutation=True,
            validation_ref="EVD-0001",
            result_fingerprint="a" * 64,
            failure_code=None,
            failure_detail=None,
            partial_effect=[],
            reported_tokens=None,
            reported_cost_microunits=None,
            limitation=[],
            observed_at=None,
        )

    def test_checkpoint_content_without_marker_is_orphan_and_prior_coordinate_wins(self) -> None:
        self.interrupt_on("after_checkpoint_content_write")
        with self.assertRaisesRegex(InjectedInterruption, "after_checkpoint_content_write"):
            self.runtime.pause_run(self.pause_args())
        report = self.runtime.status_report(self.run_id)
        self.assertEqual(report["last_committed_checkpoint"], "LWC-000000")
        self.assertEqual(report["active_projection_checkpoint"], "LWC-000000")
        self.assertEqual(report["orphan_checkpoint_content"], ["LWC-000001.json"])
        resumed = self.runtime.resume_report(self.run_id)
        self.assertEqual(resumed["last_committed_checkpoint"], "LWC-000000")
        self.assertTrue(resumed["retry_safe"])

    def test_marker_before_projection_is_committed_and_exactly_recoverable(self) -> None:
        self.interrupt_on("after_checkpoint_marker")
        with self.assertRaisesRegex(InjectedInterruption, "after_checkpoint_marker"):
            self.runtime.pause_run(self.pause_args())
        report = self.runtime.resume_report(self.run_id)
        self.assertEqual(report["last_committed_checkpoint"], "LWC-000001")
        self.assertTrue(any("projection differs" in item for item in report["findings"]))
        marker = self.runtime.load_json(
            self.runtime.marker_path(self.run_id, "LWC-000001")
        )
        self.runtime.INTERRUPTION_HOOK = lambda _phase: None
        recovered = self.runtime.recover_or_activate(
            argparse.Namespace(
                run_id=self.run_id,
                accept_marker_digest=marker["canonical_marker_digest"],
                observed_at=None,
            ),
            activate=False,
        )
        self.assertEqual(recovered["last_committed_checkpoint"], "LWC-000001")
        self.assertEqual(recovered["status"], "safely_paused")
        self.assertTrue(self.runtime.status_report(self.run_id)["projection_matches_committed_checkpoint"])

    def test_changed_instruction_blocks_recovery_of_committed_marker(self) -> None:
        self.interrupt_on("after_checkpoint_marker")
        with self.assertRaises(InjectedInterruption):
            self.runtime.pause_run(self.pause_args())
        agents = self.fixture.target / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8") + "\nChanged after checkpoint.\n", encoding="utf-8")
        marker = self.runtime.load_json(self.runtime.marker_path(self.run_id, "LWC-000001"))
        self.runtime.INTERRUPTION_HOOK = lambda _phase: None
        with self.assertRaisesRegex(self.runtime.LongWorkError, "instructions changed"):
            self.runtime.recover_or_activate(
                argparse.Namespace(
                    run_id=self.run_id,
                    accept_marker_digest=marker["canonical_marker_digest"],
                    observed_at=None,
                ),
                activate=False,
            )

    def test_malformed_projection_recovers_from_exact_marker_without_replay(self) -> None:
        projection = self.runtime.run_dir(self.run_id) / "run.json"
        projection.write_text('{"broken":\n', encoding="utf-8")
        report = self.runtime.resume_report(self.run_id)
        self.assertTrue(any("projection is unavailable" in item for item in report["findings"]))
        marker = self.runtime.load_json(
            self.runtime.marker_path(self.run_id, report["last_committed_checkpoint"])
        )
        recovered = self.runtime.recover_or_activate(
            argparse.Namespace(
                run_id=self.run_id,
                accept_marker_digest=marker["canonical_marker_digest"],
                observed_at=None,
            ),
            activate=False,
        )
        self.assertEqual(recovered["status"], "active")
        self.assertTrue(self.runtime.status_report(self.run_id)["projection_matches_committed_checkpoint"])

    def test_context_and_progress_interruptions_leave_committed_coordinate_unchanged(self) -> None:
        before = functional.snapshot(self.fixture.target)
        self.interrupt_on("before_context_compilation")
        with self.assertRaisesRegex(InjectedInterruption, "before_context_compilation"):
            self.runtime.compile_context("TASK-0001", 131072, 32, ["synthetic.txt"], [])
        self.assertEqual(functional.snapshot(self.fixture.target), before)
        self.runtime.INTERRUPTION_HOOK = lambda _phase: None
        manifest = self.fixture.accept_current_context(self.run_id)
        self.assertEqual(manifest["status"], "ready")
        checkpoint = self.runtime.load_run(self.run_id)[0]["last_committed_checkpoint"]
        for phase in (
            "before_project_validation",
            "during_validation",
            "after_validation_before_progress",
            "during_progress_recording",
        ):
            with self.subTest(phase=phase):
                self.interrupt_on(phase)
                with self.assertRaisesRegex(InjectedInterruption, phase):
                    self.runtime.record_iteration(self.record_args())
                self.assertEqual(
                    self.runtime.load_run(self.run_id)[0]["last_committed_checkpoint"],
                    checkpoint,
                )
        self.runtime.INTERRUPTION_HOOK = lambda _phase: None

    def test_history_bound_stops_before_checkpoint_mutation(self) -> None:
        observed = self.runtime.observed_utc()
        run = self.runtime.load_run(self.run_id)[0]
        for _index in range(99):
            self.runtime.write_history(run, "run_paused", observed, {"fixture": True})
        before_checkpoint = run["last_committed_checkpoint"]
        with self.assertRaisesRegex(self.runtime.LongWorkError, "100-entry bound"):
            self.runtime.pause_run(self.pause_args())
        self.assertEqual(
            self.runtime.load_run(self.run_id)[0]["last_committed_checkpoint"],
            before_checkpoint,
        )

    def test_initial_creation_interruptions_do_not_reassign_active_pointer(self) -> None:
        cancelled = self.runtime.cancel_run(
            argparse.Namespace(
                run_id=self.run_id,
                reason="prepare successor creation fixture",
                observed_at=None,
            )
        )
        self.assertEqual(cancelled["status"], "cancelled")
        args = argparse.Namespace(
            task_id="TASK-0001",
            limits=str(self.fixture.limits_path),
            allow_path=["synthetic.txt"],
            prohibit_path=[],
            predecessor_run=self.run_id,
            planned=False,
            observed_at=None,
        )
        existing = {path.name for path in self.runtime.RUNS_ROOT.iterdir()}
        self.interrupt_on("before_work_run_creation")
        with self.assertRaisesRegex(InjectedInterruption, "before_work_run_creation"):
            self.runtime.start_run(args)
        self.assertEqual({path.name for path in self.runtime.RUNS_ROOT.iterdir()}, existing)
        self.interrupt_on("after_run_content_before_marker")
        with self.assertRaisesRegex(InjectedInterruption, "after_run_content_before_marker"):
            self.runtime.start_run(args)
        added = [path for path in self.runtime.RUNS_ROOT.iterdir() if path.name not in existing]
        self.assertEqual(len(added), 1)
        self.assertFalse(any((added[0] / "checkpoints").glob("*.marker.json")))
        self.assertEqual(self.runtime.active_pointer()["run_id"], self.run_id)

    def test_fault_matrix_names_every_required_boundary_once(self) -> None:
        path = functional.SKILL_ROOT / "fixtures/long-running-work/fault-matrix.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        phases = [item["phase"] for item in value["cases"]]
        self.assertEqual(len(phases), len(set(phases)))
        required = {
            "before_work_run_creation", "after_run_content_before_marker",
            "before_context_compilation", "after_context_compilation",
            "before_planning", "after_planning", "during_transaction_staging",
            "after_staged_validation", "before_live_mutation",
            "after_each_live_path_mutation", "before_transaction_receipt",
            "after_transaction_receipt", "before_project_validation",
            "during_validation", "after_validation_before_progress",
            "during_progress_recording", "before_checkpoint_content_write",
            "after_checkpoint_content_write", "before_checkpoint_marker",
            "after_checkpoint_marker", "before_external_action",
            "after_external_action_before_acknowledgement",
            "during_external_read_back", "during_cancellation", "during_resume",
            "during_cleanup",
        }
        self.assertEqual(set(phases), required)

    def test_malformed_history_tail_is_preserved_and_refused(self) -> None:
        history = self.runtime.run_dir(self.run_id) / "history.jsonl"
        history.write_bytes(history.read_bytes() + b'{"broken":\n')
        before = hashlib.sha256(history.read_bytes()).hexdigest()
        with self.assertRaisesRegex(self.runtime.LongWorkError, "malformed preserved line"):
            self.runtime.read_history(self.run_id)
        self.assertEqual(hashlib.sha256(history.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
