# Harness Model

Read the first available harness definition:

- source checkout: `../../../harness/SPECIFICATION.md`;
- installed bundle: `../assets/octon-source/harness/SPECIFICATION.md`.

## Required layers

Generate the smallest justified profile around:

1. short root instruction routing;
2. the seven-file `.agent/` governance kernel;
3. project profile and extension contracts;
4. operational records, explicit focus, derived current state, and staged
   repository-local transactions; and
5. optional `.agents/` capability packages and generated integrity.

The harness is project-local and subordinate to higher authority. Generated
policy remains non-authorizing and deny-by-default. Do not transfer
permissions, accepted decisions, current status, evidence, identities,
endpoints, or domain constants from this specification or another project.

Guided setup is source-side orchestration over the existing init, adopt, and
upgrade planners, not a second project harness or apply engine. Its session is
a reviewed input artifact outside the target. It records recommendations,
selections, and accepted-authority references separately and always records
`permission_grant: false`. Generated projects receive its schemas and CLI
support only in a new snapshot or explicit reviewed upgrade; the catalog and
agent procedure remain Octon Mini source guidance.

## Information owners

- permission boundary: `.agent/policy.json`;
- precedence and trust: `.agent/context.json`;
- IDs and statuses: `.agent/schema.json`;
- state transitions: `.agent/lifecycle.json`;
- tool contracts: `.agent/tools.json`;
- commands and checks: `.agent/validators.json`;
- stable project hooks, collaboration assessment, and workflow adoption:
  `.agent/project.json`;
- command inventory: derived `.agent/commands.json`;
- SCM and package triggers: `.agent/scm.json` and `.agent/packages.json`;
- installed provider-neutral Git workflow, when selected:
  `.agent/workflows/small-team-git.json`;
- explicit target-project check evidence: `.agent/project-checks/evidence.json`;
- active work: `.agent/tasks/`;
- durable intent: accepted `.agent/decisions/DEC-####*.md` records;
- material decision inventory and trade-off review:
  `.agent/decisions/governance-register.json`, subordinate to accepted
  `DEC-####` authority;
- accepted-decision reuse applicability: empty-by-default
  `.agent/decisions/reuse-policy.json`, bound to exact current accepted
  decisions and never operation authority;
- direct observation: `.agent/evidence/`;
- explicit operator focus plus derived resumption: `.agent/state/`;
- plan/apply/recovery receipts: `.agent/transactions/`;
- typed refusals and plan summaries: `.agent/scripts/octon_continuation.py`; and
- governed work-completion configuration: optional `work_completion` in
  `.agent/project.json`, exact task inputs in the task's optional completion
  contract, shared engine in `.agent/scripts/octon_work_completion.py`, and monotonic local
  receipts under the repository Git common directory; and
- generated integrity: `.agent/generated/`, always non-authoritative.

The kernel uses strict JSON with duplicate-key rejection and a local schema
snapshot. Domain behavior enters only through a registered,
restrictions-only extension that declares compatibility, confined paths,
provenance, side effects, and a structured validator.

Task `dependencies` are hard `TASK-####` prerequisites. Entering or re-entering
execution passes through `ready`, which requires completed dependencies,
satisfied gates, resolved structured blockers, and reciprocal plan links. Use
the read-only ready-frontier command to identify eligible work; current
direction or an accepted priority/value/risk decision chooses among independent
items, never a date-based inference.

Routine project-check proofs remain inside the explicit evidence store. The
read-only validator may validate them but never writes or refreshes them.
Consequential adoption/release gates prohibit reuse. Transaction bundle v1 is
limited to nonoverlapping, compatibly authorized, fresh, reversible local
members with no external effect and one exact receipt.

Each profile has a closed minimum governed-file inventory. Missing router,
kernel, state, script, schema, template, fixture, store, extension-registry,
or capability-baseline files are validation failures. Add project-specific
behavior only inside the validated extension and capability namespaces; do
not use an unregistered governance path.

## Collaboration and Git workflow boundary

Every profile includes the same four base workflows: `solo_direct`,
`solo_hybrid`, `pair_pr`, and `tiny_pr`. Classify one, two, and three-to-five
write-capable humans as `solo`, `pair`, and `tiny`; zero blocks, and more than
five is explicitly unsupported. Read-only humans, bots, automation, and recent
activity do not alter the write-capable-human count. Simultaneous humans or
agents add `concurrent_work` without changing the human band.

Assessment v2 requires project-owned evidence, observation and expiry times,
and limitations for every fact used by its result. Unknown, stale, or
conflicting state selects nothing. Store only aggregate counts and safe
references, never collaborator identities. Planning reads the stored project
and supplied evidence without changing it; apply is an exact digest-bound
transaction. Ordinary `--check` never invents or refreshes collaboration facts.

A recommendation cannot adopt or authorize a workflow. Adoption requires an
accepted project-owned decision, and each Git or hosted operation still follows
its own authority class. The compact kernel ships no full Git portfolio. Once
Git is selected, a pinned, decision-bound package transaction installs the
provider-neutral catalog, whose operation references resolve to the exact,
fail-closed catalogs in `.agent/tools.json`. GitHub is optional and generated projects assert no hosted
reviewer, check, protection, environment, release, credential, permission, or
CI fact.

The one shared `work.finish` engine extends these workflows across all
assurance profiles. It starts disabled. Its optional completion event hook is
plan-only. Planning writes nothing and performs no network or provider call.
Apply reconstructs the reviewed plan, stages only task-owned paths, runs only
configured read-only hooks ephemerally, and requires exact current external
authorization. Pair and tiny workflows observe a real approval by a different
eligible developer; they never submit or fabricate it. Resumable receipts
retain partial external success without claiming atomic rollback, and cleanup
follows integration proof and fast-forward synchronization.

Do not add GitFlow, merge queues, release trains, stacked-PR trains, fork-first
internal contribution, approval hierarchies or stages, dedicated release
manager handoffs, organization-wide rulesets, multi-environment promotion, or
enterprise issue/portfolio governance.

## Adoption boundary

Scaffolding proves only that the baseline files were generated consistently.
Established projects use bounded semantic adoption with explicit exclusions,
collision and functional-equivalence review, no overwrite, exact fingerprints,
staged validation, and receipts. Target-project adoption must still inspect
actual scope and risks, resolve or explicitly classify sentinels, record the authority posture, assess every
target-project hook, execute configured hooks only through the explicit
shell-free evidence writer, run read-only checks and mutation tests in a clean
environment, and complete a real task lifecycle. Structural conformance,
project-harness adoption, and demonstrated target-project readiness are
separate conclusions.

For review-only work, instantiate the read-only review template, record
status/revision/fingerprints and exact command results before and after, and do
not refresh projections or run project hooks. Handoffs prefer canonical
references; explicit copied status markers are mechanically reconciled and
version, ownership, recommendation/adoption language, and evidence adequacy
remain mandatory human checks.

No profile includes operations/observability or security/supply-chain content
by default. Trigger assessment may install a pinned package only after an
accepted trust decision. Its strict records can support production-governance
adoption, but presence or successful validation proves neither external
execution nor a qualified conclusion.
