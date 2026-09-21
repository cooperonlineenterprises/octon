# Octon Mini Source Architecture Decisions

This file records accepted source decisions for the current `octon-mini`
repository content. Historical decisions retain the Project Blueprint terms
under which they were accepted. This file is not copied into generated
projects, does not grant permission, and does not accept a pattern on behalf
of any adopting project.

## SRC-DEC-0003 — Source-only architectural Pattern Catalog

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner implementation authorization on 2026-08-11 |
| Scope | Project Blueprint source governance only |
| Placement | `patterns/` outside the universal kernel and all generated profile inventories |
| Decision | Maintain strict, versioned pattern records with governed lifecycle and promotion rules |
| Adoption effect | None; catalog presence and status never adopt a pattern into a project |
| Permission effect | None; every record requires `permission_grant: false` |
| Compatibility | Additive in Blueprint 3.1.0; harness kernel remains 3.0.0 |

Promotion is never automatic. `recommended` requires independent project
evidence and explicit architecture review. `stable` additionally requires an
explicit compatibility and migration-support commitment. One successful
project, proof, test, or usage count is insufficient.

The source/project boundary is runtime-enforced by the versioned generation
policy. Source paths default to `source_only`; version 2 explicitly enumerates
reviewed paths. Runtime generation uses only the requested profile's allowlist,
ignores and reports unreviewed additions, and blocks only capabilities whose
reviewed dependency or hard invariant fails. Repository validation remains
strict across every profile. Forbidden outputs, source confinement, and the
exact final staged tree remain fail-closed. This proportional degradation does
not authorize a new input or manual adoption.

## SRC-DEC-0004 — Semantic, binding, Context Pack, and claim envelopes

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner implementation authorization on 2026-08-11 |
| Scope | Canonical dossier, harness, generation, optional Context Pack, and evidence-claim contracts |
| Placement | Canonical documentation, source semantic crosswalk, Generation Contract, and High-Assurance-only optional schema |
| Decision | Clarify information roles and input binding; validate adopted cross-boundary Context Packs; require bounded non-proof claims |
| Exclusion | No universal state enum and no new universal runtime mechanism |
| Permission effect | None; context possession and evidence cannot grant action authority |
| Compatibility | Additive; existing aggregate statuses and existing Context Pack prose remain unchanged until explicit reconciliation |

The semantic crosswalk explains meaning across aggregates but does not replace
their record-specific statuses. The optional Context Pack schema is available
only in newly generated High-Assurance snapshots; no pack record is generated
or adopted.

## SRC-DEC-0005 — Optional Architecture Proof family

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner implementation authorization on 2026-08-11 |
| Scope | Source-only optional proof schema and templates |
| Placement | `patterns/architecture-proof/`; never a generated profile default |
| Decision | Provide one proof family for spikes, reference slices, provider qualification, adversarial fixture packs, and readiness evidence |
| Claim boundary | Completion proves only the exact hypothesis, subject, environment, and evidence recorded |
| Permission effect | None |
| Compatibility | Additive source tooling; no generated-project migration |

An Architecture Proof may conclude `supported`, `unsupported`, or
`inconclusive`. A template, happy path, or passing structural check never
establishes production readiness.

## SRC-DEC-0006 — Reviewed lifecycle and governed-change patterns

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner implementation authorization on 2026-08-11 |
| Scope | Pattern Catalog admission only |
| Placement | `PAT-0001` and `PAT-0002` records at no higher than `reviewed` |
| Decision | Admit `lifecycle-disposition` and modular `governed-change-and-effects` for future project-specific evaluation |
| Implementation effect | None; no runtime, schema, template, generated path, extension, or profile default is authorized |
| Promotion gate | A concrete adopter must supply the applicable failure model and required proof before `experimental` or higher |
| Permission effect | None |

The governed-change record contains only the module names `impact`, `action`,
`mutation_effect`, and `recovery_incident`. It deliberately supplies no
universal verbs, action enum, external-effect infrastructure, or recovery
implementation.

## SRC-DEC-0007 — Authoritative profile manifest and explicit profile selection

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner velocity-roadmap implementation authorization on 2026-08-12 |
| Scope | Blueprint source profiles, generated inventories, package declarations, acceptance coverage, and their independent-snapshot projections |
| Placement | `shared/source-contracts/profile-manifest.json` with a versioned source schema |
| Decision | Maintain one authoritative profile manifest and derive generator choices, project-local and derived paths, generated validator inventories, package declarations, and acceptance reporting from it |
| Selection effect | Non-interactive generation and adoption planning require an explicit profile; a future interactive flow may propose Minimal but cannot adopt it without confirmation |
| Permission effect | None; manifest data and profile recommendations grant no project authority |
| Compatibility | Breaking source-tooling transition in the 4.0.0 velocity program; existing independent snapshots remain unchanged until an explicit migration |

Generated projects receive only the selected, rendered projection needed for
their independent validator. They do not depend on the Blueprint source
manifest at runtime. The manifest remains allowlist-driven, source paths remain
`source_only` by default, and its documentation and acceptance projections are
validated rather than independently maintained.

## SRC-DEC-0008 — Staged repository-local transactions and derived operating state

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner velocity-roadmap implementation authorization on 2026-08-12 |
| Scope | Generated repository-local lifecycle, maintenance, recovery, and evidence-index mutations |
| Decision | Use one closed plan/apply contract with canonical digests, instruction and path preimages, staging, declared derived writes, write-ahead recovery, exact receipts, and postimage-bound rollback |
| State effect | `state/current.json` becomes derived; non-derivable operator focus remains an explicit source in `state/focus.json` |
| Permission effect | None; a transaction executes only already-authorized repository-local work and cannot create authority, facts, review, evidence, or external-effect permission |
| Compatibility | Harness-kernel v4 change requiring explicit migration; existing independent snapshots remain unchanged |

There is no force bypass. Planning, check, doctor, resume, discovery, and
diagnostic modes are read-only. Generated-integrity refresh and project-check
evidence remain distinct explicit writers. An interrupted apply restores exact
preimages only while each affected path still matches its recorded preimage or
planned postimage.

## SRC-DEC-0009 — Progressive collaboration and trigger-installed capabilities

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner velocity-roadmap implementation authorization on 2026-08-12 |
| Scope | Collaboration assessment, concurrent-work modifier, SCM selection, domain packages, and optional schemas |
| Decision | Derive solo, pair, or tiny only from current aggregate evidence used by the result; model concurrency separately; ship only trigger metadata in the kernel and install capability payloads through pinned, decision-bound transactions |
| Profile effect | None; collaboration and concurrency never select Minimal, Standard, or High Assurance |
| Permission effect | None; detection and derived workflow selection are proposals unless an accepted project decision adopts them |
| Compatibility | Collaboration profile v2 and package registry v1 require explicit migration or reviewed legacy seeding |

Missing trigger evidence is `not_assessed`, not `not_applicable`. Package
content, accepted trust decision, applicability when claimed, installed digest,
validation receipt, owner, and lifecycle state are independently bound. The
full Git portfolio and domain mechanisms are absent from every default profile.

## SRC-DEC-0010 — Bounded semantic adoption and three-way live upgrades

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner velocity-roadmap implementation authorization on 2026-08-12 |
| Scope | Established-repository adoption and upgrades of generated independent snapshots |
| Decision | Inspect established projects through bounded allowlisted recipes; preserve all existing bytes; upgrade by comparing recorded old baseline, current project state, and candidate snapshot |
| Automatic boundary | Safe additions, exact-pristine non-authoritative implementation assets, and declared derived regeneration only |
| Review boundary | Instructions, policy, configuration, workflows, dossier sources and registries, records, stable IDs, deletions, moves, symlinks, permissions, and modified content |
| Permission effect | None; structural installation or upgrade never marks adoption or readiness |

Plans retain hashes and matched vocabulary rather than inspected content.
Every ambiguity is proposal-bound, previewable, and explicitly dispositioned.
Legacy 3.1 projects lacking an installed-baseline inventory require reviewed
seed data; no baseline is reconstructed by assertion or guess.

## SRC-DEC-0011 — Compact representation and tiered validation

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner velocity-roadmap implementation authorization on 2026-08-12 |
| Scope | New-project physical dossier layout and generated validation cost |
| Decision | Default new snapshots to the compact representation map while retaining separated layout; expose fast, integration, and release tiers with bounded mutation baselines and explicit scale benchmarks |
| Semantic effect | None; combining physical representations does not combine authority ownership, lifecycle, stable artifact IDs, or substantive review obligations |
| Profile effect | None; layout remains independent of assurance and collaboration |
| Compatibility | Layout is recorded in origin inventory v2; moves between layouts require explicit registry-aware migration |

Primitive scaffolding runs structural checks plus the fast bounded mutation
tier before atomic placement. Guided init, adoption, upgrade, release
validation, and other consequential boundaries stage the complete applicable
release tier. Full-tree tests remain where host metadata, ignore behavior,
symlinks, whole-tree fingerprinting, or cross-file integration is material.

## SRC-DEC-0012 — Decision governance within the existing decision concern

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner implementation authorization on 2026-08-13 |
| Scope | Domain-neutral decision inventory, option review, compatibility, handoff reconciliation, maturity assessment, read-only review, and closure sequencing |
| Placement | Existing `DEC-0001` concern; project-owned `.agent/decisions/governance-register.json`; accepted authority remains in `DEC-####` records |
| Decision | Add stable decision-question tracking, gate-first evidence review, exact inventory reconciliation, subordinate handoff checks, scoped requirement/gate maturity, and read-only assurance without creating parallel accepted authority |
| Exclusion | No universal readiness lifecycle, no automatic maturity promotion, no score-based override of a failed gate, and no generated owner selection or accepted decision |
| Permission effect | None; recommendations, selections, reviews, closure sets, schemas, and validators grant no action authority |
| Compatibility | Additive within unreleased Blueprint 4.0; existing independent snapshots change only through explicit upgrade review |

`DREG-####` identifies a tracked question and review; it is never silently
reused as a durable `DEC-####` identity. `accepted — authority linked` requires
a resolving accepted `DEC-####`. Generated Markdown is a review projection,
and structural conformance remains distinct from implementation and readiness.

## SRC-DEC-0013 — Governed small-team work completion

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner implementation authorization on 2026-08-13 |
| Scope | The existing small-team Git portfolio, generated `pb work finish` interface, transaction receipts, project completion hook, and optional hosted-provider adapters |
| Decision | Add one provider-neutral, digest-bound, resumable completion orchestrator that applies the already-adopted `solo_direct`, `solo_hybrid`, `pair_pr`, or `tiny_pr` policy and the existing `concurrent_work` modifier |
| External-effect boundary | A read-only plan may identify external operations; apply or resume may execute them only from an exact current task-scoped authorization attestation bound to the reviewed plan, repository, refs, and operation set |
| Recovery boundary | Local and hosted effects are recorded as monotonic, inspect-before-act progress. They are not represented as atomically rollbackable; retry must recognize exact already-completed effects and stop on ambiguous state |
| Trigger boundary | Project completion hooks are disabled by default and may automatically invoke only read-only planning. They never invoke apply, create standing authority, or silently adopt provider settings |
| Authority effect | None in generated projects; workflow adoption, configuration, a plan, a receipt, and this source decision grant no target-project operation permission |
| Compatibility | Additive within unreleased Blueprint 4.0; existing independent snapshots and installed Git portfolios change only through explicit upgrade or content-addressed package update |

This is a narrow exception to the previously deferred external-effect
infrastructure. It authorizes only small-team source-control completion through
the closed Git and hosted-change operation catalogs. It does not authorize a
universal action system, deployment or release orchestration, communications,
production operations, financial or legal effects, provider configuration, or
enterprise workflow families.

## SRC-DEC-0014 — Octon Mini clean-break product identity

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner direction on 2026-08-16 |
| Scope | Current product, repository content, bootstrap skill, command surface, protocol family, provenance, migrations, and newly generated snapshots |
| Decision | Rebrand the breaking 4.0.0 successor as Octon Mini, keep the bootstrap capability explicit as Octon Mini Project Bootstrap, and make `octon` the sole current executable |
| Product boundary | Octon Mini is the lightweight, project-local version of Octon; OctonOS is the full-scale agent operating system and governed control plane |
| Compatibility boundary | Project Blueprint 3.x upgrades only through an explicit reviewed cross-brand migration; no `pb` alias, wrapper, parser branch, warning shim, symlink, or runtime compatibility mode is retained |
| Namespace boundary | New product protocols, provenance, schemas, skill metadata, packages, and generated paths use capability-qualified `octon-mini` identities; stable generic harness, dossier, task, decision, evidence, and receipt IDs are preserved |
| Historical boundary | Historical releases, tags, decisions, closed migrations, and stable `PBV-##` workstream IDs remain truthful and are not rewritten or reallocated |
| Version continuity | Octon Mini 4.0.0 is unreleased and is the breaking successor to Project Blueprint 3.x; the version does not reset to 1.0.0 |
| External effect | None; this decision does not authorize a commit, push, pull request, tag, release, package publication, remote rename, or repository rename |
| `permission_grant` | `false` |

The source-decision IDs remain stable through the product rename. Current
Octon Mini artifacts may therefore cite `octon-mini:SRC-DEC-0013` while the
accepted text of `SRC-DEC-0013` remains a truthful historical record of the
Project Blueprint source decision. The `PBV-##` prefix similarly records the
historical Project Blueprint Velocity workstream; it is not a current product
namespace and is not reassigned.

## SRC-DEC-0015 — Post-rebrand audit remediation controls

| Field | Accepted decision |
|---|---|
| Status | `accepted` for the technical remediation scope; licensing disposition remains blocked pending explicit owner input |
| Authority | Explicit repository-owner remediation direction on 2026-08-17, excluding the unset `LICENSE_DECISION` |
| Scope | Generated package-contract consistency, observed repository-state documentation, benchmark methodology and evidence, and cross-platform `octon` command entry |
| Package contract | The authoritative profile manifest is the sole source for both a capability package version and content digest; generated and installed projections must validate the exact pair even before installation |
| Benchmark contract | Replace the three-sample benchmark report with a new capability-qualified v2 protocol that preserves cold-start and warm samples, records content-free host context, uses a documented nearest-rank percentile, and retains the existing thresholds |
| Command-entry contract | Keep `octon` as the sole command and use one extensionless Python launcher model: direct execution on Unix/macOS and explicit Python interpreter invocation on Windows |
| Observed-state boundary | Current documentation may record the completed repository and local-directory rename and current public visibility without describing those external effects as authorized by this decision or by `SRC-DEC-0014` |
| Licensing boundary | No SPDX identifier, exact license, or return-private direction was supplied; no license is selected or added, public visibility is not a license grant, and no visibility operation is authorized |
| External-effect boundary | None; this decision does not authorize a commit, push, pull request, merge, tag, release, package publication, workflow dispatch, repository setting change, or visibility change |
| `permission_grant` | `false` |

The missing license choice is an explicit unresolved owner input, not a default
policy selection. A later license or visibility policy receives a new stable
source-decision ID rather than rewriting this accepted technical-remediation
record. Repository content and successful validation still do not authorize an
external effect or establish target-project adoption or readiness.

## SRC-DEC-0016 — Public MIT-0 source licensing

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner direction on 2026-08-17: `LICENSE_DECISION: KEEP_PUBLIC_WITH_LICENSE — MIT-0`, followed by confirmation of the exact copyright holder |
| Scope | Current Octon Mini source repository, package metadata, installed source bundle, license documentation, and generated-project license boundary |
| License | SPDX `MIT-0`, using the canonical MIT No Attribution text and `Copyright 2026 Cooper Online Enterprises` |
| Public boundary | Keep `cooperonlineenterprises/octon-mini` public; public visibility, licensed reuse, and an Octon Mini release remain separate facts |
| Installed-bundle boundary | A distributed Octon Mini Project Bootstrap source bundle includes the exact repository `LICENSE` file and matching package metadata |
| Generated-project boundary | Automatic project generation does not copy the source `LICENSE` or select a target project's overall license; that remains a separate project-owned decision |
| Runtime authority | The license grants copyright permissions only under its terms; it grants no agent, repository-operation, credential, deployment, publication, release, or external-effect authority |
| External-effect boundary | This repository-content decision does not authorize a commit, push, pull request, merge, tag, GitHub Release, package publication, workflow dispatch, or repository-setting change |
| `permission_grant` | `false` |

This decision resolves the licensing input left open by `SRC-DEC-0015` without
rewriting that earlier record. The repository may be distributed under MIT-0,
but Octon Mini 4.0.0 remains unreleased until its separate release process is
authorized and completed.

## SRC-DEC-0017 — Fail-closed continuation and proof reuse

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner implementation direction on 2026-08-17 for branch `chore/fail-closed-continuation` |
| Scope | Bootstrap setup, repository-local transactions, diagnostics, plan review, project-check evidence, and routine local operation bundling |
| Decision | Keep every mutation fail-closed while making recovery continuation-oriented through typed refusals, dependency-scoped validity, immutable successor artifacts, guided one-command orchestration, bounded durable-decision reuse, human plan summaries, conservative content-addressed proof reuse, and compatible repository-local bundles |
| Continuation boundary | A refusal preserves still-valid inputs, reports exact invalidation and mutation state, and supplies one shell-free next action; it grants no permission and retains a safe unclassified fallback |
| Invalidation boundary | Reobserve volatile facts and invalidate only declared dependencies; governing instructions, relevant evidence, accepted authority, question definitions, exact path preimages, and freshness remain hard fail-closed bindings |
| Decision-reuse boundary | Reuse requires a project-owned applicability record bound to an exact accepted, unsuperseded decision and current instructions/fingerprints; it never supplies operation confirmation, runtime authorization, external-action permission, or readiness evidence |
| Proof-reuse boundary | Only the explicit project-check evidence writer may persist or reuse exact input/tool/configuration/instruction/environment/freshness-bound passing proofs; `check` remains read-only and consequential adoption/release gates run completely |
| Bundle boundary | Only compatible, reversible, repository-local members sharing one project, instruction set, freshness boundary, authority class, stage, receipt, and rollback may be combined; external, overlapping, contradictory, differently authorized, or monotonic effects are rejected |
| Compatibility | Additive successor contracts for new snapshots; setup-session v1, transaction v2, diagnostic v1, and project-check evidence v2 remain historical inputs and require explicit successor generation or reviewed upgrade |
| Permission effect | None; plans, summaries, continuation findings, confirmations, reused decisions, cached proofs, bundles, and receipts cannot create authority |
| External-effect boundary | None; this decision authorizes no push, PR, merge, release, publication, provider call, deployment, communication, or other external effect |
| `permission_grant` | `false` |

This decision closes the previously deferred bounded-invalidation trigger
without accepting a universal action, authority, readiness, trust, or state
machine. Validity classes describe reuse conditions for setup inputs and
proofs only. Aggregate-specific lifecycles and every existing deny remain in
force. Existing independent snapshots receive the implementation only through
new generation or an explicit reviewed upgrade.

## Explicitly deferred by these decisions

The following remain outside the accepted implementation:

- resource accounting and quantitative reservations;
- generic policy or rights locks;
- corpus-use machinery;
- universal action, lifecycle, readiness, trust, or state enums; and
- general-purpose external-effect infrastructure outside the narrow
  `SRC-DEC-0013` small-team work-completion exception.

Their exact future triggers remain recorded in
`ARCHITECTURAL_PATTERN_INTEGRATION_REVIEW.md`.

Bounded invalidation was deferred by `SRC-DEC-0003` through `SRC-DEC-0016` and
is accepted only within the narrow continuation scope of `SRC-DEC-0017`.

## SRC-DEC-0018 — Optional mature long-running work capability

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit current operator acceptance on 2026-08-20 after review of the exact decision, scope, maintenance commitment, evidence, limitations, and non-authorizing boundaries; this supersedes the pending direction recorded on 2026-08-19 |
| Scope | One provider-neutral, trigger-installed, domain-neutral `workflow_capability` package for a single bounded worker |
| Decision | Retain the implemented optional `long-running-work` package and dormant `octon work run` routing boundary in the Octon Mini 4.1 source architecture |
| Ownership | Existing task owns goal, scope, authority basis, and acceptance; existing transactions own reversible repository mutation; project-check evidence owns validation; work completion owns Git/provider completion; Continuation owns safe refusal; the package owns only one active run coordinate, measurable limits, derived context manifests, bounded transition history, and committed checkpoint markers |
| Lifecycle boundary | The package lifecycle is aggregate-specific and does not create a universal action, trust, readiness, task, project, or provider state machine |
| Execution boundary | Octon Mini governs an external worker through deterministic local contracts and commands; it does not host, choose, authenticate, or call a model |
| Package boundary | The package is absent and inactive by default, installed transactionally from pinned bytes, adopted separately, restrictions-only, independently snapshotted, and removable only when doing so cannot orphan active or retained run state |
| Context boundary | Context compilation is deterministic, read-only, source-referencing, budgeted, omission-visible, and non-authorizing; no model, embedding, vector store, service, hook, or network call participates |
| Recovery boundary | Only marker-backed checkpoints are resumable; resume revalidates task, instructions, authority references, context, project state, receipts, validation, and limits; ambiguous effects are never replayed |
| Quantitative boundary | Only locally measurable run limits are enforced. Missing token, cost, worker, provider, or external-resource measurements remain `unknown`, never zero |
| Compatibility | Additive optional package plus a dormant generated dispatcher route. Existing snapshots require explicit reviewed upgrade or package-compatible command use and never acquire or activate the capability automatically |
| Evidence gate | Retention requires positive, negative, mutation, fault-injection, migration, clean-runtime, benchmark-v2, package-performance, and authorized disposable-project evidence; dirty-source exercises cannot establish final-candidate maturity |
| External-effect boundary | None; this direction authorizes no commit, push, PR, merge, tag, release, publication, deployment, message, provider mutation, credential use, or other external action |
| `permission_grant` | `false` |

This acceptance retains the implemented source architecture and closes its
pending source-decision gate. It does not authorize a commit, push, PR, merge,
tag, release, publication, deployment, package installation, target-project
adoption, runtime effect, credential use, or readiness claim. The resulting
source changes remain unreleased and unadopted until those separate processes
are explicitly authorized and completed.

## SRC-DEC-0019 — Governed autonomous-delivery capability

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner acceptance on 2026-08-22 of the revised autonomous-delivery architecture, delivery-profile model, standing-authorization drafting boundary, recovery model, and human-only gates; explicit repository-owner acceptance on 2026-08-23 of the dual-mode compute-control amendment and the narrow source-repository work-completion amendment |
| Scope | One provider-neutral optional `workflow_capability` for autonomously delivering an already human-prioritized and architecturally authorized task |
| Availability | Every new, adopted, and upgraded project exposes the smallest dormant delivery surface; its initial state is `available_not_activated` and externally locked |
| Pre-activation boundary | Research, context building, applicability assessment, planning, status, explanation, and activation preview are read-only, execute no project hooks, mutate no repository or external state, create no receipt implying work, and create no authority |
| Package boundary | Write-capable behavior remains in a locally bundled, content-addressed optional package; activation requires no network installation and never occurs silently |
| Delivery-profile axis | `review_first`, `balanced_autonomous`, `fast_delivery`, and `custom` are presets independent of assurance, collaboration, concurrency, and layout; the exact accepted standing contract is authoritative |
| Recommendation boundary | `fast_delivery` may be recommended for most solo developers but is never preselected or activated; a more-permissive successor requires human confirmation |
| Ownership | Existing task and human priority authority own goal, scope, priority, authority basis, and acceptance; accepted decisions own architecture; `SRC-DEC-0020` owns standing release-evidence policy; long-running work owns the run coordinate; transactions own reversible local mutation; project-check evidence owns validation; work completion owns commit, push, PR, checks, merge, and cleanup; Continuation owns refusal; the package owns only activation, delivery-budget, and release-effect projections and references |
| Standing-authorization boundary | Setup deterministically drafts a complete non-authorizing contract and digest; only independent human confirmation of those exact bytes supplies authority, after which an immutable external record may evidence the grant outside the repository |
| Execution boundary | A short-lived exact-plan coverage projection may prove that a current standing record covers one operation; the projection, plan, profile, receipt, or command cannot create or broaden authority |
| Source-repository mode | The existing work-completion engine may govern Octon Mini source delivery from an externally supplied, immutable, digest-bound Codex task reference. It creates no source task store or second lifecycle; work completion retains commit, push, PR, checks, merge, synchronization, and cleanup ownership; the release adapter does not gain those operations. The precommitted candidate is bound by exact base, head, commit range, changed paths, source authority, standing authorization, and receipts. Integration pauses until the stable required check and exact complete candidate matrix are recorded; cleanup pauses until exact integrated-main validation evidence is recorded |
| Release adapter | The package may add only the closed Git/GitHub source-release operations accepted here; it is not a universal action runtime, deployment system, package publisher, credential broker, or external-project controller |
| Recovery boundary | Repository-local transactions may be exactly reversible; commits and unpublished task branches are recoverable; pushes, merges, tags, and Releases are monotonic effects handled through read-before-act, receipts, read-back, reconciliation, and fix-forward; an unknown outcome stops with zero automatic retries |
| Compute boundary | Each exact standing contract selects exactly one mode. `metered_api` requires host-enforced per-run and authorization-period USD ceilings and treats unknown cost as blocking. `included_subscription` permits only the selected existing plan's included allowance, requires current readable provider-enforced usage status, and prohibits separately purchased credits, API billing, pay-as-you-go capacity, add-ons, and upgrades. Unknown, unreadable, exhausted, or changed compute state blocks. Direct autonomous-worker purchasing and external spending remain zero in both modes |
| Compatibility | Additive optional capability with reviewed migration; independent snapshots never acquire activation, repository facts, provider facts, credentials, project decisions, or standing authorization automatically. Confirmed v1 records remain immutable legacy metered-API evidence; selecting another mode requires a v2 successor with a new stable authorization ID, exact predecessor binding, operator-controlled predecessor revocation before activation, and new exact-digest confirmation |
| Human-only gates | Humans retain product-priority selection, architecture acceptance or amendment, release-evidence and risk policy, product-boundary or standing-authority expansion, conflicting-authority resolution, and required specialist or external-project decisions |
| `permission_grant` | `false` |

This source decision accepts implementation architecture only. It does not
create runtime authority. The v1 `SAC-01` record was never activated and is
revoked; independently confirmed subscription-mode `SAC-02` is the current
external standing envelope. Every covered operation still requires a fresh
exact-plan projection, current subscription-status evidence, and all live
preconditions. A confirmed contract is never reinterpreted after a compute-
mode change; any changed contract requires a separately confirmed successor.

## SRC-DEC-0020 — Standing source-release evidence policy

| Field | Accepted decision |
|---|---|
| Status | `accepted` |
| Authority | Explicit repository-owner acceptance on 2026-08-22 of the revised standing release-evidence and risk policy, with the dual-mode compute-control amendment accepted on 2026-08-23 |
| Covered releases | Technically scoped final patch and minor Octon Mini source releases whose product priority was explicitly selected by a human and whose necessary architecture decisions are accepted |
| Required gates | The release stays within accepted boundaries; all applicable tests, mutation tests, fault injection, migrations, benchmarks, hosted checks, exact read-backs, and unchanged thresholds pass; no critical or high finding remains; unsuccessful evidence is retained; limitations are disclosed |
| Minor-release addition | Complete the applicable end-to-end disposable exercises and an authorized Octon Mini source exercise |
| Independent-evidence boundary | Unavailable unfamiliar-operator, independent-reviewer, independent external-project, and human-usability evidence may be disclosed for technically scoped patch and minor releases, but cannot support independent maturity, adoption, usability, project readiness, or production readiness claims |
| Standing-authority gate | Release requires an independently confirmed, current, exact standing-authorization record whose repository, branch, action, release type, limits, selected compute mode, current compute evidence, revocation, emergency-stop, and evidence bindings cover the exact operation |
| Compute gate | Direct autonomous-worker spending remains zero. Metered API mode requires current host enforcement of the selected USD ceilings. Included-subscription mode requires current readable provider-enforced included-allowance status and proves that paid credits, API or pay-as-you-go billing, add-ons, upgrades, and a billing-mode change are not in use. Unknown, unreadable, exhausted, or changed compute state blocks |
| Human reconsideration | Required for major releases; product-boundary expansion; new standing-authority or external-effect families; security, privacy, legal, credential, or destructive-migration changes; deployment; external-project release; package publication; weakened tests, gates, reviews, or thresholds; unavailable mandatory safety evidence; unresolved critical/high findings; or claims exceeding evidence |
| Historical boundary | The v4.1.0 `accept_disclosed_absence` choice remains release-specific and supplies no authority for this standing policy |
| Permission effect | None; this policy defines evidence eligibility and cannot activate delivery, create standing authorization, or authorize an individual external effect |
| `permission_grant` | `false` |

The accepted policy permits no release until the exact independent
standing-authorization confirmation and every current gate are separately
satisfied. A draft contract, profile selection, setup answer, plan, receipt,
evidence record, or successful validator is not release authority.


## SRC-DEC-0039 — Mini-derived Octon identity transition

| Field | Value |
|---|---|
| Status | Accepted for this operator-authorized local transition |
| Date | 2026-09-21 |
| `permission_grant` | `false` |

The active successor is Octon, based on released Mini 4.2.0 and preparation commit
`5e2d3025aea6b1574ab984e5ebb89b5602a38535`. This supersedes SRC-DEC-0014's current
product naming, not its historical producer identities or safety boundaries.
Version 5.0.0 is an unpublished identity-major candidate with kernel 4.2 compatibility.
Original Octon and OctonOS remain separate references. Plectarium is optional.

SRC-DEC-0021 through SRC-DEC-0038 are reserved by separately preserved unfinished
4.3 work. Those decisions, features, permissions and state are not imported here.
No ID is reused. The explicit operator request supplies this local task's scope;
this record creates no standing authority or publication permission.

Use a distinct Octon origin and typed migration, preserving published Mini schemas,
initial generation, prior migrations and project-owned records. Retain stable
compatibility wire identifiers. New provenance names the actual Octon producer.
Generation stays independent and non-authorizing; upgrades remain deliberate and
recoverable through the existing transaction owner. Reference permissions, grants,
credentials, operational state and readiness claims never transfer automatically.

GitHub addresses, historical tags/releases and existing consumers are unchanged.
Cutover and reference retirement remain separate gated outcomes; an identity label
never closes a task, proves quiescence or resolves an uncertain effect.
