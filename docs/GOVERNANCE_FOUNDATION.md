# Intent and delegation foundation

Status: versioned, source-only successor contracts and executable shadow
qualification. This is not a released kernel, live authorizer, project adoption,
grant activation or installed-consumer upgrade. Source decisions SRC-DEC-0041,
SRC-DEC-0042 and SRC-DEC-0043 own the adopted successor direction and its limits.

The normal human input is intent. A legitimately established delegation bounds
which technical decisions and effects may proceed. Intent, a technical DEC,
successful validation, and a stored grant-shaped document remain distinct from
operational authorization. Existing project-local task, decision, evidence,
transaction, run and completion owners remain canonical.

## Current versus successor behavior

The 5.0 identity candidate and kernel 4.2 generated snapshots retain their
existing active contracts, human-only clauses, single-run limit, exact grant
activation, and source/release gates. This foundation does not reinterpret their
records. Its files default to source-only under the existing profile manifest;
the ordinary generator and project command inventory do not install or dispatch
them. An installed bootstrap source bundle may retain these research/qualification
sources, just as it retains other source governance material. That is not an
active capability in generated projects.

The behavioral successor requires a separately versioned runtime/package release,
explicit consumer conversion, protected issuer/evaluator boundaries and host
qualification before live use. Do not fold those changes into the identity-only
release. No root grant is issued, renewed or widened by this PR or its fixtures.

## Ownership and replacement wording

| Concern | Canonical owner and successor contract |
|---|---|
| Root intent | Project intent registry; semantic ownership stays with the principal. A revision preserves original expression, interpretation, assumptions, acceptance basis, principal/source reference and supersession. A dossier explains and references it, never owns a competing root. |
| Derived work | Existing task/work owner. Add intent-revision and derivation links through a versioned record migration. The work graph remains a projection. |
| Durable technical choice | Existing DEC owner. An authenticated human or delegated agent actor may accept a material technical decision only when current authority covers its class and intent scope. Admission binds actor, exact intent, applicable authority decision, evidence and protected constraints; meaning changes require explicit supersession. Routine choices use rationale events. |
| Grant issuance | Independent principal/authorized issuer channel outside producer control. Grant bytes evidence that authority; record shape, digest and a successful test do not create it. |
| Action coverage | One Octon project authorization concern, evolved from standing-delivery coverage. Callers consume its contract and enforce operation-specific preconditions; they do not implement competing root permission stores. |
| Usage and reservations | Existing coordinator/usage owner after its concurrency successor is qualified. Shadow inputs are snapshots of proposed accounting, never a second mutable ledger. |
| Evidence and views | Existing evidence admission and event owners. A verifier owns its observation; Octon owns whether it satisfies an obligation. Current/Past/Now/Next projections carry references and freshness, without becoming decision or work authority. |

Replacement rule for delegated technical decisions:

> An accepted technical decision selects an authorized means toward its governing
> intent. It does not grant permission for effects. Root ends, outer delegation,
> principal reservations and genuine qualified-human obligations change only
> through their proper authority. Child delegation can only narrow its parent.

The active legacy DEC schema is not extended in place. Actor/admission fields
need a successor record version and an exact migration; this first slice supplies
their immutable intent/work/action bindings without creating a second DEC store.

## Source contracts and identity

`octon.json` registers the foundation at
`shared/source-contracts/governance-foundation-v2.schema.json`. This is the single
current source registration for these closed documents. The original v1 container
and fixture bytes remain retained, as required by SRC-DEC-0043; their historical
registration is not rewritten.

| Version | Meaning |
|---|---|
| `harness.intent-revision.v1` | Immutable intent identity/revision and explicit interpretation. |
| `harness.project-delegation.v1` | Declared principal-to-subject scope, exact intent/parent binding, validity, budgets, decision reservations and non-weakenable obligations. |
| `harness.action-coverage-request.v1` | Exact actor, work/intent, plan, expected state, policy, scope and proposed usage for one material action. |
| `harness.shadow-control-snapshot.v2` | Supplied policy, revocation, stop, obligation and explicitly coherent occupancy/accounting observations. |
| `octon.governance-shadow-input.v2` | A bounded hypothetical bundle; no implicit lookup of referenced project or authority state. |
| `octon.governance-shadow-result.v2` | Content-bound coverage evidence that always refuses to claim execution authority. |

The intent, delegation and action v1 definitions are unchanged. The control,
input and result versions change explicitly because the required observation
shape and coverage meaning change. Default evaluation rejects v1 and mixed
input/control versions with the existing non-authorizing error envelope and
exit 2. A v1 result cannot satisfy v2 qualification. The exact old reader, schema,
dependencies and fixture at `360a8dbcd0d7e0f2524a321f3b38dce6ba3e4078`
reproduce `covered-v1-result.json`; the old container and `covered.json` remain
byte-identical. No automatic converter is supplied and no active consumer
contract, record ID, grant meaning or kernel version is changed.

IDs are opaque within their typed project scope. Fixtures allocate no live
project IDs and do not add a new prefix to kernel 4.2. Existing TASK/DEC and
external source-host work identities are referenced, never reassigned. Source
decision IDs 0021–0038 remain reserved; 0039 and 0040 retain their meanings.

Canonical digests use the existing source convention: strict JSON, sorted object
keys, compact separators, UTF-8, no nonfinite numbers, and a final newline. Record
digests omit only their own `digest` member. This is byte binding, not a signature
or a public cross-language canonicalization claim. Material source/plan/state or
policy changes require new bound input and a new evaluation.

## Shadow evaluator

Run from the source checkout, with an explicit input file:

```text
python3 -B skills/octon-project-bootstrap/scripts/governance_shadow.py --input skills/octon-project-bootstrap/fixtures/governance-shadow/covered-v2.json
```

It reads that bounded regular JSON file and its own source schema, then emits a
result on stdout. It resolves no authority/evidence/work references, writes no
project or control records, runs no hooks/worker/provider commands, and creates
no leases or reservations. A successful evaluation returns exit 0 even when
coverage is `uncovered` or `indeterminate`; malformed input returns exit 2. Process
success is not admission. Rejected input values are not echoed in diagnostics.

Every result has `permission_grant: false`, `execution_authorized: false`,
`authority_effect: none`, `authority_authentication: not_performed` and
`reservations_created: false`. `covered` means only that the supplied hypothetical
facts satisfy the modeled constraints at the supplied evaluation time. Legacy
delivery activation rejects this schema. The fixture's year-2030 timestamps are
simulation data, not a claim of current authority or an implicit clock override.

Evaluation enforces:

1. Exact intent/work/action/control digest bindings, project identity, actor to
   terminal-subject identity, and unchanged expected state/current-policy digest.
2. One ordered, acyclic parent chain with unique IDs, exact parent digests and
   issuer-to-parent-subject links. The root binds the intent principal. External
   role enrollment and authentication are not inferred from matching strings.
3. Child subset scopes across resources, operations, decision classes,
   environments, data, destinations and credential categories; narrowed validity,
   limits and subdelegation depth; retained obligations and reservations.
4. Exact scope intersection with the supplied current project/host/provider
   restriction projection. Resource selectors are exact IDs; wildcards and
   implicit path/role expansion are unsupported.
5. Exact project control-source and authority-epoch bindings, half-open grant
   validity, bounded observation freshness, ancestor revocation
   and emergency stop. Stale or missing required facts cannot become a pass.
6. Shared period **and cumulative per-run** committed/reserved usage plus the
   proposed request, across every ancestor. Unknown usage is not zero. Grant,
   run and declared compute-unit bindings must match; limits cannot change units
   silently. A material request consumes at least one action count.
7. Exact-run membership and concurrency ceilings under every ancestor, and
   exact-action-bound, individually fresh obligation
   observations. Mandatory failures
   refuse coverage; missing/unknown evidence is indeterminate. A qualified-human
   obligation is not satisfied by an agent result. Human headcount/model
   confidence never replaces an obligation.

### Occupancy and accounting observations in control v2

These fields belong only to the source-only control projection. They do not
extend or reinterpret `harness.project-delegation.v1`, authenticate a run,
create a ledger or implement admission/reservation effects. The existing
coordinator remains the eventual owner of the supplied observations.

Each exact grant/run-bound budget snapshot declares `run_admission_state`:

| Observation | Starting the run | Continuing the run |
|---|---|---|
| `not_admitted` | Run usage must be zero; include one new slot in the ceiling check. | Uncovered. |
| `active` | Uncovered; the immutable run identity is already admitted. | Active count must be at least one; check the ceiling without adding a slot. |
| `ended` | Uncovered; the immutable identity cannot be reused. | Uncovered. |
| `unknown` | Indeterminate. | Indeterminate. |

The run reference must match the requested run under every ancestor. A zero
active count contradicts declared active membership. Unknown membership or
active counts cannot become zero or coverage, even when limits are zero.

`accounting_observation: coherent_at_observed_at` explicitly declares that all
usage and occupancy observations describe the control snapshot's `observed_at`.
`unknown` is indeterminate. Existing control freshness still applies. This
declaration is hypothetical; it does not prove a coherent capture or prevent
an in-flight change.

Each `period_accounting` supplies its own half-open `start`/`end` interval and
whether its committed/reserved observations include descendants. Both the
observation and evaluation must fall inside the declared interval. The interval
is not derived from grant validity, and this projection does not redefine which
accounting period a v1 grant's limits govern. A protected live reader must prove
that association through the existing policy/accounting owner. Missing interval
facts or descendant inclusion, and unequal ancestor/child intervals, are
indeterminate; the prototype never assumes that different periods are comparable.

`run_accounting: cumulative_including_descendants` declares cumulative
committed/reserved usage for the exact immutable `run_ref` through the common
observation, including descendant usage. `unknown` is indeterminate. For known,
coherent same-run observations, each ancestor committed **and** reserved
component must individually dominate its descendant for actions and declared
compute units. The same component rule applies to explicitly comparable period
observations. Equal or larger legitimate ancestor values pass; unknown counters
cannot cover. Components are compared separately because the hypothetical
snapshot declares a coherent commitment/reservation phase, not independently
timed transfers. The evaluator does not sum chain levels, which may describe the
same action.

`run_period_relation` separately declares whether the entire cumulative run is
within the supplied period or spans a period boundary. For
`whole_run_within_period`, the existing run-versus-period component inequalities
remain mandatory. For known `cross_period` observations, lifetime run usage may
legitimately exceed the current period's usage: the evaluator checks whole-run
and current-period limits independently without falsely equating their counters
or resetting lifetime usage. `unknown` is indeterminate. These are control-side
comparability facts, not a new meaning for the unchanged v1 grant limits; a live
reader must establish them through the existing accounting owner.

The v1 period-only probe lacked explicit interval/inclusion facts and remains
historical ambiguity. The v2 clarification does not relabel it as an additional
confirmed v1 defect. Continuing nonexistent runs and same-run ancestor
under-accounting are the two corrected shadow consistency defects. All outcomes
continue to withhold permission, authentication, reservations and execution.

`work_binding` is a non-authoritative projection of an existing task contract,
not a task database. The source evaluator does not authenticate the supplied
principal, confirm accepted intent, inspect the referenced task or evidence,
prove that declared scope describes the actual code, or prove human qualification.
It does not model money/provider billing modes: `compute_unit_ref` is an explicit
synthetic/project unit that must remain identical throughout the chain. Legacy
metered/subscription grants retain their original exact meanings and controls.

A live successor must supply those facts through protected current readers,
derive action classification from a trusted operation contract, revalidate at
the effect boundary, and atomically reserve resources through the one coordinator.
Two queries against one snapshot are not two valid reservations. The old delivery
evaluator and this prototype must not become parallel active authorizers: live
cutover must replace/adapt the existing owner once, with qualified legacy readers.
An epoch or a restored ledger cannot attest its own currentness. A live recovery
needs an independently current authority/high-water or an authorized non-reused
generation, plus reconciliation of surviving processes and external effects.

## Compatibility and adoption gates

The foundation's adversarial tests run under the existing source validation gate.
They also prove that legacy activation rejects the new records, the current
upgrader refuses an old origin without mutation, and an independent generated
project contains none of the new contracts and remains non-authorizing.

Current source generation rules, templates, packages, consumer wire schemas,
VERSION and kernel compatibility are unchanged. Current source installation and
all six generation combinations remain subject to the full existing validation
and acceptance suites. An available schema/helper is not a supported live upgrade.

Plectarium's repository harness is a customized Project Blueprint/kernel 1.0.0
snapshot, not a supported direct input to the current 5.0 upgrader. An existing
released conversion chain may be reused only after it is demonstrated on the
exact snapshot. Otherwise the existing transaction owner needs a versioned
conversion with preservation/interruption fixtures. This PR implements neither
conversion nor project adoption. Keep its current invocation-only DEC-0001 until
the project adopts its own standing-delegation successor. Product policy-or-human
plan authorization already permits policy decisions and needs no reversal.

See `GOVERNANCE_FOUNDATION_BASELINE.md` for inspected source/consumer boundaries.
The existing OEP-1 implementation plan continues to own sequencing. After this
foundation, qualify the runtime/manifest slice and consumer conversions, protected
control/worker isolation and one multi-run coordinator, then ChangeSets and the
existing completion owner's integration successor. Actual grants and enforcement
precede activation. Plectarium views remain optional and follow independent core
qualification. No step imports a specialist engine or new global orchestrator.

## Remaining successor dispositions

| Architecture proposal area | Disposition in this slice |
|---|---|
| O-AUTONOMY | SRC-DEC-0041 selects intent-linked delegated technical actors for the versioned successor; current consumers remain under their adopted contracts. |
| O-DELEGATION | SRC-DEC-0042 defines non-amplifying coverage and the protected live-admission gate; executable work here is shadow-only. |
| O-RECORDS | SRC-DEC-0043 registers source-only records/projections and preservation requirements. |
| O-COORDINATION | Still requires a specific successor to SRC-DEC-0018 and qualified host/reservation implementation; no real multi-run dispatch added. |
| O-SOURCE / O-LIFECYCLE | Still require successors to SRC-DEC-0013 and source Git policy, ChangeSet/composition identities and candidate-versus-delivered closure. Existing integration owner remains. |
| O-RELEASE | SRC-DEC-0020 and its evidence/effect boundaries remain active until their explicit consequence-based successor. |
| P-HARNESS | Project-owned adoption/conversion pending; no Plectarium policy or record bytes changed. |
| P-AUTHORIZATION | Preserve exact policy-or-human plan semantics; versioned issuer/revocation/reservation bindings remain suite-owned follow-up work. |
| P-DEVELOPMENT-VIEW | Optional versioned export/command-relay contract remains pending; no duplicate project work authority. |
