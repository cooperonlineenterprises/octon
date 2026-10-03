#!/usr/bin/env python3
"""Adversarial tests for source-only architectural integration contracts."""

from __future__ import annotations

import copy
import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
MODULE_PATH = SCRIPT_DIR / "validate_source_contracts.py"
SPEC = importlib.util.spec_from_file_location("validate_source_contracts", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
CONTRACTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACTS)
ROOT = CONTRACTS.ROOT


class ArchitecturalPatternContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog, self.records = CONTRACTS.load_catalog_values(ROOT)
        self.context = CONTRACTS.load_json(
            ROOT / "patterns/fixtures/context-pack/valid/active.json"
        )
        self.unsupported_proof = CONTRACTS.load_json(
            ROOT
            / "patterns/fixtures/architecture-proof/valid/unsupported-spike.json"
        )
        self.inconclusive_proof = CONTRACTS.load_json(
            ROOT
            / "patterns/fixtures/architecture-proof/valid/inconclusive-provider.json"
        )
        self.scaffolder = CONTRACTS.load_scaffolder(ROOT)

    def catalog_errors(
        self,
        catalog: dict[str, Any] | None = None,
        records: dict[str, dict[str, Any]] | None = None,
    ) -> list[str]:
        return CONTRACTS.validate_catalog_values(
            ROOT,
            catalog if catalog is not None else copy.deepcopy(self.catalog),
            records if records is not None else copy.deepcopy(self.records),
        )

    def context_errors(
        self,
        value: dict[str, Any] | None = None,
        *,
        as_of: datetime | None = None,
        consumer: str = "agent-role:architecture-reviewer",
        resources: set[str] | None = None,
        sensitivities: set[str] | None = None,
    ) -> list[str]:
        return CONTRACTS.validate_context_pack(
            value if value is not None else copy.deepcopy(self.context),
            root=ROOT,
            as_of=as_of or datetime(2030, 1, 5, tzinfo=timezone.utc),
            intended_consumer=consumer,
            requested_resources=resources
            or {
                "project-dossier/canonical/architecture-or-outcome-model.md",
                "project-dossier/provenance/README.md",
            },
            requested_purpose="architecture_review",
            permitted_sensitivities=sensitivities or {"internal"},
        )

    def assert_has(self, errors: list[str], phrase: str) -> None:
        self.assertTrue(
            any(phrase in error for error in errors),
            f"expected {phrase!r} in: {errors}",
        )

    def test_repository_contracts_are_valid(self) -> None:
        self.assertEqual(CONTRACTS.validate_repository(ROOT), [])

    def test_catalog_rejects_duplicate_stable_id(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["allocations"][1]["id"] = catalog["allocations"][0]["id"]
        self.assert_has(self.catalog_errors(catalog=catalog), "duplicate stable ID")

    def test_catalog_rejects_stable_identity_reassignment(self) -> None:
        records = copy.deepcopy(self.records)
        record = records["patterns/records/PAT-0001-lifecycle-disposition.json"]
        record["slug"] = "different-pattern"
        self.assert_has(
            self.catalog_errors(records=records),
            "allocation identity or slug mismatch",
        )

    def test_catalog_rejects_illegal_lifecycle_transition(self) -> None:
        records = copy.deepcopy(self.records)
        record = records["patterns/records/PAT-0001-lifecycle-disposition.json"]
        record["status"] = "stable"
        record["status_history"][-1]["to_status"] = "stable"
        self.assert_has(self.catalog_errors(records=records), "illegal lifecycle transition")

    def test_catalog_recommended_requires_independent_projects(self) -> None:
        records = copy.deepcopy(self.records)
        record = records["patterns/records/PAT-0003-architecture-proof.json"]
        record["status"] = "recommended"
        record["status_history"].extend(
            [
                {
                    "from_status": "reviewed",
                    "to_status": "experimental",
                    "changed_on": "2026-08-11",
                    "decision_ref": "SRC-DEC-0005",
                    "rationale": "Synthetic transition fixture."
                },
                {
                    "from_status": "experimental",
                    "to_status": "recommended",
                    "changed_on": "2026-08-11",
                    "decision_ref": "SRC-DEC-0005",
                    "rationale": "Synthetic promotion fixture."
                }
            ]
        )
        record["status_changed_on"] = "2026-08-11"
        self.assert_has(
            self.catalog_errors(records=records),
            "lacks two independent project proofs",
        )

    def test_catalog_stable_requires_support_commitment(self) -> None:
        records = copy.deepcopy(self.records)
        record = records["patterns/records/PAT-0003-architecture-proof.json"]
        record["status"] = "stable"
        record["status_history"].extend(
            [
                {
                    "from_status": "reviewed",
                    "to_status": "experimental",
                    "changed_on": "2026-08-11",
                    "decision_ref": "SRC-DEC-0005",
                    "rationale": "Synthetic transition fixture."
                },
                {
                    "from_status": "experimental",
                    "to_status": "recommended",
                    "changed_on": "2026-08-11",
                    "decision_ref": "SRC-DEC-0005",
                    "rationale": "Synthetic transition fixture."
                },
                {
                    "from_status": "recommended",
                    "to_status": "stable",
                    "changed_on": "2026-08-11",
                    "decision_ref": "SRC-DEC-0005",
                    "rationale": "Synthetic stability fixture."
                }
            ]
        )
        record["status_changed_on"] = "2026-08-11"
        self.assert_has(
            self.catalog_errors(records=records), "lacks support commitment"
        )

    def test_catalog_never_allows_automatic_migration(self) -> None:
        records = copy.deepcopy(self.records)
        record = records["patterns/records/PAT-0003-architecture-proof.json"]
        record["migration"]["automatic"] = True
        self.assert_has(self.catalog_errors(records=records), "must equal False")

    def test_catalog_successor_must_resolve(self) -> None:
        records = copy.deepcopy(self.records)
        record = records["patterns/records/PAT-0001-lifecycle-disposition.json"]
        record["status"] = "deprecated"
        record["successor"] = "PAT-9999"
        record["deprecation_reason"] = "Synthetic deprecation fixture."
        record["status_history"].append(
            {
                "from_status": "reviewed",
                "to_status": "deprecated",
                "changed_on": "2026-08-11",
                "decision_ref": "SRC-DEC-0006",
                "rationale": "Synthetic deprecation fixture."
            }
        )
        self.assert_has(self.catalog_errors(records=records), "successor does not resolve")

    def test_catalog_assets_never_enter_generated_inventories(self) -> None:
        self.assertEqual(CONTRACTS.validate_generated_inventory_boundaries(ROOT), [])

    def test_generation_policy_enforces_every_profile_inventory(self) -> None:
        policy = self.scaffolder.load_generation_policy()
        self.assertEqual(
            policy["schema_version"],
            "octon.source.profile-manifest.v4",
        )
        self.assertEqual(policy["default_disposition"], "source_only")
        self.assertTrue(
            all(
                rule["inventory_paths"]
                for rule in policy["rules"]
                if rule["disposition"] in {"generated", "profile_optional"}
            )
        )
        for profile in self.scaffolder.profile_layers(policy):
            self.scaffolder.validate_generation_boundary(
                profile,
                self.scaffolder.collect_templates(profile),
                self.scaffolder.schema_outputs(profile),
                policy,
            )

    def test_unreviewed_input_degrades_but_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="octon-mini-policy-degraded-"
        ) as temporary:
            source_root = Path(temporary)
            approved = source_root / "approved.md.tmpl"
            approved.write_text("approved\n", encoding="utf-8")
            unreviewed = source_root / "unreviewed.md.tmpl"
            unreviewed.write_text("unreviewed\n", encoding="utf-8")
            paths = [approved.name]
            rule = {
                "id": "synthetic-degraded",
                "source": "skill:synthetic",
                "match": "recursive_suffix",
                "suffix": ".tmpl",
                "disposition": "generated",
                "profiles": ["minimal"],
                "inventory_paths": paths,
                "inventory_count": 1,
                "inventory_paths_sha256": (
                    self.scaffolder.generation_inventory_digest(paths)
                ),
                "output": {"root": ".", "strip_suffix": ".tmpl"},
                "reason": "Synthetic capability degradation fixture.",
            }
            policy = {"rules": [rule], "forbidden_outputs": []}
            with mock.patch.object(
                self.scaffolder,
                "policy_source_path",
                return_value=source_root,
            ):
                report = self.scaffolder.generation_policy_diagnostics(
                    policy, ("minimal",)
                )
                templates, copied = self.scaffolder.resolve_generation_inputs(
                    "minimal", policy
                )
            self.assertEqual(
                self.scaffolder.generation_profile_mode(report, "minimal"),
                "degraded",
            )
            self.assertEqual(set(templates), {Path("approved.md")})
            self.assertEqual(copied, {})
            self.assertNotIn(unreviewed, templates.values())
            self.assertEqual(
                report["findings"][0]["failure_class"],
                "information_degradation",
            )
            self.assertEqual(
                report["findings"][0]["effect"],
                "unreviewed paths are ignored and never generated",
            )
            candidate = report["findings"][0]["candidate_policy_update"]
            self.assertEqual(candidate["status"], "review_required_not_approved")
            self.assertEqual(candidate["inventory_count"], 2)
            self.assertEqual(
                candidate["inventory_paths"],
                ["approved.md.tmpl", "unreviewed.md.tmpl"],
            )

    def test_missing_profile_dependency_does_not_block_unrelated_profile(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="octon-mini-policy-isolation-"
        ) as temporary:
            source_root = Path(temporary)
            minimal_path = source_root / "approved-minimal.md.tmpl"
            minimal_path.write_text("minimal\n", encoding="utf-8")
            minimal_paths = [minimal_path.name]
            minimal_rule = {
                "id": "synthetic-minimal-dependency",
                "source": "skill:synthetic-minimal",
                "match": "recursive_suffix",
                "suffix": ".tmpl",
                "disposition": "generated",
                "profiles": ["minimal"],
                "inventory_paths": minimal_paths,
                "inventory_count": 1,
                "inventory_paths_sha256": (
                    self.scaffolder.generation_inventory_digest(minimal_paths)
                ),
                "output": {"root": ".", "strip_suffix": ".tmpl"},
                "reason": "Synthetic available Minimal dependency.",
            }
            paths = ["missing.md.tmpl"]
            rule = {
                "id": "synthetic-high-dependency",
                "source": "skill:synthetic",
                "match": "recursive_suffix",
                "suffix": ".tmpl",
                "disposition": "generated",
                "profiles": ["high-assurance"],
                "inventory_paths": paths,
                "inventory_count": 1,
                "inventory_paths_sha256": (
                    self.scaffolder.generation_inventory_digest(paths)
                ),
                "output": {"root": ".", "strip_suffix": ".tmpl"},
                "reason": "Synthetic profile-isolation fixture.",
            }
            policy = {
                "rules": [minimal_rule, rule],
                "forbidden_outputs": [],
            }
            with mock.patch.object(
                self.scaffolder,
                "policy_source_path",
                return_value=source_root,
            ):
                report = self.scaffolder.generation_policy_diagnostics(
                    policy, ("minimal", "high-assurance")
                )
            self.assertEqual(
                self.scaffolder.generation_profile_mode(report, "minimal"),
                "normal",
            )
            self.assertEqual(
                self.scaffolder.generation_profile_mode(
                    report, "high-assurance"
                ),
                "blocked",
            )
            self.assertEqual(
                report["findings"][0]["failure_class"],
                "dependency_degradation",
            )

    def test_generation_policy_rejects_source_only_input(self) -> None:
        policy = self.scaffolder.load_generation_policy()
        templates = self.scaffolder.collect_templates("minimal")
        templates[Path("patterns/catalog.json")] = ROOT / "patterns/catalog.json"
        with self.assertRaisesRegex(ValueError, "source-only input is prohibited"):
            self.scaffolder.validate_generation_boundary(
                "minimal",
                templates,
                self.scaffolder.schema_outputs("minimal"),
                policy,
            )

    def test_generation_policy_rejects_forbidden_output_name(self) -> None:
        policy = self.scaffolder.load_generation_policy()
        templates = self.scaffolder.collect_templates("minimal")
        templates[Path("ARCHITECTURE_DECISIONS.md")] = next(iter(templates.values()))
        with self.assertRaisesRegex(ValueError, "forbidden generated output"):
            self.scaffolder.validate_generation_boundary(
                "minimal",
                templates,
                self.scaffolder.schema_outputs("minimal"),
                policy,
            )

    def test_generation_policy_rejects_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="octon-mini-policy-symlink-"
        ) as temporary:
            temp_root = Path(temporary)
            approved = temp_root / "approved"
            approved.mkdir()
            outside = temp_root / "source-only.json"
            outside.write_text("{}\n", encoding="utf-8")
            escaped = approved / "escaped.tmpl"
            try:
                escaped.symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symlink fixture unavailable: {error}")
            rule = {
                "id": "synthetic-symlink",
                "source": "skill:synthetic",
                "match": "recursive_suffix",
                "suffix": ".tmpl",
                "inventory_paths": ["escaped.tmpl"],
            }
            with mock.patch.object(
                self.scaffolder,
                "policy_source_path",
                return_value=approved,
            ):
                with self.assertRaisesRegex(ValueError, "may not be a symlink"):
                    self.scaffolder.generation_rule_inventory(rule)

    def test_generation_policy_rejects_output_collision(self) -> None:
        policy = self.scaffolder.load_generation_policy()
        templates = self.scaffolder.collect_templates("minimal")
        schemas = self.scaffolder.schema_outputs("minimal")
        schema_destination = next(iter(schemas))
        templates[schema_destination] = next(iter(templates.values()))
        with self.assertRaisesRegex(ValueError, "template/schema output collision"):
            self.scaffolder.validate_generation_boundary(
                "minimal",
                templates,
                schemas,
                policy,
            )

    def test_generation_policy_rejects_unsafe_output_path(self) -> None:
        policy = self.scaffolder.load_generation_policy()
        templates = self.scaffolder.collect_templates("minimal")
        source = templates.pop(next(iter(templates)))
        templates[Path("../escaped.md")] = source
        with self.assertRaisesRegex(ValueError, "unsafe path"):
            self.scaffolder.validate_generation_boundary(
                "minimal",
                templates,
                self.scaffolder.schema_outputs("minimal"),
                policy,
            )

    def test_staged_inventory_rejects_unexpected_file(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="octon-mini-stage-inventory-"
        ) as temporary:
            stage = Path(temporary)
            (stage / "unexpected.md").write_text("unexpected\n", encoding="utf-8")
            (stage / "unexpected-directory").mkdir()
            errors = self.scaffolder.staged_inventory_issues(stage, set())
            self.assertTrue(
                any("unexpected generated file: unexpected.md" in item for item in errors),
                errors,
            )
            self.assertTrue(
                any(
                    "unexpected generated directory: unexpected-directory" in item
                    for item in errors
                ),
                errors,
            )

    def test_semantic_crosswalk_rejects_authority_laundering(self) -> None:
        value = CONTRACTS.load_json(
            ROOT / "shared/source-contracts/information-state-semantics.json"
        )
        inferred = next(item for item in value["roles"] if item["name"] == "inferred")
        inferred["information_effect"] = "declared_scope_authority_only"
        self.assert_has(
            CONTRACTS.validate_information_state_value(ROOT, value),
            "launders information authority",
        )

    def test_identity_transition_preserves_historical_and_source_only_boundaries(self) -> None:
        migration = (ROOT / "migrations/3.1.0-to-4.0.0.md").read_text(
            encoding="utf-8"
        )
        normalized_migration = " ".join(migration.split())
        product_config = CONTRACTS.load_json(ROOT / "octon.json")
        scaffolder = CONTRACTS.load_scaffolder(ROOT)
        self.assertEqual(
            (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
            "5.0.0",
        )
        self.assertEqual(
            product_config["modules"]["harness"]["kernel_version"], "4.2.0"
        )
        self.assertEqual(scaffolder.KERNEL_VERSION, "4.2.0")
        self.assertNotIn(
            ".agent/schemas/context-pack-manifest.schema.json",
            {path.as_posix() for path in scaffolder.schema_outputs("minimal")},
        )
        self.assertNotIn(
            ".agent/schemas/context-pack-manifest.schema.json",
            {path.as_posix() for path in scaffolder.schema_outputs("standard")},
        )
        self.assertNotIn(
            ".agent/schemas/context-pack-manifest.schema.json",
            {path.as_posix() for path in scaffolder.schema_outputs("high-assurance")},
        )
        self.assertIn(
            "Nothing in this guide updates a project automatically",
            normalized_migration,
        )
        self.assertIn(
            "Existing records are never silently converted",
            normalized_migration,
        )

    def test_context_pack_accepts_exact_active_manifest(self) -> None:
        self.assertEqual(self.context_errors(), [])

    def test_context_pack_rejects_expiry_and_revalidation(self) -> None:
        errors = self.context_errors(
            as_of=datetime(2030, 1, 21, tzinfo=timezone.utc)
        )
        self.assert_has(errors, "expired")
        self.assert_has(errors, "requires revalidation")

    def test_context_pack_rejects_revocation(self) -> None:
        value = copy.deepcopy(self.context)
        value["status"] = "revoked"
        value["revocation"] = {
            "status": "revoked",
            "revoked_at": "2030-01-04T10:00:00Z",
            "reason": "Synthetic revocation fixture.",
            "successor": None,
        }
        self.assert_has(self.context_errors(value), "pack is revoked")

    def test_context_pack_rejects_wrong_recipient(self) -> None:
        self.assert_has(
            self.context_errors(consumer="agent-role:different-consumer"),
            "intended consumer does not match",
        )

    def test_context_pack_rejects_excessive_scope(self) -> None:
        self.assert_has(
            self.context_errors(resources={"project-dossier/history/secret.md"}),
            "requested resources exceed scope",
        )

    def test_context_pack_rejects_sensitivity_mismatch(self) -> None:
        self.assert_has(
            self.context_errors(sensitivities={"public"}),
            "sensitivity is not permitted",
        )

    def test_context_pack_rejects_invalid_retention(self) -> None:
        value = copy.deepcopy(self.context)
        value["retention"]["retain_until"] = "2030-01-06T10:00:00Z"
        self.assert_has(self.context_errors(value), "retention ends before valid use")

    def test_context_pack_rejects_inexact_source(self) -> None:
        value = copy.deepcopy(self.context)
        value["sources"][0]["exact_version_or_digest"] = "latest"
        errors = self.context_errors(value)
        self.assert_has(errors, "lacks an exact version")

    def test_context_pack_cannot_grant_permission(self) -> None:
        value = copy.deepcopy(self.context)
        value["permission_grant"] = True
        self.assert_has(self.context_errors(value), "must equal False")

    def test_architecture_proof_accepts_failed_and_inconclusive_results(self) -> None:
        self.assertEqual(
            CONTRACTS.validate_architecture_proof(self.unsupported_proof, root=ROOT),
            [],
        )
        self.assertEqual(
            CONTRACTS.validate_architecture_proof(self.inconclusive_proof, root=ROOT),
            [],
        )

    def test_architecture_proof_requires_stop_criteria(self) -> None:
        value = copy.deepcopy(self.unsupported_proof)
        value["stop_criteria"] = []
        self.assert_has(
            CONTRACTS.validate_architecture_proof(value, root=ROOT),
            "completed stop_criteria is unresolved",
        )

    def test_architecture_proof_requires_exact_subject(self) -> None:
        value = copy.deepcopy(self.unsupported_proof)
        value["subject"]["version_or_revision"] = "latest"
        self.assert_has(
            CONTRACTS.validate_architecture_proof(value, root=ROOT),
            "subject version_or_revision is inexact",
        )

    def test_architecture_proof_requires_completed_cleanup(self) -> None:
        value = copy.deepcopy(self.unsupported_proof)
        value["cleanup_or_rollback"]["status"] = "planned"
        self.assert_has(
            CONTRACTS.validate_architecture_proof(value, root=ROOT),
            "cleanup or rollback is incomplete",
        )

    def test_architecture_proof_requires_limitations_and_non_proof_claims(self) -> None:
        value = copy.deepcopy(self.unsupported_proof)
        value["limitations"] = []
        value["non_proven_implications"] = []
        errors = CONTRACTS.validate_architecture_proof(value, root=ROOT)
        self.assert_has(errors, "completed limitations is missing")
        self.assert_has(errors, "completed non_proven_implications is missing")

    def test_architecture_proof_cannot_infer_production_readiness(self) -> None:
        value = copy.deepcopy(self.unsupported_proof)
        value["production_readiness_inference"] = True
        self.assert_has(
            CONTRACTS.validate_architecture_proof(value, root=ROOT),
            "must equal False",
        )


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False)
    if result.result.wasSuccessful():
        print("PASS: architectural pattern integration fixtures")
    raise SystemExit(0 if result.result.wasSuccessful() else 1)
