# Octon 5.0.0 identity transition

Status: local unpublished identity-transition source. This page grants no
permission and claims no publication,
target-project adoption, runtime equivalence, or production readiness.

The foundation is Mini commit `5e2d3025aea6b1574ab984e5ebb89b5602a38535`:
released 4.2.0 plus release-record reconciliation. Unfinished 4.3 work is retained
separately and is not included. Source decision IDs through SRC-DEC-0038 remain
reserved; their features, accepted decisions and operational state are not imported.

Current identity is Octon, bootstrap `octon-project-bootstrap`, metadata
`octon.json`, local version 5.0.0 and new provenance `.octon-origin.json`.
The GitHub repository remains `cooperonlineenterprises/octon-mini`. It is the same
Mini lineage, not the original Octon runtime. That runtime and OctonOS remain
separate references; neither is required for generation, validation or operation.
Plectarium is optional and not an implementation dependency.

## Compatibility boundaries

The published `octon-mini.project.origin.v1` schema remains unchanged. The new
`octon.project.origin.v1` explicitly records product `octon`, actual generator
version and current generation. Its history accepts historical Mini migration
records under their unchanged typed definition and new Octon migration records
under a distinct type. Each type is checked explicitly by the validator.

Generic contracts, stable IDs and compatibility namespaces remain intact.
`octon_mini_version`, `OCTON_MINI_VERSION`, `octon_mini_implementation_asset`,
`octon-mini:` source locators and existing generic `octon-mini.*` wire types remain
stable Mini-lineage identifiers; they do not identify the unrelated original
Octon runtime. New origin and newly generated capability provenance explicitly
identify Octon as their producer. Historical producers and records are untouched.

The harness kernel has its own compatibility axis, still 4.2.0. Optional package
payloads and their pinned content/version contracts are unchanged. This identity
release adds no coordination, worker host, control plane, permissions or grants.
The project still owns policy, decisions, authoritative state, evidence admission,
acceptance and recovery. Dossier documentation does not become operating authority.

## Supported transition

Fresh generation supports Minimal, Standard and High Assurance in compact and
separated layouts. The explicit upgrade source is released Mini 4.2.0; older
snapshots can first use their released Mini upgrade path. Existing snapshots never
follow source changes automatically. See [the migration guide](../migrations/4.2.0-to-5.0.0.md).

The existing transaction engine owns preview, exact plan confirmation, fingerprints,
staging, receipts, interrupted-apply recovery and unchanged-receipt rollback.
There is no second upgrader or state owner. Conflicts and uncertain outcomes stop;
no reference grant or previous release authorization is transferred.

## Local verification scope

On 2026-09-21, local source validation and acceptance passed on implementation
tree `2f8754da5edd91d3262c21a67c1698b8a1c7033e`, committed unchanged as
`480d4180886247c595da66cb9e827c34ef4cb2d5`. The host was Darwin 25.6.0/arm64
with existing CPython 3.13.9. This documentation update changes no executable,
schema, template or package payload.

Coverage includes all six profile/layout combinations, real released Mini 4.2
upgrade inputs, preserved project records, prior nonempty Mini migration history,
unchanged old receipts, conflicting-origin refusal, public-command recovery at
three interruption boundaries, independent snapshots, and dormant defaults.
Applicable source, package, compatibility and negative-control suites passed.
Acceptance reports 15 automated criteria passed and seven demonstrations still
owned by consuming projects; it does not establish project readiness.

The existing enforced validation benchmark passed all 129 samples: compact-layout
scaffolding for all profiles and 0/2,000/10,000/20,000-file synthetic targets.
Combined p90 at 10,000 files was 1.38 seconds for check (limit 2 seconds).
Scaffold p90 was at most 8.79 seconds and fast-mutation p90 at most 6.97 seconds
(limits 10 seconds). Sample counts and thresholds were unchanged. These are local
host-specific measurements, not platform-wide guarantees or cache-eviction tests.

Independent plan/preservation and corrected-code reviews were accepted. The
reviewer was admitted through the operator's task-specific exception; effective
model/reasoning settings remain unverified. Exact-revision final evidence review,
cutover status and recovery locations are retained in the local transition record.
No general runtime qualification follows. Failed predecessor checks remain
retained. No 5.0 hosted matrix, other-platform execution, unfamiliar-operator or
real-provider evidence, remote release, or consumer adoption is claimed.

The current executable migration qualification is the 4.2-to-5.0 suite, using
immutable released-foundation Git input. The former 3.1-to-4.0, 4.0-to-4.1 and
4.1-to-4.2 integration suites remain historical source references and are not
reported as Octon 5.0 migration passes. Their released tools remain in Git history;
5.0 refuses direct upgrades from those older snapshots. Other applicable kernel,
package, source-work, setup and negative-control suites remain required.

Full source/acceptance qualification needs repository Git history for the exact
preparation-baseline fixture; CI explicitly fetches full history and tags.
Installed source bundles use `validate_octon_mini.py --installed-smoke` for their
contract/profile checks. Generated-project checks require neither Git history nor
the source checkout. Missing fixture history is not a passing migration result.
