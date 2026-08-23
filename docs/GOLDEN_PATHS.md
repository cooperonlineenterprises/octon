# Octon Mini 4.0 Golden Paths

These paths minimize ceremony while preserving project facts, authority,
evidence, stable IDs, no-overwrite, and explicit external-effect gates. All
planning and inspection commands are read-only. Replace example inputs with
current project-owned values; do not copy them as facts.

## Guided setup for any mode

For a TTY workflow, prefer one command and one explicit external review area:

```text
./octon init --target /absolute/project --review-dir /absolute/review
./octon adopt --target /absolute/project --review-dir /absolute/review
./octon upgrade --target /absolute/project --review-dir /absolute/review
```

The command asks only unresolved blockers, shows the shared plan summary and
full digest, requests one `apply` confirmation, then revalidates immediately.
A collision or review gate leaves immutable artifacts in the review directory
and prints the typed shortest continuation. Resume with its exact session,
proposal/review, and optional `--prior-plan` arguments. No review pause applies
or overwrites anything.

When facts are not already supplied through flags, create a read-only setup
session outside the target:

```text
./octon init setup \
  --target /absolute/project \
  --output /absolute/review/setup-session.json

# Resume through the same command after recording a reviewed answer batch.
./octon init setup \
  --target /absolute/project \
  --session /absolute/review/setup-session.json \
  --answers /absolute/review/setup-answers.json \
  --output /absolute/review/setup-session-next.json

./octon init plan \
  --target /absolute/project \
  --setup-session /absolute/review/setup-session-next.json \
  --output /absolute/review/init-plan.json
```

Use `adopt setup` or `upgrade setup` only when read-only evidence establishes
that mode; stop if detection is ambiguous. Conversational agents, TTY
interaction, and legacy flags use the same stable question IDs and validation
rules. Review observations, recommendations, selections, accepted-authority
references, reused accepted decisions, validity classifications, unknowns,
deferrals, blockers, and the exact session digest before planning. Session
creation writes only the explicitly requested external
artifact. Plan and apply remain the existing mode-specific transaction flow.

## New solo project

One plan and one apply reach a valid scaffold and first meaningful task:

```text
./octon init plan \
  --target /absolute/project \
  --project-name "Project" \
  --profile minimal \
  --layout compact \
  --writer-count 1 \
  --collaboration-source authority:<current-source> \
  --collaboration-observed-at <date-time> \
  --collaboration-expires-at <date-time> \
  --solo-integration-preference direct \
  --first-task-title <title> \
  --first-task-scope <scope> \
  --first-task-authority-basis authority:<scope-source> \
  --first-task-owner <owner-role> \
  --first-task-operator <operator-role> \
  --first-task-acceptance <criterion> \
  --first-task-validation <validation> \
  --first-task-next-action <action> \
  --output /absolute/project/.agent/transactions/plans/init.json

./octon init apply \
  --target /absolute/project \
  --plan /absolute/project/.agent/transactions/plans/init.json \
  --accept-digest <reviewed-digest>

cd /absolute/project
./octon work resume
```

The plan separates detector observations, proposals, explicit decisions, and
gates. It configures no hook and adopts no workflow. Minimal is an explicit
choice. Apply stages refresh, check, and the complete release tier before
writing. Structural conformance passes; adoption and readiness remain
unassessed.

## Established solo project

```text
./octon adopt plan \
  --target /absolute/project \
  --project-name "Project" \
  --profile minimal \
  --layout compact \
  --authority-source authority:<adoption-scope> \
  --output /absolute/project/.agent/transactions/proposals/adoption.json
```

If ambiguity exists, disposition every item in a proposal-digest-bound review
file, then create the transaction plan with `--proposal` and `--review`. Apply
the exact transaction digest. Confirm that pre-existing bytes are unchanged,
run `./octon check`, assess hooks and mandatory triggers, execute complete project
checks explicitly, and only then consider a separate adoption decision.

Low-conflict apply installs only absent paths, passes the release tier in
staging, and records adoption `in_progress`; it never marks the project ready.

## Pair or tiny team

Keep profile selection risk-based. Record only aggregate current facts:

```text
./octon maintain collaboration plan \
  --target /absolute/project \
  --writer-count 2 \
  --source authority:<collaboration-source> \
  --observed-at <date-time> \
  --expires-at <date-time> \
  --independent-review-capacity yes \
  --output /absolute/project/.agent/transactions/plans/collaboration.json
```

For three to five writers, use the same flow with the actual count. The result
proposes `pair_pr` or `tiny_pr`; it adopts nothing. Add an accepted decision
reference only when the project owner adopts the workflow. If Git is selected,
install the pinned Git portfolio in a separate content-addressed transaction.

## Concurrent human, agent, or automation work

Add `--concurrent-humans` and `--concurrent-agents` only with current evidence.
This adds the `concurrent_work` modifier; it never changes human team band or
assurance. Use project-owned write-scope coordination when overlapping work is
possible. Resume and hand off through focus rather than editing derived state:

```text
./octon work handoff --task-id TASK-0001 \
  --next-action <action> \
  --summary <bounded-summary> \
  --operator <role> \
  --output .agent/transactions/plans/handoff.json
./octon work resume
```

## Routine task closure

```text
./octon work start --help
./octon transaction apply --plan <plan> --accept-digest <digest>

# Perform authorized work and create real evidence.

./octon work close TASK-0001 \
  --criteria-met \
  --implementation-result <result> \
  --review-evidence EVD-0001 \
  --closure-evidence EVD-0001 \
  --external-effects none \
  --next-action <action> \
  --operator <role> \
  --output .agent/transactions/plans/close.json
./octon transaction apply --plan <plan> --accept-digest <digest>
```

The close command records supplied claims and evidence references; it does not
prove sufficiency. Direct closure is mechanically supported once explicit
criteria/review/evidence/effects inputs are present, avoiding status-only
ceremony.

## Opt-in governed work completion

After the project has adopted and installed one small-team Git workflow,
explicitly enable the existing `work_completion` block in
`.agent/project.json` through the normal plan/apply transaction. Record the
repository identity, remote and default branch, provider assessment, optional
solo self-PR choice, exact required check names (including an explicitly empty
set), eligible provider reviewer identities for pair/tiny workflows,
configured read-only validation hooks, assurance references, and required
local and remote cleanup for branch workflows. Set `git_hooks` to
`require_none`; v1 blocks active Git hooks and active `core.fsmonitor` rather
than treating hidden processes as reviewed actions. Configure
`commands.work_completion_plan` with the exact shell-free argv
`["python", "-B", ".agent/scripts/octon.py", "work", "finish", "plan"]` and
`read_only` side effects. Keep the completion event `disabled`, or set only
`plan_only_on_completion_event`; it references that command hook and may never
invoke apply.

When that event is enabled, applying a `work.close` transaction immediately
prints the read-only completion plan. Closure has already succeeded if this
follow-up plan reports a block; resolve or re-plan explicitly. No publication,
integration, or cleanup begins from the event.

Close the bounded task with its exact completion inputs:

```text
./octon work close TASK-0001 \
  --criteria-met \
  --implementation-result <result> \
  --review-evidence EVD-0001 \
  --closure-evidence EVD-0001 \
  --external-effects none \
  --next-action <action> \
  --operator <role> \
  --finish-path <exact-path> \
  --finish-path .agent/transactions/plans/close.json \
  --finish-commit-message <message> \
  --output .agent/transactions/plans/close.json
./octon transaction apply --plan <close-plan> --accept-digest <close-digest>

./octon work finish plan
```

If the close plan is written inside the repository, list that known plan path
explicitly as shown. The resulting exact current close receipt and its
unchanged dirty postimages are bound into the completion plan automatically;
other transaction artifacts are not hidden or inferred as task-owned.

For concurrent work, the close command also records the exact shared base,
write scope, worktree owner, completed handback, resolved partial-result state,
and coordination evidence. Pair and tiny-team projects wait for one actual
approval by a different eligible developer; no agent or self-review fills the
gap.

Review the printed plan. Obtain current task-scoped external authorization
through the project's real authority channel and record an attestation bound
to the exact digest, repository, branches, operation list, principal or role,
source, validity interval, constraints, and a canonical fingerprint. Then:

```text
./octon work finish apply \
  --accept-digest <reviewed-digest> \
  --authorization-file <current-attestation.json>

# If a later step blocks or the process is interrupted:
./octon work finish resume --receipt-id <WCR-id>
```

Planning changes no file or external system. Apply stops on any stale,
unknown, contradictory, failed, or unsafe material state and preserves prior
effects in the Git-common-directory receipt. Completion proves only the exact
Git/provider sequence recorded there; it does not prove release or production
readiness.

## Optional long-running work

Use this path only after a project has an already authorized task and has
separately assessed, installed, and adopted the optional package.

1. From the source bundle, plan and apply content-addressed installation of
   `long-running-work` with an accepted trust/applicability decision.

2. In the generated project, plan and apply `octon work run configure` with a
   separate accepted project adoption decision. Installation remains inactive
   until this step.
3. Create a strict limits file. Unknown token or cost information is `null`,
   not zero.
4. Start one run bound to the existing `TASK-####`, its current authority basis,
   and exact path narrowing.
5. Compile context and inspect every inclusion, omission, budget, and unresolved
   input. Accept only the exact current context digest.
6. Let the external worker perform one bounded step through the existing
   transaction or `work.finish` boundary.
7. Run or reference current task-bound validation, then record progress. The
   package commits a marker-backed checkpoint or stops on a limit, conflict,
   missing authority, failure, or outcome-unknown result.
8. Use `status`, `resume`, or `explain` read-only. If an interrupted projection
   differs from the newest marker, recover only the exact marker digest.
9. Complete the run only after the existing task is completed with current
   acceptance and closure evidence.

Never replay an external operation during resume. Disable the package before
removal. Removal refuses active or undispositioned retained run history.
Structural success, a run completion, or a checkpoint establishes no project
adoption, external authority, release, or readiness.

## Governed autonomous delivery

1. Inspect the locked default without changing the project:

   ```text
   ./octon delivery status
   ./octon delivery assess
   ./octon delivery activation-preview --profile fast_delivery
   ```

2. Generate a deterministic draft to an explicit external review area. The
   draft is not authority:

   ```text
   ./octon delivery authorization draft \
     --profile fast_delivery \
     --compute-mode metered_api \
     --repository-root /absolute/project \
     --repository-identity owner/repository \
     --authority-dir /absolute/operator-control \
     --evidence-root /absolute/evidence \
     --valid-from <timestamp> \
     --valid-until <timestamp> \
     --output /absolute/review/SAC-01.draft.json
   ```

3. Independently confirm the displayed exact digest. A flag is not
   confirmation. Serialize the accepted external record only from matching
   confirmation evidence.

   For a successor, use a new `SAC-##` ID and bind the exact predecessor with
   `--supersedes-authorization-record`. After the confirmed successor record
   exists, `octon delivery authorization supersede` can serialize the required
   predecessor revocation only at the exact control path bound by that
   successor.

   For an existing subscription, instead select
   `--compute-mode included_subscription` and supply a safe external or
   authority `--subscription-plan-ref`. The resulting contract permits only
   included allowance and requires a fresh readable host quota report.

4. Plan activation from the accepted record, confirmation, current evidence
   for the selected compute mode, and accepted project adoption decision; then
   apply only the exact digest. `--compute-enforcement-artifact` accepts the
   mode-specific evidence; the legacy `--cost-enforcement-artifact` spelling is
   retained only for confirmed v1 metered records.

5. Use existing long-running work, transactions, project checks, and work
   completion for ordinary delivery. Use the closed adapter only for exact
   workflow dispatch, annotated tag, tag push, GitHub source Release, and
   read-back.

6. If an attempted external effect cannot be read back conclusively, stop. Do
   not retry. Reconcile or fix forward from the monotonic receipt.

For Octon Mini source delivery, first create an external immutable Codex task
reference and then run:

```text
./octon work finish plan \
  --task-reference /absolute/evidence/codex-task.json \
  --authorization-record /absolute/control/SAC-02.json \
  --output /absolute/evidence/source-work-plan.json
```

The plan binds the already committed branch range. Apply uses a separately
projected, fresh work-completion authorization. After the stable required check
passes, dispatch and read back the complete candidate matrix. Record the exact
24/24 candidate source/acceptance job evidence with `attest-candidate-matrix`;
only then may resume reach merge. After merge and local `main` synchronization,
the receipt pauses again before cleanup. Record exact integrated-main smoke and
full-matrix evidence with `attest-post-merge`, then resume under fresh
authorization. No source `.agent/tasks` store is created.

## Hooks and evidence

Run the detector read-only, review candidate argv and side effects, then
install configuration through `./octon maintain hooks plan|apply`.
`./octon check`
never executes hooks. Run only selected authorized hooks:

```text
python -B .agent/scripts/run_project_checks.py \
  --write-evidence \
  --hook project_test
```

Use changed-scope routing for routine work and `--verify-adoption` for the full
boundary. Writing or external hooks require their explicit acknowledgment.

For exact unchanged routine `read_only` hooks, the explicit writer may reuse a
content-addressed proof:

```text
python -B .agent/scripts/run_project_checks.py \
  --write-evidence --changed-scope --reuse-proofs
```

Input, tool/version, command/configuration, instruction, environment, effect,
or freshness changes rerun only the affected selected check. Never pass proof
reuse to `--verify-adoption`; that complete gate rejects it.

## Safe local bundles

```text
./octon transaction bundle plan \
  --member registry=.agent/transactions/plans/registry.json \
  --member hooks=.agent/transactions/plans/hooks.json \
  --authority-source authority:<current-common-local-scope> \
  --output .agent/transactions/plans/bundle.json
```

Bundle only coherent reversible local plans with the same authority,
confirmation, instructions, freshness, and rollback boundary. The planner
rejects overlapping paths, nested bundles, incompatible owners or freshness,
and every external or monotonic effect. Apply the one bundle digest through
ordinary `octon transaction apply`; its receipt contains every path preimage
and postimage and rolls back atomically while unchanged.

## Recovery

```text
./octon doctor
./octon doctor --json
./octon transaction recover --pending <pending-journal>
./octon transaction rollback --receipt <applied-receipt>
```

Derived-only diagnosis may propose an exact repair digest. Invalid
configuration, stale evidence, ambiguous authority, or changed post-apply
paths require a project decision or re-plan; they are never force-repaired. A
surviving pending journal with an exact terminal receipt is finalized without
undoing the receipted result. Retry the same rollback receipt when its status
is `rollback_in_progress`.

Every covered refusal states `Nothing changed` or lists its bounded mutation.
When setup wrote immutable review artifacts outside the target, the finding
says the target was unchanged while naming those preserved artifacts instead
of claiming that no filesystem write occurred. Each finding names invalidated
and preserved proofs and provides one shell-free `argv`.
There is no global force continuation.

## Upgrade

For a native Octon Mini inventory-v2 project, run `octon upgrade plan`
directly. Project Blueprint 3.x→Octon Mini 4.0 is an explicit cross-brand
migration with no `pb` compatibility. For 3.1.0, follow
`migrations/3.1.0-to-4.0.0.md`: inspect, supply an exact reviewed old baseline,
create a non-applied seed, classify the three-way proposal, disposition every
review path, then accept the exact transaction digest.

The interactive upgrade command accepts that exact seed as a migration input,
pauses on the same three-way proposal, and resumes only after a bound review.
It does not execute or restore the legacy command.

After apply, distinguish the outcomes:

- structural conformance: checked automatically;
- harness adoption: unchanged unless project owners separately update it;
- target-project readiness: not inferred and requires current project and
  specialist evidence.
