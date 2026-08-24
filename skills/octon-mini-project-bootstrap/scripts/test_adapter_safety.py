#!/usr/bin/env python3
"""Validate the shared inert adapter-safety conformance corpus."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/adapter-safety/cases.json"
TOOLS = ROOT / "assets/templates/core/.agent/tools.json.tmpl"


class AdapterSafetyTests(unittest.TestCase):
    def test_every_case_is_unique_inert_and_fail_closed(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertFalse(value["permission_grant"])
        cases = value["cases"]
        self.assertEqual(len(cases), 30)
        self.assertEqual(len({item["id"] for item in cases}), len(cases))
        self.assertEqual(len({item["class"] for item in cases}), len(cases))
        self.assertTrue(all(item["expected"] in {"deny", "block", "unsupported"} for item in cases))
        serialized = json.dumps(value)
        self.assertNotIn("http://", serialized)
        self.assertNotIn("https://", serialized)
        self.assertNotIn("SECRET=", serialized)

    def test_operation_catalog_denies_unknown_operations(self) -> None:
        tools = json.loads(TOOLS.read_text(encoding="utf-8"))
        self.assertFalse(tools["permission_grant"])
        self.assertTrue(tools["declarative_only"])
        self.assertEqual(tools["tools"]["git"]["unknown_operations"], "deny")
        self.assertEqual(tools["tools"]["hosted_change"]["unknown_operations"], "deny")
        hosted = {item["id"]: item for item in tools["tools"]["hosted_change"]["operations"]}
        for operation in ("observe_workflow_runs", "dispatch_workflow", "observe_source_release", "create_source_release"):
            self.assertEqual(hosted[operation]["authority_class"], "separate_release_authorization")
            self.assertFalse(hosted[operation]["normal_workflow"])
        self.assertNotIn("purchase", hosted)
        self.assertNotIn("deploy", hosted)


if __name__ == "__main__":
    unittest.main(verbosity=2)
