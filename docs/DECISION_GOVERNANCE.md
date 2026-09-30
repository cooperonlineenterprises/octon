# Architecture Decision Governance

This document is the authoritative domain-neutral definition of Octon Mini
decision-governance vocabulary and review practice. The strict
machine representation is
`shared/schemas/harness-decision-governance.schema.json`; generated Markdown
workbooks and reports are review projections, not competing authority.

The practice extends dossier type `DEC-0001` and the existing harness decision
store. It does not create a universal state machine, a second accepted-decision
system, permission, or readiness.

## 1. Authority and identity model

SRC-DEC-0041 adopts an authenticated human-or-delegated-agent decision actor for
the separately versioned successor described in [the governance foundation](GOVERNANCE_FOUNDATION.md).
That source-only foundation does not change the active record schema or create
accepted decisions in current snapshots. The distinctions and canonical owners
below remain: a recommendation/selection, durable technical choice and operational
authorization are separate. Live successor admission requires exact intent,
delegation, evidence and prior-policy control bindings; root ends remain principal-owned.

`.agent/decisions/governance-register.json` owns the inventory of material
decision questions, recommendations, owner selections, reviews, compatibility
findings, and the minimum closure sequence. Each entry has a stable
`DREG-####` tracking ID.

`.agent/decisions/DEC-####*.md` owns durable accepted decisions under the
existing harness lifecycle. The identities are deliberately different:

- `DREG-####` says which question and review are being tracked;
- `DEC-####` says which durable choice was accepted under valid project
  authority.

`.agent/decisions/reuse-policy.json` owns only the machine applicability of an
accepted decision value to a matching future setup question. Each `DRP-####`
entry binds exact decision bytes, authority source, scope, instructions,
dependencies, and freshness. It is neither a third decision lifecycle nor
permission: a recommendation, owner selection, accepted durable decision,
operation confirmation, and runtime authorization remain five distinct roles.
Superseded, revoked, expired, mismatched, or unresolved decisions are never
reused.

The relationship is a reference, not identity reuse. A project must not rename
a `DREG-####` into a `DEC-####`, infer an accepted record from a register state,
or let a workbook overwrite accepted authority. An accepted register entry
names its resolving `DEC-####`, and that durable record names the `DREG-####`
in `governance_register_refs`; unrelated accepted authority cannot resolve the
question.

These distinctions are normative:

1. A recommendation is an advisory conclusion from stated evidence.
2. An owner selection is the accountable owner's stated preference.
3. An owner selection is not accepted authority.
4. A selection becomes durable authority only through the project's required
   ADR or approval process and a resolving accepted `DEC-####` record.
5. Validation work, a specialist review, implementation detail, and
   operational readiness are not automatically architecture decisions.

Generation creates only an empty register. It never preselects an option,
owner checkbox, recommendation, decision, approval, evidence result, or
readiness conclusion.

## 2. Controlled classifications

### Decision types

- `architecture decision` — a material choice about boundaries, contracts,
  ownership, state, interfaces, quality attributes, or system structure.
- `product-policy decision` — a material owner choice about intended product
  behavior, eligibility, user-facing policy, or acceptable compromise.
- `specialist-policy decision` — a choice owned or constrained by a qualified
  specialist practice such as privacy, security, legal, accessibility,
  finance, safety, or operations.
- `vendor or platform decision` — a material choice of an external provider,
  platform, service, runtime, or portability boundary.

### Timing

- `required now` — blocks the currently authorized implementation boundary.
- `required later` — material but does not block the current safe slice.
- `evidence-first` — a material gate or comparison cannot be resolved without
  a precise evidence-producing step.
- `open owner decision` — evidence is sufficient for an accountable owner to
  choose, but the owner has not selected.

### Register lifecycle

- `open` — question is material and no selection has been made.
- `evidence in progress` — the required evidence-producing step is active.
- `owner selected — ADR or approval pending` — the owner selected an option,
  but durable authority does not yet exist and `authority_ref` remains null.
- `accepted — authority linked` — a resolving accepted `DEC-####` is linked.
- `deferred` — owner has explicitly deferred the material question with its
  consequences visible.
- `superseded` — a successor question or accepted decision replaced the entry;
  history and references remain.

These values are not the durable decision lifecycle. Durable decisions retain
`proposed`, `accepted`, `rejected`, `superseded`, and `deprecated`.

## 3. Register content and exact reconciliation

The register contains:

1. use and authority boundary;
2. executive summary and mechanically reconciled counts;
3. decision dashboard;
4. one decision object for every unresolved or tracked question;
5. a dependency-valid order containing every `DREG-####` once;
6. accepted decisions outside the register that constrain options;
7. matters explicitly classified as not open decisions;
8. one trade-off review for every registered decision; and
9. the minimum closure set before broad implementation.

Every decision sheet contains the exact question, practical importance, type,
timing, lifecycle, blocking effect, accepted constraints that cannot be
reopened in that question, exclusions, one to four credible options,
recommendation, owner selection, authority link, evidence plan, accountable
owner and reviewers, traceability, blocked work, reversal/successor conditions,
authoritative references, and limitations.

Options must be mutually distinct. The register may contain one option when
accepted constraints eliminate every other credible choice, provided the
option-set rationale says so. It must not fabricate an alternative to populate
a table.

Dashboard, decision objects, dependency order, and reviews reconcile by exact
ID. Dependencies and the minimum-closure graph are acyclic. Downstream
decision links are reciprocal so a missing dependency is visible.

## 4. Evidence-based trade-off review

Review every registered decision exactly once regardless of lifecycle,
including accepted, selected, open, evidence-first, deferred, and superseded
entries. Also inspect accepted decisions outside the register when they
constrain a registered option. Each `already_settled` entry names the affected
`DREG-####` records, and each affected review records that authority among the
constraints inspected.

Before scoring, reviewers identify missing, duplicate, improperly combined,
circular, and misclassified decisions. Existing accepted authority remains in
force until an amendment or successor decision is accepted. Contradictory
evidence supports a challenge; it does not silently rewrite authority.

The review records separately:

- the best option permitted under current authority;
- the best option supported by current evidence;
- evidence strength: `strong`, `moderate`, `weak`, or `none`;
- recommendation confidence: `high`, `medium`, or `low`;
- sensitivity to reasonable assumption and weighting changes;
- disconfirming evidence;
- worst credible failure;
- exit or migration path; and
- cumulative system-wide effects.

### Layer 1: non-negotiable gates

Each option receives `pass`, `fail`, or `unknown` for exactly these gates:

1. safety and deterministic correctness;
2. authoritative ownership and data integrity;
3. privacy, security, rights, consent, and isolation;
4. preservation of unknown or pending state;
5. applicable legal, specialist, and product-policy constraints; and
6. compatibility with currently accepted authority.

A failed gate disqualifies the option. A material unknown makes the option
evidence-first and normally makes the decision evidence-first when no other
gate-eligible option resolves the question. Cost, speed, convenience, and
performance never compensate for a failed gate. Gate-ineligible options do not
receive a balanced score or total.

### Layer 2: balanced attributes

Evaluate every gate-eligible option once against:

1. Safety and correctness
2. Authority and data integrity
3. Privacy, security, rights, and consent
4. Reliability, durability, and recovery
5. Simplicity and implementation risk
6. Flexibility and evolvability
7. Portability and compatibility
8. Performance and scalability
9. Operability and auditability
10. User effort and accessibility
11. Cost and resource efficiency
12. Reversibility and blast radius

Use `5` for strongly supports, `4` supports, `3` acceptable or neutral, `2`
material disadvantage, `1` serious disadvantage, `X` gate failure, `?`
insufficient evidence, and `N/A` genuinely inapplicable.

The default weight is 1 for every attribute. A non-default weighting requires
an explicit rationale. Reviewers state how overlapping considerations were
kept from being counted twice; the machine record admits each controlled
attribute only once. A total is optional, secondary, and valid only for a
gate-eligible option. It must remain absent when `X` or `?` is present and must
equal the visible weighted numeric scores when reported. Gate results and
evidence gaps remain visible beside any total.

## 5. Review disposition and compatibility

Disposition is exactly one of:

- `reaffirm`
- `reaffirm with clarification`
- `reaffirm pending evidence`
- `change recommendation`
- `challenge owner selection`
- `amend through successor decision`
- `supersede through successor decision`
- `reopen as evidence-first`
- `retain deferred`
- `no longer material`
- `not assessable yet`

Compatibility is exactly one of:

- `compatible`
- `tension`
- `conflict`
- `unknown`

Every tension, conflict, or unknown records affected authority or components,
practical consequence, issue type, preferred resolution, whether authority,
implementation, both, or neither pending evidence should change, migration and
blast-radius implications, accountable owner, reviewers, and the required ADR,
approval, spike, or validation evidence.

## 6. Classification guidance

Use the following corrections consistently:

- A test, spike, or specialist review produces evidence for a choice or gate;
  it is not the decision itself.
- Cumulative delivery stages are sequenced work, not mutually exclusive
  options.
- Independent contract, ownership, provider, and policy choices receive
  separate IDs rather than one umbrella decision.
- An optional feature is not an alternative to a mandatory foundation. Record
  the foundation as a constraint and decide the optional feature separately.
- Illustrative handoff schemas, state names, and examples remain subordinate;
  they cannot become authority merely by repetition.
- Accepted decisions remain current until contradictory evidence supports an
  accepted amendment or successor. Review does not reopen them silently.
- An owner selection remains pending until accepted authority is linked.
- Broad accepted direction does not hide a material exact contract choice.
  Register that contract question explicitly.
- Ordinary reversible implementation choices remain with implementers unless
  they have material architectural, risk, privacy, portability, cost, or
  operational consequences.

When evidence is insufficient, retain `unknown`. State a precise evidence
owner, evidence-producing step, expected result, and stop condition. A stop
condition says when the option or investigation must stop, escalate, or remain
unselected; “research more” is insufficient.

Examples:

| Misclassification | Correct treatment |
|---|---|
| “Run a storage spike” as the decision | Register the storage contract or platform choice; route the spike as its evidence-producing step. |
| “Prototype, pilot, then rollout” as three options | Keep them as cumulative delivery stages and compare only genuinely alternative approaches. |
| “Choose architecture, vendor, retention, and access policy” under one ID | Allocate independent decision IDs and link their dependencies. |
| “Optional dashboard” versus “mandatory audit log” | Keep the audit log as a non-reopenable foundation and decide the dashboard separately. |
| A handoff example names `pending` | Treat the name as illustrative until canonical authority defines the contract. |
| An accepted direction says “use an event interface” | Register any still-material exact envelope, ordering, ownership, or compatibility contract separately. |
| A local variable or reversible library helper | Leave it with implementers unless its consequences cross the materiality threshold. |

## 7. Requirement and quality-gate maturity

Requirements and quality gates may use this scoped assessment ladder:

1. `Architecturally specified`
2. `Evidence planned`
3. `Structurally validated`
4. `Demonstrated by executable implementation`
5. `Specialist-approved`
6. `Release-ready`
7. `Production-proven`

This is an evidence assessment, not a universal runtime lifecycle. The
validator checks only the declared level and evidence links; it never promotes
a record. Completion at one level does not imply any higher level. Level 3 is
bounded to structural conformance of the exact subject checked and cannot be
reported as level 4. Level 5 requires the applicable qualified specialist;
level 6 requires current project release gates; level 7 requires observed
production evidence for the exact subject and environment.

Every assessment records the corresponding basis kind: `architecture
specification`, `evidence plan`, `structural validation`, `executable
implementation`, `specialist approval`, `release gate`, or `production
observation`. Level 3 or higher requires a resolving pass `EVD-####` record.
The validator can check that declared classification and reference; it cannot
infer evidence adequacy, specialist competence, or operational truth.

Every report states separate conclusions for:

- architecture quality;
- documentation completeness;
- implementation evidence;
- specialist approval;
- release readiness;
- production readiness; and
- product efficacy or commercial viability.

Evidence in one conclusion does not transfer to another.

## 8. Authority and handoff contradiction review

Handoff is subordinate navigation and should link rather than copy mutable
status. Before reliance, reviewers must compare:

1. gate statements with `project-dossier/validation/QUALITY_GATES.json`;
2. accepted decision references with current accepted `DEC-####` records;
3. version and ownership statements with canonical sources and the artifact
   registry;
4. recommendations and owner selections with the governance register; and
5. implementation/readiness claims with current executable, operational, and
   specialist evidence.

When a copied status is unavoidable, an `octon-handoff-claim` marker permits exact
mechanical comparison for gates, durable decisions, register lifecycle, and
overall gate readiness. Semantic version/ownership language, whether a
recommendation is portrayed as adopted, and evidence adequacy remain mandatory
human review items; the validator does not pretend those judgments are fully
automatable.

## 9. Read-only assurance protocol

A read-only review:

1. records repository path, status, revision, and useful authoritative and
   generated-artifact fingerprints before review;
2. records pre-existing tracked, untracked, ignored, stale, and malformed
   state;
3. runs only explicitly authorized read-only commands from the project
   contract;
4. records exact argv/command, start/end, exit status, result, and side effects;
5. identifies unavailable and skipped checks with reasons;
6. separates structural validation from executable and operational evidence;
7. does not refresh generated artifacts, execute project hooks, write evidence,
   install packages, or query external systems without separate read-only
   authorization;
8. reports stale authoritative inputs and affected projections without
   rewriting them;
9. repeats the same status, revision, and fingerprint observations afterward;
   and
10. states whether files or external systems changed.

Any review-caused file or external-system change prevents a read-only assurance
claim. Before/after comparison distinguishes pre-existing drift from current
operation mutations. A legitimate source remains in fingerprint and integrity
scope even when its change makes a projection stale.

Diagnostics distinguish, where evidence permits:

- pre-existing repository drift;
- stale generated projections;
- malformed authoritative source records;
- missing implementation hooks or evidence; and
- mutations caused by the current operation.

## 10. Minimum closure sequence

The minimum closure set is the smallest dependency-ordered combination of:

- ADRs or approvals;
- owner decisions;
- evidence-first spikes;
- contract drafts;
- specialist reviews; and
- gate evidence

required before broad authoritative implementation may proceed.

Each `CLOSE-####` item names its decisions, dependencies, owner, completion
evidence and resolvable evidence references, status, and whether it blocks
broad implementation. A completed ADR/approval resolves to accepted authority;
a completed evidence-first spike or gate-evidence item resolves to passing
`EVD-####` evidence; and a completed owner-decision item resolves to a recorded
owner selection without treating that selection as accepted authority. The register
lists every closure item exactly once in a valid dependency order and declares
parallel groups. It separately lists bounded work safe before full closure,
such as read-only analysis, reversible prototypes isolated from authority, or
contract drafting. The boundary states what must not begin.

Closure items are not complete because a template is filled, an option is
selected, a structural validator passes, or a plan exists. They close only
with the specified project-owned authority and evidence.
