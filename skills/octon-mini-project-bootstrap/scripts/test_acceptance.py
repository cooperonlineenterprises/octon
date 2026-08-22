#!/usr/bin/env python3
"""End-to-end and adversarial acceptance suite for Octon Mini."""

from __future__ import annotations

import hashlib
import copy
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath


SKILL_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CANDIDATE = SKILL_ROOT.parents[1]
BUNDLED_CANDIDATE = SKILL_ROOT / "assets/octon-mini-source"
ROOT = (
    SOURCE_CANDIDATE
    if (SOURCE_CANDIDATE / "octon-mini.json").is_file()
    else BUNDLED_CANDIDATE
)
SCAFFOLDER = SKILL_ROOT / "scripts/scaffold_project.py"
PLANNER = SKILL_ROOT / "scripts/plan_adoption.py"
INSTALLER = SKILL_ROOT / "scripts/install_skill.py"
MIGRATION_TESTS = (
    SKILL_ROOT / "scripts/test_migration_1_0_1_to_2_0_0.py",
    SKILL_ROOT / "scripts/test_migration_2_0_0_to_3_0_0.py",
    SKILL_ROOT / "scripts/test_migration_3_1_0_to_4_0_0.py",
)
PACKAGE_SCRIPT = SKILL_ROOT / "scripts/package_project.py"
ARCHITECTURAL_CONTRACT_TESTS = (
    SKILL_ROOT / "scripts/validate_source_contracts.py",
    SKILL_ROOT / "scripts/test_architectural_patterns.py",
)
PROFILE_MANIFEST = json.loads(
    (ROOT / "shared/source-contracts/profile-manifest.json").read_text(
        encoding="utf-8"
    )
)
PROFILES = tuple(item["id"] for item in PROFILE_MANIFEST["profiles"])
GIT_PORTFOLIO_CONTRACT = next(
    item
    for item in PROFILE_MANIFEST["packages"]
    if item["id"] == "small-team-git-portfolio"
)
SUPPORTED_WORKFLOWS = ("solo_direct", "solo_hybrid", "pair_pr", "tiny_pr")
GIT_OPERATION_IDS = (
    "status",
    "diff",
    "show_current_revision",
    "list_branches",
    "list_worktrees",
    "inspect_remote_configuration",
    "list_tags",
    "compare_revisions",
    "create_branch",
    "switch_branch",
    "stage_paths",
    "unstage_paths",
    "create_worktree",
    "remove_clean_worktree",
    "delete_merged_branch",
    "create_commit",
    "fast_forward_branch",
    "merge_branch",
    "abort_merge",
    "rebase_branch",
    "continue_rebase",
    "abort_rebase",
    "revert_commit",
    "fetch_remote",
    "push_branch",
    "delete_remote_branch",
    "create_annotated_tag",
    "push_tag",
    "force_push_with_lease",
    "reset_hard",
    "clean_untracked",
    "discard_worktree_changes",
    "delete_unmerged_branch",
    "remove_dirty_worktree",
    "delete_or_move_tag",
    "pull",
    "force_push",
)
HOSTED_OPERATION_IDS = (
    "locate_pull_request",
    "observe_change_checks",
    "observe_pull_request_reviews",
    "open_pull_request",
    "submit_pull_request_review",
    "merge_pull_request",
    "observe_workflow_runs",
    "dispatch_workflow",
    "observe_source_release",
    "create_source_release",
)
COLLABORATION_BASELINE = {
    "schema_version": "harness.collaboration-profile.v2",
    "permission_grant": False,
    "assessment_status": "not_assessed",
    "facts": {
        "writer_count": {"value": None, "evidence": None},
        "solo_integration_preference": {"value": None, "evidence": None},
        "independent_review_capacity": {"value": None, "evidence": None},
        "concurrency": {
            "human_writers": None,
            "agents_or_automation": None,
            "evidence": None,
        },
        "external_contribution_mode": {"value": None, "evidence": None},
    },
    "conflicting_signals": [],
    "limitations": ["generated_unassessed_baseline"],
    "team_band": "unknown",
    "concurrent_work": False,
    "workflow_selection": {
        "status": "not_assessed",
        "base_workflow": None,
        "modifiers": [],
        "review_mode": "not_assessed",
        "integration_method": None,
        "adoption_decision_ref": None,
        "used_fact_ids": [],
    },
}
PRODUCTION_EXTENSIONS = {
    item["id"]
    for item in PROFILE_MANIFEST["packages"]
    if item["kind"] == "domain_extension"
}
ACCEPTANCE_COVERAGE = {
    item["id"]: item["release_coverage"]
    for item in PROFILE_MANIFEST["acceptance_criteria"]
}


def run(
    command: list[str],
    cwd: Path,
    *,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    if env_overrides:
        environment.update(env_overrides)
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def require(
    condition: bool,
    message: str,
    failures: list[str],
) -> None:
    if not condition:
        failures.append(message)


def generate(target: Path, profile: str, name: str) -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            "-B",
            str(SCAFFOLDER),
            "--target",
            str(target),
            "--project-name",
            name,
            "--profile",
            profile,
        ],
        ROOT,
    )


def check_project(target: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            "-I",
            "-B",
            ".agent/scripts/validate.py",
            "--check",
        ],
        target,
    )


def assess_collaboration(target: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            "-I",
            "-B",
            ".agent/scripts/validate.py",
            "--assess-collaboration",
        ],
        target,
    )


def ready_frontier_project(target: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            "-I",
            "-B",
            ".agent/scripts/validate.py",
            "--ready-frontier",
        ],
        target,
    )


def refresh(target: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            "-I",
            "-B",
            ".agent/scripts/refresh.py",
            "--refresh",
        ],
        target,
    )


def write_task(
    target: Path,
    task_id: str,
    status: str,
    previous: str | None,
    dependencies: list[str],
    *,
    prepared: bool = False,
) -> None:
    value = {
        "schema_version": "harness.task.v2",
        "id": task_id,
        "status": status,
        "previous_status": previous,
        "title": "Acceptance mutation",
        "authority_basis": "authority:synthetic-test",
        "owner": "acceptance-suite",
        "created_at": "2030-01-02",
        "updated_at": "2030-01-02",
        "dependencies": dependencies,
        "plan_item_refs": [],
        "gate_refs": [],
        "blocking_refs": [],
        "scope": "Synthetic acceptance mutation only.",
        "acceptance_criteria": ["Synthetic acceptance criterion"] if prepared else [],
        "validation_plan": ["Synthetic validation plan"] if prepared else [],
        "implementation_result": None,
        "review_evidence": [],
        "blocked_by": [],
        "reopened_by": None,
        "acceptance_criteria_met": False,
        "closure_evidence": [],
        "external_effects": "none",
        "limitations": [],
    }
    path = target / ".agent/tasks" / f"{task_id}-mutation.md"
    path.write_text(
        "---\n" + json.dumps(value, indent=2) + "\n---\n\n# Mutation\n",
        encoding="utf-8",
    )


def write_accepted_decision(target: Path, decision_id: str) -> None:
    template = (target / ".agent/templates/decision.md").read_text(encoding="utf-8")
    header_end = template.find("\n---\n", 4)
    value = json.loads(template[4:header_end])
    value.update(
        id=decision_id,
        status="accepted",
        previous_status="proposed",
        title="Trust packaged sample restriction extension",
        authority_source="authority:synthetic-acceptance",
        owner="acceptance-suite",
        scope="sample-restriction extension at the generated revision",
    )
    path = target / ".agent/decisions" / f"{decision_id}-extension-trust.md"
    path.write_text(
        "---\n" + json.dumps(value, indent=2, sort_keys=True)
        + "\n---\n\n# Synthetic acceptance decision\n",
        encoding="utf-8",
    )


def write_passing_evidence(
    target: Path,
    evidence_id: str,
    task_id: str,
) -> None:
    value = {
        "schema_version": "harness.evidence.v1",
        "id": evidence_id,
        "title": "Synthetic extension contract evidence",
        "task": task_id,
        "recorded_at": "2030-01-02",
        "authority_source": "authority:synthetic-acceptance",
        "owner": "acceptance-suite",
        "scope": "Generated extension integration test only.",
        "method": "Repository-contained deterministic fixture validation.",
        "environment": "Temporary acceptance project.",
        "subject_revision_or_fingerprint": "synthetic-extension-fixture-v1",
        "result": "pass",
        "fresh_until": "2099-12-31",
        "supersedes": None,
        "limitations": [
            "Synthetic evidence does not establish an external production control."
        ],
    }
    path = target / ".agent/evidence" / f"{evidence_id}-extension-fixture.md"
    path.write_text(
        "---\n" + json.dumps(value, indent=2, sort_keys=True)
        + "\n---\n\n# Synthetic extension evidence\n",
        encoding="utf-8",
    )


def main() -> int:
    if sys.version_info < (3, 11):
        print("FAIL: Python 3.11+ is required")
        return 2
    failures: list[str] = []
    source_contracts = runpy.run_path(
        str(SKILL_ROOT / "scripts/validate_source_contracts.py")
    )
    continuation_schema = json.loads(
        (ROOT / "shared/schemas/harness-continuation.schema.json").read_text(
            encoding="utf-8"
        )
    )
    continuation_fixture = json.loads(
        (
            SKILL_ROOT
            / "fixtures/continuation/valid/blocked-operation.json"
        ).read_text(encoding="utf-8")
    )
    continuation_issues = source_contracts["schema_issues"](
        continuation_fixture,
        continuation_schema,
        "continuation valid fixture",
    )
    require(
        not continuation_issues,
        "valid Continuation Contract fixture failed: "
        + "; ".join(continuation_issues),
        failures,
    )
    continuation_mutations = json.loads(
        (
            SKILL_ROOT
            / "fixtures/continuation/invalid/mutations.json"
        ).read_text(encoding="utf-8")
    )["mutations"]
    for mutation in continuation_mutations:
        value = copy.deepcopy(continuation_fixture)
        current = value
        for part in mutation["path"][:-1]:
            current = current[part]
        current[mutation["path"][-1]] = mutation["value"]
        issues = source_contracts["schema_issues"](
            value,
            continuation_schema,
            f"continuation mutation {mutation['id']}",
        )
        require(
            mutation["expected_diagnostic"] in "; ".join(issues),
            f"Continuation Contract mutation {mutation['id']} did not fail as expected: {issues}",
            failures,
        )
    work_completion = run(
        [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_work_completion.py")],
        ROOT,
    )
    require(
        work_completion.returncode == 0,
        "governed work-completion positive/negative/mutation suite failed: "
        + (work_completion.stderr.strip() or work_completion.stdout.strip()),
        failures,
    )
    guided_setup = run(
        [sys.executable, "-B", str(SKILL_ROOT / "scripts/test_guided_setup.py")],
        ROOT,
    )
    require(
        guided_setup.returncode == 0,
        "guided setup positive/negative/mutation suite failed: "
        + (guided_setup.stderr.strip() or guided_setup.stdout.strip()),
        failures,
    )
    scaffolder_namespace = runpy.run_path(str(SCAFFOLDER))
    canonical_posix_paths = scaffolder_namespace["canonical_posix_paths"]
    refresh_path_values = (
        "project-dossier/ARTIFACT_CATALOG.json",
        "project-dossier/MANIFEST.json",
        "project-dossier/machine-readable/path-authority.json",
    )
    expected_refresh_paths = sorted(refresh_path_values)
    windows_native_order = [
        path.as_posix()
        for path in sorted(PureWindowsPath(value) for value in refresh_path_values)
    ]
    require(
        windows_native_order != expected_refresh_paths,
        "cross-platform ordering fixture does not expose Windows path ordering",
        failures,
    )
    require(
        canonical_posix_paths(
            PurePosixPath(value) for value in refresh_path_values
        )
        == expected_refresh_paths
        and canonical_posix_paths(
            PureWindowsPath(value) for value in refresh_path_values
        )
        == expected_refresh_paths,
        "scaffolder path rendering is not deterministic across host platforms",
        failures,
    )
    migration_labels = (
        "1.0.1 to 2.0.0",
        "2.0.0 to 3.0.0",
        "3.1.0 to 4.0.0",
    )
    for migration_test, migration_label in zip(
        MIGRATION_TESTS,
        migration_labels,
        strict=True,
    ):
        migration_result = run(
            [sys.executable, "-B", str(migration_test)],
            ROOT,
        )
        require(
            migration_result.returncode == 0,
            f"executable {migration_label} migration fixtures failed: "
            f"{migration_result.stderr or migration_result.stdout}",
            failures,
        )

    for contract_test in ARCHITECTURAL_CONTRACT_TESTS:
        contract_result = run(
            [sys.executable, "-B", str(contract_test)],
            ROOT,
        )
        require(
            contract_result.returncode == 0,
            f"architectural source-contract test failed ({contract_test.name}): "
            f"{contract_result.stderr or contract_result.stdout}",
            failures,
        )

    ci_workflow = (ROOT / ".github/workflows/validate.yml").read_text(
        encoding="utf-8"
    )
    ci_push_block = re.search(
        r"(?ms)^  push:\n(?P<body>.*?)(?=^  [A-Za-z_][^:\n]*:|\Z)",
        ci_workflow,
    )
    require(
        ci_push_block is not None
        and ci_push_block.group("body") == "    branches:\n      - main\n"
        and re.search(r"(?m)^  pull_request:\s*$", ci_workflow) is not None,
        "source CI does not limit push validation to main while retaining PR validation",
        failures,
    )
    require(
        (
            "concurrency:\n"
            "  group: ${{ github.workflow }}-${{ github.event_name }}-${{ "
            "github.event.pull_request.number || github.run_id }}\n"
            "  cancel-in-progress: ${{ github.event_name == 'pull_request' }}"
        ) in ci_workflow,
        "source CI concurrency does not preserve uncancelled push/manual evidence",
        failures,
    )
    require(
        "workflow_dispatch:" in ci_workflow
        and (
            "pull-request-gate:\n    name: required\n"
            "    if: github.event_name == 'pull_request'"
        ) in ci_workflow
        and (
            "main-smoke:\n    name: main-smoke\n"
            "    if: github.event_name == 'push' && "
            "github.ref == 'refs/heads/main'"
        ) in ci_workflow
        and (
            "full-source-matrix:\n    name: full source / ${{ matrix.os }} / Python "
            "${{ matrix.python }}\n"
            "    if: github.event_name == 'workflow_dispatch'"
        ) in ci_workflow
        and (
            "full-acceptance-matrix:\n    name: full acceptance / ${{ matrix.os }} / Python "
            "${{ matrix.python }}\n"
            "    if: github.event_name == 'workflow_dispatch'"
        ) in ci_workflow
        and ci_workflow.count(
            "os: [ubuntu-latest, macos-latest, windows-latest]"
        ) == 2
        and ci_workflow.count(
            'python: ["3.11", "3.12", "3.13", "3.14"]'
        ) == 2
        and ci_workflow.count("timeout-minutes: 90") == 2
        and ci_workflow.count(
            "python -B skills/octon-mini-project-bootstrap/scripts/validate_octon_mini.py"
        ) == 3
        and ci_workflow.count(
            "python -B skills/octon-mini-project-bootstrap/scripts/test_acceptance.py"
        ) == 2,
        "source CI does not preserve the tiered routine/manual validation boundary",
        failures,
    )
    require(
        "permissions:\n  contents: read" in ci_workflow
        and "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803"
        in ci_workflow
        and "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1"
        in ci_workflow,
        "source CI weakened read-only permissions or pinned action revisions",
        failures,
    )
    with tempfile.TemporaryDirectory(prefix="octon-mini-acceptance-") as temp:
        temp_root = Path(temp)
        omitted_profile_target = temp_root / "omitted-profile"
        omitted_profile_result = run(
            [
                sys.executable,
                "-B",
                str(SCAFFOLDER),
                "--target",
                str(omitted_profile_target),
                "--project-name",
                "Omitted Profile",
            ],
            ROOT,
        )
        require(
            omitted_profile_result.returncode != 0
            and "--profile is required for non-interactive generation"
            in (omitted_profile_result.stderr or omitted_profile_result.stdout)
            and not omitted_profile_target.exists(),
            "non-interactive generation silently selected a profile: "
            f"{omitted_profile_result.stderr or omitted_profile_result.stdout}",
            failures,
        )
        legacy_console_target = temp_root / "legacy-console-dry-run"
        legacy_console_result = run(
            [
                sys.executable,
                "-B",
                str(SCAFFOLDER),
                "--target",
                str(legacy_console_target),
                "--project-name",
                "Legacy console α",
                "--profile",
                "minimal",
                "--dry-run",
            ],
            ROOT,
            env_overrides={"PYTHONIOENCODING": "cp1252"},
        )
        require(
            legacy_console_result.returncode == 0
            and "Legacy console \\u03b1" in legacy_console_result.stdout,
            "scaffolder diagnostics failed safely encoded CP-1252 dry run: "
            f"{legacy_console_result.stderr or legacy_console_result.stdout}",
            failures,
        )
        require(
            not legacy_console_target.exists(),
            "legacy-console dry run wrote the target",
            failures,
        )
        projects: dict[str, Path] = {}
        names = {
            "minimal": 'A "Quoted" Project: [α]',
            "standard": "Standard Cross-Domain Initiative",
            "high-assurance": "High Assurance Hybrid Initiative",
        }
        for profile in PROFILES:
            target = temp_root / profile
            result = generate(target, profile, names[profile])
            require(
                result.returncode == 0,
                f"{profile} generation failed: {result.stderr or result.stdout}",
                failures,
            )
            if result.returncode:
                continue
            projects[profile] = target
            require(
                not (target / "LICENSE").exists()
                and not (target / "LICENSE").is_symlink(),
                f"{profile} copied the source license into the generated project",
                failures,
            )
            project_json = json.loads(
                (target / ".agent/project.json").read_text(encoding="utf-8")
            )
            origin = json.loads(
                (target / ".octon-mini-origin.json").read_text(
                    encoding="utf-8"
                )
            )
            require(
                origin["product"] == "octon-mini"
                and origin["octon_mini_version"] == "4.2.0"
                and origin["generator_version"] == "4.2.0"
                and origin["harness_kernel_version"] == "4.2.0"
                and origin["initial_generation"]["product"] == "octon-mini"
                and origin["initial_generation"]["version"] == "4.2.0"
                and origin["initial_generation"]["generator_version"] == "4.2.0"
                and origin["layout"] == "compact"
                and origin["installed_inventory"]["schema_version"]
                == "octon-mini.project.installed-inventory.v1",
                f"{profile} generated incoherent 4.2.0 provenance or layout inventory",
                failures,
            )
            generated_inventory = set(origin["generated_paths"])
            require(
                not any(
                    path.startswith("patterns/")
                    or path in {
                        "ARCHITECTURE_DECISIONS.md",
                        "ARCHITECTURAL_PATTERN_INTEGRATION_REVIEW.md",
                    }
                    for path in generated_inventory
                ),
                f"{profile} generated a source-only pattern or source decision artifact",
                failures,
            )
            context_schema = (
                target / ".agent/schemas/context-pack-manifest.schema.json"
            )
            require(
                not context_schema.exists(),
                f"{profile} physically installed the trigger-only Context Pack schema",
                failures,
            )
            context_directory = target / "project-dossier/context-packs"
            require(
                not context_directory.is_dir()
                or not any(context_directory.glob("*.json")),
                f"{profile} generated a Context Pack manifest or adoption record",
                failures,
            )
            require(
                project_json["project"]["name"] == names[profile],
                f"{profile} project name was not JSON-safe",
                failures,
            )
            require(
                project_json["project"]["adoption_status"] == "not_assessed"
                and project_json["project"]["adoption_decision_ref"] is None
                and all(
                    command["status"] == "not_assessed"
                    for command in project_json["commands"].values()
                ),
                f"{profile} generation fabricated project adoption or command assessment",
                failures,
            )
            require(
                project_json["project"]["profile"] == profile
                and project_json["collaboration_profile"]
                == COLLABORATION_BASELINE,
                f"{profile} generation coupled assurance selection to team size or "
                "fabricated collaboration observations",
                failures,
            )
            workflow_paths = (
                target / ".agent/workflows/README.md",
                target / ".agent/workflows/github-adapter.md",
                target / ".agent/workflows/small-team-git.json",
            )
            require(
                not any(path.exists() for path in workflow_paths),
                f"{profile} generation physically installed the trigger-only Git portfolio",
                failures,
            )
            tools_json = json.loads(
                (target / ".agent/tools.json").read_text(encoding="utf-8")
            )
            scm_json = json.loads(
                (target / ".agent/scm.json").read_text(encoding="utf-8")
            )
            git_ids = tuple(
                operation["id"]
                for operation in tools_json["tools"]["git"]["operations"]
            )
            hosted_ids = tuple(
                operation["id"]
                for operation in tools_json["tools"]["hosted_change"]["operations"]
            )
            require(
                tools_json["schema_version"] == "harness.tools.v2"
                and git_ids == GIT_OPERATION_IDS
                and hosted_ids == HOSTED_OPERATION_IDS
                and tools_json["tools"]["git"]["unknown_operations"] == "deny"
                and tools_json["tools"]["hosted_change"]["unknown_operations"]
                == "deny",
                f"{profile} generated an incomplete or open Git operation vocabulary",
                failures,
            )
            require(
                scm_json["selection"] == "not_assessed"
                and scm_json["selection_decision_ref"] is None
                and scm_json["portfolio"]["status"] == "not_installed"
                and scm_json["portfolio"]["version"]
                == GIT_PORTFOLIO_CONTRACT["version"]
                and scm_json["portfolio"]["sha256"]
                == GIT_PORTFOLIO_CONTRACT["sha256"],
                f"{profile} SCM trigger fabricated selection or installed state",
                failures,
            )
            assessor_before = snapshot(target)
            assessment_result = assess_collaboration(target)
            assessor_after = snapshot(target)
            try:
                assessment_report = json.loads(assessment_result.stdout)
            except json.JSONDecodeError:
                assessment_report = {}
            require(
                assessment_result.returncode == 0
                and assessment_report.get("permission_grant") is False
                and assessment_report.get("status") == "not_assessed"
                and assessment_report.get("team_band") == "unknown"
                and assessment_report.get("recommendation", {}).get("base_workflow")
                is None
                and "grants no permission"
                in assessment_report.get("non_authorization", ""),
                f"{profile} collaboration assessor selected or authorized a workflow: "
                f"{assessment_result.stderr or assessment_result.stdout}",
                failures,
            )
            require(
                assessor_before == assessor_after,
                f"{profile} collaboration assessment wrote project state",
                failures,
            )
            require(
                not (target / ".github").exists(),
                f"{profile} generation fabricated adopted GitHub configuration",
                failures,
            )
            leaked_paths: list[str] = []
            source_pattern_paths: list[str] = []
            for generated_path in target.rglob("*"):
                if not generated_path.is_file():
                    continue
                try:
                    generated_text = generated_path.read_text(
                        encoding="utf-8"
                    ).casefold()
                except UnicodeDecodeError:
                    continue
                if any(
                    marker in generated_text
                    for marker in (
                        "jamesryancooper",
                        "cooperonlineenterprises",
                        "github.com/cooperonlineenterprises/octon-mini",
                    )
                ):
                    leaked_paths.append(generated_path.relative_to(target).as_posix())
                if any(
                    marker in generated_text
                    for marker in (
                        "pat-0001",
                        "pat-0002",
                        "pat-0003",
                        "lifecycle-disposition",
                        "governed-change-and-effects",
                        "src-dec-0003",
                        "src-dec-0004",
                        "src-dec-0005",
                        "src-dec-0006",
                    )
                ):
                    source_pattern_paths.append(
                        generated_path.relative_to(target).as_posix()
                    )
            require(
                not leaked_paths,
                f"{profile} generated current-repository identities or hosted facts: "
                + ", ".join(leaked_paths),
                failures,
            )
            require(
                not source_pattern_paths,
                f"{profile} generated source-only catalog content: "
                + ", ".join(source_pattern_paths),
                failures,
            )
            extension_registry_path = target / ".agent/extensions/registry.json"
            require(
                not (target / ".agent/extensions/operations-observability").exists()
                and not (target / ".agent/extensions/security-supply-chain").exists(),
                f"{profile} physically bundled trigger-only production extensions",
                failures,
            )
            if profile != "minimal":
                extension_registry = json.loads(
                    extension_registry_path.read_text(encoding="utf-8")
                )
                require(
                    extension_registry["extensions"] == [],
                    f"{profile} preinstalled a trigger-only extension registry entry",
                    failures,
                )
            packages = json.loads((target / ".agent/packages.json").read_text(encoding="utf-8"))
            require(
                packages["packages"] == []
                and packages["requirements"]["absence_means_not_applicable"] is False,
                f"{profile} package absence implied non-applicability",
                failures,
            )
            result = check_project(target)
            require(
                result.returncode == 0,
                f"{profile} isolated validation failed: {result.stderr or result.stdout}",
                failures,
            )
        for profile, target in projects.items():
            source_change = target / f"acceptance-refresh-{profile}.txt"
            source_change.write_text(
                "legitimate project-maintained source change\n",
                encoding="utf-8",
            )
            result = check_project(target)
            require(
                result.returncode != 0
                and "stale source fingerprint" in result.stderr,
                f"{profile} source change did not stale integrity",
                failures,
            )
            result = refresh(target)
            require(
                result.returncode == 0,
                f"{profile} refresh failed: {result.stderr or result.stdout}",
                failures,
            )
            result = check_project(target)
            require(
                result.returncode == 0,
                f"{profile} post-refresh check failed: "
                f"{result.stderr or result.stdout}",
                failures,
            )

        nonempty = temp_root / "nonempty"
        nonempty.mkdir()
        sentinel = nonempty / "sentinel.txt"
        sentinel.write_text("preserve\n", encoding="utf-8")
        before = snapshot(nonempty)
        result = generate(nonempty, "standard", "Must Refuse")
        require(result.returncode != 0, "nonempty target was accepted", failures)
        require(snapshot(nonempty) == before, "nonempty target changed on refusal", failures)

        invalid_name_target = temp_root / "invalid-name"
        result = generate(invalid_name_target, "minimal", "line one\nline two")
        require(result.returncode != 0, "control-character name was accepted", failures)
        require(not invalid_name_target.exists(), "invalid-name target was created", failures)

        broken_skill = temp_root / "broken-octon-mini-project-bootstrap"
        shutil.copytree(
            SKILL_ROOT,
            broken_skill,
            ignore=shutil.ignore_patterns(".git", ".DS_Store", "__pycache__", "*.pyc"),
        )
        broken_source = broken_skill / "assets/octon-mini-source"
        if not broken_source.is_dir():
            shutil.copytree(
                ROOT,
                broken_source,
                ignore=shutil.ignore_patterns(
                    ".git", ".DS_Store", "__pycache__", "*.pyc"
                ),
            )
        for layer, profile in (
            ("core", "minimal"),
            ("standard", "standard"),
            ("high-assurance", "high-assurance"),
        ):
            injected_template = (
                broken_skill
                / "assets/templates"
                / layer
                / "source-only-watchlist.md.tmpl"
            )
            injected_template.write_text(
                "# Synthetic source-only watchlist\n",
                encoding="utf-8",
            )
            boundary_target = temp_root / f"policy-boundary-{profile}"
            result = run(
                [
                    sys.executable,
                    "-B",
                    str(broken_skill / "scripts/scaffold_project.py"),
                    "--target",
                    str(boundary_target),
                    "--project-name",
                    f"Policy Boundary {profile}",
                    "--profile",
                    profile,
                ],
                broken_source,
            )
            require(
                result.returncode == 0
                and "Generation capability: degraded" in result.stdout
                and "information_degradation" in result.stdout
                and "source-only-watchlist.md.tmpl" in result.stdout,
                f"{profile} did not degrade truthfully for an unreviewed input: "
                f"{result.stderr or result.stdout}",
                failures,
            )
            require(
                boundary_target.is_dir()
                and not (boundary_target / "source-only-watchlist.md").exists(),
                f"{profile} generated an ignored unreviewed input",
                failures,
            )
            diagnostic = run(
                [
                    sys.executable,
                    "-B",
                    str(broken_skill / "scripts/scaffold_project.py"),
                    "--diagnose-generation-policy",
                    "--profile",
                    profile,
                ],
                broken_source,
            )
            require(
                diagnostic.returncode == 1
                and '"operation_mode": "recovering"' in diagnostic.stdout
                and '"capability_status": "degraded"' in diagnostic.stdout
                and "source-only-watchlist.md.tmpl" in diagnostic.stdout
                and "ignored and never generated" in diagnostic.stdout
                and "review_required_not_approved" in diagnostic.stdout,
                f"{profile} diagnostics did not expose recovery guidance: "
                f"{diagnostic.stderr or diagnostic.stdout}",
                failures,
            )
            injected_template.unlink()

        unrelated_high_template = (
            broken_skill
            / "assets/templates/high-assurance/unreviewed-high-only.md.tmpl"
        )
        unrelated_high_template.write_text(
            "# Unreviewed High-Assurance-only input\n",
            encoding="utf-8",
        )
        unaffected_minimal_target = temp_root / "unaffected-minimal"
        result = run(
            [
                sys.executable,
                "-B",
                str(broken_skill / "scripts/scaffold_project.py"),
                "--target",
                str(unaffected_minimal_target),
                "--project-name",
                "Unaffected Minimal",
                "--profile",
                "minimal",
            ],
            broken_source,
        )
        require(
            result.returncode == 0
            and "Generation capability: normal" in result.stdout
            and "unreviewed-high-only" not in result.stdout
            and not (
                unaffected_minimal_target / "unreviewed-high-only.md"
            ).exists(),
            "an unrelated High-Assurance drift degraded Minimal generation: "
            f"{result.stderr or result.stdout}",
            failures,
        )
        unrelated_high_template.unlink()

        missing_high_template = (
            broken_skill
            / "assets/templates/high-assurance/.agent/metrics/README.md.tmpl"
        )
        missing_high_text = missing_high_template.read_text(encoding="utf-8")
        missing_high_template.unlink()
        isolated_minimal_target = temp_root / "isolated-minimal"
        result = run(
            [
                sys.executable,
                "-B",
                str(broken_skill / "scripts/scaffold_project.py"),
                "--target",
                str(isolated_minimal_target),
                "--project-name",
                "Isolated Minimal",
                "--profile",
                "minimal",
            ],
            broken_source,
        )
        require(
            result.returncode == 0
            and "Generation capability: normal" in result.stdout,
            "a missing High-Assurance dependency blocked Minimal generation: "
            f"{result.stderr or result.stdout}",
            failures,
        )
        blocked_high_target = temp_root / "blocked-high-assurance"
        result = run(
            [
                sys.executable,
                "-B",
                str(broken_skill / "scripts/scaffold_project.py"),
                "--target",
                str(blocked_high_target),
                "--project-name",
                "Blocked High Assurance",
                "--profile",
                "high-assurance",
            ],
            broken_source,
        )
        require(
            result.returncode != 0
            and "high-assurance generation capability is blocked"
            in (result.stderr or result.stdout)
            and "dependency_degradation" in (result.stderr or result.stdout)
            and not blocked_high_target.exists(),
            "a missing High-Assurance dependency did not block only that profile: "
            f"{result.stderr or result.stdout}",
            failures,
        )
        missing_high_template.write_text(missing_high_text, encoding="utf-8")

        repository_skill = (
            broken_source / "skills/octon-mini-project-bootstrap"
        )
        drift_skill = (
            repository_skill if repository_skill.is_dir() else broken_skill
        )
        strict_drift_template = (
            drift_skill
            / "assets/templates/high-assurance/strict-ci-drift.md.tmpl"
        )
        strict_drift_template.write_text(
            "# Strict repository drift fixture\n",
            encoding="utf-8",
        )
        strict_result = run(
            [
                sys.executable,
                "-B",
                str(
                    drift_skill / "scripts/validate_source_contracts.py"
                ),
            ],
            broken_source,
        )
        require(
            strict_result.returncode != 0
            and "generation inventory drift [information_degradation]"
            in (strict_result.stderr or strict_result.stdout)
            and "strict-ci-drift.md.tmpl"
            in (strict_result.stderr or strict_result.stdout),
            "repository validation did not remain strict under ignored drift: "
            f"{strict_result.stderr or strict_result.stdout}",
            failures,
        )
        strict_drift_template.unlink()

        source_policy_path = (
            broken_source / "shared/source-contracts/profile-manifest.json"
        )
        source_policy_text = source_policy_path.read_text(encoding="utf-8")
        invalid_source_policy = json.loads(source_policy_text)
        invalid_source_policy["permission_grant"] = True
        source_policy_path.write_text(
            json.dumps(invalid_source_policy, indent=2) + "\n",
            encoding="utf-8",
        )
        authority_target = temp_root / "authority-degraded-target"
        authority_result = run(
            [
                sys.executable,
                "-B",
                str(broken_skill / "scripts/scaffold_project.py"),
                "--target",
                str(authority_target),
                "--project-name",
                "Authority Degraded",
                "--profile",
                "minimal",
            ],
            broken_source,
        )
        require(
            authority_result.returncode != 0
            and "authority_degradation"
            in (authority_result.stderr or authority_result.stdout)
            and not authority_target.exists(),
            "an invalid generation authority contract was not classified and blocked: "
            f"{authority_result.stderr or authority_result.stdout}",
            failures,
        )
        source_policy_path.write_text(source_policy_text, encoding="utf-8")
        policy_template = (
            broken_skill
            / "assets/templates/core/.agent/policy.json.tmpl"
        )
        policy_text = policy_template.read_text(encoding="utf-8")
        policy_template.write_text(
            policy_text.replace(
                '"permission_grant": false,',
                '"permission_grant": false,\n  "permission_grant": true,',
                1,
            ),
            encoding="utf-8",
        )
        failed_target = temp_root / "failed-transaction-target"
        result = run(
            [
                sys.executable,
                "-B",
                str(
                    broken_skill
                    / "scripts/scaffold_project.py"
                ),
                "--target",
                str(failed_target),
                "--project-name",
                "Failed Transaction",
                "--profile",
                "minimal",
            ],
            broken_source,
        )
        require(result.returncode != 0, "invalid staged snapshot was installed", failures)
        require(
            not failed_target.exists(),
            "failed staged validation changed the target",
            failures,
        )

        adoption_target = temp_root / "existing"
        adoption_target.mkdir()
        (adoption_target / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
        (adoption_target / "src").mkdir()
        (adoption_target / "src/domain.txt").write_text("existing\n", encoding="utf-8")
        before = snapshot(adoption_target)
        result = run(
            [
                sys.executable,
                "-B",
                str(PLANNER),
                "--target",
                str(adoption_target),
                "--profile",
                "standard",
                "--format",
                "json",
            ],
            ROOT,
        )
        require(result.returncode == 0, "adoption planner failed", failures)
        require(snapshot(adoption_target) == before, "adoption planner wrote target", failures)
        if result.returncode == 0:
            plan = json.loads(result.stdout)
            require(
                "AGENTS.md" in plan["collisions"],
                "adoption planner missed root instruction collision",
                failures,
            )
            require(
                "AGENTS.md"
                in plan["functional_equivalent_candidates"][
                    "repository_instructions"
                ],
                "adoption planner missed repository-instruction candidate",
                failures,
            )
            require(
                "always require review"
                in plan["functional_equivalence_limit"].casefold()
                and any(
                    item.get("path") == "AGENTS.md"
                    for item in plan.get("unresolved_ambiguity", [])
                ),
                "adoption plan treated path/name candidates as accepted equivalents",
                failures,
            )

        skill_parent = temp_root / "personal-codex/skills"
        skill_parent.mkdir(parents=True)
        installed_skill = skill_parent / "octon-mini-project-bootstrap"
        result = run(
            [
                sys.executable,
                "-B",
                str(INSTALLER),
                "--destination",
                str(installed_skill),
            ],
            ROOT,
        )
        require(
            result.returncode == 0,
            f"self-contained skill installation failed: {result.stderr or result.stdout}",
            failures,
        )
        require(
            (
                installed_skill
                / "assets/octon-mini-source/dossier/artifact-types.json"
            ).is_file(),
            "installed skill lacks bundled dossier taxonomy",
            failures,
        )
        installed_license = installed_skill / "assets/octon-mini-source/LICENSE"
        require(
            installed_license.is_file()
            and not installed_license.is_symlink()
            and installed_license.read_bytes() == (ROOT / "LICENSE").read_bytes(),
            "installed skill lacks the exact source MIT-0 license",
            failures,
        )
        if installed_skill.is_dir():
            before = snapshot(installed_skill)
            result = run(
                [
                    sys.executable,
                    "-B",
                    str(INSTALLER),
                    "--destination",
                    str(installed_skill),
                ],
                ROOT,
            )
            require(result.returncode != 0, "skill installer overwrote a collision", failures)
            require(
                snapshot(installed_skill) == before,
                "skill collision refusal changed installed files",
                failures,
            )

        if "standard" in projects:
            standard = projects["standard"]
            artifact_path = standard / "project-dossier/acceptance-lifecycle.md"
            artifact_path.write_text(
                "# Acceptance lifecycle artifact\n",
                encoding="utf-8",
            )
            artifact_registry_path = (
                standard
                / "project-dossier/machine-readable/artifact-registry.json"
            )
            artifact_registry = json.loads(
                artifact_registry_path.read_text(encoding="utf-8")
            )
            artifact_registry["artifact_types"].append(
                {
                    "id": "TST-9000",
                    "recommended_name": "Acceptance lifecycle artifact",
                    "category": "acceptance_test",
                    "classification": "optional",
                    "purpose": (
                        "Exercise project-local dossier artifact maintenance."
                    ),
                    "questions": [
                        "Can a registered artifact be added, renamed, and omitted?"
                    ],
                    "intended_audiences": ["maintainers"],
                    "owner_role": "acceptance_suite",
                    "required_inputs": ["authority:synthetic-test"],
                    "downstream_consumers": ["lifecycle acceptance"],
                    "recommended_formats": ["Markdown"],
                    "source_of_truth_expectations": (
                        "The registered Markdown file owns only its synthetic scope."
                    ),
                    "dependencies": [],
                    "creation_timing": "During lifecycle acceptance testing.",
                    "update_triggers": ["acceptance mutation"],
                    "review_cadence": "on_change",
                    "validation_checks": ["registered physical path exists"],
                    "triggers": ["explicit synthetic acceptance"],
                    "omission_or_combination": (
                        "May be omitted only after a not-applicable assessment."
                    ),
                    "representative_evidence": ["authority:synthetic-test"],
                    "profile": "standard",
                    "applicability": {
                        "status": "applicable",
                        "rationale": "Explicit synthetic lifecycle acceptance.",
                        "assessed_on": "2030-01-02",
                        "assessed_by": "acceptance_suite",
                    },
                }
            )
            artifact_registry["representations"].append(
                {
                    "id": "REP-9000",
                    "artifact_type_ids": ["TST-9000"],
                    "path": "project-dossier/acceptance-lifecycle.md",
                    "profile": "standard",
                    "representation_role": "acceptance_test",
                    "information_state": "current_state",
                    "authority": "bounded_synthetic_test_source",
                    "source_direction": "authoritative_edit_source",
                    "generated": False,
                    "owner_role": "acceptance_suite",
                    "review_cadence": "on_change",
                    "update_triggers": ["acceptance mutation"],
                    "sensitivity": "internal",
                    "applicability": {
                        "status": "applicable",
                        "rationale": "Physical acceptance artifact is present.",
                        "assessed_on": "2030-01-02",
                    },
                    "review": {
                        "status": "not_reviewed",
                        "last_reviewed_on": None,
                        "basis": "Synthetic acceptance only.",
                    },
                    "superseded_by": None,
                    "legacy_v1_id": None,
                }
            )
            write_json(artifact_registry_path, artifact_registry)
            result = refresh(standard)
            require(
                result.returncode == 0,
                f"registered artifact add failed: {result.stderr or result.stdout}",
                failures,
            )
            result = check_project(standard)
            require(
                result.returncode == 0,
                f"registered artifact add did not validate: "
                f"{result.stderr or result.stdout}",
                failures,
            )

            renamed_artifact_path = (
                standard / "project-dossier/acceptance-lifecycle-renamed.md"
            )
            artifact_path.rename(renamed_artifact_path)
            artifact_registry = json.loads(
                artifact_registry_path.read_text(encoding="utf-8")
            )
            next(
                item
                for item in artifact_registry["representations"]
                if item["id"] == "REP-9000"
            )["path"] = "project-dossier/acceptance-lifecycle-renamed.md"
            write_json(artifact_registry_path, artifact_registry)
            result = refresh(standard)
            require(
                result.returncode == 0,
                f"registered artifact rename failed: "
                f"{result.stderr or result.stdout}",
                failures,
            )
            result = check_project(standard)
            require(
                result.returncode == 0,
                f"registered artifact rename did not validate: "
                f"{result.stderr or result.stdout}",
                failures,
            )

            renamed_artifact_path.unlink()
            artifact_registry = json.loads(
                artifact_registry_path.read_text(encoding="utf-8")
            )
            artifact_registry["representations"] = [
                item
                for item in artifact_registry["representations"]
                if item["id"] != "REP-9000"
            ]
            retained_type = next(
                item
                for item in artifact_registry["artifact_types"]
                if item["id"] == "TST-9000"
            )
            retained_type["applicability"] = {
                "status": "not_applicable",
                "rationale": "Synthetic lifecycle representation was removed.",
                "assessed_on": "2030-01-02",
                "assessed_by": "acceptance_suite",
            }
            write_json(artifact_registry_path, artifact_registry)
            result = refresh(standard)
            require(
                result.returncode == 0,
                f"registered artifact omission failed: "
                f"{result.stderr or result.stdout}",
                failures,
            )
            result = check_project(standard)
            require(
                result.returncode == 0,
                f"registered artifact omission did not validate: "
                f"{result.stderr or result.stdout}",
                failures,
            )
            catalog = json.loads(
                (standard / "project-dossier/ARTIFACT_CATALOG.json").read_text(
                    encoding="utf-8"
                )
            )
            require(
                any(
                    item["id"] == "TST-9000"
                    and item["applicability"]["status"] == "not_applicable"
                    for item in catalog["artifact_types"]
                )
                and all(
                    item["id"] != "REP-9000"
                    for item in catalog["representations"]
                ),
                "artifact omission erased its not-applicable assessment",
                failures,
            )

            unregistered_path = (
                standard / "project-dossier/unregistered-acceptance.md"
            )
            unregistered_path.write_text(
                "# Unregistered acceptance mutation\n",
                encoding="utf-8",
            )
            before_failed_refresh = snapshot(standard)
            result = refresh(standard)
            require(
                result.returncode != 0
                and "artifact registry missing project-maintained dossier files"
                in result.stderr,
                "refresh invented metadata for an unregistered dossier file",
                failures,
            )
            require(
                snapshot(standard) == before_failed_refresh,
                "failed unregistered-file refresh changed project files",
                failures,
            )
            unregistered_path.unlink()
            result = check_project(standard)
            require(
                result.returncode == 0,
                "unregistered-file refusal did not preserve prior valid state",
                failures,
            )

            illegal = temp_root / "illegal-transition"
            shutil.copytree(standard, illegal)
            write_task(illegal, "TASK-9001", "proposed", "completed", [])
            result = check_project(illegal)
            require(
                result.returncode != 0 and "illegal task transition" in result.stderr,
                "illegal lifecycle transition passed",
                failures,
            )

            broken = temp_root / "broken-reference"
            shutil.copytree(standard, broken)
            write_task(broken, "TASK-9002", "proposed", None, ["TASK-9999"])
            result = check_project(broken)
            require(
                result.returncode != 0 and "unresolved reference TASK-9999" in result.stderr,
                "broken record reference passed",
                failures,
            )

            dependency_cycle = temp_root / "task-dependency-cycle"
            shutil.copytree(standard, dependency_cycle)
            write_task(
                dependency_cycle,
                "TASK-9020",
                "proposed",
                None,
                ["TASK-9021"],
            )
            write_task(
                dependency_cycle,
                "TASK-9021",
                "proposed",
                None,
                ["TASK-9020"],
            )
            result = check_project(dependency_cycle)
            require(
                result.returncode != 0
                and "task dependency cycle" in result.stderr,
                "task dependency cycle passed",
                failures,
            )

            incomplete_dependency = temp_root / "incomplete-task-dependency"
            shutil.copytree(standard, incomplete_dependency)
            write_task(
                incomplete_dependency,
                "TASK-9022",
                "ready",
                "proposed",
                [],
                prepared=True,
            )
            write_task(
                incomplete_dependency,
                "TASK-9023",
                "in_progress",
                "ready",
                ["TASK-9022"],
                prepared=True,
            )
            result = check_project(incomplete_dependency)
            require(
                result.returncode != 0
                and "dependency:TASK-9022" in result.stderr
                and "unsatisfied readiness" in result.stderr,
                "execution against incomplete dependency passed",
                failures,
            )

            frontier_target = temp_root / "ready-frontier"
            shutil.copytree(standard, frontier_target)
            write_task(
                frontier_target,
                "TASK-9024",
                "proposed",
                None,
                [],
                prepared=True,
            )
            write_task(
                frontier_target,
                "TASK-9025",
                "proposed",
                None,
                ["TASK-9024"],
                prepared=True,
            )
            before_frontier = snapshot(frontier_target)
            result = ready_frontier_project(frontier_target)
            require(
                result.returncode == 0,
                f"ready frontier failed: {result.stderr or result.stdout}",
                failures,
            )
            require(
                snapshot(frontier_target) == before_frontier,
                "ready frontier command wrote project files",
                failures,
            )
            if result.returncode == 0:
                frontier = json.loads(result.stdout)
                require(
                    frontier.get("tasks") == ["TASK-9024"],
                    "ready frontier included waiting work or omitted eligible work",
                    failures,
                )
                require(
                    frontier.get("permission_grant") is False
                    and frontier.get("priority_ordered") is False
                    and frontier.get("timeline_fields_determine_readiness") is False,
                    "ready frontier implied authority, priority, or timeline readiness",
                    failures,
                )

            dossier_broken = temp_root / "broken-dossier-reference"
            shutil.copytree(standard, dossier_broken)
            findings_path = (
                dossier_broken
                / "project-dossier/machine-readable/findings.json"
            )
            findings = json.loads(findings_path.read_text(encoding="utf-8"))
            findings["findings"] = [
                {
                    "id": "FIND-9001",
                    "title": "Broken requirement reference",
                    "requirement_refs": ["REQ-9999"],
                    "status": "not_assessed",
                    "assessed_on": "2030-01-02",
                    "subject_version": "synthetic",
                    "inspected_evidence": [],
                    "rationale": "Synthetic acceptance mutation.",
                    "owner_role": "acceptance_suite",
                    "remediation_plan_refs": [],
                    "limitations": [],
                }
            ]
            findings_path.write_text(
                json.dumps(findings, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            result = check_project(dossier_broken)
            require(
                result.returncode != 0
                and "unresolved reference REQ-9999" in result.stderr,
                "broken dossier reference passed",
                failures,
            )

            nested = temp_root / "nested-authority"
            shutil.copytree(standard, nested)
            (nested / "src").mkdir()
            (nested / "src/AGENTS.md").write_text(
                '# Invalid\n\n"permission_grant": true\n',
                encoding="utf-8",
            )
            result = check_project(nested)
            require(
                result.returncode != 0
                and "nested instruction may expand authority" in result.stderr,
                "nested authority expansion passed",
                failures,
            )

            secret = temp_root / "secret-redaction"
            shutil.copytree(standard, secret)
            (secret / "src").mkdir()
            secret_value = "synthetic_acceptance_secret_123456"
            (secret / "src/secret.txt").write_text(
                f"api_key: {secret_value}\n",
                encoding="utf-8",
            )
            result = check_project(secret)
            require(
                result.returncode != 0 and "secret assignment" in result.stderr,
                "synthetic secret passed",
                failures,
            )
            require(
                secret_value not in result.stderr + result.stdout,
                "synthetic secret value was echoed",
                failures,
            )

        if "high-assurance" in projects and "standard" in projects:
            kernel_paths = (
                ".agent/policy.json",
                ".agent/context.json",
                ".agent/schema.json",
                ".agent/lifecycle.json",
                ".agent/tools.json",
                ".agent/validators.json",
            )

            package_cases = (
                ("operations-observability", projects["standard"], True, "9001"),
                ("security-supply-chain", projects["standard"], True, "9101"),
                ("sample-restriction", projects["high-assurance"], False, "9201"),
                ("small-team-git-portfolio", projects["minimal"], False, "9301"),
            )
            for package_id, base, assess_applicable, numeric_id in package_cases:
                package_contract = next(
                    item
                    for item in PROFILE_MANIFEST["packages"]
                    if item["id"] == package_id
                )
                package_target = temp_root / f"installed-{package_id}"
                shutil.copytree(base, package_target)
                decision_id = f"DEC-{numeric_id}"
                write_accepted_decision(package_target, decision_id)
                kernel_before = {
                    path: hashlib.sha256((package_target / path).read_bytes()).hexdigest()
                    for path in kernel_paths
                }
                plan_path = package_target / ".agent/transactions/plans/package.json"
                command = [
                    sys.executable,
                    "-B",
                    str(PACKAGE_SCRIPT),
                    "plan",
                    "--target",
                    str(package_target),
                    "--package",
                    package_id,
                    "--owner",
                    "acceptance-suite",
                    "--trust-decision-ref",
                    decision_id,
                    "--output",
                    str(plan_path),
                ]
                if assess_applicable:
                    command.append("--assess-applicable")
                result = run(command, ROOT)
                require(
                    result.returncode == 0,
                    f"{package_id} package plan failed: {result.stderr or result.stdout}",
                    failures,
                )
                if result.returncode:
                    continue
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                result = run(
                    [
                        sys.executable,
                        "-B",
                        str(PACKAGE_SCRIPT),
                        "apply",
                        "--target",
                        str(package_target),
                        "--plan",
                        str(plan_path),
                        "--accept-digest",
                        plan["canonical_plan_digest"],
                    ],
                    ROOT,
                )
                require(
                    result.returncode == 0,
                    f"{package_id} package apply failed: {result.stderr or result.stdout}",
                    failures,
                )
                result = check_project(package_target)
                require(
                    result.returncode == 0,
                    f"installed {package_id} did not validate: {result.stderr or result.stdout}",
                    failures,
                )
                registry = json.loads((package_target / ".agent/packages.json").read_text(encoding="utf-8"))
                installed = next(
                    (item for item in registry["packages"] if item["id"] == package_id),
                    None,
                )
                require(
                    installed is not None
                    and installed["validation_receipt_ref"] in installed["evidence_refs"]
                    and len(installed["installed_paths_sha256"]) == 64
                    and installed["version"] == package_contract["version"]
                    and installed["sha256"] == package_contract["sha256"],
                    f"{package_id} omitted content or validation receipt binding",
                    failures,
                )
                if installed is None:
                    continue
                if package_id == "small-team-git-portfolio":
                    scm = json.loads((package_target / ".agent/scm.json").read_text(encoding="utf-8"))
                    require(
                        scm["selection"] == "git"
                        and scm["selection_decision_ref"] == decision_id
                        and scm["portfolio"]["status"] == "installed"
                        and scm["portfolio"]["version"]
                        == package_contract["version"]
                        and scm["portfolio"]["sha256"]
                        == package_contract["sha256"]
                        and (package_target / ".agent/workflows/small-team-git.json").is_file(),
                        "Git selection did not transactionally vendor its independent portfolio",
                        failures,
                    )
                    # Simulate an exact-pristine earlier portfolio baseline and
                    # prove that update is explicit, digest-bound, and does not
                    # rewrite workflow adoption or provider configuration.
                    installed["version"] = "1.0.0"
                    installed["sha256"] = "0" * 64
                    (package_target / ".agent/packages.json").write_text(
                        json.dumps(registry, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    scm["portfolio"]["version"] = "1.0.0"
                    scm["portfolio"]["sha256"] = "0" * 64
                    (package_target / ".agent/scm.json").write_text(
                        json.dumps(scm, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    update_path = package_target / ".agent/transactions/plans/package-update.json"
                    updated = run(
                        [
                            sys.executable,
                            "-B",
                            str(PACKAGE_SCRIPT),
                            "plan",
                            "--target",
                            str(package_target),
                            "--package",
                            package_id,
                            "--owner",
                            "acceptance-suite",
                            "--trust-decision-ref",
                            decision_id,
                            "--update",
                            "--output",
                            str(update_path),
                        ],
                        ROOT,
                    )
                    require(
                        updated.returncode == 0,
                        f"{package_id} explicit update plan failed: {updated.stderr or updated.stdout}",
                        failures,
                    )
                    if updated.returncode == 0:
                        update_plan = json.loads(update_path.read_text(encoding="utf-8"))
                        updated = run(
                            [
                                sys.executable,
                                "-B",
                                str(PACKAGE_SCRIPT),
                                "apply",
                                "--target",
                                str(package_target),
                                "--plan",
                                str(update_path),
                                "--accept-digest",
                                update_plan["canonical_plan_digest"],
                            ],
                            ROOT,
                        )
                        require(
                            updated.returncode == 0,
                            f"{package_id} explicit update apply failed: {updated.stderr or updated.stdout}",
                            failures,
                        )
                    registry = json.loads((package_target / ".agent/packages.json").read_text(encoding="utf-8"))
                    installed = next(item for item in registry["packages"] if item["id"] == package_id)
                    scm = json.loads((package_target / ".agent/scm.json").read_text(encoding="utf-8"))
                    require(
                        installed["version"] == package_contract["version"]
                        and installed["sha256"] == package_contract["sha256"]
                        and scm["portfolio"]["version"] == package_contract["version"]
                        and scm["portfolio"]["sha256"] == package_contract["sha256"],
                        "Git portfolio update did not bind the current package version",
                        failures,
                    )
                elif package_id in PRODUCTION_EXTENSIONS:
                    project = json.loads((package_target / ".agent/project.json").read_text(encoding="utf-8"))
                    require(
                        project["packages"]["trigger_assessments"][package_id.replace("-", "_")]
                        == "applicable",
                        f"{package_id} installation did not retain explicit applicability",
                        failures,
                    )
                kernel_after = {
                    path: hashlib.sha256((package_target / path).read_bytes()).hexdigest()
                    for path in kernel_paths
                }
                require(
                    kernel_before == kernel_after,
                    f"trigger installation for {package_id} rewrote unrelated kernel authority",
                    failures,
                )
                if installed is not None:
                    tamper_path = package_target / installed["installed_paths"][0]
                    tamper_path.write_bytes(tamper_path.read_bytes() + b"\n")
                    tampered = check_project(package_target)
                    require(
                        tampered.returncode != 0
                        and "installed content digest is stale" in tampered.stderr,
                        f"tampered {package_id} payload retained passing package evidence",
                        failures,
                    )

            interrupted = temp_root / "interrupted-refresh"
            shutil.copytree(projects["high-assurance"], interrupted)
            report_path = interrupted / ".agent/generated/validation-report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["generation_id"] = "0" * 32
            report_path.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            result = check_project(interrupted)
            require(
                result.returncode != 0 and "mismatched generation IDs" in result.stderr,
                "partial refresh generation mismatch passed",
                failures,
            )

    if failures:
        print(f"FAIL: {len(failures)} acceptance failure(s)")
        for failure in failures:
            print(f"- {failure}")
        return 1
    acceptance_section = (
        (ROOT / "harness/SPECIFICATION.md")
        .read_text(encoding="utf-8")
        .split("## 14. Acceptance criteria", 1)[1]
        .split("## 15. Evidence crosswalk", 1)[0]
    )
    documented_criteria = {
        int(match.group(1))
        for match in re.finditer(r"^(\d+)\. ", acceptance_section, re.MULTILINE)
    }
    if set(ACCEPTANCE_COVERAGE) != documented_criteria:
        print("FAIL: acceptance coverage map is incomplete")
        return 1
    print("PASS: Octon Mini acceptance suite")
    print(f"- profiles: {', '.join(PROFILES)}")
    print(
        "- generation: transactional, format-safe, allowlist-driven, and "
        "capability-scoped under degradation"
    )
    print(
        "- source-only contracts: catalog/proof assets absent from all profiles; "
        "trigger-only Context Pack schema and manifest absent from every default profile"
    )
    print(
        "- maintenance: derived focus/current refresh plus registered add, rename, "
        "combine, supersede, omission, and refusal paths"
    )
    print(
        "- migration: supported executable transitions preserve idempotence, exact "
        "rollback evidence, reviewed legacy seeding, and fail-closed ambiguity coverage"
    )
    print(
        "- adoption: read-only planning/checks plus separately explicit, "
        "fingerprint-bound project-check evidence"
    )
    print(
        "- guided setup: one catalog and shared session engine across init, adopt, "
        "and upgrade with target-read-only inspection and stale-digest refusal"
    )
    print(
        "- validator: adversarial authority, progressive collaboration classification, "
        "triggered Git portfolio, dependency readiness/frontier, lifecycle, "
        "reference, secret, extension, and freshness checks"
    )
    print(
        "- triggered packages: absent-by-default controls, strict fixture suites, "
        "content-addressed installation, decision binding, and refusal paths"
    )
    print(
        "ACCEPTANCE_COVERAGE_JSON="
        + json.dumps(
            {
                "schema_version": "octon-mini.source.acceptance-coverage.v1",
                "criteria": {
                    str(number): status
                    for number, status in sorted(ACCEPTANCE_COVERAGE.items())
                },
                "scope": "Octon Mini release automation",
                "failures": [],
                "skipped_checks": [
                    "target-project human demonstrations remain project-owned"
                ],
                "limitations": [
                    "structural automation does not prove project readiness",
                    "runtime policy text is not an external sandbox",
                ],
                "dirty_state": "not_assessed_by_acceptance_suite",
                "external_effects": "none",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    for number, status in sorted(ACCEPTANCE_COVERAGE.items()):
        print(f"criterion_{number:02d}={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
