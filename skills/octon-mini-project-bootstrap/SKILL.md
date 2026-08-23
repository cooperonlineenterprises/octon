---
name: octon-mini-project-bootstrap
description: Create, adopt, configure, operate, recover, or upgrade a project-local Octon Mini agent harness and project dossier. Use for project bootstrap, new-project initialization, established-project adoption, guided setup, harness and dossier creation, profile and layout selection, governed work lifecycle, autonomous-delivery discovery and activation, validation and recovery, collaboration assessment, package installation, and deliberate upgrades.
---

# Octon Mini Project Bootstrap

Build an independent project snapshot. Transfer structure and validators, never
facts, identities, permissions, accepted decisions, evidence, or readiness.

## Start

1. Read every applicable target-repository instruction.
2. Inspect source control, files, implementation, and existing documentation.
3. Read only the references needed for the task:
   - dossier: `references/dossier-model.md`;
   - harness: `references/harness-model.md`;
   - profile/layout/collaboration: `references/profile-selection.md`;
   - creation, adoption, maintenance, recovery, upgrade:
     `references/generation-workflow.md`;
   - conversational, TTY, or answer-file setup and resume:
     `references/guided-setup.md`;
   - autonomous-delivery discovery, activation, effects, and recovery:
     `references/autonomous-delivery.md`.
4. Keep these axes independent:
   - Minimal, Standard, High Assurance: project risk and assurance;
   - solo, pair, tiny: one, two, or three-to-five write-capable humans;
   - `concurrent_work`: simultaneous humans, agents, or automation;
   - compact or separated: physical representation layout;
   - `review_first`, `balanced_autonomous`, `fast_delivery`, `custom`, or
     locked: delivery behavior, independently confirmed and unrelated to the
     other axes.

## Workflow

Use the source `scripts/octon.py` interface for bootstrap operations. Its
authoritative command inventory is projected to every generated
`.agent/commands.json`, where each command labels its bootstrap-source or
generated-project availability; primitive scripts remain advanced diagnostics.
The source checkout exposes the dispatcher through root `octon`; an installed
skill exposes it at `assets/octon-mini-source/octon`. From either launcher root,
use `./octon` on Unix/macOS, or invoke the same file as `python -B octon` or
`py -3 -B octon` on Windows. Generated projects use the same platform forms and
command identity with their generated-project command inventory.

- Guided setup: use `octon init|adopt|upgrade setup`. Determine mode from target
  evidence, stop on ambiguity, inspect read-only, and ask only unresolved
  dependency-eligible catalog questions—normally one to three at a time. State
  importance, choices, recommendation/rationale, allowed unknown or deferral,
  and blocked consequences without preselecting an answer. Keep observations,
  inferences, recommendations, selections, accepted-authority references,
  unknowns, deferrals, and runtime authorization distinct. Write a session only
  to an explicitly requested external path, use immutable successors, summarize
  before planning, and bind `--setup-session` into the existing planner.
- Guided one-command operation: use interactive `octon init`, `octon adopt`, or
  `octon upgrade` with an explicit target and external review directory. Let it
  inspect, ask only unresolved blockers, create immutable session/plan
  artifacts, show the shared summary and full digest, ask once for confirmation,
  then revalidate before apply. A collision or review gate must preserve the
  artifacts and return the Continuation Contract; never guess or auto-apply.
- New project: `octon init plan|apply`. Non-interactive planning requires an
  explicit profile flag or a reviewed setup-session answer. Interactive
  `octon init` proposes Minimal and requires confirmation. Archetypes, hooks, and collaboration are proposals; create a
  first task only from explicitly supplied purpose, scope, authority,
  acceptance, ownership, validation, and next action.
- Established project: `octon adopt plan|apply`. Use the default bounded semantic
  inspection; review every functional equivalent or authority collision.
  Adoption apply never overwrites existing content and leaves adoption
  `in_progress`.
- Routine work: generated `octon work start|block|close|reopen|handoff|resume`.
  Lifecycle writers allocate IDs and synchronize mechanical links and derived
  state, but never invent scope, authority, criteria, review, evidence, or
  external-effect authorization.
- Long-running work: use generated `octon work run` only after the optional
  `long-running-work` package is transactionally installed and separately
  adopted through a current accepted project decision. Bind one run to an
  existing task and exact path narrowing; compile deterministic context, accept
  only its current digest, perform effects only through existing transaction or
  `work.finish` boundaries, require current validation before progress, and
  resume only from marker-backed checkpoints. Status, context, resume, and
  explain are read-only. Never replay an ambiguous effect or treat run state as
  task scope, permission, acceptance, release, or readiness.
- Autonomous delivery: every generated project exposes `octon delivery` in
  `available_not_activated`. Research, context, applicability, planning,
  status, explanation, and activation preview are read-only and hook-free.
  Setup may recommend `fast_delivery` for most solo developers but never
  selects it. Deterministically draft the complete standing contract, display
  every field and digest, and require independent human confirmation of those
  exact bytes before serializing an external evidence record or activating the
  locally bundled package. Revalidate revocation, emergency stop, repository,
  branch, task, plan, action, release, evidence, the one selected compute mode,
  and limits before every effect. Metered API mode requires host-enforced
  ceilings. Included-subscription mode permits only current readable included
  allowance and no paid credits, API/pay-as-you-go billing, add-ons, or
  upgrades. Direct spending is zero; unknown compute or effect state blocks,
  and an unknown effect has zero automatic retries. Read
  `references/autonomous-delivery.md` for activation or delivery work.
- Governed completion: use `octon work finish plan|apply|resume` only after the
  project explicitly enables the shared engine and adopts the installed
  small-team Git workflow. Planning is read-only. Apply requires the exact
  digest, unchanged preconditions, and current task-scoped authorization for
  its exact external operations; external progress is resumable and cannot
  claim atomic rollback. The disabled-by-default completion event may dispatch
  only the exact read-only plan hook after successful task closure.
- Configuration: use `octon maintain hooks`, `octon maintain collaboration`,
  `octon maintain registry`, and source `octon maintain package` plan/apply flows.
  Package applicability, owner, trust decision, version, digest, and successful
  receipt evidence are mandatory.
- Validation: `octon check` is always read-only and never runs project hooks.
  `octon maintain refresh --apply` is the explicit generated-integrity writer.
  `.agent/scripts/run_project_checks.py --write-evidence` is the separately
  explicit hook/evidence writer.
- Routine proof reuse: only the explicit project-check writer may pass
  `--reuse-proofs`, and only for an exact current unexpired passing `read_only`
  proof. Input, tool/version, configuration, instruction, environment, effect,
  or freshness changes are misses. Never reuse at adoption/release gates or for
  external state or runtime authorization.
- Recovery: use `octon doctor`, then exact `octon transaction recover` for a pending
  journal or `octon transaction rollback` for an unchanged applied receipt. Never
  add or simulate a force bypass.
- Continuation and bundles: render human output concisely and use `--json` for
  strict automation. A covered refusal states mutation outcome, invalidated and
  preserved proofs, owning source, and one shell-free next argv. Bundle only
  compatible reversible repository-local plans through `octon transaction
  bundle plan`; reject overlaps, different authority/freshness/confirmation,
  nested bundles, and external or monotonic effects.
- Upgrade: use the applicable migration guide and `octon upgrade plan|apply`.
  The 3.1→4.0 path first creates a reviewed legacy inventory seed. Automatic
  upgrade is limited to safe additions, exact-pristine non-authoritative
  implementation assets, and derived regeneration.

Every plan is non-authorizing and content-addressed. Repository-local mutation
plans are instruction- and path-fingerprint-bound, staged, validated,
receipted, and exactly recoverable. Governed external completion instead uses
monotonic evidence-backed receipts and safe resume or fix-forward. Stale or
ambiguous plans fail closed.

Setup-session v2 preserves a prior value only while its declared question,
dependency, instruction, evidence, authority, and expiry bindings remain
current. Accepted project decisions may be reused only through the empty-by-
default project-owned decision-reuse registry and never as operation
confirmation, runtime authorization, external-action permission, or readiness.

## Non-negotiable boundaries

- The dossier is documentation, never permission.
- Generated policy is deny-by-default and cannot create authority.
- Existing target paths are never silently overwritten.
- Stable IDs and authority ownership are never silently reassigned.
- Generated snapshots remain independent and versioned.
- Optional long-running work is absent and inactive by default; a dormant
  dispatcher and unassessed trigger do not establish applicability or adoption.
- Autonomous delivery is available but externally locked by default. A profile,
  draft, setup answer, plan, projection, receipt, or stored record cannot create
  standing authority; only independent exact-digest human confirmation can.
- The installed source bundle includes the repository MIT-0 license; generated
  projects do not receive that `LICENSE` file or a project-wide license choice.
- `check`, detection, diagnosis, planning, and resume views are read-only.
- Guided question generation is target-read-only; session output is explicit,
  external to the target, non-authorizing, and secret-free.
- Generated-integrity and project-check evidence writes stay explicit and
  separate.
- External, destructive, credentialed, financial, legal, publication,
  deployment, communication, and production effects require explicit current
  authorization.
- Inferences remain sourced, timed, confidence-scored, limited, previewable,
  overridable, and recoverable.
- Structural conformance, harness adoption, and target-project readiness are
  separate claims.
- Trigger absence never means `not_applicable`.
- The Git portfolio is installed only when Git is explicitly selected; an
  uninstalled portfolio is not a runtime dependency.
- Generated work completion and its event hook start disabled. A completion
  event may automatically create only a read-only plan; it cannot apply.
- Require Python 3.11 or newer and strict JSON for the kernel.

## Commands

Run from the skill directory or use absolute paths.

```text
python3 -B scripts/octon.py init \
  --target /absolute/project/path \
  --review-dir /absolute/review-area

python3 -B scripts/octon.py init setup \
  --target /absolute/project/path \
  --output /absolute/review-area/setup-01.json

python3 -B scripts/octon.py init plan \
  --target /absolute/project/path \
  --project-name "Project Name" \
  --profile minimal \
  --layout compact \
  --output /absolute/project/path/.agent/transactions/plans/init.json

python3 -B scripts/octon.py init setup \
  --target /absolute/project/path \
  --session /absolute/review-area/setup-01.json \
  --record-plan /absolute/review-area/init-plan.json \
  --output /absolute/review-area/setup-02.json

python3 -B scripts/octon.py init apply \
  --target /absolute/project/path \
  --plan /absolute/project/path/.agent/transactions/plans/init.json \
  --accept-digest <reviewed-digest>

python3 -B scripts/octon.py adopt plan --help
python3 -B scripts/octon.py upgrade plan --help
python3 -B scripts/test_guided_setup.py
python3 -B scripts/validate_octon_mini.py
python3 -B scripts/test_acceptance.py
```

Inside a generated project:

```text
# Unix and macOS
./octon check
./octon work resume
./octon work finish plan
./octon doctor

# Windows equivalents use the same command identity and arguments.
python -B octon check
py -3 -B octon work resume

python -B .agent/tests/test_validate.py --tier fast
```

## Output contract

Report the Octon Mini version, profile, layout, collaboration assessment and
workflow-adoption status, setup-session digest/status, recommendations versus
selections versus accepted authority versus reused decisions, reinspection
classifications, unknowns/deferrals, continuation code/next argv, plan-summary
digest, exact plan/receipt
identity, collisions or deferred review, work-completion closure sequence,
validation proof hits/misses and complete-gate execution, bundle members,
phase timings, rollback/recovery path, and remaining adoption or readiness work.
Never describe setup, structural success, a cached proof, or a selected option as
permission or readiness.
