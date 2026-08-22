# Optional Long-Running Work Capability

## Status and boundary

This document specifies the accepted source architecture and implementation of
the optional `long-running-work` package under `SRC-DEC-0018`, accepted on
2026-08-20. That source decision does not grant permission, adopt the capability
for a project, release Octon Mini, or establish project or production readiness.

Octon Mini governs one external worker. It does not host or select a model,
store credentials, create project authority, or provide a universal action
runtime.

## Placement and trigger

- Package kind: `workflow_capability`.
- Package ID: `long-running-work`.
- Profiles: Minimal, Standard, and High Assurance.
- Installation: explicit content-addressed package plan/apply.
- Trigger: a project has an already authorized task that materially benefits
  from bounded unattended continuation.
- Adoption: a separate accepted project decision recorded after installation.
- Default: absent and inactive.

Assurance changes retained evidence and review strength; team size does not
select the package or its assurance behavior.

## Information ownership

| Concern | Owner |
|---|---|
| Goal, scope, authority basis, acceptance | Existing `TASK-####` record |
| Plan dependencies and readiness | Existing task and plan contracts |
| Current operator intent | `.agent/state/focus.json` |
| Derived current project state | `.agent/state/current.json` |
| Reversible repository mutation | Existing transaction system |
| Project-check results and reusable proofs | Existing project-check evidence store |
| Git/provider completion | Existing `work.finish` engine |
| Safe refusal and successor | Existing Continuation Contract |
| Run coordinate, limits, attempts | Package-owned active run record |
| Applicable reading list | Derived context manifest |
| Run transition chronology | Package history referencing existing records |
| Committed resume coordinate | Marker-backed package checkpoint |

The package does not introduce a mission store, task lifecycle, accepted
decision store, evidence store, current-state replacement, or generic event
platform.

Mutable package-owned operational state lives under `.agent/work-runs/`,
separate from the immutable installed payload under
`.agent/capabilities/long-running-work/`. Like transaction journals, work-run
state is excluded from general source fingerprints and validated by its own
strict package validator. This prevents progress bookkeeping from invalidating
the project evidence it references.

## Run lifecycle

The closed lifecycle is:

```text
planned -> active
active -> safely_paused | blocked -> active
active -> limit_stopped | cancelled | completed_with_current_evidence
active -> failed_known_outcome | stopped_partial_or_unknown
```

A limit stop is terminal for that run. Continuing with reviewed new limits
requires a separately created successor run; the exhausted record is never
silently reopened or edited.

`completed_with_current_evidence` additionally requires the owning task to be
completed with its current acceptance and closure evidence. A model response,
run marker, plan, transaction receipt, or validation proof cannot substitute
for task closure.

## Iteration protocol

An external worker repeatedly:

1. asks for status or the next deterministic phase;
2. compiles current context;
3. proposes one bounded step under the existing task;
4. uses an existing transaction or work-completion boundary for effects;
5. runs the explicit project-check writer when validation is required;
6. records exact plan, receipt, evidence, project, and result fingerprints;
7. lets the package evaluate progress and limits;
8. commits a checkpoint marker for the next safe coordinate; and
9. continues or stops according to the closed lifecycle.

The package does not interpret prose as proof that an operation occurred.

## Limits and stuck detection

Supported enforceable limits are maximum iterations, elapsed seconds,
consecutive failures, repeated identical failure signatures, no-progress
iterations, context bytes, and validation retries. Token, cost, provider, and
worker measurements may be reported by an external worker but remain `unknown`
when unavailable.

Elapsed time uses the local process clock. The public dispatcher does not
accept caller-supplied clock values; `--observed-at` exists only for direct
disposable-fixture execution and is rejected during ordinary package dispatch.
Reported token and cost totals, when supplied, must be nonnegative and
monotonic.

No progress is deterministic: a completed iteration has made no progress when
the committed task, project, governed receipt, and validation evidence basis is
unchanged and the committed coordinate did not advance. A caller-chosen result
label or changed claimed digest cannot establish progress by itself. Repeated
failure uses an exact normalized failure signature. A model judgment is never
the sole stuck detector.

## Context builder

The builder emits a strict JSON manifest containing exact references, digests,
information states, inclusion or omission reasons, precedence, bounded
selection descriptions, freshness, measured bytes, limitations, and unresolved
inputs. It reads only known governing paths, the owning task and its explicit
decision, plan, and evidence references, requested scope-path instruction
chains, and explicitly requested references such as a separately validated
current Context Pack manifest. The Context Pack owner retains its own validity,
consumer, rights, retention, and revocation checks.

It executes no hook, model, parser extension, network request, refresh, or
mutation. Required sources that exceed the budget block the context rather than
being silently omitted. Output is byte-identical for identical bytes and
arguments. Persistent receipts are not part of package v1.

## History and checkpoints

History records one meaningful transition per strict JSONL entry. Entries
reference existing task, plan, transaction, validation, continuation, context,
effect, and checkpoint records rather than copying them. A malformed tail is
reported and preserved; it is never silently rewritten.

Checkpoint content is written and validated before an atomic marker is
created. Only marker-backed content is committed. Orphan content is reported
and never adopted automatically. Resume revalidates current task bytes,
governing instructions, project fingerprint, authority reference, context
inputs, evidence, receipts, and limits. Changed or unknown state produces a
Continuation finding. Resume never executes or replays a task operation.
If the mutable run projection is malformed or interrupted, explicit recovery
can reconstruct it from the exact accepted marker digest. Activation commits a
new checkpoint; it does not leave an uncommitted active projection.

## Context and storage budgets

- active run projection: preferably fewer than 100 lines;
- resume output: one primary next action and fewer than two pages;
- context: explicit byte and item limits;
- history: at most 100 current entries before explicit archive/compaction;
- checkpoint: bounded metadata and references only;
- source content and raw reasoning: not copied by default.

Retention and removal are project-owned. Deactivation stops new mutation but
retains evidence. Uninstall refuses while an active run or undispositioned run
history exists.

## Performance and claim boundary

Context, status, resume, and explain target warm p90 below two seconds on the
10,000-file fixture. Existing scaffold, check, and fast-mutation thresholds do
not change. Failed samples remain evidence.

The first implementation was released in 4.1.0. A later dirty source-tree
exercise may demonstrate exact current behavior but cannot establish
final-candidate real-project maturity under `docs/REAL_PROJECT_VALIDATION.md`.

## Deferred capabilities

The package does not include a semantic repository map, generic output
trimmer, multiple workers, automatic scheduling, helper agents, MCP/ACP,
vision mining, contradiction graph, model routing, full filesystem snapshots,
hosted/database history, or automatic instruction/skill promotion. Each needs
a separate trigger, proof, placement, and decision.
