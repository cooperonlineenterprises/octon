#!/usr/bin/env python3
"""Octon Mini Project Bootstrap and project-local workflow interface."""

from __future__ import annotations

import subprocess
import sys
import json
import importlib.util
import types
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent


def load_continuation():
    path = SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_continuation.py.tmpl"
    spec = importlib.util.spec_from_file_location("octon_source_continuation", path)
    if spec is None or spec.loader is None:
        module = types.ModuleType("octon_source_continuation")
        module.__file__ = str(path)
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
        return module
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTINUATION = load_continuation()


def emit_block(code: str, operation: str, cause: str, next_argv: list[str]) -> int:
    report = CONTINUATION.finding(
        failure_code=code,
        blocked_operation=operation,
        phase="inspect",
        root_cause=cause,
        authority_source="authoritative_command_manifest",
        repair_class="input_required",
        next_action=CONTINUATION.action(
            "Inspect the current supported command inventory.",
            next_argv,
            read_only=True,
        ),
        safe_read_only_actions=[],
    )
    print(
        CONTINUATION.render_finding(report, json_output="--json" in sys.argv),
        file=sys.stderr,
    )
    return 2


def availability_values(value: object) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return set(value)
    return set()


def nonempty_strings(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def execute(script: Path, arguments: list[str]) -> int:
    return subprocess.run(
        [sys.executable, "-B", str(script), *arguments],
        cwd=Path.cwd(),
        check=False,
        shell=False,
    ).returncode


def command_manifest() -> dict[str, object]:
    candidates = (
        SKILL_ROOT.parents[1] / "shared/source-contracts/commands.json",
        SKILL_ROOT / "assets/octon-mini-source/shared/source-contracts/commands.json",
    )
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        raise ValueError("authoritative command manifest is unavailable")
    value = json.loads(path.read_text(encoding="utf-8"))
    commands = value.get("commands", [])
    if not isinstance(commands, list) or any(not isinstance(item, dict) for item in commands):
        raise ValueError("authoritative command manifest commands must be objects")
    names = [item.get("name") for item in commands]
    capabilities = value.get("capabilities", [])
    if not isinstance(capabilities, list) or any(
        not isinstance(item, dict) for item in capabilities
    ):
        raise ValueError("authoritative command manifest capabilities must be objects")
    capability_ids = [item.get("id") for item in capabilities]
    capability_id_set = {
        item for item in capability_ids if isinstance(item, str) and item
    }
    allowed_availability = {"bootstrap_source", "generated_project"}
    allowed_behavior = {"read_only", "mutating", "mixed"}
    vague_display_names = {
        "Octon Mini Skill",
        "Octon Mini Engine",
        "Octon Mini Manager",
        "Octon Mini Tool",
        "Octon Mini Service",
    }
    capability_contracts_valid = all(
        isinstance(item.get("id"), str)
        and bool(item["id"].strip())
        and isinstance(item.get("display_name"), str)
        and bool(item["display_name"].strip())
        and item["display_name"] not in vague_display_names
        and isinstance(item.get("purpose"), str)
        and bool(item["purpose"].strip())
        and isinstance(item.get("availability"), list)
        and bool(availability_values(item.get("availability")))
        and availability_values(item.get("availability")) <= allowed_availability
        and nonempty_strings(item.get("command_entry_points"))
        and nonempty_strings(item.get("implementation_entry_points"))
        and item.get("default_behavior") in allowed_behavior
        and isinstance(item.get("mutation_behavior"), str)
        and bool(item["mutation_behavior"].strip())
        and isinstance(item.get("authorization_boundary"), str)
        and bool(item["authorization_boundary"].strip())
        and nonempty_strings(item.get("limitations"))
        for item in capabilities
    )
    command_contracts_valid = all(
        isinstance(item.get("name"), str)
        and bool(item["name"].strip())
        and isinstance(item.get("capability_id"), str)
        and item["capability_id"] in capability_id_set
        and isinstance(item.get("description"), str)
        and bool(item["description"].strip())
        and isinstance(item.get("availability"), list)
        and bool(availability_values(item.get("availability")))
        and availability_values(item.get("availability")) <= allowed_availability
        and item.get("default_behavior") in allowed_behavior
        and isinstance(item.get("mutation_model"), str)
        and bool(item["mutation_model"].strip())
        and isinstance(item.get("authorization_boundary"), str)
        and bool(item["authorization_boundary"].strip())
        for item in commands
    )
    roots = {str(name).split(".", 1)[0] for name in names}
    expected = {"init", "adopt", "upgrade", "detect", "check", "doctor", "work", "delivery", "maintain", "transaction"}
    help_command_names = {
        "init",
        "adopt",
        "upgrade",
        "detect",
        "maintain.package",
        "maintain.collaboration",
    }
    help_capability_ids = {
        "bootstrap.initialization",
        "bootstrap.adoption",
        "bootstrap.upgrade",
        "bootstrap.detection",
        "maintenance.packages",
        "maintenance.collaboration",
    }
    availability = {
        item
        for command in commands
        for item in availability_values(command.get("availability"))
    }
    bootstrap_roots = {
        str(item.get("name")).split(".", 1)[0]
        for item in commands
        if "bootstrap_source" in availability_values(item.get("availability"))
    }
    project_roots = {
        str(item.get("name")).split(".", 1)[0]
        for item in commands
        if "generated_project" in availability_values(item.get("availability"))
    }
    if (
        value.get("schema_version") != "harness.command-manifest.v2"
        or value.get("document_role")
        != "authoritative_workflow_interface_and_capability_catalog"
        or value.get("permission_grant") is not False
        or not capability_contracts_valid
        or not command_contracts_valid
        or len(names) != len(set(names))
        or len(capability_ids) != len(set(capability_ids))
        or capability_id_set
        != {str(item.get("capability_id")) for item in commands}
        or not help_command_names <= set(names)
        or not help_capability_ids <= capability_id_set
        or roots != expected
        or availability != {"bootstrap_source", "generated_project"}
        or bootstrap_roots != {"init", "adopt", "upgrade", "detect", "work", "delivery", "maintain"}
        or project_roots != {"check", "doctor", "work", "delivery", "maintain", "transaction"}
    ):
        raise ValueError("authoritative command manifest is malformed or differs from the dispatcher")
    return value


def workflow_help(manifest: dict[str, object]) -> str:
    commands = {
        str(item["name"]): str(item["description"])
        for item in manifest["commands"]
        if isinstance(item, dict)
    }
    capabilities = {
        str(item["id"]): str(item["display_name"])
        for item in manifest["capabilities"]
        if isinstance(item, dict)
    }
    return f"""Octon Mini workflow interface

{capabilities['bootstrap.initialization']}:
  ./octon init [--target ...]           Guided inspect/question/plan/confirm/apply.
  ./octon init setup|plan|apply ...     {commands['init']}
{capabilities['bootstrap.adoption']}:
  ./octon adopt [--target ...]          Guided flow; pauses on proposal review.
  ./octon adopt setup|plan|apply ...    {commands['adopt']}
{capabilities['bootstrap.upgrade']}:
  ./octon upgrade [--target ...]        Guided flow; pauses on migration review.
  ./octon upgrade setup|plan|apply ...  {commands['upgrade']}
{capabilities['bootstrap.detection']}:
  ./octon detect --target PATH          {commands['detect']}
{capabilities['maintenance.packages']}:
  ./octon maintain package ...          {commands['maintain.package']}
{capabilities['maintenance.collaboration']}:
  ./octon maintain collaboration ...    {commands['maintain.collaboration']}
{capabilities['work.autonomous_delivery']}:
  ./octon delivery ...                  {commands['delivery']}
{capabilities['work.completion']}:
  ./octon work finish ...               Source mode uses an external digest-bound Codex task reference; generated projects retain their project task records.

Launcher forms:
  Unix/macOS: ./octon ...
  Windows:    python -B octon ...  or  py -3 -B octon ...

Generated-project capabilities are delegated directly to a verified
`.agent/scripts/octon.py` in the current project. Run `./octon --help` there for
project-local validation, diagnostics, work, maintenance, and transactions.

No command grants permission and there is no global force option.
"""


def local(arguments: list[str]) -> int:
    project_root = Path.cwd().resolve()
    agent_root = project_root / ".agent"
    scripts_root = agent_root / "scripts"
    script = scripts_root / "octon.py"
    manifest_path = agent_root / "commands.json"
    if (
        not agent_root.is_dir()
        or agent_root.is_symlink()
        or not scripts_root.is_dir()
        or scripts_root.is_symlink()
        or not script.is_file()
        or script.is_symlink()
        or not manifest_path.is_file()
        or manifest_path.is_symlink()
        or script.resolve() == Path(__file__).resolve()
    ):
        return emit_block(
            "OCTON-CMD-1002",
            "generated_project.dispatch",
            "No verified generated-project Octon Mini interface exists in the current directory.",
            ["./octon", "--help"],
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            not isinstance(manifest, dict)
            or manifest.get("schema_version") != "harness.command-manifest.v2"
            or manifest.get("permission_grant") is not False
            or not isinstance(manifest.get("commands"), list)
            or not isinstance(manifest.get("capabilities"), list)
        ):
            raise ValueError("generated-project command inventory has invalid metadata")
        commands = manifest.get("commands", [])
        capabilities = manifest.get("capabilities", [])
        capability_ids = {
            item.get("id")
            for item in capabilities
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if (
            not capability_ids
            or not commands
            or len(capability_ids) != len(capabilities)
            or any(
                not isinstance(item, dict)
                or item.get("capability_id") not in capability_ids
                or not isinstance(item.get("availability"), list)
                for item in commands
            )
        ):
            raise ValueError("generated-project command inventory has invalid capability references")
        generated_roots = {
            str(item.get("name")).split(".", 1)[0]
            for item in commands
            if isinstance(item, dict)
            and "generated_project" in availability_values(item.get("availability"))
        }
    except (OSError, ValueError, json.JSONDecodeError, AttributeError):
        return emit_block(
            "OCTON-CMD-1003",
            "generated_project.dispatch",
            "The generated-project command inventory is invalid.",
            ["./octon", "check", "--json"],
        )
    if not arguments or arguments[0] not in generated_roots:
        return emit_block(
            "OCTON-CMD-1004",
            "generated_project.dispatch",
            "The requested workflow is not available in this generated project snapshot.",
            ["./octon", "--help"],
        )
    return execute(script, arguments)


def main() -> int:
    try:
        manifest = command_manifest()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 2
    arguments = sys.argv[1:]
    if not arguments or arguments[0] in {"-h", "--help", "help"}:
        print(workflow_help(manifest))
        return 0
    command, rest = arguments[0], arguments[1:]
    if command == "init":
        if not rest or rest[0].startswith("-"):
            return execute(SCRIPT_ROOT / "guided_workflow.py", ["initialization", *rest])
        return execute(SCRIPT_ROOT / "init_project.py", rest)
    if command == "adopt":
        if not rest or rest[0].startswith("-"):
            return execute(SCRIPT_ROOT / "guided_workflow.py", ["adoption", *rest])
        return execute(SCRIPT_ROOT / "adopt_project.py", rest)
    if command == "upgrade":
        if not rest or rest[0].startswith("-"):
            return execute(SCRIPT_ROOT / "guided_workflow.py", ["upgrade", *rest])
        script = SCRIPT_ROOT / "upgrade_project.py"
        if not script.is_file():
            print("[FAIL] live upgrade planner is unavailable in this snapshot", file=sys.stderr)
            return 2
        return execute(script, rest)
    if command == "detect":
        return execute(SCRIPT_ROOT / "detect_project.py", rest)
    if command == "delivery":
        return execute(
            SKILL_ROOT / "assets/templates/core/.agent/scripts/octon_autonomous_delivery.py.tmpl",
            ["--target", str(Path.cwd().resolve()), *rest],
        )
    if command == "work" and rest and rest[0] == "finish" and (Path.cwd() / "octon-mini.json").is_file():
        return execute(
            SCRIPT_ROOT / "source_work_completion.py",
            ["--target", str(Path.cwd().resolve()), *rest[1:]],
        )
    if command == "maintain" and rest:
        if rest[0] == "package":
            return execute(SCRIPT_ROOT / "package_project.py", rest[1:])
        if rest[0] == "collaboration":
            return execute(SCRIPT_ROOT / "collaboration_project.py", rest[1:])
    if command in {"work", "check", "doctor", "maintain", "transaction"}:
        return local(arguments)
    return emit_block(
        "OCTON-CMD-1001",
        "source.dispatch",
        f"Unknown or unsupported workflow: {command}",
        ["./octon", "--help"],
    )


if __name__ == "__main__":
    raise SystemExit(main())
