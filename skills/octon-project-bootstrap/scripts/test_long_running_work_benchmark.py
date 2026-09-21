#!/usr/bin/env python3
"""Methodology tests for the long-running-work benchmark."""

from __future__ import annotations

import unittest

import benchmark_long_running_work as benchmark


class LongRunningWorkBenchmarkTests(unittest.TestCase):
    def test_nearest_rank_preserves_failed_or_slow_samples(self) -> None:
        values = [0.1, 0.2, 0.3, 0.4, 3.0, 0.5, 0.6, 0.7, 0.8, 0.9]
        self.assertEqual(benchmark.nearest_rank(values, 0.9), 0.9)
        self.assertEqual(benchmark.nearest_rank(values, 1.0), 3.0)

    def test_empty_percentile_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires samples"):
            benchmark.nearest_rank([], 0.9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
