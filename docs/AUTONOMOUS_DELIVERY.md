# Governed Autonomous Delivery

## Status and boundary

`SRC-DEC-0019` accepts one optional autonomous-delivery workflow capability.
`SRC-DEC-0020` separately accepts the standing source-release evidence policy.
Neither decision creates runtime authority. Every project starts
`available_not_activated` and externally locked.

The capability coordinates one already human-prioritized and architecturally
authorized task. It does not select priorities, accept architecture, establish
release-risk policy, expand product boundaries, host a model, store a
credential, deploy, publish a package, control an external project, or schedule
multiple write-capable workers.

## Independent delivery-profile axis

Delivery profile is independent from assurance, collaboration, concurrency,
and physical layout.

| Profile | Preset behavior |
|---|---|
| `review_first` | Research, implement, test, push, and prepare a PR; human confirmation remains required for merge and release. |
| `balanced_autonomous` | Complete PRs and qualifying patch releases; minor release requires human confirmation. |
| `fast_delivery` | Complete qualifying patch and minor releases under generous bounded limits. |
| `custom` | Use the exact human-selected actions, release types, limits, budgets, and expiry. |

`fast_delivery` is the recommendation for most solo developers. It is never
preselected. A preset grants nothing; the exact independently confirmed
standing contract is authoritative. A more-permissive successor always needs
human confirmation, and no profile can weaken a hard safety rule.

## Dormant surface

Every snapshot contains a small `octon delivery` dispatcher and exact inert
offline payloads for autonomous delivery and its long-running-work dependency.
No network installation is required.

Before activation, these commands are read-only:

- `octon delivery research`;
- `octon delivery context`;
- `octon delivery assess`;
- `octon delivery plan`;
- `octon delivery status`;
- `octon delivery explain`; and
- `octon delivery activation-preview`.

They execute no project hook, write no receipt implying work, mutate no
repository or external state, and create no authority. Research is a bounded
request projection for an optional external read-only worker; Octon Mini core
does not require a model or network.

## Authority creation and activation

1. Gather repository, branch, profile, action, release, limit, evidence,
   expiration, revocation, emergency-stop, and exactly one compute mode.
2. Produce byte-identical draft bytes for identical inputs.
3. Display every field and the canonical SHA-256 digest.
4. Obtain independent human confirmation of that exact digest.
5. Serialize an immutable external record only after confirmation.
6. Store the record and confirmation outside the repository in an
   operator-controlled location.
7. Bind a read-only activation plan to the exact record, confirmation, package
   bytes, accepted project adoption decision, current mode-matching compute
   evidence, and project fingerprint.
8. Apply only that digest through the existing transaction system.

The draft, profile, setup answer, plan, projection, receipt, and stored record
do not create authority. The independent human confirmation is the authority
source; the record is evidence of that grant.

An accepted record is immutable. A changed compute mode or other binding uses a
new stable `SAC-##` ID and names the exact predecessor record and contract
digests. Activation of the successor additionally requires an
operator-controlled revocation record for that predecessor naming the new
authorization ID. The worker cannot write either control record.
After exact successor confirmation, `octon delivery authorization supersede`
can serialize that revocation only at the predecessor path already bound in the
successor contract; it derives the authority source and successor identity from
the confirmed records rather than accepting a permissive flag.

Octon Mini validates bytes, paths, digests, timing, and declared authority
source; it cannot cryptographically prove that a human authored a file. The
operator-controlled filesystem permissions, worker write boundary, provider
credential scope, and protected remote controls remain the real enforcement
boundaries. If those controls do not prevent the worker from altering the
confirmation, authorization, revocation, or stop records, activation must not
proceed.

Noninteractive activation requires the accepted record and a separate exact-
digest confirmation artifact. `--yes`, `--accept`, `--force`, or another flag
cannot create confirmation.

## Ownership

| Concern | Owner |
|---|---|
| Goal, scope, priority, authority basis, acceptance | Existing task and human priority authority |
| Architecture | Existing accepted decision system |
| Release evidence and risk | `SRC-DEC-0020` or project successor |
| Run coordinate and continuation limits | Existing long-running-work mechanism |
| Reversible local mutation | Existing transactions |
| Project validation | Existing project-check evidence |
| Commit, push, PR, checks, merge, cleanup | Existing work completion |
| Refusal and successor | Existing Continuation Contract |
| Release-specific effects | Closed autonomous-delivery adapter |
| Standing permission | Independently confirmed external record |
| Delivery chronology | Package references to existing receipts and evidence |

There is no second task lifecycle, decision store, evidence store, current-state
file, run loop, or generic event platform.

## Fast-delivery limits

| Limit | Value |
|---|---:|
| Authorization lifetime | Up to 90 days, constrained by earlier authority expiry |
| Delivery-run duration | 14 days |
| Work iterations | 500 |
| Correction cycles | 10 |
| Commits per run | 50 |
| PRs per run | 12 |
| Hosted workflow dispatches per run | 40 |
| Safe read-only retries | 5 |
| Retries after proven no effect | 2 |
| Retries after unknown outcome | 0 |
| Covered patch/minor releases | 12 |
| Concurrent write-capable runs | 1 |
| Metered API compute | Host-enforced USD 250 per run and USD 1,000 per authorization period |
| Included-subscription compute | Current readable provider-enforced included allowance only; no paid credits, API/pay-as-you-go billing, add-ons, or upgrades |
| Purchases or direct external spending | USD 0 |

Warnings occur at 70%, 85%, and 95%; execution stops at 100%. Each standing
contract selects exactly one compute mode. Unknown metered cost is not zero.
Unreadable, exhausted, or changed subscription usage blocks. A mode change
requires a newly confirmed successor and never reinterprets an accepted record.

The worker cannot purchase a service, subscription, infrastructure, paid API,
domain, license, marketplace product, or other external good or service.

## Closed source-release adapter

The adapter supports only:

- exact hosted-workflow dispatch and observation;
- annotated local tag creation;
- exact tag push;
- GitHub source Release creation and read-back; and
- receipt-backed read-only reconciliation.

Work completion retains commit, task-branch push, PR, hosted-check, merge, and
cleanup ownership. A plan-bound work-completion authorization may be derived
only after the accepted standing record, confirmation, revocation, emergency
stop, selected compute enforcement and usage, repository, branch, task,
operation list, and limits are revalidated.

## Recovery

Repository-local transactions may be exactly reversible while their recorded
preimage/postimage rules remain satisfied. Commits and unpublished task
branches are recoverable.

Pushes, merges, workflow dispatches, published tags, and GitHub Releases are
monotonic external effects. Each effect follows:

1. revalidate current standing coverage;
2. inspect before acting;
3. persist a requested and attempted marker;
4. perform at most the exact closed operation;
5. read back the result; and
6. persist an immutable successor receipt.

An attempted operation with inconclusive read-back becomes `outcome_unknown`.
It stops with zero automatic retries. Resume observes without replaying.
Public effects are never described as atomically rollbackable; reconciliation
and fix-forward are the recovery model.

## Human-only gates

Human input remains mandatory for product-priority selection or material
change; architecture acceptance, amendment, or supersession; release-evidence
or risk-policy change; product-boundary or standing-authority expansion;
conflicting accepted authority; and any required human, specialist, security,
legal, or external-project decision.

Expiration, revocation, emergency stop, unknown metered cost, unreadable,
exhausted, or changed subscription allowance, unavailable required
authentication, failed safety gates, unavailable mandatory evidence,
critical/high findings, unknown external outcomes, evidence-preservation
failure, tag conflict, user-owned change conflict, and any excluded action also
stop delivery.

## Claim boundary

Implementation and automated evidence can establish bounded source behavior.
They do not establish independent human usability, field maturity, project
adoption, project readiness, production readiness, efficacy, or commercial
viability. Missing independent evidence remains explicit under
`SRC-DEC-0020`.
