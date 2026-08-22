# Octon Mini

Octon Mini is the lightweight, project-local version of Octon. OctonOS is the
full-scale agent operating system.

Octon Mini is a lightweight, project-local version of Octon for governed agent
work. It gives any project a durable harness, dossier, setup workflow,
validation system, work lifecycle, and recovery model without requiring the
full OctonOS control plane.

Octon Mini Project Bootstrap is the capability that creates, adopts,
configures, recovers, and upgrades the Octon Mini harness and project dossier.
It works across software, product, business, brand, research, operations, and
hybrid projects.

Octon Mini works for any project and is standalone. It is not a seed, trial,
free tier, required precursor to OctonOS, “OctonOS Lite,” or an OctonOS runtime. Its smaller scope
does not weaken safety or evidentiary rigor. It retains deny-by-default,
non-authorizing behavior, holds no credentials, and creates no authority for
external effects.

The generated systems remain separate:

- the **harness** defines repository-local guidance, deny-by-default authority
  boundaries, work records, automation contracts, and validation;
- the **dossier** documents definition, intended and observed state,
  conformance, plans, provenance, evidence, and handoff.

A dossier is never permission. Generated policy cannot create authority, and
automation cannot invent facts, owners, identities, decisions, approvals,
evidence, stable IDs, adoption, or readiness.

Generated projects are independent snapshots. They do not track or acquire
later Octon Mini changes automatically.

## Current source and 4.0 changes

Current unreleased 4.2 source work adds governed autonomous delivery under
accepted `SRC-DEC-0019` and standing release-evidence policy
`SRC-DEC-0020`. Every snapshot exposes a dormant, read-only delivery surface
and exact inert offline payloads. Write-capable work and external effects remain
locked until an operator independently confirms the complete deterministic
standing contract digest and activates it. Direct spending is zero, unknown
cost is never zero, and ambiguous external effects are never replayed.

Released 4.1 added the optional, trigger-installed long-running-work
capability. It governs one external worker under an existing task through
deterministic context, exact measurable limits, validated progress,
no-progress detection, marker-backed checkpoints, and read-only resume. It
does not host a model, create task scope, grant permission, or replace existing
work owners.

Version 4.0 makes the universal kernel thinner and ordinary operation faster:

- one authoritative profile/layout/package/inventory/acceptance manifest;
- one workflow-oriented `octon` command inventory projected into every snapshot;
- one catalog-driven, resumable, non-authorizing setup interview feeding the
  existing digest-bound initialization, adoption, and upgrade planners;
- read-only semantic detection and diagnosis;
- fully derived current state plus a small authoritative focus source;
- selective project checks and bounded immutable evidence history;
- one opt-in, provider-neutral, digest-bound and resumable small-team
  work-completion engine;
- trigger-installed Git, operations/observability, security/supply-chain,
  sample restriction, and optional-schema packages;
- compact physical dossier representation by default, with separated layout
  still supported; and
- fast, integration, and release validation tiers plus scale benchmarks; and
- one versioned Continuation Contract, dependency-scoped setup successors,
  concise plan summaries, conservative routine proof reuse, and compatible
  reversible local transaction bundles.

Decision governance extends the existing decision concern with one
project-owned `DREG-####` register, gate-first trade-off review, compatibility
findings, read-only assurance, and a minimum closure graph. Recommendations,
owner selections, and accepted `DEC-####` authority remain distinct; scores
cannot compensate for a failed gate or conceal an evidence gap. See
`docs/DECISION_GOVERNANCE.md`.

Repository-local transactions are staged, validated, instruction- and
path-fingerprint-bound, receipted, and exactly recoverable. External Git and
provider effects cannot be rolled back atomically; governed work completion
records monotonic progress and resumes or fixes forward. There is no global
force mode.

Fail-closed mutation is continuation-oriented: a refusal states whether
anything changed, identifies the smallest invalidated proof, preserves current
inputs, and returns one shell-free next action. It never weakens an authority,
freshness, instruction, path, digest, collision, or external-effect gate.

## Independent selection axes

Choose each axis for its own reason:

| Axis | Values | Select from |
|---|---|---|
| assurance | Minimal, Standard, High Assurance | project risk and control needs |
| collaboration | solo, pair, tiny | 1, 2, or 3–5 write-capable humans |
| concurrency | `concurrent_work` or none | simultaneous human/agent/automation work |
| layout | compact or separated | representation ownership/lifecycle/review needs |
| delivery | review-first, balanced autonomous, fast delivery, custom, or locked | operator-selected delivery actions and limits; independent exact contract confirmation still required |

Minimal is the interactive recommendation, never a silent non-interactive
default. Missing, stale, or conflicting collaboration evidence selects no
workflow. A workflow proposal becomes adopted only through an accepted
project-owned decision. Team size never selects assurance.

## Capability names

Capability names state what the capability does instead of using the product
name alone. The authoritative command manifest records each capability's
availability, implementation entry points, mutation behavior, authorization
boundary, and limitations.

| Capability | Main command | Availability and boundary |
|---|---|---|
| Octon Mini Project Bootstrap | `octon init`, `octon adopt`, `octon upgrade` | interactive one-command flow or explicit plan/apply; every apply requires current inputs and the exact reviewed digest |
| Octon Mini Guided Setup | `octon init\|adopt\|upgrade setup` | source workflow; target-read-only, with an optional explicit external session write |
| Octon Mini Project Detection | `octon detect` | source workflow; read-only and non-adopting |
| Octon Mini Project Validation | `octon check` | generated project; read-only and never runs hooks |
| Octon Mini Diagnostics and Recovery | `octon doctor` | generated project; uses the shared typed Continuation Contract and any derived repair requires its reviewed digest |
| Octon Mini Work Lifecycle | `octon work start\|block\|close\|reopen\|handoff\|resume` | generated project; views are read-only and lifecycle changes use explicit plan/apply receipts |
| Octon Mini Governed Work Completion | `octon work finish` | generated disabled; planning is read-only and external effects require exact current task-scoped authorization |
| Octon Mini Long-Running Work | `octon work run` | dormant generated route; executes only an installed, digest-valid, separately adopted optional package for one existing task |
| Octon Mini Governed Autonomous Delivery | `octon delivery` | read-only and available while locked; write-capable activation requires exact independent standing-contract confirmation and locally bundled package installation |
| Octon Mini Project Maintenance | `octon maintain` | source or generated by subcommand; every writer retains its specific review and authority gate |
| Octon Mini Transaction Recovery | `octon transaction` | generated project; compatible reversible local plans may bundle, while apply, rollback, and recovery remain exact-plan or exact-receipt bound |

## Repository layout

| Path | Role |
|---|---|
| `dossier/` | dossier specification, artifact taxonomy, reference evidence |
| `harness/` | harness architecture and acceptance contracts |
| `shared/` | generation contract, source manifests, schemas |
| `patterns/` | source-only pattern catalog and Architecture Proof assets |
| `skills/octon-mini-project-bootstrap/` | Octon Mini Project Bootstrap skill, templates, detectors, packages, scripts, fixtures |
| `migrations/` | version-to-version migration guidance |
| `docs/GOLDEN_PATHS.md` | verified operating paths |
| `docs/COMPATIBILITY.md` | v4 compatibility, migration, and deprecation boundary |
| `docs/DECISION_GOVERNANCE.md` | authoritative decision, review, maturity, handoff, and read-only assurance practice |
| `docs/GUIDED_SETUP.md` | canonical setup interview, session, authority, staleness, and migration practice |
| `docs/REAL_PROJECT_VALIDATION.md` | source-only real-project usability protocol and content-free report template |
| `VELOCITY_VALIDATION.md` | benchmarks, touchpoints, validation matrix |
| `RELEASE_READINESS.md` | non-authorizing 4.1.0 release evidence and known-limitations record; `RELEASE.md` retains the release gate |

Strict JSON and Python 3.11+ keep the generated kernel portable and
duplicate-key rejecting. Extensions may add formats only with a pinned parser
and validated adapter.

## Command entry across platforms

The source checkout, installed source bundle, and generated project each expose
one extensionless Python launcher named `octon`. A given source or generated
command uses the same arguments on every supported platform:

```text
# Source checkout or installed source bundle: Unix/macOS, then Windows
./octon detect
python -B octon detect

# Generated project: Unix/macOS, then Windows
./octon check
python -B octon check
# Or, with the Python launcher for Windows:
py -3 -B octon check
```

The examples below use the Unix/macOS form. On Windows, replace only the
`./octon` prefix with `python -B octon` or `py -3 -B octon`. Source and generated
command inventories remain context-specific. The launchers keep bytecode
disabled, resolve the correct dispatcher, and do not introduce a second command
identity.

## New project

The interactive one-command path performs inspection, asks only unresolved
blocking questions, writes immutable session and plan artifacts to an explicit
external review directory, renders a concise summary, requests one final
confirmation of the displayed digest, revalidates, and applies:

```text
./octon init \
  --target /absolute/path/to/new-project \
  --review-dir /absolute/review-area
```

If confirmation is withheld or a hard block appears, the artifacts remain
available and the command emits `octon-mini.continuation.v1`. Non-interactive
automation continues to use the explicit setup/plan/apply forms below.

An AI agent or TTY can first run the shared setup interview. Question
generation is target-read-only; the optional session output is explicit and
must be outside the target:

```text
./octon init setup \
  --target /absolute/path/to/new-project \
  --output /absolute/review-area/setup-01.json

# Supply a digest-bound answer batch, or use --tty, and write a successor.
./octon init setup \
  --target /absolute/path/to/new-project \
  --session /absolute/review-area/setup-01.json \
  --answers /absolute/review-area/answers-01.json \
  --output /absolute/review-area/setup-02.json
```

The interview asks only unresolved, dependency-eligible questions, normally
one to three at a time. It preserves observations, inferences,
recommendations, owner selections, accepted-authority references, unknowns,
deferrals, and runtime authorization as different information roles. No
answer is preselected, and setup never stores secrets or grants permission.
See `docs/GUIDED_SETUP.md`.

Plan without changing the target:

```text
./octon init plan \
  --target /absolute/path/to/new-project \
  --project-name "Example Project" \
  --profile minimal \
  --layout compact \
  --output /absolute/path/to/new-project/.agent/transactions/plans/init.json
```

After a session reaches `ready_for_plan`, the same existing planner accepts
`--setup-session /absolute/review-area/setup-02.json` instead of duplicate
setup flags. The plan binds the exact session digest and bytes. Apply
revalidates the session, target, instructions, plan digest, and ordinary
transaction preconditions.

Review the observations, inferences, explicit decisions, authorization gates,
exact operations, validation, rollback, and digest. Then apply that digest:

```text
./octon init apply \
  --target /absolute/path/to/new-project \
  --plan /absolute/path/to/new-project/.agent/transactions/plans/init.json \
  --accept-digest <reviewed-digest>
```

Interactive `octon init` proposes Minimal without preselecting it and asks for
one exact-plan confirmation. Scripted use
must pass `--profile`. An explicitly supplied first task is created in the
same candidate only when all task semantics are supplied. The full release
tier passes in staging before the target is written.

The primitive `scaffold_project.py` remains available for advanced generation
diagnostics and `--dry-run`. Generation uses
`shared/source-contracts/profile-manifest.json`; unreviewed source additions
are ignored and diagnosed, while unsafe paths, output collisions, forbidden
destinations, and missing required inputs fail closed.

## Established project

`./octon adopt --target <path> --review-dir <external-path>` provides the same
interactive orchestration. A collision or functional-equivalence ambiguity
preserves the session and proposal and stops for review; it never overwrites or
auto-dispositions established content.

Use content-aware adoption rather than the empty-project generator:

```text
./octon adopt plan --help
```

Use `octon adopt setup` before planning when a guided interview is desired. It
does not replace the bounded semantic proposal/review contract; proposal-bound
collision and functional-equivalence dispositions remain authoritative.

Default inspection is bounded to 200 allowlisted text/config files, 256 KiB
each, and 4 MiB total. It excludes secrets, `.env*`, private keys, symlinks,
binaries, ignored/generated/vendor/dependency/build/coverage content, and
sensitivity-marked paths. It retains hashes and matched semantic vocabulary,
not project content.

The proposal distinguishes confirmed collisions, likely functional
equivalents, authority conflicts, safe and reviewed additions, unresolved
project facts, hook candidates, and ambiguity. Functional equivalence and
authority preservation always require proposal-bound review. Apply preserves
all established content, runs the release tier in staging, and leaves harness
adoption `in_progress`.

## Routine project operation

Every generated snapshot includes `./octon` as its sole current command. There
is no `pb` alias or compatibility command:

```text
./octon work start --help
./octon work close --help
./octon work handoff --help
./octon work resume
./octon work finish plan
./octon work run --help
./octon delivery status
./octon delivery activation-preview --profile fast_delivery
./octon check
./octon doctor
./octon maintain registry plan
./octon maintain hooks plan --help
./octon maintain collaboration plan --help
./octon maintain refresh --apply
./octon transaction bundle plan --help
```

Bundle planning accepts only two or more non-authorizing repository-local
transaction plans with nonoverlapping paths, the same governing instructions,
compatible authority/confirmation/freshness/reversibility requirements, and no
external or monotonic effect. One accepted bundle digest produces one stage,
receipt, and exact rollback boundary.

Work automation allocates stable IDs and synchronizes legal transitions,
reciprocal plan links, focus, derived current state, and handoff pointers. The
operator still owns task purpose, scope, authority basis, acceptance criteria,
priority, substantive review, closure claims, evidence, and external-effect
authorization.

`work finish` is generated disabled and becomes usable only after explicit
project adoption of its existing small-team workflow, repository, provider,
check, eligible peer reviewers where applicable, exact read-only completion
command hook, and cleanup inputs. `plan` performs no writes, refresh,
fetch, hosted query, or receipt update. `apply` reconstructs the plan from the
completed task's exact completion contract, accepts only its reviewed digest,
and requires current task-scoped authorization for the exact external
operation list. `resume` observes completed effects before acting so a partial
run does not duplicate commits, PRs, merges, pushes, or deletes. Pair and tiny
teams require a real approval by another eligible developer; agent or
self-review never counts. See the installed small-team workflow README for the
configuration and receipt contract.

`work finish plan` uses the same concise plan-summary renderer. Use `--json`
for its strict summary or `--details-json` for the complete deterministic,
non-authorizing completion plan.

`./octon check` is read-only and never runs hooks. Configure each test, lint,
build, and closure hook with shell-free argv, owner, rationale, version probe,
freshness, and side effects—or explicitly assess it `not_applicable`. Run hooks
only through the separate explicit evidence writer:

```text
python -B .agent/scripts/run_project_checks.py --write-evidence
```

Use `--hook`, changed-scope routing, and `--acknowledge-side-effects` as their
contracts require. `--verify-adoption` runs the complete configured hook set,
refresh, and final read-only check. Current evidence is bounded; prior records
move to immutable date-partitioned archives with successor relationships.

After explicit package installation and a separate accepted project adoption
decision, `./octon work run` coordinates a bounded external worker. Context,
status, resume, and explain are read-only. Progress requires current task-bound
validation; local changes still use transactions and Git/provider completion
still uses `work.finish`. An outcome-unknown effect stops for reconciliation
and is never replayed.

Routine explicit checks may add `--reuse-proofs`. A hit requires an exact
unexpired passing `read_only` proof bound to inputs, argv, executable/version,
configuration, instructions, environment characteristics, and side effects.
Any mismatch reruns the check. Adoption and release verification prohibit
reuse and remain complete. `./octon check` never writes a proof, evidence,
report, cache, or bytecode.

## Collaboration, SCM, and domain packages

Collaboration v2 requires evidence only for facts used by the result, while
every used fact has source, observation time, expiry, and limitations. It
stores no identities. Concurrent work is a modifier. Assurance remains
unchanged.

The kernel contains a compact SCM trigger and pinned package digest, not the
full Git portfolio. Detection proposes Git without selecting it. An accepted
decision triggers a transactional, content-addressed installation:

```text
./octon maintain package plan --help
```

Domain-trigger absence never means `not_applicable`. Applicable packages
require explicit owner, accepted trust decision, pinned version/digest, exact
installed-content digest, and a successful transaction receipt. Extensions are
installed disabled; readiness and enablement remain separate.

## Recovery and upgrades

`./octon doctor` emits versioned codes with root cause, owning authority source,
exact invalidated and preserved proofs, mutation state, one shell-free next
action, safe read-only alternatives, successor availability, and repair class.
Human output is concise; `--json` emits the strict contract. Doctor is read-only
unless an exact derived-only repair digest is explicitly accepted.

```text
./octon transaction recover --pending <journal>
./octon transaction rollback --receipt <receipt>
```

Recovery restores only exact preimages or finalizes an exact terminal receipt.
Rollback durably marks its in-progress state, resumes after interruption, and
refuses a path changed independently. Stale plans, evidence, instructions, or
target bytes require re-planning.

Live upgrade is a three-way comparison of recorded old baselines, current
project, and candidate Octon Mini snapshot:

```text
./octon upgrade plan --help
```

Use `./octon upgrade --target <path> --review-dir <external-path>` for the
interactive path. The current Project Blueprint cross-brand migration may be
recognized only as a reviewed legacy migration input and still requires its
exact seed; no legacy runtime fallback is introduced.

`octon upgrade setup` uses the same session engine. Every nonautomatic path still
requires one exact disposition in the existing proposal-bound upgrade review;
the session references that review rather than duplicating it.

Only exact-pristine non-authoritative implementation assets, safe additions,
and derived regeneration are automatic. Instructions, policy, project config,
workflow adoption, dossier sources/registries, records, current facts, stable
IDs, deletions/moves, permissions, symlinks, and modified content require
explicit review. Project Blueprint 3.x→Octon Mini 4.0 is an explicit,
reviewed, recoverable cross-brand migration. For 3.1→4.0, first create the
reviewed legacy inventory seed described in
`migrations/3.1.0-to-4.0.0.md`. The migration replaces the old launcher and
provenance with `octon` and Octon Mini identities; it does not retain `pb`
compatibility. Structural upgrade does not imply harness adoption or project
readiness.

## Validate, benchmark, and install

```text
python3 -B skills/octon-mini-project-bootstrap/scripts/validate_skill_package.py
python3 -B skills/octon-mini-project-bootstrap/scripts/verify_reference_evidence.py
python3 -B skills/octon-mini-project-bootstrap/scripts/validate_source_contracts.py
python3 -B skills/octon-mini-project-bootstrap/scripts/test_architectural_patterns.py
python3 -B skills/octon-mini-project-bootstrap/scripts/test_benchmark_validation.py
python3 -B skills/octon-mini-project-bootstrap/scripts/test_octon_launchers.py
python3 -B skills/octon-mini-project-bootstrap/scripts/test_migration_1_0_1_to_2_0_0.py
python3 -B skills/octon-mini-project-bootstrap/scripts/test_migration_2_0_0_to_3_0_0.py
python3 -B skills/octon-mini-project-bootstrap/scripts/test_migration_3_1_0_to_4_0_0.py
python3 -B skills/octon-mini-project-bootstrap/scripts/test_velocity_workflows.py
python3 -B skills/octon-mini-project-bootstrap/scripts/validate_octon_mini.py
python3 -B skills/octon-mini-project-bootstrap/scripts/test_acceptance.py
python3 -B skills/octon-mini-project-bootstrap/scripts/profile_large_project.py --sizes 0 2000 10000 20000
python3 -B skills/octon-mini-project-bootstrap/scripts/benchmark_validation.py --enforce
```

The skill installer is collision-safe, bundles an independent source snapshot,
and validates it before placement:

```text
python3 -B skills/octon-mini-project-bootstrap/scripts/install_skill.py --dry-run
```

When `SKILL.md` or `agents/openai.yaml` changes, also run the installed
skill-creator `quick_validate.py`. See `RELEASE.md`, `CHANGELOG.md`,
`docs/GOLDEN_PATHS.md`, and `VELOCITY_VALIDATION.md` for verified details and
limitations.

## License

The public `cooperonlineenterprises/octon-mini` source repository is licensed
under the [MIT No Attribution license](LICENSE), SPDX identifier `MIT-0`, with
`Copyright 2026 Cooper Online Enterprises`. This permits use, modification, and
redistribution without an attribution-carrying condition. Octon Mini 4.1.0 is
the current completed source release: annotated tag `v4.1.0` targets
`6d1cfb0f13d300b9d4b78bf7078cf07daa7febd6`, and its GitHub Release is
published. No separate package registry or package channel was used. Existing
generated projects remain independent snapshots and do not acquire the release
or optional long-running-work package automatically.

An installed Octon Mini Project Bootstrap source bundle includes the repository
license. Generated target projects do not receive this `LICENSE` file and do not
silently acquire a project-wide licensing decision. Each target project retains
authority over its own overall license.

## Claim boundary

Generation transfers structure, schemas, vocabulary, and validation behavior;
never implementation state, decisions, permission, approvals, credentials,
providers, legal conclusions, or readiness. Report structural conformance,
harness adoption, and target-project readiness separately, including unknowns,
skipped work, stale evidence, dirty state, limitations, and external effects.
