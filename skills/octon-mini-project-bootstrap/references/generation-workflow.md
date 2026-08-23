# Creation, Adoption, Maintenance, Recovery, and Upgrade

## Guided setup

Interactive `scripts/octon.py init|adopt|upgrade` provides the one-command
inspect/question/plan/summary/confirmation/apply path. Require an explicit
external review directory. Preserve its immutable artifacts on collision or
review block and return the typed Continuation Contract. Scripted workflows
continue to use explicit setup, plan, and apply plus `--accept-digest`.

Use `scripts/octon.py init|adopt|upgrade setup` when project facts or policy
selections are not already supplied through legacy flags. The command reads the
target without running detected hooks, refreshing projections, querying a
provider, or changing the target. Write a setup-session artifact only to an
explicit path outside the target, then answer or resume it through the same
catalog used by conversational agents and TTY interaction.

Determine the mode from evidence: an empty target initializes, an established
project without valid Octon Mini provenance adopts, and a snapshot with valid
provenance upgrades. Stop on ambiguity. Ask only eligible unresolved questions
in catalog dependency order. Keep observations, inferences, recommendations,
owner selections, accepted-authority references, unknowns, deferred matters,
and runtime authorization separate. A setup answer is never standing
permission or accepted project authority.

Summarize the reviewed session, then pass it to the existing planner with
`--setup-session`. The resulting init, adopt, or upgrade plan binds the session
digest and current target, instruction, catalog, and Octon Mini inputs. Apply
uses the existing transaction engine and rejects stale bindings. Legacy-style
setup flags on the current `octon` interface map to stable question IDs; this
does not preserve the old `pb` command.

## New project

1. Use `scripts/octon.py init plan` with an explicit profile and layout, or finish
   a guided setup session and pass it with `--setup-session`. Interactive
   `octon init` may propose Minimal without preselecting it and must receive the
   one exact-plan confirmation.
2. Review the plan sections separately: observations, inferences, explicit
   decisions, and authorization gates. Hook detection runs no candidate or
   version command and adopts nothing.
3. Accept the exact digest with `octon init apply`. Apply stages the entire
   scaffold, refresh, structural check, and release-tier tests before writing.
4. If supplied, the first task is built only from explicit semantics. Resume
   with generated `./octon work resume`.
5. Assess hooks, collaboration, SCM, and mandatory domain triggers separately.
   Run the explicit project-check writer only after reviewing declared side
   effects and current authority.

## Established project

Use `scripts/octon.py adopt plan|apply`, optionally with a reviewed guided setup
session. Default semantic inspection is bounded to
200 allowlisted UTF-8 text/config files, 256 KiB each, and 4 MiB total. It
excludes symlinks, binaries, ignored/generated/vendor/dependency/build/coverage
paths, credentials, private keys, `.env*`, and sensitivity-marked paths.
Sensitive or larger inspection requires an exact path-scoped opt-in.

The proposal classifies collisions, likely functional equivalents,
authority-bearing conflicts, safe and review-required additions, missing
project facts, hook candidates, and ambiguity. Review functional equivalence
and authority preservation explicitly. Apply refuses every existing-path
overwrite, stages the complete release tier, preserves project bytes, and
leaves adoption `in_progress`.

## Autonomous-delivery availability

Every generated 4.2 snapshot exposes `octon delivery` in
`available_not_activated`. Research, context, applicability, planning, status,
explanation, and activation preview are read-only and execute no hooks. Exact
inert autonomous-delivery and long-running-work payloads are stored under
`.agent/available-packages/` for network-free activation, but are not installed
or adopted.

Activation first drafts and displays a complete non-authorizing contract. A
human must independently confirm its exact digest; a flag, setup answer,
profile, plan, or record cannot do so. The accepted record and confirmation
stay outside the repository. Activation binds them, current evidence for the
one selected metered-API or included-subscription compute mode, an accepted
project adoption decision, target bytes, and package digests into the existing
transaction system. Upgrade advertises but
never activates, renews, or broadens this state.

## Routine work and maintenance

Generated commands use plan/apply receipts:

```text
./octon work start --help
./octon work close --help
./octon work handoff --help
./octon work resume
./octon maintain registry plan
./octon maintain hooks plan --help
./octon maintain collaboration plan --help
./octon maintain refresh --apply
```

`state/current.json` is fully derived. `state/focus.json` is the small
authoritative source for current operator focus and next action. Refresh is
non-inferential and never edits the authoritative artifact registry. Registry
reconciliation may propose reuse and IDs but requires explicit ownership,
applicability, source direction, representation role, omission, supersession,
and stable-ID choices.

Project checks support selected hooks and changed-scope routing. Current
evidence is bounded; overflow is archived immutably with successor links. Hook
execution and evidence writing remain separate from read-only `check` and from
generated-integrity refresh.

For one bounded unattended worker, first install the optional
`long-running-work` package through the source `maintain package` plan/apply
flow, then separately adopt it through generated `octon work run configure`.
The package remains subordinate to the existing task, transaction,
project-check, work-completion, and Continuation owners. Context, status,
resume, and explain are target-read-only. Checkpoints are marker-backed logical
records, never filesystem snapshots or authority to replay an effect.

If the installed Git portfolio and accepted workflow are applicable, a project
may separately adopt the disabled `work_completion` block. Record exact
repository/provider/check/eligible-reviewer/hook/cleanup assessments without
changing accepted workflow authority. Close a task with its explicit staging,
commit, PR/review, and concurrent-handback inputs; include any in-repository
close-plan path in the exact staging inventory, while the resulting current
close receipt and unchanged postimages are bound automatically; then run
`./octon work finish plan`. The optional
completion event uses the existing `commands.work_completion_plan` hook and
may run only that exact read-only command. Apply accepts the reviewed digest
and a current task-scoped external authorization attestation; resume uses the
Git-common-directory receipt. Never refresh during planning or describe a
receipt as release or production readiness.

The Octon Mini source checkout routes the same `octon work finish` owner through
`source_work_completion.py`. Source mode accepts only an external immutable,
digest-bound Codex task reference, never creates `.agent/tasks`, and treats the
existing committed branch range as the local candidate. It retains monotonic
receipts, blocks merge until the required check and all 24 candidate matrix jobs
pass, and defers remote/local branch cleanup until exact integrated-main
validation evidence passes.

Source `octon delivery effect` is the source-only entry to the existing closed
effect adapter. Candidate dispatch requires the exact task branch/revision;
tag and GitHub source Release actions require exact clean `main`. The adapter
remains separate from work-completion ownership.

Maintain decision questions in the project-owned governance register. Keep
recommendations, owner selections, and accepted `DEC-####` authority separate;
reconcile every decision and trade-off review exactly once and derive the
minimum closure graph before broad implementation. A read-only decision review
does not refresh generated outputs.

## Recovery

Run `./octon doctor` first. Structured diagnostics identify root cause, authority
source, dependent symptoms, safe next action, and whether repair is derived or
project-owned. Doctor is read-only unless the operator explicitly accepts a
derived-only repair digest.

- Pending journal: `./octon transaction recover --pending <path>` restores exact
  preimages only while all paths still match before or planned-after states.
- Applied receipt: `./octon transaction rollback --receipt <path>` refuses any
  independently changed post-apply path.
- Stale plan, evidence, or instruction fingerprint: re-plan; never force.
- Interrupted refresh: diagnose, run explicit derived refresh, then read-only
  check. Project-check evidence is not repaired by integrity refresh.

Every covered refusal reports stable code, mutation outcome, invalidated and
preserved proofs, authority source, repair class, one shell-free next argv,
safe read-only alternatives, and successor support. Human rendering is concise;
use `--json` for the strict contract.

For routine configured `read_only` hooks, the explicit project-check writer may
use `--reuse-proofs`. Exact input/tool/configuration/instruction/environment/
effect/freshness bindings must hit; otherwise rerun. Adoption and release
verification always run completely. Bundle only compatible reversible local
plans with one stage/receipt/rollback through `octon transaction bundle plan`.

## Upgrade

`scripts/octon.py upgrade plan|apply`, optionally with a reviewed guided setup
session, performs a three-way comparison among the
recorded old installed inventory, current project, and candidate snapshot. It
classifies unchanged pristine, exact-pristine update, project-modified,
additive, removed upstream, conflicting, derived, and provenance paths.

Automatic handling is limited to new noncolliding Octon Mini-owned paths,
exact-pristine non-authoritative implementation assets, and derived
regeneration. Instructions, policy, project configuration/hooks, workflow
adoption, dossier sources/registries, records, current facts, stable IDs,
deletions/moves, permissions, and symlinks require proposal-bound review.

The work-completion engine/schema are safe additions only when absent and
noncolliding. The disabled project configuration, workflow package version,
accepted decisions, hook commands, provider and branch settings, cleanup, and
authorization policy require explicit review; upgrade never enables the
completion hook.

For 3.1→4.0, first run the reviewed legacy inventory seed workflow in
`migrate_3_1_0_to_4_0_0.py`. It refuses assessed collaboration and every unknown
static pristine baseline. The seed is never applied directly; the upgrader
rechecks it and produces the only mutation receipt. Run the migration and
release suites, then reassess adoption and readiness independently.

This is the explicit Project Blueprint 3.x→Octon Mini 4.0 cross-brand
migration. Legacy launchers, origin records, and schema identities are inputs
to transform only. A successful upgrade installs `octon` and current Octon Mini
provenance and retains no `pb` alias or runtime compatibility path.

Earlier executable migrations remain closed reference transformations rather
than in-place upgrade tools. See the matching file under `migrations/`.
