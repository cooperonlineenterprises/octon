# Octon 5.0 generation identity

Current producer is Octon, source metadata `octon.json`, and current origin `.octon-origin.json` using `octon.project.origin.v1`. The published Mini origin schema remains unchanged. Newly generated capability provenance names Octon; historical producers are retained. Generic kernel 4.2 contracts, Mini-lineage wire keys and source namespaces below remain compatibility identifiers. See `docs/IDENTITY_TRANSITION.md` and the explicit 4.2.0-to-5.0.0 migration. No ownership, permission, package-activation or snapshot-independence boundary changes.

The foundation contract below is retained where unchanged. Historical 3.x/4.x migration descriptions apply to those releases; 5.0 directly upgrades only Mini 4.2.0. Current origin locators use `.octon-origin.json` wherever the foundation described the former current `.octon-mini-origin.json`.

# Generation Contract

## Source and output roles

`octon-mini` is the versioned reference and generator source. A target
project receives an independent snapshot containing:

- `AGENTS.md`;
- `.agent/`;
- `.agents/` for profiles that include capability packages;
- `project-dossier/`;
- the project-local `octon` launcher; and
- `.octon-mini-origin.json`.

Generated files do not remain linked to this repository.

## Generation disposition boundary

`shared/source-contracts/profile-manifest.json` is the canonical,
machine-readable source for profile order and layers, reviewed generation
inventories, project-local and derived paths, optional or triggered packages,
acceptance coverage, and documentation projections. Its generation rules are
the boundary between Octon Mini source and automatic target-project output, and
its schema is versioned separately. Every source path defaults to `source_only`;
only a reviewed rule with disposition `generated` or an explicitly installed,
content-addressed package may enter the selected profile.

Profile-manifest v2 retains the v1 generated rules: they enumerate the exact
reviewed relative paths and bind that list by count and SHA-256 digest. Its
versioned OEP-1 target installation section is source-only and not selectable
for generation. It binds a reviewed core seed inventory and root ownership but
does not claim qualified runtime assets, target adoption, or migration. Adding,
removing, renaming, or moving a
template or copied schema therefore requires an explicit policy inventory
review. A file's location under a template directory is not sufficient
authority to generate it.

Runtime generation is allowlist-driven and scoped to the requested profile.
An additional matching file that is absent from the reviewed list is ignored,
reported as information degradation, and never added to the output. It does
not block an otherwise valid setup. A missing reviewed dependency blocks only
profiles that require it; a problem confined to High Assurance cannot block
Minimal or Standard. The read-only adoption planner uses the same selected-
profile boundary.

The generator capability reports four operation-local modes without creating
a universal project state enum:

- `normal` — all reviewed inputs required by the selected profile are present;
- `degraded` — unreviewed additions were ignored while the reviewed capability
  remains intact;
- `blocked` — a selected-profile dependency, authority contract, or hard
  invariant cannot be established; and
- `recovering` — the read-only diagnostic is exposing exact findings and
  recovery guidance without changing policy or files.

Findings use capability-specific failure classes. Unreviewed additions are
`information_degradation`; missing reviewed inputs are
`dependency_degradation`; an invalid policy identity or non-authority contract
is `authority_degradation`; and a symlink, escape, forbidden output, collision,
or exact-stage violation is `safety_invariant_degradation`. Degradation may
reduce availability or generated scope, but never truthfulness, correctness,
safety, authority, or evidentiary standards.

Hard boundaries remain fail-closed for the affected operation. Generation
must leave the target unchanged when a reviewed selected-profile source is
missing, a source-only or profile-inapplicable input is selected, a reviewed
source is a symlink or escapes its boundary, an output collides or is
forbidden, or the staged file/directory tree differs from the exact intended
output or contains a symlink or special file.

Run the read-only recovery diagnostic with:

```text
python3 skills/octon-project-bootstrap/scripts/scaffold_project.py \
  --diagnose-generation-policy \
  --profile minimal
```

Omit `--profile` to inspect all profiles. Diagnostics return nonzero when any
inspected capability is degraded or blocked. Repository validation always
inspects all profiles strictly, so an ignored unreviewed path still fails
Octon Mini CI until it is removed, retained outside a generated source root, or
explicitly reviewed into the versioned inventory. When an addition is the only
drift, the diagnostic calculates a candidate path list, count, and digest to
reduce maintenance work; that candidate is labeled
`review_required_not_approved`, is never written automatically, and remains a
review input rather than authority.

This capability contract does not add irrelevant timeout, retry, or circuit
machinery to deterministic local scaffolding. Such controls remain required
only for project capabilities with applicable volatile or external
dependencies.

The installed Codex skill remains a source bundle and may contain the catalog,
review, migration guidance, and other source-governance material needed to
operate the skill. That bundle is not a generated project. Deliberate manual
adoption of a source-only artifact is a separate project-owned change and is
not authorized by this generation policy.

The installed source bundle also includes the repository's MIT-0 `LICENSE`.
Automatic target-project generation treats that source license as an explicit
forbidden output: it neither copies `LICENSE` nor chooses a target project's
overall license. MIT-0 permits source reuse without an attribution-carrying
condition, while the target project's licensing decision remains project-owned.

`shared/source-contracts/setup-questions.json` is the one authoritative setup
question catalog. It and its catalog schema are source-only. The strict setup
answer and session schemas may be included in a newly generated snapshot or
added through an explicit reviewed upgrade according to the profile manifest.
A setup session itself is never generated into a project, never copied between
projects, and never becomes project authority merely because a planner accepts
its digest.

New snapshots receive both the historical setup-session v1 schema and the
dependency-scoped v2 successor schema. They also receive the non-authorizing
Continuation Contract, plan-summary, decision-reuse, validation-proof,
transaction-v3, diagnostic-v2, and project-check-evidence-v3 schemas plus the
shared continuation renderer. The project-owned decision-reuse registry is
generated empty; generation creates no reusable decision record.

## Non-transfer rules

The intent/delegation foundation registered in `octon.json` is source-only.
Its versioned schema, synthetic fixture and shadow helper are not selected by
the current profile rules and are not a generated project capability. Installed
bootstrap source bundles may retain them as source governance/qualification data.
No intent, grant, shadow result, activated policy or new DEC actor is copied into
an existing or freshly generated consumer. Actual successor adoption requires its
separately versioned release and exact project-owned migration.

Generation transfers structure, schemas, vocabulary, and validation patterns.
It does not transfer:

- project facts, implementation status, or project-owned unresolved values;
- collaborator identities, maintainer counts, access observations, activity,
  reviewer capacity, or hosted repository settings;
- decisions, approvals, evidence, or readiness claims;
- recommendations, owner selections, trade-off results, compatibility
  findings, or project-specific minimum closure claims;
- permissions or standing authorization;
- legal, privacy, security, or compliance conclusions;
- a target-project-wide license selection or legal ownership conclusion;
- external accounts, credentials, URLs, vendors, providers, or provider state;
- source-project history or evidence.

The generated harness is an unadopted baseline. Its policy is deliberately
non-authorizing, project command hooks are unassessed, and generated reports
do not claim target-project readiness.

Three states remain distinct throughout generation and validation:

1. structural Octon Mini conformance means the generated contracts are
   internally valid;
2. project-harness adoption means project owners have assessed the hooks,
   triggers, authority basis, and evidence required by the selected profile;
3. demonstrated target-project readiness requires current project-specific
   implementation, operational, specialist, and external evidence.

Neither of the first two states implies the third.

Every 4.2 snapshot includes a dormant `octon delivery` surface plus inert,
content-addressed local payload bytes for autonomous delivery and its
long-running-work dependency. This is availability, not installation,
activation, applicability, adoption, permission, repository/provider
configuration, or readiness. The generated project records exactly
`available_not_activated`, locked writes, locked external effects, no profile,
no authorization reference, and an unassessed trigger.

Pre-activation research, context, applicability, planning, status,
explanation, and activation preview execute no project hook and mutate no
target or external state. A deterministic standing-contract draft may be
written only to an explicitly requested external review path. It remains
non-authorizing until an independent human confirms its exact digest. The
accepted record and confirmation remain outside the repository; generation
never supplies either.

Generation must not invent, transfer, or upgrade facts, decisions, evidence,
credentials, providers, authority, or readiness. A template default is not a
project observation. A source decision is not a target-project decision. A
generated schema is not evidence that its optional artifact applies.

Guided question generation and target inspection are read-only capabilities.
They may write a user-requested session only to an explicit external path; they
must not mutate the target, refresh projections, execute detected hooks,
install packages, update receipts, query hosted providers without separate
authority, or create accepted decisions. The final plan remains an ordinary
init, adopt, or upgrade transaction plan, bound to the canonical session
digest and current fingerprints.

Interactive `octon init`, `octon adopt`, and `octon upgrade` are orchestration
over these same mechanisms. They write session and plan artifacts only to the
operator's explicit external review directory, may pass the full displayed
digest internally after one confirmation, and must revalidate unchanged plan
bytes plus every normal precondition before apply. A review block preserves
the artifacts and emits the Continuation Contract; it never becomes an
overwrite or auto-apply exception.

## Binding classes and revalidation

Generator inputs are classified by when and where they may be bound:

1. **Source-stable inputs** are versioned Octon Mini contracts, schemas,
   vocabularies, and profile inventories. They are selected from the exact
   source revision and recorded in origin provenance.
2. **Generation-time identity inputs** are the explicitly supplied project
   name, derived slug, selected profile, creation date, Octon Mini version,
   generator version, and harness-kernel version. They identify the snapshot;
   they do not describe project reality.
3. **Project-owned unresolved inputs** include owners, authority sources,
   decisions, commands, applicability, providers, environments, facts, and
   readiness. Generation preserves explicit `unknown`, `not_assessed`, null,
   or replacement sentinels until project-owned evidence and authority resolve
   them.
4. **Execution-volatile inputs** include current revisions, access, provider
   state, credentials, tool availability, freshness, external outcomes, and
   other time-sensitive facts. They are never frozen into the scaffold as
   durable truth and must be revalidated at every consequential boundary that
   relies on them.

These binding classes are not information authority or permission classes.
An execution-time observation may be fresh and still lack action authority.
Unresolved or unknown template variables remain validation failures; explicit
project sentinels are retained only where the corresponding schema allows them.

## Collision and mutation rules

New-project generation accepts only a nonexistent or empty target directory.
The generator resolves its complete intended output, renders it in a sibling
staging directory, validates the staged snapshot, and atomically places the
snapshot at the target. Validation failure leaves the target unchanged. It
must not offer an overwrite, force, or in-place merge mode.

Integration with an established repository starts with bounded, read-only
semantic adoption planning. The default reads at most 200 allowlisted UTF-8
text/config files, 256 KiB per file, and 4 MiB total, while excluding secrets,
symlinks, binaries, ignored/generated/vendor/dependency/build/coverage and
sensitivity-marked content. It retains content hashes and matched vocabulary,
not file contents. Functional equivalence and authority preservation always
require proposal-bound review. Apply refuses every existing-path overwrite,
stages the release tier, and leaves adoption `in_progress`.

## Origin and upgrade rules

The origin record contains:

- Octon Mini product name and version;
- selected profile;
- generation date;
- target project name and slug;
- generated path inventory;
- physical layout;
- generator and kernel versions;
- a transaction generation ID;
- an immutable initial-generation snapshot;
- an append-only migration history; and
- an installed inventory containing role, upgrade policy, baseline Octon Mini
  version, mode, and exact pristine hash for every static path.

The snapshot also records the harness kernel version and generator version
where available. This provenance is not a live dependency: later Octon Mini
changes cannot silently change a generated project's rules.

An upgrade is a three-way migration task using the recorded old inventory,
current project, and candidate snapshot. It must preserve
`initial_generation`, classify each path, preserve project-specific content,
append typed authority/evidence provenance, and never replace accepted
target-project authority silently. Automation is limited to safe additions,
exact-pristine non-authoritative implementation assets, and derived
regeneration. Project-owned, authority-bearing, modified, deleted, moved,
permission, symlink, workflow, record, stable-ID, and configuration cases
require explicit review.

Adding `work.finish` to an existing generated project is therefore an explicit
upgrade or pinned package update. Safe automation may add the previously
absent engine and schema and may preserve an exact-pristine disabled baseline,
but it must not enable the hook or overwrite project-owned accepted decisions,
workflow adoption, task records, hook commands, provider settings, branch
rules, cleanup policy, or authorization policy. A project can keep the
feature disabled indefinitely and remain structurally valid.

Adding guided setup support to an existing snapshot follows the same explicit
upgrade boundary. New catalog questions appear unresolved and receive no
silent answer. An upgrade may add absent Octon Mini-owned implementation or
schema paths when policy permits, but it cannot overwrite instructions,
accepted decisions, setup selections, workflow adoption, hooks, provider or
branch settings, package choices, or any other project-owned file. Current
Octon Mini CLI flags map deterministically to stable question IDs. Project
Blueprint command and field identities may be recognized only as inputs to the
explicit reviewed cross-brand migration; Octon Mini provides no `pb` runtime
compatibility.

Adding continuation, decision reuse, persistent validation proofs, or bundle
support follows that same boundary. An upgrade may add absent Octon Mini-owned
schemas and implementation files. It may not create a decision-reuse record,
convert an old decision into reusable authority, enable a project hook, rewrite
project-check evidence, bundle a prior operation, or treat an old plan as
accepted. Setup-session v1 and transaction v2 artifacts remain immutable
predecessors and become current only through explicit successor workflows.

Adding the 4.1 dormant long-running-work dispatcher is an explicit reviewed
snapshot upgrade. It never installs or adopts the package. Package installation
is a later content-addressed transaction recording applicability, owner, trust
decision, exact version/digest, installed paths, and validation receipt. The
package is installed inactive; project adoption is a separate digest-bound
transaction referencing a current accepted project decision.

Project Blueprint 3.x→Octon Mini 4.0.0 is the current cross-brand migration.
It may read legacy `pb`, `.project-blueprint-origin.json`, and
`project-blueprint.*` identities only as legacy inputs to transform; it must
not execute or dispatch `pb`. A successful result contains `octon`,
`.agent/scripts/octon.py`, `.octon-mini-origin.json`, and current
capability-qualified Octon Mini identities, and contains no current legacy
launcher, runtime module, alias, or origin record. Removing an established
legacy path is a reviewed migration operation, never a silent overwrite
exception.

A breaking migration must also ship executable valid and invalid fixtures. A
legacy snapshot without exact installed baselines requires reviewed seed data;
the migrator may not infer pristine hashes or authority from current bytes. Its
reference transformation or reconciler must preserve stable IDs and accepted
authority, require explicit classification when a legacy relationship is
ambiguous, reject mixed live schema authorities, retain the exact pre-migration
state as rollback evidence, validate the candidate result against the new
schemas, and produce no further change when applied a second time.

## Template variables

The initial generator supports:

- `PROJECT_NAME` (derived and Markdown-escaped for prose templates);
- `PROJECT_NAME_JSON` (derived with a standards-compliant JSON encoder);
- `PROJECT_SLUG`;
- `CREATED_DATE`;
- `OCTON_MINI_VERSION`;
- `HARNESS_KERNEL_VERSION` (the independently versioned harness-kernel
  compatibility axis);
- `PROFILE`;
- `HARNESS_REFRESH_COMMAND` and `HARNESS_REFRESH_WRITES` (derived from the
  selected profile, not supplied as project facts);
- `GIT_PORTFOLIO_VERSION` and `GIT_PORTFOLIO_SHA256` (derived together from
  the single authoritative `small-team-git-portfolio` package contract in the
  profile manifest, never maintained as independent template constants).

Unresolved or unknown template variables are validation failures.

## Harness generation requirements

Every profile generates the seven-file governance kernel, explicit focus,
derived compact current state, task and decision templates, staged transaction
and diagnostic helpers, a read-only validator, and positive and negative tests.
It also generates an empty project-owned decision-governance register plus
blank owner-workbook, trade-off-review, and read-only-review templates. The
register contains no decision question, recommendation, owner selection,
accepted authority, evidence result, or readiness conclusion.
It also generates an empty decision-reuse registry and the shared continuation
renderer. Neither artifact creates accepted authority, operation confirmation,
runtime authorization, or a readiness claim.
It also generates a project-check evidence store, an explicit project-check
writer, an unassessed privacy-minimized collaboration profile, and compact SCM
and package triggers. The full provider-neutral Git portfolio and domain
packages are absent until a reviewed trigger transaction installs their pinned
content. The validator exposes a full read-only check, ready-frontier and
resumption derivations, and coded diagnostics; none executes project hooks.
Larger profiles add operational records, project-extension contracts,
capability packages, and generated-integrity tooling.

The selected profile also defines a closed minimum operational-file
inventory. The generated validator rejects a missing required router, kernel
file, schema, script, state or store entry point, template, fixture, extension
registry, or capability-package baseline. Project-specific additions belong
inside the registered extension and capability namespaces; they do not make a
required baseline path optional. This harness-retention rule is separate from
the dossier artifact registry, whose assessed applicability and durable
omission records intentionally support combining or omitting dossier
representations.

Canonical structured files are strict JSON. Every parser rejects duplicate
keys. YAML is allowed only inside a registered extension that declares and
bootstraps a pinned parser; YAML never becomes a hidden dependency of the
domain-neutral kernel.

The scaffold validator must:

- run without another repository's environment;
- require Python 3.11 or newer;
- use `--check` as a read-only operation;
- reject critical authority-policy mutations;
- validate all repository source paths by default, with only explicit,
  reasoned fingerprint exclusions;
- detect unresolved generation placeholders and redact obvious secret
  assignments;
- validate strict syntax, schemas, controlled IDs, references, lifecycle
  transitions, plan and task acyclicity, dependency-gated readiness,
  reciprocal plan/task links, structured blockers, dossier traceability,
  nested instructions, extension compatibility, and path authority;
- validate the decision-governance inventory, controlled type/timing/lifecycle/
  disposition/compatibility vocabularies, unique `DREG-####` IDs, accepted
  reciprocal `DEC-####` authority links, recommendation/selection/acceptance separation,
  evidence-first owner and stop conditions, option gates, non-overlapping
  balanced attributes, accepted outside-register constraints, dashboard/review
  reconciliation, closure evidence, and acyclic decision and minimum-closure
  dependencies;
- validate collaboration evidence, freshness, confidence, team-band and
  workflow-selection coherence without counting read-only people, bots,
  automation, or activity as write authority;
- reject unknown, stale, conflicting, no-writer, and over-five workflow
  selection failures safely, reject enterprise workflow identifiers, and
  require every workflow operation to resolve to the closed tool catalog;
- derive an unordered ready frontier only from completed hard dependencies,
  passed or validly waived gates, resolved structured blockers, reciprocal
  links, and populated readiness contracts;
- keep timeline fields outside the closed readiness contracts and never use
  dates when deriving or ordering the core ready frontier;
- enforce the selected profile's minimum governed-file inventory and reject
  unregistered extension or capability roots; and
- label structural success as distinct from project readiness.

Primitive new-project scaffolding runs the structural check and bounded fast
mutation tier before atomic placement. Guided initialization, semantic
adoption, live upgrade, and release gates stage the complete applicable release
tier. This performance distinction changes validation cost, not safety claims
or target-project readiness.

The generator may create initial empty stores and unassessed configuration. It
must not create an accepted decision, completed task, passing evidence record,
human approval, or readiness certification. A generated empty ready frontier
does not establish project adoption or permission.

A generated maturity field is unassessed. Structural validation never advances
a requirement or gate from `Architecturally specified` through
`Production-proven`, and no maturity level implies a higher one.

The source-only Pattern Catalog, its records and fixtures, and the Architecture
Proof schema and templates are not generated, adopted, or copied into a
profile inventory. The optional Context Pack schema is a trigger-installed
package. Its absence never means CTX-0001 is inapplicable; generation does not
create a manifest, select a consumer or source, or infer purpose, validity,
sensitivity, retention, revocation, or permission.

Every new 4.1 snapshot contains only the dormant `octon work run` route and a
`long_running_work: not_assessed` trigger. The payload, adoption record, active
run, history, and checkpoints are absent until separately installed and
adopted. Package-owned `.agent/work-runs/` state is excluded from general source
fingerprints so progress bookkeeping cannot stale the project evidence it
references; the package validator owns its structural and checkpoint checks.
Ordinary dispatch supplies the runtime clock, rejects symlink-ancestor state
paths, and revalidates adopted decision bytes, governed receipts, current
validation evidence, and marker-backed recovery before advancing.

## Collaboration and Git workflow rules

Every generated profile begins with collaboration v2
`assessment_status: not_assessed`, unknown team band, null fact/evidence pairs,
empty conflicts, `concurrent_work: false`, and no workflow. This is the only
transferable state. Each fact used by a result requires source, observation
time, expiry, and limitations. Templates never contain collaborator facts,
identities, reviewers, providers, hosted settings, or accepted workflows.

The supported human bands are exactly one (`solo`), two (`pair`), and three to
five (`tiny`) write-capable humans. Zero is blocked; more than five is
`unsupported_team_size` and has no enterprise fallback. Bots, automation,
read-only access, and recent activity do not change the human band. Expected
simultaneous human or agent work may add `concurrent_work` without changing
human count.

The base portfolio is exactly `solo_direct`, `solo_hybrid`, `pair_pr`, and
`tiny_pr`. It is provider-neutral and non-authorizing. The kernel stores only a
compact SCM trigger and pinned package digest; the full portfolio is installed
transactionally only when Git is selected or explicitly adopted. An
uninstalled portfolio is not a runtime dependency. Unknown, expired, or
conflicting evidence cannot silently select a workflow. Adoption requires a
resolving accepted project-owned decision, but
that decision grants no local mutation, network, publication, review,
integration, release, or destructive authority. Project risks may add controls
without changing the team band or automatically selecting an assurance
profile.

Every profile also receives one shared `work.finish` implementation and a
disabled, non-authorizing `work_completion` configuration. The implementation
is inert while the trigger-installed Git portfolio is absent or completion is
disabled. A project may enable it only after adopting one supported workflow,
assessing its repository, provider, optional self-PR, required checks,
eligible provider reviewer identities where peer review is required, the exact
`commands.work_completion_plan` read-only argv, read-only validation hooks,
an explicit no-active-Git-hooks policy, cleanup, and assurance references, and preserving
the accepted workflow authority link. Team size and assurance profile never
select another completion engine.

An enabled completion event hook references the existing project command-hook
model and is restricted to the exact shell-free argv for `octon work finish
plan`.
Planning performs no write, refresh, fetch, provider query, receipt update, or
external action. Apply is bound to the deterministic plan digest and current
preconditions; exact task-scoped external authorization is supplied at run
time and revalidated before each effect. Configuration, generation, package
installation, workflow adoption, or command invocation cannot supply it.
External effects use monotonic resumable receipts and never claim the exact
rollback guarantees of repository-local transactions.
The generated dispatcher consults the hook only after a successful
`work.close` transaction. It prints the read-only plan or reports a
post-closure planning block; it never treats the event as authorization to
apply.

## Proposal and transaction rules

The source and generated workflow interfaces project one authoritative command
manifest. Each command declares whether its independently usable surface is the
bootstrap source or the generated project, so the combined inventory is not
mistaken for a promise that every command is installed locally. Planning and
diagnosis are read-only. Every plan records operation,
scope, source evidence, observations/inferences/explicit decisions/gates,
assumptions, confidence, limitations, governing-instruction fingerprint,
per-path type/mode/hash, exact operations, conflicts/exclusions, staged and
post-apply validation, rollback strategy, planned receipt identity, and a
canonical digest.

New plans use `harness.transaction-plan.v3`. A semantic successor names its
immutable predecessor and records changed and identical fields, preserved
review conclusions, review-again fields, and digest-change reasons. The shared
`harness.plan-summary.v1` projection groups create/replace/delete/derived
writes, non-changes, safety rules, review items, local/external effects,
validation, recovery, reused current inputs, the full digest, and its one
confirmation. Detailed plan bytes remain the machine authority for apply.

Two or more plans may form `harness.transaction-bundle.v1` only when they
target one project, use current identical governing instructions, have
nonoverlapping operations, compatible authority/confirmation/freshness and
reversibility requirements, one atomic staging/receipt/rollback boundary, and
no external or monotonic effect. Every other combination fails or remains
separate. One bundle receipt retains every per-path preimage and postimage.

Apply requires that exact reviewed digest, refuses changed instructions,
evidence or targets, clones the repository into staging, permits only declared
derived writes, validates the staged result, writes a pending journal before
target mutation, then validates the target read-only. The receipt embeds exact
preimages and postimages. Recovery restores only when paths match before or
planned-after state, or finalizes an exact terminal receipt. Rollback records a
durable in-progress state, resumes only across exact before/after states, and
refuses subsequent independent changes. There is no force mode.

Transaction receipt v3 records host-specific phase timings for staging,
refresh, staged validation, live apply, post-apply validation, and receipt
preparation. The apply process emits receipt-persistence and total timing only
after the immutable receipt write completes. These measurements guide
optimization but are not human-usability
evidence and do not permit hardlinks, shared writable inodes, skipped final
gates, or weaker isolation.

GitHub is an optional integration boundary. Generation does not imply an
account, provider, credential, reviewer, branch protection, required check,
environment, release, successful CI result, or hosted permission. Any hosted
observation is gathered separately through an explicit read-only network
action; any push or PR publication remains explicitly authorized external
mutation.

The optional adapter separates read-only PR location, check observation, and
review observation from PR creation and merge. It cannot infer required check
names, reviewer eligibility, merge method, branch deletion, or authority from
provider defaults. An agent or self-review never satisfies required peer
approval.

The separately activated autonomous-delivery adapter may add only exact
workflow dispatch, annotated source tag, tag push, GitHub source Release, and
read-back operations covered by a current independently confirmed standing
record. It must revalidate revocation, emergency stop, current evidence for the
one selected metered-API or included-subscription compute mode, repository,
branch, task, exact plan, action, release type, evidence, and remaining limits
before every effect. It persists an attempted marker before
the call and never replays an unknown outcome. Direct external spending is
always zero.

The source checkout may route `octon work finish` to the existing
work-completion engine through a source-only runner. That runner consumes an
external immutable, digest-bound Codex task reference and a precommitted source
candidate; it generates no target task record and is never copied as a second
generated-project lifecycle. Source merge remains blocked until the required
check and all 24 candidate matrix jobs pass; cleanup remains blocked until
exact integrated-main validation evidence is recorded.

The source checkout may route `octon delivery effect` through a source-only
wrapper around the same closed delivery-effect adapter. Candidate dispatch is
task-branch-bound; release effects are clean-`main`-bound. The source wrapper
is not copied as a generated-project runtime and does not broaden the adapter's
four supported operations.

The generated portfolio excludes GitFlow, merge queues, release trains,
stacked-PR dependency trains, fork-first internal contribution, multi-level
CODEOWNERS approval, multiple mandatory approval stages, dedicated release
manager handoffs, organization-wide ruleset orchestration, multi-environment
promotion pipelines, and enterprise issue or portfolio governance.

## Project-command and adoption evidence rules

Each `project_test`, `project_lint`, `project_build`, and `project_closure`
hook is deliberately assessed as exactly one of:

- `not_assessed`, allowed only before project-harness adoption;
- `configured`, with an owner, nonempty argv-style command and version command,
  both using the same executable, declared side effects and write scope, and
  an evidence-freshness contract;
- `not_applicable`, with a named owner and nonempty project-specific rationale.

Commands are represented as argument arrays and executed without implicit
shell interpretation. Structural `--check` validates configuration and
existing evidence only. It must never execute a project hook, update evidence,
or reinterpret a configured command as permission.

A read-only review must also avoid refresh and generation. It records the
pre-existing repository revision/status and useful fingerprints, exact commands
and exit statuses, unavailable/skipped checks, and the same observations after
review. A stale projection is reported by source and affected output rather
than rewritten. Any review-caused file or external-system change prevents a
read-only assurance claim.

The separately invoked project-check writer is an explicit mutating workflow.
It runs only configured hooks, records unavailable and not-applicable outcomes
without converting them to passes, and appends closed evidence containing the
exact argv and tool version, executable fingerprint, source revision or
fingerprint, environment, dirty/untracked/ignored scope, start and end time,
outcome, limitations, skipped checks, declared possible external effects,
explicitly unassessed observed external effects, and repository mutations.
Output content is hashed rather than retained when it could expose secrets.
Mutation comparison is detection, not sandbox isolation.

For routine iteration only, that writer may reuse
`harness.validation-proof.v1` results stored in project-check evidence v3. A
hit binds the exact declared input set, check identity and shell-free argv,
executable bytes and version output, configuration, governing instructions,
hashed environment characteristics, side-effect class, observation and
freshness, passing result, and limitations. Any changed binding, expiry,
external effect, or runtime authorization is a miss. `check` writes and
refreshes no proof. Adoption and release gates prohibit reuse and execute the
complete applicable boundary.

An adopted project requires coherent adoption status, a resolved accepted
externally grounded adoption decision, no adoption blockers, every command
hook assessed, and fresh source- and command-bound passing evidence for every
configured hook. An adopted High-Assurance project additionally requires all
Conditional and Optional dossier triggers to be assessed and every applicable
control to retain an active owner, representation, review state, and current
evidence references. These checks establish adoption conformance only; they
cannot certify specialist conclusions or production readiness.

## Derived-file rules

Initial generation selects the profile-applicable artifact types and physical
representations from `dossier/artifact-types.json` and writes them to
`project-dossier/machine-readable/artifact-registry.json`. That project-local
registry becomes the authoritative source for artifact metadata in the
independent snapshot. It is not regenerated from Octon Mini source during
ordinary maintenance or upgrade.

`project-dossier/ARTIFACT_CATALOG.json` is a generated mirror of the
project-local registry.
`project-dossier/machine-readable/path-authority.json` is generated from the
same registry and its registered physical paths. The two files are sibling
mirrors; neither is the other's edit source. Shared JSON schemas are copied
into `.agent/schemas/` so every generated project is independently
validatable.

Every profile includes an explicit refresh command. Refresh first validates
non-derived sources, requires exact registry coverage for physical dossier
files, stages all applicable outputs, and only then replaces the derived set.
Minimal and Standard refresh the catalog, path-authority map, and manifest.
High Assurance additionally refreshes `project-dossier/CHECKSUMS.sha256` and
`.agent/generated/*`.

All refreshed outputs carry or are bound to one generation ID. Because
ordinary filesystems cannot atomically replace multiple files, the final
read-only check rejects any interrupted, partial, or mismatched set. Refresh
does not infer entries for unregistered files, rewrite the authoritative
registry, overwrite non-derived artifacts, or delete project sources.
Generated validation reports are closed machine-readable records scoped to
the checks actually performed before refresh. They distinguish `pass` from
`not_run`, enumerate failures and skips, disclose fingerprint and Git scope,
external effects, and limitations, and never convert structural success into
a readiness or authorization claim. Consequential evidence states what its
result does not prove. The post-refresh exact-tree check is
reported by the refresh command's exit status rather than retroactively
claimed by the pre-refresh report.

## Extension boundary

The kernel is stable and domain-neutral. A registered extension must declare
its version, compatible kernel major version, confined config and validator
paths, owner, provenance, side effects, deprecation path, and
`authority_effect: restrictions_only`. Enabled validators return structured
JSON findings. Disabling an extension must require no kernel edit.

No default profile includes a production-control payload. Trigger assessment
may install the pinned operations/observability or security/supply-chain
package after an accepted trust decision. Installed extensions start disabled,
validate only project-owned declarations and evidence references, deny network
and undeclared filesystem effects, and never claim that a deployment, monitor,
scanner, review, signing service, or external platform exists or ran. Enabling
either package before its project-level adoption is complete fails closed; a
`not_applicable` trigger installs nothing.

## Disposable target qualification exception

The source profile v3 retains the exact v2 generation rules and inactive target
design, and adds a closed nonselecting disposable-runtime dependency contract.
The original profile v2 schema/reader remain supported with their original closed
shape. Only `qualify_disposable_runtime.py --disposable-qualification` projects
fresh canonical minimal/compact staging assets into actual target paths. It
neither enables ordinary target generation nor upgrades a live consumer.
See [qualified scope and recovery boundaries](../docs/DISPOSABLE_RUNTIME_QUALIFICATION.md).


## Source-v4 runtime binding qualification

Source v4 keeps the current manifest as the single inventory owner and validates
its complete legacy generation semantics through the named exact historical-v3
adapter. Its inactive target-design v2 binds only runtime.manifest/runtime.entry
and the nine existing core modules for the explicit fresh plain Minimal/compact
`--runtime-binding-qualification` route. Other target rows remain unbound and
ordinary target selection remains disabled. Old schemas/readers/templates are
retained byte-for-byte. Current and historical parent input locators/digests are
recorded separately.

The additive runtime facet preserves the old parent's initial inventory, binds
its immutable bytes, and is itself independently pinned outside target custody.
The existing full fingerprint includes parent and facet. Final packaging refresh
may change only the four already-null Minimal derived JSONs; complete before/after
type/mode/byte inventories and every non-null output/asset binding prove that
boundary. High Assurance outputs and mixed fixture modes refuse this route.
Both external source and facet raw pins are mandatory for the standalone data-only
reader. Raw schemas, actual entry/manifest serializers and all render/dependency
inputs are bound without a source/facet self digest or final candidate SHA.
See [the exact byte, reader and native qualification contract](../docs/RUNTIME_BINDING_QUALIFICATION.md).
