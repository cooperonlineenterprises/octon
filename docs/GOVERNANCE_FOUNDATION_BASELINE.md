# Governance foundation baseline and adoption inventory

Observed September 27, 2026. This is source-owned implementation evidence and a
compatibility disposition, not a grant or a portfolio-wide readiness claim.

## Source baseline and preserved work

| Surface | Exact inspected state | Disposition |
|---|---|---|
| Octon source | `fd6d20b55d1053864b6e859e95e22708008dc58a` on `imp1/source-boundaries` | Committed implementation base for this foundation. Existing source PR #1 owns the preceding OEP-1 changes. |
| Octon hosted main | `a1d528e1cfd4272c953c7d50ea6e9d16d283e002` | Earlier identity baseline; do not imply the pending IMP-1 source is integrated. |
| Original Octon working tree | Modified OEP-1 plan and legacy allowlist; untracked Plectarium integration decision/disposition documents | Preserved in place. This branch starts from committed bytes, not those unrelated edits. Pre/post file hashes and Git state are retained outside the repository. |
| Source workflow | Active `protect-main`, app-bound `required`, strict up-to-date, merge-only, zero approvals, no bypass, deletion/force-push protection | Current configuration observed through GitHub, not inferred from older source workflow prose. No control change or autonomy activation in this slice. |
| Plectarium hosted main | `ca120a9b57febc4f9fa02294663f252b13de0d93` | Its scoped CI PR is integrated and post-merge validation passed. This does not qualify a new harness or general autonomous integration. |
| Original Plectarium checkout | `47181c370ebfd4fcd47177f169d192910c49fd32` plus unrelated uncommitted architecture records | Preserve. Do not treat source-copy similarity as a completed consumer cutover. |
| Plectarium CI closure | Local checkpoint `c3dde6feb621feadfa1f415588ab0a17a44046c6` after the observed merge | Actual completion is recorded on PR #1 and locally. The later record-only checkpoint is not in the published merge tree; reconcile it through a later scoped project change. |

The owner-directed architecture reference is version 1.0, SHA-256
`3648e8cf6dd879399b3f1164d550401584f38bd20f6ef83543fb210488e62ca9`.
Its requirements select the destination; historical pins/observations do not prove
current enforcement or supply operational authorization. Source decisions
SRC-DEC-0041–0043 translate only the first foundation into repository contracts.

The existing OEP-1 target-manifest work remains an inactive design inventory.
Source version 5.0.0 and kernel compatibility 4.2.0 are not changed here.
Unfinished 4.3 decisions/features and original runtime identities are not imported.

## First consumer boundary

Plectarium remains a customized high-assurance 1.0.0 snapshot with these directly
read inputs (unchanged by its CI work):

| Source | Version / SHA-256 |
|---|---|
| `.agent/schema.json` | `harness.schema.v1`, kernel 1.0.0; `941af3249b23df0409e064a89fa1e540efe7c8323ed9500da86bbc3dc03e4ed8` |
| `.agent/project.json` | `harness.project.v1`, high-assurance 1.0.0; `1d3c01785593df93e26a307aa836a3f08a211d88d27468130243015f34ba214c` |
| `.project-blueprint-origin.json` | `project-blueprint.origin.v1`, generator 1.0.0; `2cd6038d2ac83b5675c0cf7874f0e1b93d5ceb0e4a6721165e6f99b80e837b7d` |
| `.agent/policy.json` | `harness.policy.v1`, invocation-scoped DEC-0001 posture; `ed113ef2ee39a552e0e88a2fa07ccdd31312b3942616a9322da667e357f2e0ae` |

The current upgrader accepts released Mini 4.2.0 for the identity transition;
Plectarium's origin is explicitly refused without mutation. The compatibility
test exercises that real refusal with synthetic inert legacy input. It does not
claim an implemented 1.0.0 conversion. Before adopting the behavioral successor:

1. Resolve the exact project snapshot, custom fields/commands, accepted IDs,
   local closure and pending architecture records through Plectarium's owner.
2. Demonstrate a suitable released migration chain on that exact snapshot, or
   implement a versioned conversion through the existing transaction owner.
3. Inventory any active holders, journals, grants and attempted/unknown effects.
   Finish them under the original contract or map them once; never replay an
   unknown effect to make a conversion appear complete.
4. Fence the predecessor writer before activating its replacement. Preserve
   historical readers, preimages, receipts, origin history and independent use.

The installed `project-bootstrap` source still declares version/kernel 1.0.0.
It is an independent installed snapshot, not a live link to this repository.
Its full payload/effective host selection and other discovered consumers need
their own scoped inventory before upgrading. Custom/external-state consumers
such as Texenda require their existing owner and a qualified binding conversion;
no new Octon task/receipt writer may be installed beside an active predecessor.

## Canonical-owner disposition

Octon's source work remains owned by the current external Codex task; this PR
creates no source `.agent/tasks` ledger. Accepted source choices remain in
`ARCHITECTURE_DECISIONS.md`. Project work/DEC/evidence/transaction/run/completion
mechanisms remain their existing owners. The schema defines immutable references
and hypothetical projections, not a second task graph, grant store or coordinator.

The three initial successor areas are adopted for inactive source qualification.
Concurrent coordination, ChangeSets/integration, delivered acceptance, source
release and Plectarium's project/product follow-ups retain the explicit remaining
dispositions in `GOVERNANCE_FOUNDATION.md`. No existing grant is widened in place.

## Unresolved facts and exact blocking scope

| Fact not qualified here | Blocks |
|---|---|
| Actual principal grants, issuer authentication, protected storage/stop controls and current limits | Live authorization/activation; synthetic shadow checks need none of those grants. |
| Worker isolation, credential scope, independent verification baseline, atomic reservations and fencing | Concurrent real execution and autonomous admission. |
| Exact in-flight state of each consumer and qualified custom conversion | That consumer's migration/cutover, not this source-only foundation. |
| Whole-portfolio installed versions and active ownership | Portfolio rollout; no broad readiness/inventory completion is claimed. |
| Remaining source PR/full-matrix and project-owned demonstrations | Their respective integration/release/adoption gates; no historical pass substitutes for an exact candidate result. |

The initial implementation tests declared semantics and preserves active behavior.
It must not be used to bypass any of these gates or to reinterpret a stored grant,
accepted decision, passing CI run or current task instruction as standing authority.
