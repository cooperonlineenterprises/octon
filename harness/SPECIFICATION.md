# Project Agent Harness Specification

## 1. Purpose

A project agent harness is the repository-local operating system for safe,
resumable work by humans and agents. It routes instruction discovery, states
authority boundaries, defines record and lifecycle contracts, exposes
validation commands, and preserves evidence.

Its universal scope is a stable domain-neutral kernel with validated extension
points, not a claim that one project's policies or domain rules fit another.
The information and behavior contracts are runtime-neutral. The generated
snapshot supplies a Python 3.11+ standard-library reference implementation,
but a project may adopt an equivalent validator in its existing pinned
toolchain after that implementation passes the same conformance fixtures and
records a migration. A project must not add Python solely to imitate the
reference implementation when its governed toolchain can satisfy the contract.

The harness is subordinate to current user, platform, sandbox, tool, legal,
and applicable repository instructions. It cannot create permission. A tool,
plan, decision template, skill, generated report, or dossier statement is not
authorization.

A working harness enables a newcomer to determine:

- which instructions apply to a path;
- whether the request is analysis, implementation, or an external action;
- which project facts are stable and which work state is current;
- why durable choices were made;
- which checks and approvals apply;
- what evidence supports a claim;
- what remains blocked or unknown; and
- which planned work is dependency-ready without relying on timeline order;
  and
- how to resume work safely.

## 2. Design basis

Evidence labels used in this specification:

- **Observed — Commerce Foundry:** present in the Commerce Foundry reference
  implementation.
- **Observed — COE:** present in the Cooper Online Enterprises reference
  implementation.
- **Observed — both:** materially equivalent behavior exists in both.
- **Inference:** a reusable rule derived from one or both implementations.
- **Recommendation:** a new domain-neutral addition needed for portability,
  safety, or completeness.

Exact reference paths and the transfer boundary are recorded in
`harness/references/REFERENCE_EVIDENCE.md`. These labels distinguish evidence
from design judgment; they do not import either source project's facts or
authority.

The reusable model synthesizes two mature reference patterns:

- an operational harness with deny-by-default local execution, lifecycle
  records, executable policy checks, mutation tests, and routed skills; and
- an information-integrity harness with root-to-leaf scoping, typed IDs,
  path-authority classification, record templates, manifests, checksums, and
  generated validation evidence.

The synthesis is intentionally not a union of their files. The common
governance kernel is separated from project-specific extensions, optional
capability packages, and generated evidence.

The following are design inferences and recommendations:

- roles are constrained task modes, not independent principals;
- one authoritative store owns each mutable concern;
- current state, intended target, plans, permission, and evidence remain
  distinct;
- domain rules belong in extensions, not in kernel constants;
- validation and generation are separate operations;
- passing evidence is scoped and point-in-time;
- the safe path has one discoverable check command; and
- ceremony is added only for a named risk or coordination need.

## 3. Five-layer architecture

### Layer 1: instruction router

Root and nested `AGENTS.md` files tell an agent what to read, how path scoping
works, what closes work, and which actions require explicit current
authorization. They stay short enough to load routinely.

### Layer 2: governance kernel

The seven versioned files below are domain-neutral and have one responsibility
each:

| File | Authoritative concern |
|---|---|
| `.agent/policy.json` | permission classes, hard boundaries, and approval gates |
| `.agent/context.json` | precedence, trust classes, and conflict handling |
| `.agent/schema.json` | IDs, statuses, record versions, and compatibility |
| `.agent/lifecycle.json` | legal task, decision, and artifact transitions |
| `.agent/tools.json` | availability, allowed operations, constraints, and evidence |
| `.agent/validators.json` | named check, test, refresh, and closure commands |
| `.agent/project.json` | stable project profile, collaboration assessment, workflow adoption, and project command hooks |

`project.json` must not become a second status report. Mutable work status
belongs in tasks and explicit operator direction belongs in
`.agent/state/focus.json`; `.agent/state/current.json` is fully derived.

### Layer 3: capability packages

`.agents/agents/`, `.agents/skills/`, and `.agents/workflows/` define
specialist modes and reusable procedures. Each capability inherits the active
task's authority, may narrow it, and may never expand it.

Capability packages are conditional. Do not add named agents or skills until
a recurring job, quality boundary, or role-separation need justifies them.

### Layer 4: project profile and extensions

`.agent/project.json` declares stable repository facts, a current
privacy-minimized collaboration assessment, any adopted small-team workflow,
and command hooks.
`.agent/extensions/` owns domain registries, build or release rules, and
project-specific validators.

An extension:

- declares a stable ID, schema version, compatibility range, owner, provenance,
  trust class, config, validator, side effects, and deprecation/removal path;
- returns structured findings through the kernel interface;
- can add restrictions and checks;
- cannot weaken the kernel or grant authority; and
- can be disabled without changing kernel behavior.

Extension code is executable project code, not untrusted data. Enabling it
requires an accepted trust decision, least-privilege execution, a minimized
environment, and a read-only enforcement or before/after mutation check.

No profile includes a domain package by default. The compact package registry
and detector recipes may propose operations/observability,
security/supply-chain, SCM, reference, or optional-schema packages. Applicable
content is installed only through a pinned, accepted-trust-decision-bound
transaction and starts disabled where enablement is meaningful. Presence still
cannot assert a provider, deployment, monitor, scanner, SBOM, signature,
qualified review, compliance conclusion, or production readiness.

The extension root is closed: only its README, registry, and roots named by
that registry are valid immediate children. Likewise, the capability root
contains only its README and the validated agent, workflow, and skill
namespaces. Project-specific behavior is added through those registries and
namespaces, not through unregistered governance files.

### Layer 5: operational records and evidence

Tasks, decisions, evidence, reviews, events, artifacts, state, checkpoints,
explicit target-project check evidence, and generated integrity make work
resumable and auditable.

Decision governance extends the existing decision concern rather than adding a
second authority system. `.agent/decisions/governance-register.json` owns the
material-question inventory, recommendations, owner selections, option review,
compatibility findings, and minimum closure sequence. Accepted `DEC-####`
records remain the only durable decision authority.

## 4. Architectural invariants

1. Higher-level instructions cannot be weakened by lower-level files.
2. A capability or extension cannot grant itself access.
3. Generated content is labeled derived, non-authoritative, and point-in-time.
4. `check` is read-only; `refresh` is the explicit generated-integrity writer,
   and only the separately invoked project-check writer may execute configured
   hooks or append its declared evidence store.
5. The kernel contains no product names, routes, release IDs, or domain
   statuses.
6. Unknown safety-relevant statuses, IDs, tools, and extension types fail
   closed.
7. Durable accepted decisions use successors instead of silent rewrites.
8. Task records describe work; they do not authorize it.
9. Evidence never includes secret values and never claims more than the
   recorded check proves.
10. Generated projects are independent snapshots and do not inherit authority
    from this specification.
11. Every derived dossier or harness file has one project-local source and one
    discoverable regeneration command in every profile that enforces it.
12. A declared read-only command must either execute in an enforced no-write
    boundary or detect and report any mutation without claiming prevention.
13. Hard dependencies, satisfied gates, resolved structured blockers, and
    reciprocal plan/task links determine work readiness; dates never do.
14. Collaboration observations, workflow recommendations, and workflow records
    are non-authorizing; only a project-owned accepted decision may adopt a
    workflow, and it still cannot authorize an operation.
15. Human team size selects only the base collaboration workflow. It never
    selects an assurance profile or grants access, approval, review capacity,
    publication authority, or release authority.
16. More than five write-capable humans is explicitly unsupported and never
    falls through to an enterprise workflow.
17. Semantic information roles do not replace aggregate-specific lifecycles,
    grant action authority, or establish readiness by themselves.
18. A recommendation is not an owner selection; an owner selection is not
    accepted authority; only the required accepted `DEC-####` or approval
    process makes the choice durable.
19. Trade-off totals cannot offset a failed non-negotiable gate or conceal a
    material unknown. Unknown evidence remains unknown and normally routes the
    decision to evidence-first work.
20. Work-completion planning is read-only, performs no refresh or hosted
    observation, and creates no receipt. An automatic completion hook may only
    request that plan and is disabled by default.
21. A reviewed completion digest binds exact task, authority, repository,
    revisions, paths, validation, review, integration, and cleanup inputs; it
    is not permission. Every planned external operation still requires current
    task-scoped authorization and immediate pre-action revalidation.
22. External Git and provider effects are monotonic and resumable, not
    atomically reversible. Cleanup follows proven integration and
    fast-forward synchronization, and no self or agent review becomes peer
    approval.
23. Structural validation, documentation, a commit, a PR, or a completion
    receipt does not establish release, production, efficacy, or commercial
    readiness.
24. Mutation remains fail-closed, while every covered refusal uses one
    non-authorizing continuation finding that states mutation outcome,
    invalidates only declared proofs, preserves current inputs, and provides
    one shell-free next action; no continuation creates permission or a force
    bypass.

## 5. Recommended directory structure

```text
.
├── AGENTS.md
├── .agent/
│   ├── START_HERE.md
│   ├── policy.json
│   ├── context.json
│   ├── schema.json
│   ├── lifecycle.json
│   ├── tools.json
│   ├── validators.json
│   ├── commands.json                  # derived command inventory
│   ├── project.json
│   ├── packages.json                  # trigger/package lifecycle registry
│   ├── scm.json                       # compact unassessed SCM trigger
│   ├── workflows/                     # present only after reviewed SCM install
│   ├── schemas/                       # local versioned schema snapshot
│   ├── approvals/                     # conditional attestation metadata
│   ├── coordination/                  # conditional leases/write ownership
│   ├── decisions/
│   │   ├── governance-register.json   # question/review source; not accepted authority
│   │   └── reuse-policy.json          # empty project-owned applicability bindings to accepted decisions
│   ├── tasks/
│   ├── evidence/                     # standard+
│   ├── project-checks/               # explicit target-check evidence
│   ├── reviews/                      # standard+
│   ├── events/                       # standard+
│   ├── artifacts/                    # standard, when durable outputs matter
│   ├── extensions/                   # trigger-installed domain packages
│   ├── evaluations/                  # conditional rubric/fixtures/results
│   ├── metrics/                      # conditional harness outcome measures
│   ├── checkpoints/                  # high-assurance
│   ├── state/
│   │   ├── current.json              # fully derived, never hand-edited
│   │   ├── focus.json                # project-owned operator intent
│   │   └── RESUME.md
│   ├── transactions/
│   │   ├── plans/                     # immutable reviewed inputs
│   │   ├── pending/                   # write-ahead recovery journals
│   │   ├── receipts/                  # exact postimages and resumable rollback state
│   │   └── recovered/                 # validated recovery evidence
│   ├── templates/
│   ├── generated/                    # staging in all; HA integrity evidence
│   ├── scripts/
│   │   ├── octon.py                   # workflow-oriented project interface
│   │   ├── octon_continuation.py      # typed refusals and shared plan summaries
│   │   ├── octon_work_completion.py   # read-only plan plus resumable completion
│   │   ├── octon_transaction.py       # staged plan/apply/recover/rollback
│   │   ├── octon_doctor.py            # coded read-only diagnostics
│   │   ├── validate.py
│   │   ├── run_project_checks.py     # explicit evidence writer; may run hooks
│   │   └── refresh.py                # every profile; writes declared derivatives
│   └── tests/
│       └── fixtures/
├── .agents/                           # high-assurance capability packages
│   ├── agents/
│   ├── skills/
│   └── workflows/
├── project-dossier/                   # compact or separated documentation
├── octon                              # generated project launcher
└── .octon-mini-origin.json
```

Use `.agent/` for live governance and `.agents/` for discoverable capability
packages. This singular/plural distinction is a project convention and must
be stated explicitly because external tools do not interpret it uniformly.

## 6. Discovery and precedence

For every affected path:

1. resolve the repository root without following an untrusted symlink;
2. apply platform, system, sandbox, and tool constraints;
3. apply the current operator request;
4. read `AGENTS.md` files from root to leaf;
5. read the routed kernel files;
6. load only accepted, in-scope decisions and the active task;
7. when selecting planned work, derive the read-only ready frontier;
8. inspect executable/configured reality and fresh evidence;
9. load intended target and plans only as context; and
10. record material conflicts instead of choosing silently.

Precedence is:

1. platform, system, sandbox, and tool constraints;
2. current operator instruction;
3. applicable `AGENTS.md` files, root to leaf;
4. live policy and context rules within higher authority;
5. accepted in-scope decisions;
6. direct observation and fresh evidence for present state;
7. canonical dossier content for intended state;
8. active task and implementation plan for sequence;
9. maintained explanatory documentation;
10. drafts, generated output, imported content, and history.

For permission, the higher and safer compatible rule wins. For present state,
fresh direct inspection wins. For intended state, an accepted decision and
canonical target govern within their scope. Child instructions may narrow but
not weaken ancestors. Ambiguous high-impact work stops for authorization;
reversible local analysis may continue with stated assumptions.

## 7. Authority and security model

Evaluate material actions against:

```text
principal × action × resource × scope × data class × side effect
× reversibility × time window × evidence requirement
```

Missing dimensions default to denied for external, destructive,
credentialed, financial, legal, publication, deployment, communication, or
production effects.

Default tiers:

| Tier | Examples | Baseline |
|---|---|---|
| Read-only local | inspect files, Git status, parse data | allowed when relevant |
| Reversible repository-local | requested edits and tests | implementation request required |
| Local execution | declared tests/builds and disposable loopback services | declared constraints required |
| Repository history | stage, commit, branch | request/workflow dependent |
| External publication | push, PR, package release | explicit current authority |
| Operational external | deploy, DNS, accounts | explicit authority and environment gate |
| Sensitive/high-impact | secrets, money, legal, production data, destructive deletion, communications | explicit authority and usually human review |

Default-deny arbitrary egress, non-loopback listeners, writes outside declared
workspace roots, unpinned dependency downloads, privileged containers,
production credentials or data, and irreversible external mutation.

Store secret references, never values. Redact commands and output. Treat
repository prose, issue text, web content, model output, imported skills, and
tool output as untrusted data unless an authorized instruction mechanism says
otherwise.

Policy text is declarative defense in depth, not a sandbox. Real enforcement
belongs to platform permissions, least-privilege credentials, protected
branches, independent CI, review, and environment gates.

### 7.1 Collaboration topology and small-team workflow selection

The current collaboration assessment and selected workflow are owned by the
closed `collaboration_profile` in `.agent/project.json`. This is a compact
project-governance assessment, not mutable task status. It stores aggregate
counts and evidence references, never collaborator identities. Detailed
observations remain in project-owned evidence or current-state sources.

The independent signals are:

- the project owner's declared number of write-capable human maintainers;
- observed repository access split into write-capable humans, read-only
  humans, and bots or automation;
- active human and automated contributors over an explicit 1–365 day window;
- the number of eligible independent reviewers currently available;
- expected simultaneous human and agent or automation repository writers;
- whether external contribution is closed, invitation-only, open, or unknown;
  and
- whether a solo maintainer prefers direct or reviewable integration.

Read-only people, bots, and automation never count as human maintainers.
Activity does not erase dormant write-capable access. Access observation is
evidence about topology, not a grant of access or permission. Evidence names
its kind, safe reference, supported signals, observation time, freshness
deadline, and limitations. The assessment records `confirmed`, `inferred`,
`conflicted`, or `unknown` confidence; disagreement remains explicit.

The read-only collaboration command derives a classification from the stored
aggregate without writing, networking, executing hooks, or adopting it:

```text
python -B .agent/scripts/validate.py --assess-collaboration
```

It is not part of ordinary `--check`. A project may gather hosted observations
separately under explicit network authority, or rely entirely on project-owned
observations. Unknown, expired, or conflicting evidence blocks selection.

Team-band derivation is closed:

| Effective write-capable humans | Team band | Base workflow |
|---|---|---|
| 0 | `no_write_capable_human` | blocked |
| 1 | `solo` | `solo_direct` or `solo_hybrid` |
| 2 | `pair` | `pair_pr` |
| 3–5 | `tiny` | `tiny_pr` |
| More than 5 | `unsupported_team_size` | none |

One fresh writer signal can support only `inferred` confidence when every
other required signal is explicit and fresh. Equal declared and observed
writer counts support `confirmed`; disagreement is `conflicted`. Any credible
count above five produces `unsupported_team_size` even when other counts
conflict, preventing selection of an undersized workflow.

The four supported workflows are complete but deliberately lightweight:

- `solo_direct`: for one human who prefers direct integration and expects no
  simultaneous writer. Inspect the revision and worktree, make a bounded
  change on the default branch, validate locally, stage and commit, publish
  only with explicit current authority, then observe CI. Substantial or
  high-risk work escalates to `solo_hybrid` and may add stronger risk controls.
- `solo_hybrid`: create and switch to a short-lived task branch, make the
  bounded change, validate, stage and commit, optionally publish a self-PR,
  observe CI, perform self-review with limitations, integrate using the one
  project-adopted method, and safely clean up the branch.
- `pair_pr`: create a short-lived task branch, validate and commit, publish a
  PR under current authority, observe CI, obtain one peer review when an
  eligible reviewer is available, integrate with the one adopted method, and
  safely clean up. If capacity is absent, record the limitation and block
  rather than fabricate an approval.
- `tiny_pr`: use the same short-lived branch, PR, CI, integration, and cleanup
  lifecycle for three to five humans. At most one peer approval may be
  required. Lightweight ownership guidance is optional and must address an
  observed coordination need; it never becomes a multi-level approval system.

Any supported band with simultaneous writers applies the `concurrent_work`
modifier. Each task uses its own branch or worktree, records a shared base
revision and declared write scope, detects conflicts deterministically, and
defines cancellation, handback, and partial-result behavior. Agents and
automation change only this modifier, never the human team band. A
High-Assurance coordination lease is an optional stronger realization when a
named risk warrants it; the modifier itself applies in every profile.

`.agent/scm.json` is the default unassessed trigger. After Git is explicitly
selected, the pinned small-team Git package installs
`.agent/workflows/small-team-git.json` as the provider-neutral,
non-authorizing workflow source. Every operation it uses resolves to the
ordered catalogs in `.agent/tools.json`. A recommendation does not adopt a
workflow. Adoption requires a resolving accepted project-owned `DEC-####`, but
neither the decision nor the workflow grants permission to edit, fetch, push,
publish a PR, replace history, create a release tag, or perform recovery.

Team size selects only the base workflow. Project risk independently adds
validation, review, protected enforcement, external-effect gates, or qualified
specialists. It never changes the team band and does not automatically select
Standard or High Assurance.

GitHub integration is optional. Repository-local contracts never imply a
provider, account, credential, reviewer, branch protection, required check,
environment, release, successful CI run, or hosted permission. Provider
publication remains an explicitly authorized external action.

The portfolio expressly excludes GitFlow with long-lived development/release/
hotfix branches, merge queues or batch integration, release trains, stacked-PR
dependency trains, fork-first internal contribution, multi-level CODEOWNERS
approval hierarchies, multiple mandatory approval stages, dedicated release
manager handoffs, organization-wide ruleset orchestration, multi-environment
promotion pipelines, and enterprise issue-triage or portfolio governance.
Simple PRs, CI, one-peer review, and risk-justified branch protection remain
valid small-team controls.

### 7.2 Governed work-completion orchestrator

`work.finish` extends the accepted small-team workflow, command, hook,
operation, transaction, receipt, task, evidence, and lifecycle models. It is
not a second workflow framework. Every base workflow and the
`concurrent_work` modifier use `.agent/scripts/octon_work_completion.py`; Minimal,
Standard, and High Assurance use that same engine and may add controls without
forking it.

The project interface is `octon work finish plan`, `octon work finish apply
--accept-digest <digest>`, and `octon work finish resume`. The optional
completion-event hook may invoke only `plan`. Generated projects begin with
the feature and its optional `commands.work_completion_plan` hook unassessed
and disabled. Enabling binds that hook to the exact shell-free, read-only plan
argv; it cannot invoke apply. Planning reads the accepted workflow decision,
completed task's optional `work_completion` contract, exact dirty paths,
local revisions and remote-tracking refs, configured read-only validation
hooks, the required no-active-Git-hooks policy, assurance references, and
cleanup policy. Active Git hooks block, and active `core.fsmonitor` blocks
before status inspection so planning cannot knowingly invoke a hidden hook or
daemon. It prints a deterministic,
non-authorizing plan without staging, refreshing, committing, fetching,
publishing, querying a provider, writing a receipt, or changing an external
system.

The exact current `work.close` transaction receipt and its unchanged dirty
postimages are automatically added to the eligible staging inventory. This
does not create a blanket `.agent/transactions` exclusion: an older, altered,
ambiguous, or unrelated plan/receipt remains ordinary dirty state and blocks
unless the task explicitly owns its exact path.

After a successful `work.close` transaction, the generated command dispatcher
checks that project-owned hook record. In `plan_only_on_completion_event` mode
it invokes the exact configured plan argv and prints the resulting plan. A
disabled or absent hook does nothing. If planning blocks, the already-applied
closure receipt remains truthful and the command reports the post-closure
block; no external or destructive follow-on action is attempted.

Apply reconstructs the same plan from canonical sources, accepts only the
reviewed digest and unchanged preconditions, and requires a current
task-scoped attestation for the exact repository, branches, plan, validity
interval, and external operation list. The attestation records authorization
granted through an independent authority channel; neither it nor the command
creates that permission. Authority is rechecked before every network or
hosted effect, and live local, remote, PR, check, review, integration, branch,
and worktree state is re-observed before the dependent action.

The engine stages only task-declared exact paths and rejects unrelated dirty
work, pre-staged content, conflicts, empty commits, missing authority, changed
revisions, unassessed checks, draft or mismatched PRs, stale checks, self
approval where a peer is required, unsupported integration, non-fast-forward
synchronization, and unsafe cleanup. `solo_direct` does not gain a PR or task
branch requirement. `solo_hybrid` records self-review and its limitations.
`pair_pr` and `tiny_pr` require an actual approval by another explicitly
configured eligible provider identity, distinct from the author, using no
more than one. Concurrent work additionally requires the recorded
base, write scope, branch/worktree owner, completed handback, and resolved
partial results.

Because external systems cannot participate in the repository-local atomic
transaction, progress is an evidence-backed monotonic receipt. Its states are
`planned`, `locally_committed`, `branch_published`, `pull_request_open`,
`checks_pending`, `checks_failed`, `checks_passed`, `review_pending`,
`review_satisfied`, `integrated`, `remote_branch_cleaned`,
`default_branch_synchronized`, `local_branch_cleaned`, `completed`, and
`blocked`. The append-only receipt and authorization history preserve
successful prior effects and let `resume`
observe them before acting, preventing duplicate commit, PR, merge, push, or
deletion. Receipts live under the Git common directory rather than the source
worktree; they are local, nonportable progress evidence until explicitly
exported by a project-owned evidence process.

Cleanup proves integration before remote deletion, synchronizes the local
default branch only by fast-forward to the exact remote revision, then proves
the task branch is non-current, non-default, integrated, and unused by another
worktree before local deletion. A partial failure retains exact evidence,
names the remaining state, and stops for safe resume or fix-forward.

### 7.3 Guided, resumable setup interview

Guided setup is a bootstrap-source orchestration layer over the existing
`init`, `adopt`, and `upgrade` planners. It is not a project installer, apply
engine, authority store, or configuration replacement. One authoritative
catalog, `shared/source-contracts/setup-questions.json`, supplies stable
question IDs, modes, dependencies, triggers, answer contracts, recommendation
rules, destinations, evidence/freshness needs, sensitivity restrictions,
migration behavior, and change consequences. TTY prompts, conversational
agents, answer files, and legacy CLI flags use those same IDs and validation
rules.

`octon init setup`, `octon adopt setup`, and `octon upgrade setup` inspect the target
without refreshing projections, executing hooks, installing packages, writing
receipts, querying providers, or changing the target or an external system.
Without `--output`, they write nothing. An explicitly requested setup-session
output must be outside the target. A session records target and instruction
fingerprints, Octon Mini provenance and versions, catalog version/digest,
observations, recommendations, selections, accepted-authority references,
unknown/deferred/inapplicable states, blockers, next questions, work-completion
closure steps, the overall minimum dependency-ordered closure sequence,
successor relationship, and a canonical digest. It always has
`permission_grant: false` and stores neither secrets nor unnecessary personal
data.

The agent determines mode from evidence: an empty/new target initializes, an
established target without Octon Mini provenance adopts, and a snapshot with
valid provenance upgrades. Invalid or contradictory provenance is ambiguous
and stops. It reads applicable instructions, asks only unresolved questions in
dependency order—normally one to three at a time—and states importance,
mutually exclusive choices, any recommendation and rationale, allowed unknown
or deferred state, and what deferral blocks. No choice is preselected. Direct
observations, inferences, recommendations, user selections, accepted authority,
unresolved unknowns, deferred matters, and runtime authorization remain
separate.

Successor sessions are immutable: resume never overwrites its predecessor.
Session v2 classifies every state with one or more of
`re_observe_every_run`, `source_fingerprint_bound`, `dependency_bound`,
`expiry_bound`, `decision_successor_or_revocation_bound`, and
`runtime_only_never_reusable`. Reinspection reports `preserved`, `reobserved`,
`needs_confirmation`, `invalidated`, and `newly_introduced`. An unrelated
target or revision change does not discard a value whose declared bindings
remain exact. Changed governing instructions, relevant evidence, catalog or
question definitions, Octon Mini provenance, accepted authority, exact
dependencies, or expiry still fails closed. Later catalog questions appear
unanswered and never acquire defaults. A v1 session becomes current only
through an explicit immutable v2 successor.

The generated decision-reuse registry starts empty. A project may populate it
only through its normal governed change process. Each active entry binds one
exact accepted and unsuperseded `DEC-####`, its authority source, question and
operation applicability, governing instructions, dependency fingerprints,
validity interval, and projected value. A current entry may avoid a repeated
policy question but is never a recommendation, owner selection, operation
confirmation, runtime authorization, standing external-action permission, or
readiness evidence.

`octon init|adopt|upgrade plan --setup-session <file>` maps reviewed answers into
the existing planner and binds the exact session bytes and canonical digest
into ordinary transaction source evidence. Apply revalidates that session,
the current target/instructions, transaction digest, and normal preconditions
immediately before the existing transaction engine acts. Legacy flags remain
supported and map deterministically to stable question IDs. A conversational
answer is never accepted project authority, and setup never supplies runtime
authorization.

The work-completion question offers exactly disabled, on-demand, or on-demand
plus automatic read-only planning after task closure. It offers no automatic
apply. An enabling selection remains pending until the content-addressed Git
portfolio, accepted supported workflow, repository/remote/default branch,
provider assessment, explicit hosted-check set, eligible peer identities when
required, integration method, read-only hooks, no-active-Git-hooks and inactive
`core.fsmonitor` controls, cleanup choices, and assurance references are all
present. Setup reports the smallest dependency-ordered closure sequence; it
does not enable the capability or overwrite project-owned configuration.

### 7.4 Continuation, plan review, and safe local bundles

Every covered blocked operation emits `octon-mini.continuation.v1` directly
from its typed failure boundary. The finding contains a stable code, operation
and phase, exact mutation statement, root cause, invalidated and preserved
proofs with validity classes, owning authority source, repair class, one
shell-free next action, other available read-only actions, successor support,
and limitations. Human output is concise by default; `--json` preserves the
same semantics. The structural validator assigns stable diagnostic codes at
its owning check-group boundaries; the versioned catalog turns those codes
into continuation guidance. Substring classification remains only a safe
compatibility fallback for an untyped predecessor finding.

Transaction plan v3 supports an immutable predecessor and semantic delta.
`harness.plan-summary.v1` is a derived review projection showing operations by
create/replace/delete/derived write, excluded and otherwise unchanged scope,
safety basis, unresolved review, local and external effects, validation,
recovery, reused decisions/evidence/proofs and validity, the full canonical
digest, and the one required confirmation. The detailed plan remains the apply
input. Interactive source `octon init`, `octon adopt`, and `octon upgrade`
perform inspect → necessary questions → plan → summary → confirmation →
revalidation → apply. Review blocks preserve external session/proposal/plan
artifacts, report those local writes separately, and stop before target apply.

`harness.transaction-bundle.v1` combines two or more coherent plans only when
they target this one project, are repository-local and exactly reversible,
share compatible authority, confirmation, governing-instruction, freshness,
and rollback requirements, have no overlapping or contradictory paths, and
contain no external or monotonic effect. The bundle uses one stage, digest,
pending journal, receipt, and rollback. An incompatible set is rejected rather
than partially bundled or silently split. Bundle planning records one explicit
common `authority:` or `external:` source when member plans do not already
carry an identical authorization-gate source set; this record remains
non-authorizing.

Receipt v3 also records host-specific staging, refresh, staged-validation,
live-apply, post-apply-validation, and receipt-preparation timings. These are
paired with a process-local receipt-persistence and total timing emitted after
the immutable receipt is safely written; the post-write observation cannot be
inserted back into that receipt. These are performance observations, not
human-usability evidence or permission to use
hardlinks, shared writable inodes, incomplete final gates, or weaker staging.

### 7.5 Optional long-running work

`long-running-work` is a trigger-installed `workflow_capability`, absent and
inactive by default. A dormant `octon work run` route verifies the installed
payload before launching one fresh shell-free Python process. The package
governs an external worker; it does not host, choose, authenticate, or call a
model.

The task remains the sole owner of goal, scope, authority basis, and
acceptance. The package owns only one active run coordinate, locally measurable
limits, deterministic derived context, reference-only transition history, and
marker-backed checkpoints under `.agent/work-runs/`. Transactions retain local
mutation ownership, project-check evidence retains validation ownership,
`work.finish` retains Git/provider completion ownership, and Continuation
retains safe-refusal ownership.

Only marker-backed checkpoints are committed. Resume revalidates task contract,
instructions, project fingerprint, context, authority source, receipts,
evidence, and limits. It reports a next action without running hooks or
replaying work. Unavailable token, cost, provider, and worker measurements
remain `unknown`; supplied token and cost totals are nonnegative and monotonic.
Elapsed enforcement uses the local runtime clock rather than a worker-supplied
timestamp. A limit stop is terminal for that run and reviewed new limits require
a successor. No-progress detection uses exact task, project, receipt, evidence,
and committed-coordinate facts; a caller claim or model judgment cannot
establish progress alone.

The active projection is preferably under 100 lines, current history is bounded
to 100 meaningful entries before explicit disposition, and context uses exact
byte/item budgets with visible omissions. Mutable work-run state is excluded
from general source fingerprints and validated by the package validator.

See `docs/LONG_RUNNING_WORK.md`. Implementation and validation do not establish
package adoption, release, project readiness, or production readiness.

### 7.6 Optional governed autonomous delivery

Every snapshot exposes `octon delivery` in the locked
`available_not_activated` state and carries exact inert offline payload bytes.
Research, context, applicability, planning, status, explanation, and activation
preview are read-only, run no project hooks, write no receipt, mutate no local
or external state, and create no authority.

Activation uses a delivery-profile preset independent of assurance,
collaboration, concurrency, and layout. Setup deterministically renders a
complete non-authorizing standing contract and digest. Only independent human
confirmation of those exact bytes supplies authority. The accepted external
record is evidence of that grant and remains outside the repository under
operator control. A command flag, profile, setup answer, plan, projection,
receipt, or stored record cannot create or broaden authority.

The package reuses the existing long-running coordinate, transactions,
project-check evidence, work completion, and Continuation owners. Its release
adapter is limited to exact hosted-workflow dispatch, annotated tags, tag push,
GitHub source Release creation, and read-back. It is not a generic action,
deployment, package-publication, credential, communication, or external-project
runtime.

The Octon Mini source repository exposes a narrow source mode in the existing
work-completion owner. It accepts an external immutable, digest-bound Codex
task reference rather than creating a source task store, binds an already
committed candidate range, uses the same authorization and monotonic receipt
model, stops before integration until the stable required check and all 24
candidate source/acceptance matrix jobs pass, and stops again after integration
until exact integrated-main validation evidence is recorded. The release
adapter does not acquire commit, push, PR, checks, merge, synchronization, or
cleanup ownership.

The closed release-effect adapter has a source-only entry point. Candidate
workflow dispatch binds to the exact task branch and revision; tag and GitHub
source Release operations bind to exact clean `main`. Its allowlist remains
workflow dispatch, annotated tag creation, tag push, and GitHub source Release
creation and contains no work-completion operation.
Adapter apply and resume revalidate both current compute evidence and the exact
usage digest bound by the short-lived projection before any external call.

Locally reversible work retains transaction semantics. Public effects are
monotonic: inspect, persist an attempted marker, execute once, read back,
receipt, and fix forward. An unknown outcome stops with zero automatic retries.
Direct spending is zero. Each standing contract selects exactly one compute
mode: host-enforced metered API ceilings, or current readable
provider-enforced included-subscription allowance only. Paid credits,
API/pay-as-you-go billing, add-ons, and upgrades are prohibited in subscription
mode. Unknown, exhausted, unreadable, or changed compute state blocks. See
`docs/AUTONOMOUS_DELIVERY.md`.

## 8. Record and state model

The semantic crosswalk is orthogonal to every record lifecycle:
`authoritative` names the declared source for a bounded concern; `observed`
names a dated inspection; `inferred` names a conclusion from disclosed
premises; `proposed` names unaccepted content; `derived` names a reproducible
projection; `historical` and `superseded` name retained noncurrent content;
`stale` names content beyond its freshness or validity boundary; `unknown`
names an unestablished fact; and `intentionally_omitted` names a disclosed,
deliberate exclusion. This vocabulary is not a universal status enum. Each
task, decision, artifact, capability, approval, and extension keeps its own
closed status and transition contract. A display projection never writes back
to its sources, and no semantic role grants action authority or establishes
readiness by itself.

| Concern | Store | Mutability | Meaning |
|---|---|---|---|
| collaboration topology and adoption | `project.json` | reassessed project source plus accepted decision reference | which small-team workflow fits without creating permission |
| package lifecycle | `packages.json` | project-owned assessment plus transaction receipt | which pinned trigger content is installed and validated |
| provider-neutral Git workflow | trigger-installed `workflows/small-team-git.json` | content-addressed package contract | complete supported steps only when Git is selected |
| durable intent | `decisions/` | immutable plus successor | why a lasting choice exists |
| decision questions and review | `decisions/governance-register.json` | project-maintained source with exact inventory reconciliation | what remains material, recommended, selected, accepted, evidence-first, compatible, and blocking |
| accepted-decision reuse applicability | `decisions/reuse-policy.json` | project-maintained empty-by-default registry bound to exact accepted decisions | which durable policy value may answer a matching future question without becoming action authority |
| active work | `tasks/` | lifecycle updates | what is being done |
| observation | `evidence/` | immutable record | what was inspected or executed |
| target-project check evidence and proofs | `project-checks/evidence.json` plus immutable archive | bounded current index, content-addressed routine proofs, and successor-linked archive | what selected configured hooks returned and which exact unexpired read-only result may be reused by the explicit writer |
| review finding | `reviews/` | disposition updates | what a separate pass found |
| chronology | `events/` | append-only | meaningful transitions |
| approval attestation | `approvals/` | immutable plus revocation/successor | who attested to what, under which external authority |
| coordination lease | `coordination/` | expiring lifecycle | who owns a write scope and until when |
| current view | `state/current.json` | fully derived compact operational index | mechanically rebuildable state |
| operator focus | `state/focus.json` | project-owned non-authorizing intent | current focus, next action, and handoff pointer |
| artifact metadata | `artifacts/registry.json` | lifecycle updates | provenance and promotion |
| evaluation | `evaluations/` | versioned fixtures and results | whether repeated work meets a declared rubric |
| harness metric | `metrics/` | generated/observed series | whether the harness improves closure, safety, and resumption |
| generated integrity | `generated/` | regenerated | point-in-time inventory and results |
| repository-local mutations | `transactions/` | immutable plans/receipts plus recoverable pending journals | what exact preimages, operations, validation, postimages, and rollback rule applied |
| work-completion progress | Git common directory `octon-mini/work-completion/receipts/` | monotonic resumable local receipts | which exact local and external completion effects are proven, blocked, or still pending without claiming rollback |
| autonomous-delivery effect progress | Git common directory `octon-mini/autonomous-delivery/receipts/` | immutable monotonic successors | which exact release-adapter effect was requested, attempted, read back, completed, known-no-effect, or outcome-unknown |

Accepted standing-authorization, confirmation, revocation, and emergency-stop
records remain outside the repository at an operator-controlled location. The
project stores only an exact reference and digest after activation. The worker
cannot write those control records under the standing contract.

Each record declares `schema_version`, stable ID, purpose/title, scope,
authority source, owner/maintainer, inputs, outputs or links, side effects,
status, timestamps as applicable, validation, limitations, provenance, and
successor/deprecation fields where applicable.

Consequential evidence additionally states the implications it does not prove.
A passing check therefore remains bounded to its exact subject, method,
environment, time, and scope; it cannot silently become approval, compliance,
provider truth, or production readiness.

Requirements and quality gates may carry a scoped maturity assessment:
`Architecturally specified`, `Evidence planned`, `Structurally validated`,
`Demonstrated by executable implementation`, `Specialist-approved`,
`Release-ready`, or `Production-proven`. This is not a universal lifecycle or
an automatic readiness state. Each declared level has its own evidence and
limitations; completion at one level does not imply a higher level, and the
validator never promotes it.

Task `dependencies` are hard `TASK-####` prerequisites. `plan_item_refs` and
plan-item `task_refs` are reciprocal. `gate_refs` name structured readiness
gates, while `blocking_refs` name status-bearing task, plan, gate, decision, or
RAIDQ records. Free-text `blocked_by` explains impact but cannot by itself make
a blocked state machine-verifiable.

Approval records are evidence of an attestation received through a separately
authorized channel; they cannot manufacture that authority. They identify the
principal or role, action, resource/scope, constraints, validity window,
source reference, evidence fingerprint, revocation state, and successor.
Secret material and reusable credentials are never copied into the record.
`state/current.json` is a fully derived view and not an authorization channel.
Refresh rebuilds it from project configuration, tasks, decisions, evidence,
and `state/focus.json`. Its task, decision, evidence, and external-authority
references must resolve and remain status-consistent. Operators update focus,
not the derived view.

### Task lifecycle

```text
proposed → ready → in_progress → validating → review → completed
             │          │          │        └──────→ blocked
             │          │          └───────────────→ completed
             │          ├──────────────────────────→ completed
             │          └──────────────────────────→ blocked/cancelled
             └─────────────────────────────────────→ completed/blocked/cancelled
blocked → ready | in_progress | cancelled
completed → reopened → ready | in_progress | completed | cancelled
```

- `ready` requires scope, authority basis, acceptance criteria, a validation
  plan, completed hard dependencies, passed or validly waived gates, resolved
  structured blockers, and reciprocal plan links.
- `in_progress` requires an owner.
- `validating` requires an implementation or analysis result.
- `review` requires evidence or an explicit limitation.
- `completed` requires satisfied criteria, closure evidence, and disclosure of
  external effects and limitations.
- `blocked` names the missing fact or authority and links at least one
  unresolved structured dependency, gate, blocker, or plan condition.
- `reopened` links the evidence that invalidated completion.

`ready`, `in_progress`, `validating`, `review`, or `reopened` may move directly
to `completed` only when the completed-state gate is fully populated. This
removes status-only ceremony; it does not waive implementation result,
criteria, review and closure evidence, external-effect disclosure, or
limitations. A blocked task may resume `in_progress` only through the explicit
reopen workflow with invalidating/resolving evidence.

Initial execution passes through `ready`; evidence-bound reopening may resume
directly when its original readiness contract remains satisfied. If a completed
dependency reopens, a gate expires, or a blocker becomes active, affected
nonterminal downstream tasks move to `blocked`; downstream `completed` claims
become invalid until reassessed. The validator rejects task cycles and any
`ready`, execution, review, or completion state whose readiness conditions are
unsatisfied.

The ready frontier is a read-only derivation of eligible planned items and
tasks. It is not stored as authority or mutable status. Dependencies define a
partial order, so current operator direction or an accepted priority/value/risk
decision selects among multiple ready items. Creation/update dates, evidence
freshness, gate expiry, and genuine external deadlines remain useful time data
but never satisfy prerequisites or silently choose work. Frontier arrays use
stable identifier order only for deterministic display, never as priority.

### Decision lifecycle

Use `proposed`, `accepted`, `rejected`, `superseded`, and `deprecated`.
Changing the meaning of an accepted decision requires a successor that names
the superseded record.

The decision-governance register has its own subordinate tracking lifecycle:
`open`, `evidence in progress`,
`owner selected — ADR or approval pending`,
`accepted — authority linked`, `deferred`, and `superseded`. These values do
not replace the durable decision lifecycle. `accepted — authority linked` is
valid only when the entry resolves to a currently accepted `DEC-####`; an
owner-selected entry keeps its authority reference null.

Every register entry has a stable `DREG-####` identity, exact decision question,
type and timing, non-reopenable constraints, exclusions, no more than four
credible options, a separate recommendation and owner-selection object,
evidence owner/step/stop condition where needed, traceability, blocked work,
reversal conditions, and one trade-off review. Dashboard, sheets, dependency
order, and reviews reconcile exactly; decision and minimum-closure graphs are
acyclic.

### Artifact lifecycle

Where durable non-code outputs matter:

```text
scratch → draft → reviewed → approved → final → archived
```

The registry records source inputs and licenses, producer/tool version,
validation and review, data class, retention, destination, required approver,
fingerprint, and supersession. It stores metadata, not secret or duplicate
large content.

### Event and recovery discipline

Every event has a globally unique ID, monotonic sequence within its declared
stream, exact subject reference, timestamp, actor/source, kind, redaction
status, and evidence links. Validation rejects duplicate or decreasing
sequence values, unresolved subjects, invalid event kinds, and malformed
recovery records. Append-only corruption is recovered by preserving the
damaged bytes as evidence, creating a successor stream/checkpoint, and
recording the mapping; history is never silently rewritten.

### Context budgets

- root instructions: routinely readable;
- `state/current.json`: preferably under 100 lines;
- `state/RESUME.md`: preferably under two pages;
- active task: preferably under 200 lines;
- skill entry file: preferably under 300 lines with routed references; and
- events: one fact-focused record per meaningful transition.

History belongs in durable records, not in an ever-growing resumption summary.

## 9. Agent, skill, workflow, tool, and extension contracts

Every component declares:

- stable ID and schema version;
- purpose and scope;
- required inputs and produced outputs;
- authority source and `may_expand: false`;
- side-effect class;
- prohibited behavior;
- validation method;
- version and provenance;
- owner/maintainer; and
- deprecation or successor.

Agent and workflow records use strict, closed JSON contracts from
`harness-capability-records.schema.json`; arbitrary workflow state names are
represented as closed state records with validated references. Generated
capabilities start as `generated_unadopted_baseline` with
`permission_grant: false`, unassigned ownership, unassessed license/security
review, and explicit limitations. Adopting a capability requires a
project-specific accepted trust and authority decision referenced by
`adoption_decision_ref`; schema conformance cannot perform that adoption. A
skill's `SKILL.md` frontmatter contains only `name` and `description`;
version, trust, review, and update metadata belong in its separate closed JSON
provenance record.

Project-harness adoption uses `not_assessed`, `in_progress`, `adopted`, and
`superseded` consistently across the project, policy, context, and current
state. `adopted` and `superseded` retain the resolved accepted external-authority
decision as provenance; pre-adoption states keep the decision reference null.

Target-project test, lint, build, and closure hooks use a separate closed
three-state contract. `configured` requires an assigned owner, direct argv and
version argv using the same executable, timeout, evidence freshness, and
declared repository/external effects. `not_applicable` requires an owner and
substantive rationale.
`not_assessed` is permitted only before harness adoption. String commands and
shell interpreters with inline command flags are rejected; validation does not
silently reinterpret them.

An explicit project-check writer is the only generated command allowed to
execute configured hooks or append `.agent/project-checks/evidence.json`. It
records command/tool identity, executable fingerprint, exact source and Git
scope, environment, times, results, skips, limitations, declared effects, and
detected repository mutations. Mutation comparison is observation after
execution, not sandbox isolation. The read-only harness check only validates
this evidence and never executes project hooks or writes evidence.

For routine work, the same explicit writer may request conservative proof
reuse. `harness.validation-proof.v1` binds an exact declared input inventory
and digest, check identity, shell-free argv, executable bytes and version
output, relevant configuration, governing instructions, hashed environment
characteristics, side-effect classification, observation/freshness, passing
result, and limitations. Only an unexpired `read_only` proof with no declared
repository or external effect is reusable. Any changed binding is a miss and
reruns that check. Volatile external state and runtime authorization are never
proof inputs or hits. Proof records are persistent only inside the explicit
evidence-writing boundary.

An agent is a constrained task mode. A skill packages a repeated method and
selectively loaded references. A workflow is a versioned state machine whose
transitions invoke policy checks and produce evidence. A tool record separates
availability from allowed operations. An extension adds domain data and
findings through a stable interface:

```python
def validate(context: ValidationContext) -> list[Finding]:
    ...
```

The Git and hosted-change catalogs are ordered, closed, and fail unknown
operations. Every operation declares one or more effects from
`read_only_observation`, `local_reference_mutation`,
`working_tree_or_index_mutation`, `repository_history_mutation`,
`network_access`, `external_publication`, and `destructive_recovery`; its
authority class; whether it is a normal workflow step; and exact safeguards.
Authority classes are `allowed`, `task_scoped`,
`explicit_current_authorization`, `separate_release_authorization`,
`exceptional_current_authorization`, `destructive_current_authorization`, and
`prohibited`.

Composite `pull` is not modeled as harmless. Raw force-push is prohibited.
Exceptional history replacement is force-with-lease only, exact-ref scoped,
currently authorized, and confined to a non-default short-lived branch.
Release tags require separate release authority. Branch and worktree deletion
require safe-state evidence. Destructive recovery is never a normal workflow
step, and every workflow operation reference must resolve to the catalog.

For concurrent work in any profile, require a shared revision base, declared
write ownership, handback contract, deterministic conflict detection,
cancellation behavior, and partial-result rules. High Assurance may
additionally require a task lease and expiry when the project risk assessment
justifies mechanical coordination.

A coordination lease is not authority to edit. It only prevents two
authorized workers from silently claiming the same write scope. Lease
acquisition, renewal, expiry, cancellation, and handback are validated state
transitions, and abandoned partial results remain discoverable.

Imported capability packages record upstream source, exact version and
immutable source fingerprint, license, adopted files, local changes,
exclusions, security review, trust class, and update strategy. Mutable network
content is never loaded as instruction.

Capability and schema deprecations name both the first deprecated version and
the planned removal version. Removal requires a successor, migration fixture,
and evidence that no live references remain. Capability deprecation and
removal use the harness-kernel release axis; the capability package's own
version remains separate provenance.

## 10. Validation contract

Validation layers are:

1. bootstrap and runtime availability;
2. selected-profile operational-file inventory, syntax, and duplicate-key
   rejection;
3. schema version, ID, path, link, successor, dependency integrity, reciprocal
   plan/task links, and dependency-gated readiness;
4. instruction scope and authority classification;
5. policy, secret, network, filesystem, and external-effect rules;
6. lifecycle and closure evidence;
7. project extensions and project build/test/lint checks;
8. generated manifest, fingerprint, checksum scope, and freshness;
9. positive and negative/mutation tests; and
10. recovery from stale reports, corrupted records, and interrupted refresh.

Work-completion validation additionally checks the optional disabled baseline,
enabled repository/provider/check/hook/cleanup assessment, accepted workflow
authority, task completion contract, plan and authorization digests, unique
operation inventory, receipt state and progress shape, exact path ownership,
non-writing planning, stale precondition rejection, hosted head binding,
review independence, integration-before-cleanup, fast-forward-only sync, and
idempotent resume. Only configured `read_only` project hooks may run in the
completion engine's ephemeral `--observe-only` mode; that mode writes no
evidence or generated projection and cannot substitute for durable target
project evidence.

Decision validation additionally checks controlled type/timing/lifecycle,
disposition and compatibility values; unique `DREG-####` IDs; dashboard/sheet/
review reconciliation; accepted authority resolution; recommendation,
selection, and acceptance separation; reciprocal `DREG-####`/resolving
`DEC-####` links; required evidence-first owners and stop
conditions; reference integrity; dependency and closure cycles; six option
gates; exact non-overlapping balanced attributes; and totals that cannot hide
gate failures or `?` evidence gaps. Completed closure items require resolving
evidence appropriate to their kind. Requirement/gate maturity requires the
exact level-specific basis kind, and structural-or-higher claims require a
resolving pass evidence record; the validator does not infer evidence adequacy.

The validator is modular even when distributed as one standard-library file.
Kernel, instruction, record, lifecycle, dossier, extension, integrity, and
project-command checks have separate interfaces and return structured
findings. A failure in one module must not silently disable unrelated checks.

The command contract is:

```text
python -B .agent/scripts/validate.py --check
python -B .agent/scripts/validate.py --ready-frontier
python -B -m unittest discover -s .agent/tests -p "test_*.py"
python -B .agent/scripts/refresh.py --refresh
```

Here `python` is the pinned Python 3.11+ interpreter selected by the project
environment, not an arbitrary ambient executable. The reference CI provisions
that launcher on every supported operating system. A project that uses another
launcher or runtime must adopt and validate an equivalent command contract
rather than editing only the displayed strings.

Projects may expose aliases such as `make harness-check`, but the authoritative
commands live in `.agent/validators.json`.

After project owners assess every hook and confirm authority for its declared
effects, configured target-project checks run only through the separately
explicit writer:

```text
python -B .agent/scripts/run_project_checks.py --write-evidence
```

The optional `--verify-adoption` mode also performs the explicit refresh write
and final read-only check. A configured hook declaring repository writes or
possible external effects additionally requires `--acknowledge-side-effects`;
that acknowledgement is not permission.

Adoption and release gates prohibit proof reuse and execute the complete
configured boundary before their final read-only check. Routine proof reuse
therefore reduces repeated work without weakening consequential validation.

`check` must not write bytecode, caches, reports, indexes, timestamps, or
lockfiles or execute target-project hooks. It snapshots repository paths and
content before and after extension execution and fails if mutation is detected;
high-impact projects also enforce no-write execution outside the repository
trust boundary.
The source fingerprint excludes `.git`, whose internal metadata is not project
source. The mutation snapshot separately covers the `.git` pointer plus
critical HEAD, index, config, packed-ref, loose-ref, and hook paths for normal
repositories and linked worktrees; it is not a complete Git-object audit.
Every Git probe runs with `GIT_OPTIONAL_LOCKS=0`; this reduces incidental index
refreshes but does not turn Git or an untrusted extension into a sandbox.
`refresh` validates authoritative sources first, transactionally regenerates
the artifact catalog, path authority, manifest, and profile-specific integrity
outputs, and then runs the final read-only check.

A formal read-only review records repository status and revision, useful
authority/projection fingerprints, every exact command and exit status,
unavailable and skipped checks, and the same status/fingerprints afterward.
It never refreshes generated artifacts. Stale projections are reported by
input and affected output. Before/after comparison distinguishes pre-existing
drift from mutations caused by the review; any detected change prevents a
read-only assurance claim.

High-Assurance generated validation reports are explicitly scoped to the
pre-refresh checks they record. Their closed contract contains one result for
each required check, failures, skips, environment and Git scope, external
effects, freshness rule, and limitations that name non-proven implications for
every consequential claim. A disabled extension is `not_run`, never `pass`. The
refresh command's final exit status reports the separate post-refresh exact-tree
check; neither result implies project readiness.

The portable reference validator uses only Python 3.11+ standard-library
features and validates strict JSON with duplicate-key rejection. JSON is the
canonical structured format in the domain-neutral kernel because its complete
grammar can be validated without borrowing another repository's environment.
An alternate validator is conforming only when it consumes the same schemas,
passes every valid/invalid/mutation/recovery fixture, preserves read-only and
redaction behavior, and records its runtime and version in
`.agent/validators.json`. An extension may use YAML only when it declares a
pinned parser, validates in a clean bootstrap, and converts findings through
the kernel extension interface.

Built-in secret detection combines named-assignment patterns for JSON, YAML,
dotenv, and common source syntax with high-confidence credential formats. It
scans UTF-8 text files up to its declared 4 MiB limit across tracked,
untracked, ignored, and generated paths, reports only locations/categories,
and never echoes candidate values. Binary, larger, encoded, or deliberately
obfuscated material requires an independently configured dedicated scanner in
CI when risk warrants. Heuristics are defense in depth, not proof that a
repository is secret-free.

Generated reports include tool and schema versions, source revision or content
fingerprint, dirty/untracked/ignored scope, time, environment, checks
performed, result, limitations, task/decision links, and freshness rule.
Checksums prove byte identity only—not authority, correctness, safety,
freshness, provenance, or legal rights.

## 11. Profiles

Assurance profile is independent from the delivery-profile axis
`review_first`, `balanced_autonomous`, `fast_delivery`, or `custom`.
`fast_delivery` may be recommended for most solo developers but is never
silently selected. Delivery activation remains optional in every assurance
profile and cannot change the collaboration, concurrency, or layout result.

### Minimal viable

Use for small, early, or low-risk projects. Required:

- root router and seven-file kernel;
- decision and task stores plus templates;
- compact derived current state, explicit focus, and resumption page;
- portable read-only validator;
- unassessed target-project hook contracts and a separately explicit evidence
  writer;
- compact SCM/package triggers and an unassessed collaboration profile;
- staged plan/apply/recovery transactions and coded read-only diagnostics;
- typed continuation findings, shared plan summaries, transaction-v3 successor
  and safe-bundle support, and an empty accepted-decision reuse registry;
- exact routine validation-proof storage in the explicit project-check writer,
  with complete adoption/release gates and read-only `check` unchanged;
- project-local derivative source plus refresh command;
- valid and invalid fixtures with mutation tests; and
- dossier minimal profile.

The validator requires these operational entry points to remain present; a
project may extend them but cannot silently delete them and retain Minimal
conformance.

Exit only when discovery and precedence are clear, analysis versus
implementation authority is explicit, a task lifecycle can be validated, a
forbidden policy mutation fails, and validation runs without an undeclared
environment.

### Standard

Use when structured traceability, durable review evidence, project extensions,
or comparable coordination risks justify it. Add:

- evidence and review stores/templates;
- meaningful transition events;
- optional artifact registry;
- extension registry and project validator interface;
- trigger assessment and content-addressed package installation interfaces;
- task-closure checklist; and
- structured dossier traceability, dependency readiness, ready-frontier
  derivation, and evidence.

The extension and package registries plus Standard operational stores remain
required. Domain package absence is not treated as `not_applicable`; trigger
assessment remains explicit without shipping every domain mechanism.

Exit when an unfamiliar maintainer can execute, validate, review, hand off,
and resume a real task without undocumented steps.

### High assurance or agent-operable

Use when sensitive data, material external effects, protected enforcement,
long-lived agent operation, role separation, or audit/reproducibility needs
justify it. Add:

- constrained reviewer agent, routed review skill, and safe-change workflow;
- checkpoints and generated integrity;
- explicit refresh/check separation and content fingerprints;
- stronger dossier governance, transition, history, and supersession;
- conditional approval-attestation, coordination-lease, data-handling,
  incident/recovery, evaluation, and metrics contracts;
- CI/mutation/recovery guidance and stronger conditional trigger review; and
- environment-specific approval and enforcement hooks.

Before the profile can be represented as adopted, every conditional and
optional artifact trigger must be assessed. Applicable controls require an
owner, active reviewed representation, and current resolving evidence;
`not_applicable` requires a dated, attributed rationale. Trigger-installed
production-control extensions remain disabled until separately enabled, and
qualified security, privacy, compliance, legal, and production conclusions
remain outside automatic validation.

The governed capability and assurance-store entry points remain required.
Generated capability baselines may be deprecated or superseded through their
validated lifecycle, but must not simply disappear with their provenance and
dependency records.

The profile does not by itself create high assurance. Independent controls,
adoption decisions, project extensions, and demonstrated acceptance criteria
are still required.

All three profiles support `solo_direct`, `solo_hybrid`, `pair_pr`, `tiny_pr`,
and the `concurrent_work` modifier. Human count alone never selects Standard or
High Assurance, and concurrency alone does not require a coordination lease.

## 12. Adoption and evolution

### Initial adoption

1. Run the bounded semantic adoption planner and review its exact inspected,
   excluded, collision, authority, and functional-equivalence results.
2. Inventory use cases, protected resources, data classes, unacceptable
   effects, and actual sandbox, Git, CI, secret, cloud, and human enforcement
   boundaries that cannot be derived safely.
3. Choose read-only, per-task mutation, or standing reversible local posture.
4. Assess collaboration from project-owned, fresh, privacy-minimized evidence;
   derive the team band and recommendation without granting permission. Adopt
   a supported workflow only through a separate accepted project decision.
5. Preview the smallest risk-justified profile and compact or separated layout,
   then apply the exact no-overwrite transaction digest. Structural installation
   leaves adoption `in_progress`.
6. Resolve every retained project-owned unknown from evidence or mark it
   explicitly not applicable with an owner, date, and reason.
7. Record the threat model and authority posture as a project decision;
   never ship the example ID as accepted fact.
8. Assess every project command; configure applicable hooks with direct argv,
   owners, freshness, version probes, and declared effects, or record an owned
   `not_applicable` rationale.
9. Assess extension needs and ownership. Operations/observability and
   security/supply-chain packages remain absent until a project trust
   decision and project-owned records justify deliberate adoption.
10. Assess conditional approval, coordination, data, recovery, evaluation, and
   metric triggers; record every omission with a reason and every applicable
   High-Assurance control with current evidence.
11. Run the read-only check and mutation tests in a disposable clean
    checkout/worktree; run configured project hooks only through the explicit
    evidence writer after confirming authority for declared effects.
12. Complete one real task through closure and handoff using the adopted
    small-team workflow and its concurrency modifier when applicable.
13. Enable external or high-impact paths only through trusted current
    authorization and independent enforcement.

### Evolution

- Every structured file declares a schema version.
- Compatible additions increment the compatible version; breaking changes
  require a new major version, migration, fixtures, and transition window.
- Accepted policy changes use successor decisions.
- Extensions declare core compatibility and deprecation fields.
- Generated projects upgrade through a project-specific migration; the
  Octon Mini never overwrites them.
- Remove redundant summaries and expired exceptions.
- Track useful outcome measures such as time-to-orientation, time-to-resume,
  invalid-transition rejection, stale-evidence detection, closure rework,
  exception age, and false-positive/false-negative findings. Metrics describe
  harness performance and never become readiness approval.

Recommended cadence:

- per change: affected schemas, references, lifecycle, and extensions;
- weekly during active work: current-state compaction and stale tasks;
- monthly: policy exceptions, dependencies, evidence age, and summary size;
- quarterly: clean bootstrap, mutation suite, recovery, and authority review;
- per release: exact fingerprint, limitations, and final read-only check.

## 13. Common failure modes

| Failure | Required response |
|---|---|
| documentation becomes permission | classify trust and allow permission only from declared channels |
| installed tool becomes authority | separate availability, permission, and enforcement |
| passing report is treated as current forever | bind it to fingerprints and freshness rules |
| validator borrows an ambient runtime | pin/bootstrap the supported toolchain |
| domain constants enter the kernel | move them to a registered extension |
| status is copied across files | assign one owner and generate views |
| recommendation or owner selection is presented as accepted | keep separate fields and require a resolving accepted `DEC-####` authority link |
| trade-off score hides a failed safety or authority gate | disqualify the option before scoring and keep the failure visible |
| evidence gap is converted to a fact | retain `unknown`, choose an evidence owner/step/stop condition, and use evidence-first timing |
| handoff contradicts canonical authority | prefer references; validate explicit claim markers and complete the mandatory semantic reconciliation checklist |
| structural validation is called implementation readiness | report architecture, documentation, implementation, specialist, release, production, and efficacy conclusions separately |
| summaries become histories | compact current state and retain durable records |
| checksums are treated as truth | state their byte-integrity limitation |
| role names become principals | inherit and narrow task authority |
| child instructions weaken root | validate root-to-leaf compatibility |
| check writes caches or reports | suppress writes and test an unchanged tree |
| repository validates its own trust root | add protected independent CI where risk warrants |
| old harnesses look live | archive, banner, and test discovery |
| ceremony exceeds value | require every artifact to mitigate a named risk |

## 14. Acceptance criteria

A harness is complete only when these demonstrations pass:

1. A newcomer discovers instructions, current work, and closure command without
   oral context.
2. A nested-path fixture applies root and child rules and rejects weakening.
3. Review-only work cannot mutate, and local implementation cannot publish.
4. Valid task transitions and dependency-ready progressions pass; cycles,
   incomplete predecessor execution, unresolved gates/blockers, broken
   reciprocal plan links, and invalid transitions fail clearly. Decision
   dashboard/review inventories reconcile; decision and closure cycles,
   selected-as-accepted entries, gate-compensating scores, and missing
   evidence-first stop conditions fail clearly.
5. Each critical deny has a failing mutation.
6. A clean checkout runs the documented runtime and check.
7. Read-only validation leaves no tracked, untracked, ignored, cache, or
   timestamp change and never executes a target-project hook; the explicit
   project-check writer records truthful, fingerprint-bound outcomes and
   distinguishes failure, unavailable, skipped, and not-applicable states.
   A read-only review also records before/after status and fingerprints and
   reports stale projections without rewriting them.
8. Managed-source changes invalidate stale generated evidence.
9. Synthetic credentials are detected and output is redacted.
10. A trigger-installed sample extension validates and can be disabled without
    kernel edits; production-control packages reject invalid, stale-evidence,
    broken-reference, authority-expansion, unpinned-content, and unbound-review
    cases while remaining absent from every default profile.
11. Another maintainer resumes interrupted work from compact state, task, and
    linked evidence within an agreed time.
12. Interrupted refresh and corrupted event recovery are exercised.
13. Harness and real project checks pass on the exact handed-off revision; an
    adopted High-Assurance harness has no unresolved mandatory conditional or
    optional trigger assessment.
14. Final reporting states scope, failures, skipped checks, limitations, dirty
    state, and external effects without overclaiming.
15. Fresh solo, pair, and tiny-team assessments select only the supported
    provider-neutral workflows; unknown, stale, conflicted, zero-writer, and
    over-five states fail safely; concurrency does not change human count;
    every workflow operation resolves; and enterprise workflow identifiers are
    absent or rejected.
16. Governed completion planning changes no repository or external state;
    accepted digests stale when relevant inputs change; all four workflows and
    concurrent handback enforce their distinct requirements; missing or stale
    authority/check/review/PR/revision/ownership evidence blocks; interruption
    after every external action resumes without duplication; and cleanup occurs
    only after integration and fast-forward synchronization are proven.
17. Guided question generation changes no target or projection; one catalog and
    shared session engine govern initialization, adoption, and upgrade; TTY,
    answer-file, and legacy-flag inputs reconcile to stable IDs; unknown and
    deferred answers survive resume; unrelated target edits preserve valid
    answers while changed mode, instructions, catalog/question definitions,
    Octon Mini provenance, relevant evidence/authority/dependencies, expiry,
    session digest, or plan digest fails closed;
    recommendations, selections, accepted authority, and runtime permission
    remain distinct; work completion stays disabled or pending until every
    prerequisite is proven; and malformed/mutation fixtures are rejected.
18. Covered refusals use stable typed continuation codes, state whether
    anything changed, preserve exact current inputs, and provide concrete
    shell-free next argv; interactive init reaches one reviewed confirmation
    and apply; adoption and upgrade preserve proposal/session state across
    review; human and JSON summaries match detailed plans; accepted decisions
    reuse only under current applicability while runtime authorization never
    does; routine validation proofs hit only on exact current bindings while
    adoption/release gates run completely; `check` remains unchanged-tree;
    compatible bundles apply and roll back atomically; and overlapping,
    differently authorized, incompatible-freshness, or externally effective
    bundles fail without a global force path.
19. Long-running work is absent and inactive by default; installed payloads are
    digest-bound; one active run binds an existing task, authority source, path
    narrowing, instructions, context, project state, limits, validation, and
    marker-backed checkpoints; deterministic context shows omissions; exact
    limits and no-progress findings stop admission; every tested interruption
    selects an exact committed coordinate or conservatively refuses; read-only
    status/resume/explain write nothing; and an outcome-unknown effect is never
    replayed.
20. Authorized representative exercises cover software, structured-content or
    research work, interruption, changed instructions, repeated validation
    failure, budget exhaustion, no progress, context pressure, restart, and a
    safe local ambiguous-effect fixture. Unavailable unfamiliar-operator,
    pair/tiny, historical-project, cross-platform, or provider evidence remains
    explicitly `not_run`.
21. Autonomous delivery is available but externally locked in every profile;
    all seven pre-activation surfaces are deterministic, hook-free, and
    unchanged-tree; profiles never self-select; draft bytes and digests are
    deterministic; changed or missing confirmation blocks; activation installs
    exact local bytes through one transaction; current revocation, emergency
    stop, repository, branch, task, action, release, evidence, warning, limit,
    and selected compute-mode bindings are revalidated; both metered API and
    included-subscription paths fail closed; direct spending remains zero; and
    forbidden force, bypass, deployment, package-publication, communication,
    credential, settings, external-project, purchase, and tag-movement actions
    are absent or rejected.
22. Disposable initialization, adoption, upgrade, profile, activation,
    correction, release-adapter, reconciliation, cleanup, and interruption
    exercises prove zero duplicate external effects and exact or conservative
    recovery. Missing unfamiliar-operator, independent-reviewer, independent
    external-project, and human-usability evidence remains `not_run` and cannot
    support maturity, adoption, usability, or readiness claims.

Passing these criteria proves the harness is usable and testable. It does not
prove production safety, security, accessibility, legal compliance,
organizational approval, or suitability for every project.

Acceptance has two explicit gates:

| Gate | Criteria | Required evidence |
|---|---|---|
| Octon Mini release automation | 2, 4–10, 12, 15–19, 21, plus structural portions of 1, 3, and 14 | cross-profile valid/invalid fixtures, collaboration/workflow/setup/continuation/long-work/autonomous-delivery matrices, proof hit/miss and full-gate coverage, checkpoint/bundle/effect recovery mutations, operation-reference coverage, unchanged-tree checks, stale/partial recovery, extension confinement, secret redaction |
| Target-project adoption | human portions of 1 and 3, plus 11, 13, 14, 20, and 22 | timed unfamiliar-maintainer exercise, actual platform enforcement, one real task/closure, representative long-work and delivery exercises, exact project revision checks, truthful handoff report |

The release suite reports every criterion as `automated_pass`,
`project_demonstration_required`, or `not_exercised`; it may not summarize a
partial matrix as complete acceptance.

## 15. Evidence crosswalk

| Reusable concern | Reference evidence | Octon Mini treatment |
|---|---|---|
| Root instruction routing and local policy | **Observed — both** | Short root router plus root-to-leaf nested instruction validation |
| Deny-by-default action policy | **Observed — Commerce Foundry** | Core `policy.json`; declarative and explicitly non-authorizing |
| Typed records and lifecycle control | **Observed — both** | Stable four-digit IDs, schema validation, legal transitions, and closure gates |
| Path authority and canonical-source classification | **Observed — COE** | Dossier artifact catalog and generated path-authority mirror |
| Executable validation and mutation tests | **Observed — Commerce Foundry** | `CF:scripts/validate-local.sh`, `CF:scripts/strict_yaml.py`, and `CF:tests/test_strict_yaml.py` inform the portable validator and adversarial fixtures |
| Manifest, checksum, and generated evidence | **Observed — COE** | Transactional refresh with shared generation ID and freshness fingerprint |
| Domain-specific registries and policies | **Observed — both** | Restrictions-only extension API; never kernel constants |
| Extension compatibility and disable behavior | **Recommendation** | Versioned registry, confined paths, validator protocol, and disable test |
| Clean-runtime portability | **Inference** | Strict JSON contracts, Python reference implementation, alternate-runtime conformance suite, CI runtime matrix |

## 16. Implementation and adoption checklist

1. Select assurance from risk, collaboration from current writer count,
   concurrency as a separate modifier, and layout from representation needs.
2. Use interactive `octon init|adopt|upgrade` for one-command orchestration, or
   the read-only setup plus explicit plan/apply interfaces for automation;
   summarize observations, recommendations, selections, reused decisions,
   authority, unknowns, deferrals, continuation findings, and closure steps;
   then accept only the exact displayed digest.
3. Inspect `.octon-mini-origin.json`, the artifact catalog, and all
   proposed or unassessed sentinels.
4. Read applicable project instructions and classify real authority sources.
5. Record fresh aggregate collaboration evidence, derive the team band, and
   adopt a supported workflow through an accepted project decision; do not
   treat the assessment or decision as operation authority.
6. Adopt project scope, commands, owners, and applicable trigger packages
   through accepted project decisions; generation supplies none of them.
7. Populate intended state, dated current state, findings, plan, risks,
   provenance, evidence, and handoff without collapsing their information
   states.
8. Build hard plan/task dependency graphs, reciprocal plan/task links,
   structured gates and blockers, then derive the ready frontier before
   selecting planned work. Use valid direction rather than dates to choose
   among independent ready items.
9. Register every dossier representation in the project-local artifact source;
   run refresh to derive catalog, path authority, and integrity outputs.
10. Run changed-scope checks during work, optionally reusing only exact current
    routine proofs through the explicit writer, and run the read-only validator,
    complete project checks, release tier, and recovery tests without proof
    reuse at adoption/release gates.
11. Demonstrate one real dependency-gated task lifecycle through the adopted
    SCM workflow when applicable and a safe focus-derived handoff.
12. Record conditional trigger decisions, remaining unknowns, and limits; do
    not translate structural success
    into a readiness claim.

## 17. Automatically validated baseline and project-owned obligations

| Release automation validates | The target project must still decide or prove |
|---|---|
| syntax, duplicate keys, kernel/record schemas, schema-kind agreement, IDs, links, legal transitions, dependency cycles/readiness, and reciprocal plan/task links for declared stores | actual project facts, owners, requirements, acceptance criteria, and priority among independent ready items |
| closed collaboration bands, workflow mappings, freshness/conflict failures, review-capacity caps, operation references, and enterprise exclusions | actual maintainer topology, reviewer availability, workflow adoption, hosted settings, and permission for any Git or provider action |
| structured instruction and extension rules cannot declare authority expansion; prohibited mutations fail fixtures | who may authorize specific actions and whether the execution platform actually enforces the boundary |
| the core check writes nothing and executes no project hook; explicit project-check evidence is schema-valid, fingerprint-bound, and fresh; extension or hook mutation is detected after execution | whether configured commands and extension code are authorized and trustworthy, and whether an external sandbox or no-write boundary is required |
| project-local artifact source, derived catalog/path roles, traceability structure, and integrity metadata cohere | whether requirements are correct and evidence is substantively sufficient |
| extension compatibility, path confinement, typed validator response, unique IDs, trust declaration, disable behavior, and strict operations/security production-control record contracts | which domain extensions and controls apply, whether referenced external systems or reviewers actually exist, and who maintains or approves them |
| generated evidence is fresh for its declared byte scope | implementation quality, safety, compliance, legal rights, or release readiness |

The universal claim ends at this boundary: the kernel, contracts, validators,
profiles, and extension points are domain-neutral; project content,
enforcement integrations, risk decisions, and readiness conclusions are
necessarily project-specific.
