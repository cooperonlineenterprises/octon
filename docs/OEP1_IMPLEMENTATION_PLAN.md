# Octon implementation plan for OEP-1 and the ecosystem target

- **Plan revision:** 1.0.0
- **Recorded:** 24 September 2026
- **Status:** Planned; implementation has not started under this document
- **Strategy owner:** [SRC-DEC-0040](../ARCHITECTURE_DECISIONS.md#src-dec-0040)
- **Source baseline:** a1d528e1cfd4272c953c7d50ea6e9d16d283e002

## 1. Purpose and ownership

This is the source-owned implementation sequence for the accepted development
strategy. The strategy and its rationale live only in SRC-DEC-0040. This plan
connects that decision to concrete milestones, component dispositions, validation
and cutover requirements.

The [OEP-1 specification](../../../../../octon-project-standard/SPECIFICATION.md)
owns the finalized project structure and conformance obligations. The
[ecosystem specification](../../../../../octon_plectarium_quoris_ecosystem_specification/docs/05-octon-product.md)
owns the proposed product and integration boundaries. Their source-specific
successors and implementation must be reconciled before conflicting behavior is
changed. This plan creates no additional project lifecycle or runtime permission.

Keep the active repository and develop the successor implementation through
bounded candidate changes. Retain a usable baseline for comparisons and recovery.
Source edits do not hot-update an operating Octon installation. The filesystem
relocation of Octon's own checkout is a separate milestone from its product-code
redesign, so regressions remain attributable.

## 2. Component disposition

| Area | Treatment | Required evidence before cutover |
|---|---|---|
| Authority, accepted decisions, records and lifecycle | Preserve required meanings; extract cohesive modules | Positive/negative semantic fixtures, stable IDs, no broadened authority |
| Strict JSON, source identity and integrity | Review and reuse focused primitives | Duplicate/nonfinite rejection, deterministic identities, exact source/subject binding |
| Transactions, preimages, receipts and recovery | Preserve behavior while separating the implementation | Stale-plan refusal, interruption at commit boundaries, exact rollback/recovery, unknown-effect handling |
| Schemas, provenance and historical readers | Retain or explicitly migrate versioned contracts | Exact predecessor fixtures, preserved project records, declared reader support |
| Path handling | Introduce one OEP-1 layout resolver and binding contract | Confinement, reserved-name collisions, moved roots, platform paths and one state owner |
| Runtime packaging and generation | Replace large application-logic templates with pinned copied modules plus generated configuration | Exact output inventories, independent clones, no sibling imports, all supported profiles |
| Dispatcher and optional functionality | Establish narrow command/package interfaces and lazy loading | Optional-package absence, command discovery, unchanged mandatory behavior and clear unavailability |
| Directory and artifact selection | Integrate OEP-1's catalog into the existing profile-manifest mechanism | Complete applicable outputs, dependency resolution, no undeclared paths or fabricated project facts |
| Native host adapters and project checks | Preserve the adapter boundary and qualify target paths | Instruction discovery, source/projection ownership, shell-free declared commands, exact evidence |
| Quoris/Plectarium bridges and workers | Implement as separately qualified optional integrations | Correct delegation/attempt owners, direct/suite equivalence where applicable, refusal/cancellation/reconciliation |
| Obsolete code and compatibility machinery | Retire after consumer and recovery gates pass | Consumer inventory, preserved history/readers, replacement evidence and an explicit removal decision |

Code reuse is assessed per component. Required behavior does not imply preserving
the original module boundaries or every implementation line. Deliberate semantic
changes need their own accepted basis and migration tests; behavior comparisons
must distinguish intended changes from regressions.

## 3. Milestones and dependencies

All milestones below are planned. Gate descriptions are requirements, not passing
results. Evidence must identify the exact candidate revision and environment.

### IMP-0 - Establish the current baseline

Record the current source head, working-tree/ignored scope, package and schema
versions, environment and source-generation inventories. Preserve the exact
baseline through normal source history and verified recovery material. Do not
invent a published release or treat an existing tag as fresh qualification.

Run the existing source and acceptance checks declared in
[CI](../.github/workflows/validate.yml), including relevant identity/migration
fixtures. Measure the affected import/dependency graph, cold-start behavior and
existing benchmarks. Record pre-existing failures and their disposition.

**Exit gate:** Reproducible baseline report; necessary fixtures/history available;
known failures separated from new regressions; exact recovery route recorded.

### IMP-1 - Adopt source contracts and establish module boundaries

Depends on IMP-0. Reconcile the required source decisions, OEP-1 layout/catalog,
package boundaries and compatibility promises. Extract cohesive implementation
modules under the existing observable interfaces first. Introduce the path resolver
and compatibility shims with explicit roots and no guessed namespace equivalence.

Keep the source generation policy as the one inventory owner. Preserve the
distinction between authored records, immutable implementation, derived views,
local durable state and scratch material. Optional packages must not be imported
by unrelated basic checks.

**Exit gate:** Focused behavior/import/path checks pass; required old behavior is
preserved or explicitly amended; no second state owner or production registry.

### IMP-2 - Qualify one complete target slice

Depends on IMP-1. Produce one minimal OEP-1 project with the pinned runtime and
selected harness/dossier files. Demonstrate read-only inspection/checking, a real
task transition, an interrupted local operation, recovery and bounded rollback.
Then adopt a disposable predecessor fixture while preserving its project-owned
instructions, decisions, tasks, evidence and provenance.

The slice must exercise actual target paths and transaction boundaries. A rendered
directory tree, schema-valid plan or successful candidate self-check is insufficient.

**Exit gate:** Exact evidence for the complete slice, its negative cases and the
preservation comparison. Reassess individual component replacement where this
evidence exposes an unsuitable extraction boundary.

### IMP-3 - Complete profiles, storage and optional boundaries

Depends on IMP-2. Expand the catalog compiler, project-specific customization,
documentation representations, native adapters, ignore/export integration,
external worktree/recovery storage and canonical state binding. Cover supported
assurance profiles, relevant non-Git domains and independent clone/offline use.

Add optional packages through their declared applicability/adoption boundaries.
Develop ecosystem bridges as discrete qualified increments; a missing sibling
must not disable unrelated inspection or local recovery. Avoid expanding the
mandatory kernel to implement Quoris portfolio or Plectarium job semantics.

**Exit gate:** Applicable OEP-V01 through OEP-V07 and OEP-V12/OEP-V13 evidence;
registered commands and exact generated inventories; no nested worktree route.

### IMP-4 - Qualify supported migrations and real-project pilots

Depends on IMP-3. Implement source-version-specific converters for the observed
Blueprint and Octon lineages. Historical converter presence is not a claim that
it already supports the new target. Qualify reserved .octon collisions, custom
YAML controls, external state, interrupted conversions and receipt preservation.

Pilot an existing application, a Blueprint installation, a wrapped family member,
a non-Git project and an external-state configuration. Each pilot requires an
exact source/target map, current task authority, useful-work preservation,
baseline checks, after-checks and recovery evidence.

**Exit gate:** Applicable OEP-V08 through OEP-V12 and OEP-V15 evidence; complete
consumer mappings for the proposed supported migration set; unresolved semantics
block only their affected conversion and are not silently discarded.

### IMP-5 - Adopt the successor in Octon and expand the portfolio

Depends on IMP-4 for the relevant migration path. Migrate Octon's own management
environment and its repo-wrapper placement as an attributable project transition.
Use an accepted operating baseline while candidate tools run with isolated data.
Do not switch the active toolchain in the middle of a task without an explicit
transition and revalidation of ongoing work.

Expand to other projects through their validated plans. Quoris observes project
commitments; each project retains its own acceptance and state writer.

**Exit gate:** OEP-V14 self-development/promotion/recovery evidence and the relevant
project acceptance records. Uniform layout is observed, not inferred from intent.

### IMP-6 - Retire superseded active implementation

Depends on qualified replacement and consumer cutover evidence. Remove obsolete
active code, shims or setup entry points only after the retirement checklist below
is satisfied. Preserve historical versions, required readers and recovery assets.
The active Octon repository remains the maintained product repository.

**Exit gate:** The source tree has one active implementation for each concern;
remaining historical/reader surfaces have explicit support and retirement rules.

## 4. Validation and retirement gates

Use focused regression checks after bounded changes and the required source,
acceptance and platform checks at their declared integration/release gates. The
existing test inventory is a starting asset; add target-specific cases where the
new layout, ownership or recovery behavior introduces risk. Do not weaken a
negative test merely to make the successor pass.

Before retiring an implementation component, record:

1. The replacement revision, supported profiles and exact contract obligations.
2. Consumer mappings, old-artifact readability and declared compatibility horizon.
3. Required positive, negative, interruption, migration and recovery results.
4. Performance/usability comparisons against the declared baseline where affected.
5. Known failures, unassessed behavior and their explicit dispositions.
6. Cutover, rollback or authorized fix-forward instructions and preserved material.
7. Review and acceptance under the current source/project process.

Unknown external outcomes are reconciled by their original owner. Source rollback
does not reverse publication, revive revoked grants or authorize a duplicate effect.
No lifecycle or source decision can qualify itself through a generated report.

## 5. Reconsideration and reporting

Report progress through exact milestone evidence and the source's existing work
process. This document is not a duplicate live task ledger.

Reconsider a component's implementation when measured extraction complexity,
regressions, poor isolation or maintenance cost justify a replacement with an
equivalent required contract. A whole-product restart requires a successor to
SRC-DEC-0040 and an explicit consumer/history/recovery transition. Neither a high
line count nor one failed experiment establishes that conclusion.

The plan ends with a qualified successor implementation and completed supported
adoptions. It does not end merely when files have moved or templates have rendered.
