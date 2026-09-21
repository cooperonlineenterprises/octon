# Octon 5.0.0 identity transition

Status: local unpublished candidate; validation and independent implementation
review are in progress. This page grants no permission and claims no publication,
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

Current checks must cover all six profile/layout combinations, real released
Mini upgrade inputs, preserved records/history, conflict refusals, interruption
recovery, independent snapshots and dormant/non-authorizing defaults. Source,
package, compatibility, negative-control and performance results are recorded for
the exact candidate. Unavailable hosted/platform evidence must remain disclosed.
This record will be completed after those checks and independent review; it is
not evidence that unrun checks passed.


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
