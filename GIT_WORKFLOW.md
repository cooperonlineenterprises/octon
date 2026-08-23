# Source Repository Git Workflow Assessment

This document applies only to the `octon-mini` source repository. It is
not copied into generated projects and grants no permission. It records
accepted source-repository decision `SRC-DEC-0001`; release-history decision
`SRC-DEC-0002` is recorded in `RELEASE.md`. Neither decision transfers into
generated projects or creates authority for an individual Git, GitHub, or
release operation.

## SRC-DEC-0001 — Source Git and GitHub workflow

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner approval on 2026-08-11 |
| Scope | This source repository only; recorded at acceptance as `project-blueprint` and continued under the `octon-mini` identity by `SRC-DEC-0014` |
| Declared write-capable human maintainers | 1 |
| Independent review capacity | 0 (`not_established`) |
| Base workflow | `solo_hybrid` |
| Concurrent-work modifier | Use `concurrent_work` only while humans or agents are expected to write concurrently; it does not change the human team count |
| Integration method | `merge_commit` |
| Required peer approvals | 0 until eligible independent-review capacity is actually established |
| Hosted execution | Applied on 2026-08-11: expose only `merge_commit` and automatically delete merged head branches |
| Reassessment | By 2026-09-10 and immediately after any access, contributor, reviewer-capacity, or standing-concurrency change |
| Permission effect | None; workflow selection remains non-authorizing and every Git, GitHub, integration, cleanup, and release operation still requires current scope and authority |

Each material task uses a short-lived branch. Schema, template, validator,
migration, CI, workflow, policy, and release changes require a self-PR. A
self-PR records reviewability, validation, and known limitations; it is not
independent review.

The adopted PR integration method is `merge_commit`. Under separate owner
authority on 2026-08-11, hosted configuration was changed to expose only that
method and automatically delete merged head branches. Required peer approvals
remain zero until an eligible independent reviewer is actually available.

At acceptance time the repository was private, and the decision prohibited
making it public or changing plans solely to obtain branch protection.
`SRC-DEC-0016` later recorded the independently owner-directed public MIT-0
boundary. Public visibility does not change contributor access, human team
band, reviewer capacity, workflow adoption, or authority. Stage A of the
ruleset proposal below was applied on 2026-08-18 under separate owner
authorization; Stage B remains unapplied.

## Current read-only observation

This successor observation updates changeable hosted facts without amending or
replacing the accepted text of `SRC-DEC-0001`.

| Field | Current assessment |
|---|---|
| Information role | Explicit repository-owner declaration plus direct local Git and read-only hosted GitHub observation |
| Observed on | 2026-08-18 |
| Reassess by | 2026-09-10, or immediately after an access, contributor, reviewer-capacity, or standing-concurrency change |
| Confidence | Hosted settings and aggregate access are `confirmed` for the observation time; availability, qualifications, intended responsibility, and future state are not established |
| Declared write-capable human maintainers | 1 |
| Observed write-capable human access | 1 |
| Observed read-only human access | 1 |
| Active human contributors in the preceding 90 days | 1 |
| Human team band | `solo` |
| Independent review capacity | 0 (`not_established`) |
| Current implementation concurrency | One primary repository writer; no concurrent repository writer is expected |
| Standing post-task concurrency expectation | `not_assessed`; reassessment required |
| Repository visibility | `public`; visibility is not contributor acceptance, access, review capacity, or authority |
| External contribution mode | `not_assessed`; public readability and forkability do not establish the accepted contribution path |
| Default-branch enforcement | `main` is protected by active repository ruleset `21013176` (`main-stage-a-solo-hybrid`) |
| Adopted base workflow | `solo_hybrid` |
| Current modifier | None; `concurrent_work` is not selected for this task |
| Adoption status | `accepted` |
| Accepted decision reference | `SRC-DEC-0001` |
| Permission grant | `false` |

The 2026-08-17 read-only hosted observation found one write-capable human, one
read-only human, no repository teams, no pending invitations, one human
commit/PR author in the inspected windows, and no qualifying independent
approval. Bots and automation were excluded from human counts; read-only
access was not counted as write capability. These aggregate observations do
not establish availability, qualifications, intended responsibility, or
independence, so independent-review capacity remains zero rather than being
inferred from public visibility or activity.

The repository is public and permits public forks. Only `merge_commit` is
enabled and automatic merged-head deletion remains enabled. Active repository
ruleset `21013176` now requires pull requests and the stable `required` check,
permits zero approvals under `solo_hybrid`, allows only merge commits, blocks
force pushes and `main` deletion, and configures no bypass actor. Public
visibility and forkability grant no write access, reviewer eligibility,
operation authority, or accepted contribution path. Hosted settings remain
dated observations, not authority or proof of future enforcement.

The release stabilization and reconciliation tasks used one primary repository
writer. Because no second writer was authorized or expected, they did not
select `concurrent_work`. Standing post-task concurrency remains unknown and
must be reassessed rather than silently carried forward.

## Adopted workflow: `solo_hybrid`

The confirmed solo human band and accepted preference for reviewable
integration establish `solo_hybrid` as the base workflow for this source
repository. The current bounded task has one primary writer and no expected
concurrent writer, so no `concurrent_work` modifier applies:

1. inspect the working tree, exact revision, applicable instructions, and
   current remote state;
2. use a short-lived task branch for a bounded change;
3. run the full applicable local validation before publication;
4. stage only reviewed paths and create intentional commits;
5. publish the required self-PR for material schema, template, validator,
   migration, CI, workflow, policy, or release changes with explicit current
   authority;
6. observe CI without treating availability as success or enforcement;
7. record self-review limitations and unresolved test gaps;
8. integrate only with `merge_commit` and only after current merge authority
   is supplied; and
9. remove only fully integrated local branches and separately authorized
   remote branches.

A self-PR records reviewability and limitations; it does not become independent
review, merge authority, or proof of branch protection.

## Governed autonomous-delivery boundary

Accepted `SRC-DEC-0019` permits implementation of one optional delivery
capability, and `SRC-DEC-0020` defines eligible standing patch/minor source-
release evidence. Neither decision supplies Git or GitHub authority.

The source-specific v1 `SAC-01` record was independently confirmed but never
activated. The accepted dual-mode amendment requires a v2 successor selecting
exactly one compute mode; standing authority remains inactive until the
repository owner independently confirms that successor's final exact digest.
Before that confirmation, the
authorized implementation program may create local branch
`chore/autonomous-delivery`, local commits, tests, benchmarks, disposable
fixtures, and external draft evidence only. It may not push, create or update a
PR, dispatch a workflow, merge, tag, publish a Release, or clean a remote ref.

After exact activation, ordinary autonomous delivery remains limited to new
`chore/autonomous-*` branches, normal non-force task-branch pushes, self-PRs,
the required check, complete candidate and integrated-main matrices,
`merge_commit`, immutable annotated patch/minor tags, GitHub source Releases,
exact evidence read-back, and proven-safe merged-branch cleanup. Direct pushes
to `main`, force, rebase, squash, published-history amendment, bypass,
repository settings, deployment, package publication, communication,
purchase, and external-project changes remain prohibited.

The completed 3.0.0 release-candidate task used `concurrent_work` with disjoint
file ownership, a shared base revision, conflict detection, and explicit
handback rules. That modifier ended with the task. Future work must reassess
whether humans or agents are expected to write concurrently before selecting
it again. Coordination never grants edit authority.

Project risk remains separate. Sensitive, externally effective, or
high-consequence work may add stronger CI, self-review, or a separately
authorized qualified reviewer without changing the solo topology or
automatically selecting Standard or High Assurance.

## Local CI reconciliation

The source workflow is configured locally to validate:

- every pull request; and
- pushes to `main` only.

Superseded pull-request runs may be cancelled by a concurrency group scoped to
the workflow, event, and PR number. Push-to-`main` and `workflow_dispatch` runs
use their unique run identity and are not cancelled or displaced merely because
they target `main`, preserving post-integration and release evidence. The
workflow retains read-only token permissions, pinned action revisions, and the
full operating-system/Python matrix.

This local configuration does not prove that GitHub accepted or ran it. Before
this change, each update to the only observed open PR triggered duplicate full
matrices through both `push` and `pull_request`. Restricting ordinary push
validation to `main` removes that duplicate event path while retaining PR and
post-merge coverage.

## Applied hosted configuration

Under separate owner authority on 2026-08-11, the hosted settings selected by
`SRC-DEC-0001` were applied:

- only the adopted `merge_commit` integration method is exposed;
- merged head branches are automatically deleted; and
- no peer approval is required while eligible independent-review capacity is
  not established.

No visibility, plan, protection, ruleset, collaborator, or permission change
accompanied the 2026-08-11 merge-settings operation. The later public-license
boundary is recorded separately by `SRC-DEC-0016`; it did not apply a ruleset
or create operation authority. On 2026-08-18, separate current owner authority
applied repository ruleset `21013176` exactly as Stage A below. No collaborator,
visibility, or independent-review-capacity change accompanied that operation.

## Default-branch ruleset — Stage A applied; Stage B unapplied

This section does not amend `SRC-DEC-0001` or create permission. Stage A was
applied on 2026-08-18 under separate current owner authorization; Stage B
remains a non-authorizing proposal. Any later settings mutation, bypass, or
Stage B transition requires separate current authority and its stated trigger.

### Stage A — current `solo_hybrid` topology

- target the default branch (`main` at the observation time);
- require changes through pull requests;
- require the existing stable `required` status check;
- require zero independent approvals while eligible independent-review
  capacity remains unestablished;
- prohibit force pushes and default-branch deletion;
- retain `merge_commit` and do not require linear history; and
- configure no bypass actor. Any future emergency bypass requires a separate
  owner decision naming its exact actor, scope, and audit expectation.

Stage A does not silently add conversation resolution, CODEOWNERS review,
signed commits, a merge queue, or strict up-to-date-branch behavior.

Applied observation: repository ruleset `21013176`, named
`main-stage-a-solo-hybrid`, is active on `refs/heads/main`. API read-back
confirmed every rule above and an empty bypass-actor list.

### Stage B — only after collaboration reassessment

Stage B is inapplicable until a qualified write-capable maintainer actually
exists and an accepted workflow reassessment adopts the corresponding
collaboration change. It would retain Stage A and additionally:

- require one independent approval;
- require approval of the latest reviewable push by someone other than its
  author, or dismiss stale approvals under an explicitly selected equivalent;
- require conversation resolution; and
- require CODEOWNERS review only after real ownership boundaries are
  established.

An agent, bot, self-review, public contributor, or merely configured account
does not satisfy independent review. Stage B proposes no bypass; any later
bypass remains a separate owner choice.

## Release-state boundary

Accepted source release representation is governed by `SRC-DEC-0002` in
`RELEASE.md`. Version `1.0.1` is retained as an untagged, superseded source
milestone. The annotated `v2.0.0` tag was created on 2026-08-11 and targets
exactly `ef8f352ca32a7fbdf1131726263ff545cdd8b08a`; it was not backdated.
Version `3.0.0` was integrated at
`1af3c1f85cd17e2c840857ad720e1a27e874585a`, passed the full hosted `main`
matrix in run `31539907441`, and received an annotated `v3.0.0` tag on
2026-08-11. Octon Mini 4.0.0 was integrated at
`68701faa1898879779e5a7c4c8cedbf8009c6ce0`, passed all twelve jobs in
manually dispatched run `32185219444`, and received annotated tag `v4.0.0` and
its GitHub Release on 2026-08-18. Octon Mini 4.1.0 was integrated through
pull requests #18 and #19 at
`6d1cfb0f13d300b9d4b78bf7078cf07daa7febd6`; automatic smoke run
`32540532990` and manually dispatched source/acceptance run `32540555019`
passed on that exact revision before annotated tag `v4.1.0` and its GitHub
Release were published on 2026-08-22. Failed predecessor runs remain retained.
Separate package publication was `none`. This workflow record does not
authorize moving a published tag or performing a later release operation.

## Unsupported workflow families

This repository's source workflow does not support GitFlow, merge queues,
release trains, stacked-PR dependency trains, fork-first internal contribution,
multi-level CODEOWNERS approval, multiple mandatory approval stages,
dedicated release-manager handoffs, organization-wide ruleset orchestration,
multi-environment promotion pipelines, or enterprise issue/portfolio
governance. A team with more than five write-capable humans receives
`unsupported_team_size`; no enterprise fallback is selected.
