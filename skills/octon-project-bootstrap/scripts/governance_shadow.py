#!/usr/bin/env python3
"""Read-only, source-only intent/delegation coverage. Never authorizes execution."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "octon_source_contract_validation", SCRIPT_DIR / "validate_source_contracts.py"
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("source contract validator is unavailable")
CONTRACTS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(CONTRACTS)
ROOT = CONTRACTS.ROOT
SCHEMA_PATH = "shared/source-contracts/governance-foundation-v2.schema.json"
MAX_BYTES = 1024 * 1024
SCOPE_SETS = (
    "resources", "operations", "decision_classes", "environments",
    "data_classes", "destinations", "credential_classes",
)
BUDGET_UNITS = ("actions", "compute_units")
LIMITATIONS = [
    "Supplied intent, work, grants, policy, evidence and usage are hypothetical snapshots, not authenticated authority.",
    "Coverage is not permission; no grant, decision, task, reservation, lease or effect is created or changed.",
    "A qualified protected loader, current host/provider checks and atomic reservation owner remain required for live use.",
    "This result is not a legacy delivery coverage projection and cannot activate or renew a grant.",
]


class GovernanceError(ValueError):
    """Invalid source contract or bounded shadow input."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def record_digest(value: dict[str, Any]) -> str:
    return digest({key: item for key, item in value.items() if key != "digest"})


def intent_reference(intent: dict[str, Any]) -> dict[str, Any]:
    return {key: intent[key] for key in ("id", "revision", "digest")}


def delegation_reference(grant: dict[str, Any]) -> dict[str, str]:
    return {key: grant[key] for key in ("id", "digest")}


def aware(value: str) -> datetime:
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise GovernanceError("invalid timestamp") from error
    if stamp.tzinfo is None:
        raise GovernanceError("timestamps require a timezone")
    return stamp.astimezone(timezone.utc)


def schema(root: Path = ROOT) -> dict[str, Any]:
    value = CONTRACTS.load_json(root / SCHEMA_PATH)
    issues = CONTRACTS.lint_schema(value)
    if issues:
        raise GovernanceError("source schema is invalid: " + "; ".join(issues))
    return value


def validate_shape(value: Any, definition: str, contract: dict[str, Any]) -> None:
    errors = CONTRACTS.validate_schema(
        value, {"$ref": "#/$defs/" + definition}, root_schema=contract
    )
    if errors:
        # Existing schema diagnostics can contain supplied values. Keep those
        # out of CLI logs; the named source definition is the inspection route.
        raise GovernanceError("contract mismatch in " + definition + "; inspect the source schema")


def load_input(path: Path) -> Any:
    if not stat.S_ISREG(path.lstat().st_mode):
        raise GovernanceError("input must be a regular file, not a symlink or special file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise GovernanceError("input must be a regular file")
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise GovernanceError("input exceeds the one-MiB limit")
    try:
        value = json.loads(raw.decode("utf-8"),
                           object_pairs_hook=CONTRACTS.strict_object,
                           parse_constant=CONTRACTS.reject_json_constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise GovernanceError("input is not bounded strict UTF-8 JSON") from error
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > 20000 or depth > 24:
            raise GovernanceError("input exceeds structural limits")
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
    return value


def evaluate(value: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    """Evaluate prospective coverage over declared facts, without trusting them."""
    if len(canonical_bytes(value)) > MAX_BYTES:
        raise GovernanceError("input exceeds the one-MiB limit")
    contract = schema(root)
    validate_shape(value, "input", contract)
    at = aware(value["evaluation_time"])
    intent, work, grants, action, controls = (
        value["intent"], value["work_binding"], value["delegations"],
        value["action"], value["controls"],
    )
    refused: set[str] = set()
    unknown: set[str] = set()

    for label, record in [("intent", intent), ("action", action), ("controls", controls)]:
        if record["digest"] != record_digest(record):
            refused.add(label + "_digest_mismatch")
    intent_ref = intent_reference(intent)
    if intent["supersedes"] is not None:
        prior = intent["supersedes"]
        if prior["id"] != intent["id"] or prior["revision"] >= intent["revision"]:
            refused.add("invalid_intent_supersession")
    if work["intent_ref"] != intent_ref or action["intent_ref"] != intent_ref:
        refused.add("intent_lineage_mismatch")
    if (action["work_ref"] != work["record_ref"] or
            action["work_contract_digest"] != work["contract_digest"]):
        refused.add("work_binding_mismatch")
    if not set(action["resources"]) <= set(work["resources"]):
        refused.add("action_exceeds_work_scope")
    if action["changes_sovereign_boundary"]:
        refused.add("sovereign_change_requires_principal_channel")
    if action["project_id"] != intent["project_id"] or controls["project_id"] != intent["project_id"]:
        refused.add("project_identity_mismatch")
    if not aware(controls["observed_at"]) <= at < aware(controls["fresh_until"]):
        unknown.add("control_snapshot_stale_or_future")
    if action["policy_digest"] != controls["policy_digest"]:
        refused.add("policy_digest_mismatch")
    if action["expected_authority_epoch"] != controls["authority_epoch"]:
        refused.add("authority_epoch_mismatch")
    if action["expected_state_digest"] != controls["state_digest"]:
        refused.add("expected_state_mismatch")
    if controls["emergency_stop"]:
        refused.add("emergency_stop")

    ids = [grant["id"] for grant in grants]
    if len(set(ids)) != len(ids):
        refused.add("duplicate_delegation_identity")
    required = set(work["required_obligations"]) | set(action["required_obligations"]) | set(controls["required_obligations"])
    reserved = set(controls["reserved_decision_classes"])
    for index, grant in enumerate(grants):
        if grant["digest"] != record_digest(grant):
            refused.add("delegation_digest_mismatch")
        if grant["project_id"] != intent["project_id"] or grant["intent_ref"] != intent_ref:
            refused.add("delegation_intent_or_project_mismatch")
        if grant["policy_ref"] != controls["policy_ref"]:
            refused.add("delegation_policy_identity_mismatch")
        if grant["authority_controls_ref"] != controls["authority_controls_ref"]:
            refused.add("authority_control_source_mismatch")
        if grant["compute_unit_ref"] != action["compute_unit_ref"]:
            refused.add("budget_unit_mismatch")
        start, end = aware(grant["valid_from"]), aware(grant["valid_until"])
        if not start < end or not start <= at < end:
            refused.add("delegation_not_current")
        if grant["id"] in controls["revoked_delegation_ids"]:
            refused.add("delegation_revoked")
        required.update(grant["required_obligations"])
        reserved.update(grant["reserved_decision_classes"])
        if any(grant["per_run_limits"][unit] > grant["period_limits"][unit] for unit in BUDGET_UNITS):
            refused.add("invalid_per_run_limit")
        if index == 0:
            if grant["parent_ref"] is not None or grant["issuer_ref"] != intent["principal_ref"]:
                refused.add("root_delegation_binding_mismatch")
        else:
            parent = grants[index - 1]
            if grant["parent_ref"] != delegation_reference(parent) or grant["issuer_ref"] != parent["subject_ref"]:
                refused.add("delegation_parent_or_issuer_mismatch")
            if any(not set(grant["scope"][key]) <= set(parent["scope"][key]) for key in SCOPE_SETS):
                refused.add("child_scope_widening")
            if start < aware(parent["valid_from"]) or end > aware(parent["valid_until"]):
                refused.add("child_validity_widening")
            if (parent["remaining_delegation_depth"] == 0 or
                    grant["remaining_delegation_depth"] >= parent["remaining_delegation_depth"]):
                refused.add("subdelegation_not_covered")
            if grant["concurrency_limit"] > parent["concurrency_limit"] or any(
                grant[limit][unit] > parent[limit][unit]
                for limit in ("period_limits", "per_run_limits") for unit in BUDGET_UNITS
            ):
                refused.add("child_limit_widening")
            if grant["compute_unit_ref"] != parent["compute_unit_ref"]:
                refused.add("child_budget_unit_change")
            if not set(parent["required_obligations"]) <= set(grant["required_obligations"]):
                refused.add("child_obligation_weakening")
            if not set(parent["reserved_decision_classes"]) <= set(grant["reserved_decision_classes"]):
                refused.add("child_reservation_weakening")

    if action["actor_ref"] != grants[-1]["subject_ref"]:
        refused.add("actor_not_delegated_subject")
    if action["decision_class"] in reserved:
        refused.add("reserved_decision_class")
    requested = {
        "resources": set(action["resources"]), "operations": {action["operation"]},
        "decision_classes": {action["decision_class"]},
        "environments": {action["environment"]}, "data_classes": {action["data_class"]},
        "destinations": set(action["destinations"]),
        "credential_classes": set(action["credential_classes"]),
    }
    for scope in [grant["scope"] for grant in grants] + [controls["policy_scope"]]:
        for key, wanted in requested.items():
            if not wanted <= set(scope[key]):
                refused.add("uncovered_" + key)

    budgets = controls["budget_snapshots"]
    if len({item["delegation_ref"]["id"] for item in budgets}) != len(budgets):
        refused.add("duplicate_budget_snapshot")
    coherent_accounting = controls["accounting_observation"] == "coherent_at_observed_at"
    if not coherent_accounting:
        unknown.add("accounting_observation_unknown")
    exact_budgets: list[dict[str, Any] | None] = []
    comparable_periods: list[tuple[datetime, datetime] | None] = []
    for grant in grants:
        matches = [item for item in budgets if item["delegation_ref"] == delegation_reference(grant)]
        if len(matches) != 1:
            unknown.add("missing_exact_delegation_budget")
            exact_budgets.append(None)
            comparable_periods.append(None)
            continue
        budget = matches[0]
        if budget["run_ref"] != action["run_ref"]:
            unknown.add("run_budget_binding_mismatch")
            exact_budgets.append(None)
            comparable_periods.append(None)
            continue
        exact_budgets.append(budget)
        period = budget["period_accounting"]
        period_interval = None
        if period["start"] is None or period["end"] is None or period["includes_descendants"] is not True:
            unknown.add("period_accounting_unknown_or_excludes_descendants")
        else:
            start, end = aware(period["start"]), aware(period["end"])
            if start >= end:
                refused.add("invalid_period_accounting_interval")
            elif not start <= aware(controls["observed_at"]) <= at < end:
                unknown.add("period_accounting_observation_not_current")
            else:
                period_interval = (start, end)
        comparable_periods.append(period_interval)
        if budget["run_accounting"] != "cumulative_including_descendants":
            unknown.add("run_accounting_unknown")
        for unit in BUDGET_UNITS:
            cost = action["proposed_usage"][unit]
            committed, outstanding = budget["committed"][unit], budget["reserved"][unit]
            run_committed, run_reserved = budget["run_committed"][unit], budget["run_reserved"][unit]
            if run_committed is None or run_reserved is None:
                unknown.add("run_budget_usage_unknown")
            elif run_committed + run_reserved + cost > grant["per_run_limits"][unit]:
                refused.add("per_run_limit_exceeded")
            elif action["starts_run"] and (run_committed or run_reserved):
                refused.add("new_run_already_has_usage")
            if committed is None or outstanding is None:
                unknown.add("budget_usage_unknown")
            elif committed + outstanding + cost > grant["period_limits"][unit]:
                refused.add("shared_period_limit_exceeded")
            if ((run_committed is not None and committed is not None and run_committed > committed) or
                    (run_reserved is not None and outstanding is not None and run_reserved > outstanding)):
                refused.add("inconsistent_run_and_period_usage")
        active = budget["active_runs"]
        membership = budget["run_admission_state"]
        if membership == "unknown":
            unknown.add("run_membership_unknown")
        elif membership == "ended":
            refused.add("run_identity_ended")
        elif membership == "active":
            if action["starts_run"]:
                refused.add("run_already_admitted")
            if active is not None and active < 1:
                refused.add("active_run_membership_contradiction")
        else:  # Explicitly not_admitted; a continuing action cannot reserve retroactively.
            if not action["starts_run"]:
                refused.add("continuation_run_not_active")
            for unit in BUDGET_UNITS:
                if any(budget[field][unit] not in (None, 0) for field in ("run_committed", "run_reserved")):
                    refused.add("unadmitted_run_has_usage")
        if active is None:
            unknown.add("active_run_count_unknown")
        elif active + int(action["starts_run"] and membership == "not_admitted") > grant["concurrency_limit"]:
            refused.add("concurrency_limit_exceeded")

    # These are comparisons of the same observations, not additional charges.
    # Never sum chain levels: an ancestor may include the descendant's action.
    if coherent_accounting:
        for index in range(1, len(grants)):
            parent, child = exact_budgets[index - 1], exact_budgets[index]
            if parent is None or child is None:
                continue
            fields = []
            if parent["run_accounting"] == child["run_accounting"] == "cumulative_including_descendants":
                fields.extend(("run_committed", "run_reserved"))
            if comparable_periods[index - 1] is not None and comparable_periods[index - 1] == comparable_periods[index]:
                fields.extend(("committed", "reserved"))
            else:
                unknown.add("period_accounting_not_comparable")
            for field in fields:
                for unit in BUDGET_UNITS:
                    ancestor, descendant = parent[field][unit], child[field][unit]
                    if ancestor is None or descendant is None:
                        unknown.add("ancestor_" + field + "_usage_unknown")
                    elif ancestor < descendant:
                        refused.add("ancestor_" + field + "_underaccounted")

    observations = controls["obligation_results"]
    if len({item["id"] for item in observations}) != len(observations):
        refused.add("duplicate_obligation_observation")
    human_required = set(controls["qualified_human_obligations"])
    required.update(human_required)
    for obligation in required:
        matches = [item for item in observations if item["id"] == obligation]
        if len(matches) != 1:
            unknown.add("obligation_evidence_missing")
            continue
        observation = matches[0]
        if observation["action_digest"] != action["digest"]:
            unknown.add("obligation_action_binding_mismatch")
            continue
        if not aware(observation["observed_at"]) <= at < aware(observation["fresh_until"]):
            unknown.add("obligation_evidence_stale_or_future")
            continue
        if observation["outcome"] == "failed":
            refused.add("mandatory_obligation_failed")
        elif observation["outcome"] == "unknown" or observation["evidence_ref"] is None:
            unknown.add("obligation_evidence_unknown")
        elif obligation in human_required and observation["actor_kind"] != "qualified_human":
            refused.add("qualified_human_obligation_not_satisfied")

    result = {
        "schema_version": "octon.governance-shadow-result.v2",
        "information_role": "derived_non_authorizing_coverage",
        "coverage": "uncovered" if refused else "indeterminate" if unknown else "covered",
        "permission_grant": False, "execution_authorized": False, "authority_effect": "none",
        "authority_authentication": "not_performed", "reservations_created": False,
        "evaluation_time": value["evaluation_time"], "input_digest": digest(value),
        "action_digest": action["digest"], "intent_ref": intent_ref,
        "delegation_refs": [delegation_reference(item) for item in grants],
        "policy_digest": controls["policy_digest"], "control_snapshot_digest": controls["digest"],
        "authority_controls_ref": controls["authority_controls_ref"],
        "authority_epoch": controls["authority_epoch"],
        "reasons": sorted(refused | unknown), "limitations": LIMITATIONS.copy(),
    }
    result["result_digest"] = digest(result)
    validate_shape(result, "result", contract)
    return result


def validate_contract_source(root: Path = ROOT) -> list[str]:
    """Source gate; fixtures are examples, never installed authority."""
    try:
        contract = schema(root)
        metadata = CONTRACTS.load_json(root / "octon.json")
        expected = {
            "status": "source_only_shadow",
            "schema": SCHEMA_PATH,
            "implementation": "skills/octon-project-bootstrap/scripts/governance_shadow.py",
            "qualification": "skills/octon-project-bootstrap/scripts/test_governance_shadow.py",
            "generated": False,
            "runtime_authorization": False,
        }
        governance = metadata.get("source_governance") if isinstance(metadata, dict) else None
        if not isinstance(governance, dict) or governance.get("intent_delegation_foundation") != expected:
            return ["governance foundation registration or non-authority boundary differs"]
        fixture = root / "skills/octon-project-bootstrap/fixtures/governance-shadow/covered-v2.json"
        if not fixture.is_file():
            fixture = SCRIPT_DIR.parent / "fixtures/governance-shadow/covered-v2.json"
        value = load_input(fixture)
        result = evaluate(value, root=root)
        if result["coverage"] != "covered" or result["execution_authorized"] is not False:
            return ["governance shadow fixture does not produce non-authorizing coverage"]
        if contract["$defs"]["result"]["properties"]["permission_grant"] != {"const": False}:
            return ["governance shadow result must remain non-authorizing"]
        return []
    except (OSError, ValueError, KeyError) as error:
        return ["governance foundation: " + str(error)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Bounded hypothetical snapshot; references are never fetched")
    args = parser.parse_args()
    try:
        result = evaluate(load_input(args.input))
    except (OSError, ValueError, RecursionError) as error:
        print(json.dumps({"schema_version": "octon.governance-shadow-error.v1",
                          "permission_grant": False, "execution_authorized": False,
                          "error": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
