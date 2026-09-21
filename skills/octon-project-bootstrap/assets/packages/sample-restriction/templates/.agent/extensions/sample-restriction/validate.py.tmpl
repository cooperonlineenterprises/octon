#!/usr/bin/env python3
"""Reference restrictions-only extension validator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> object:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)


def main() -> int:
    if sys.version_info < (3, 11):
        print("Python 3.11+ is required.", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    findings: list[dict[str, str]] = []
    try:
        config = load_json(args.config)
        if not isinstance(config, dict):
            raise ValueError("config must be an object")
        if config.get("permission_grant") is not False:
            findings.append({
                "code": "EXT-AUTHORITY",
                "severity": "error",
                "message": "extension config must remain non-authorizing"
            })
        prefixes = config.get("prohibited_path_prefixes")
        if not isinstance(prefixes, list) or not all(
            isinstance(item, str) and item for item in prefixes
        ):
            findings.append({
                "code": "EXT-CONFIG",
                "severity": "error",
                "message": "prohibited_path_prefixes must be a string array"
            })
    except (OSError, ValueError, json.JSONDecodeError) as error:
        findings.append({
            "code": "EXT-CONFIG",
            "severity": "error",
            "message": str(error)
        })
    print(json.dumps({
        "schema_version": "harness.extension-findings.v1",
        "extension_id": "sample-restriction",
        "findings": findings
    }, sort_keys=True))
    return 1 if any(item["severity"] == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
