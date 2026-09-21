#!/usr/bin/env python3
"""Methodology tests for the autonomous-delivery benchmark."""

from __future__ import annotations

import unittest

import benchmark_autonomous_delivery as benchmark


class AutonomousDeliveryBenchmarkTests(unittest.TestCase):
    def test_nearest_rank_percentile_is_deterministic(self) -> None:
        self.assertEqual(benchmark.percentile_nearest_rank([0.1, 0.3, 0.2, 0.4, 0.5], 0.90), 0.5)

    def test_small_benchmark_covers_every_surface_and_sample(self) -> None:
        report = benchmark.benchmark(25, 1, 2, 2.0)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(set(report["measurements"]), {"status", "context", "activation_preview", "resume", "explain"})
        for measurement in report["measurements"].values():
            self.assertEqual(len(measurement["cold_seconds"]), 1)
            self.assertEqual(len(measurement["warm_seconds"]), 2)
            self.assertTrue(measurement["threshold_pass"])
        self.assertTrue(report["storage"]["informational"])
        self.assertEqual(report["storage"]["projected_100_transition_bytes"], report["storage"]["sample_transition_bytes"] * 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
