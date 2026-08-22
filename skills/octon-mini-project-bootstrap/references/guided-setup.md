# Guided setup reference

Read this reference when initializing, adopting, or upgrading through a
conversation, TTY, or answer file. For the complete contract, read the bundled
`assets/octon-mini-source/docs/GUIDED_SETUP.md` and the authoritative
`assets/octon-mini-source/shared/source-contracts/setup-questions.json`.

Command examples use `./octon` on Unix/macOS. On Windows, invoke the same
extensionless launcher and arguments as `python -B octon` or `py -3 -B octon`.
This changes only interpreter entry, not command identity, setup semantics, or
authority.

## Required sequence

For a TTY, interactive `octon init`, `octon adopt`, and `octon upgrade` may
orchestrate this whole sequence with an explicit external review directory.
They still use the same catalog, session, planner, summary, digest, and apply
engine. Non-interactive callers retain explicit setup/plan/apply.

1. Read target instructions and run the mode-specific `setup` command without
   output first when only question generation is requested.
2. Stop if mode is ambiguous. Do not choose init, adopt, or upgrade from user
   wording when target evidence contradicts it.
3. Report observations separately. Do not ask for facts that were safely
   observed.
4. Ask the emitted questions in order, normally one to three. Do not preselect
   a choice. State the catalog recommendation separately.
5. Preserve allowed `unknown`, `deferred`, and `not_applicable` states and say
   what each blocks.
6. Bind every answer batch to the exact session digest. Store no secret,
   credential, unnecessary identity, endpoint, or runtime authorization.
7. Write sessions only to explicit paths outside the target. Create an
   immutable successor; never overwrite the prior session.
8. Reinspect with setup-session v2 validity bindings. Classify each prior state
   as preserved, reobserved, needs confirmation, invalidated, or new. Preserve
   an answer after an unrelated edit only when its exact question,
   dependencies, instructions, evidence, authority, and freshness still match;
   otherwise confirm or invalidate it. Never rewrite the predecessor.
9. Summarize recommendations, selections, accepted-authority references,
   unknowns, deferrals, blockers, and the minimum dependency-ordered closure
   sequence, including parallel-safe steps.
10. Pass the reviewed session to the existing `plan --setup-session` command.
    Optionally record the exact plan through `setup --record-plan` into a new
    immutable session successor. Require explicit acceptance of the resulting
    plan digest before apply.

When re-planning, pass `--prior-plan` so the immutable successor exposes the
semantic delta and retained review conclusions. Use the shared concise summary
by default and `--json` for automation.

## Authority checks

- A recommendation is not a user selection.
- A user selection is not accepted authority.
- A current accepted decision may answer a matching future policy question only
  through a project-owned reuse record bound to exact decision bytes,
  applicability, instructions, dependencies, and freshness.
- A reused decision is not the operation confirmation and is never runtime
  authorization or standing external-action permission.
- An `authority:` or `external:` reference is stored separately and must still
  resolve under the project process.
- Adoption and upgrade proposal/review artifacts remain authoritative for their
  dispositions.
- A pause reports immutable review-artifact writes separately from target
  mutation and provides the exact latest session or plan resume argv.
- Setup never authorizes commit, push, PR, review, merge, synchronization,
  cleanup, package install, hook execution, or provider access.

## Autonomous delivery

Initialization, adoption, and upgrade display autonomous delivery as available
but externally locked. The profile question offers locked, `review_first`,
`balanced_autonomous`, `fast_delivery`, and `custom`; it may recommend
`fast_delivery` for most solo developers but selects nothing.

Before activation, research, context, applicability, planning, status,
explanation, and activation preview are read-only and hook-free. If deferred,
record `available_not_activated` and print the exact later activation command.

Setup may gather draft inputs and render deterministic bytes. It may not accept
standing authority as an answer. Display the full contract and digest, then
require an independent exact-digest human confirmation before serializing the
external accepted record. Noninteractive flags are inputs only and cannot
replace confirmation. Upgrade never renews or broadens an existing contract.

## Work completion

Offer exactly disabled, on-demand, or on-demand plus plan-only closure-event
planning. Offer no automatic apply. An enabling selection remains pending
until the session reports every Git portfolio, workflow authority, repository,
provider, check, reviewer, integration, hook, hidden-Git-effect, cleanup, and
assurance prerequisite closed. Apply those changes later through existing
project-owned decision, package, collaboration, hook, and configuration
transactions.

## Reporting

Report structural conformance, adoption, implementation evidence, specialist
approval, release readiness, production readiness, and efficacy/commercial
viability separately. Setup completion proves none of the higher states.
