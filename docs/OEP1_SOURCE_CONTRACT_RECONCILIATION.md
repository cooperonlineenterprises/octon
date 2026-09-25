# OEP-1 source contract reconciliation and post-baseline evidence

Recorded 2026-09-25 against base source commit
`a1d528e1cfd4272c953c7d50ea6e9d16d283e002` on task branch
`imp1/source-boundaries`. This is implementation evidence and a boundary
assessment, not a new accepted source decision, runtime release, project
migration, or permission grant. [IMP-0](IMP0_BASELINE.md) remains the unchanged
historical before-state report.

## Post-baseline legacy-reference resolution

The three IMP-0 findings came from two already-edited documentation files.
Their text, intended migration meaning, and historical identifiers are
unchanged. The exact exception inventory now binds:

| Entry | Reviewed disposition |
|---|---|
| `LEGACY-0002` | Retain `truthful_historical_record` and its 13 matches; update only the decision file SHA-256 to `ee1f86d37665082db052c9c131f6e41e1d9aa928a0fdb6914baed0f3c114f6f6`. |
| `LEGACY-0062` | Add the plan's two predecessor-lineage migration references as `explicit_legacy_migration_input`, bound to file SHA-256 `9788fd3987ecdfec4bc347d7e0e4dbb1293da086f16daaaaf6ae182de7d7bf89`. The plan describes future converters and a pilot; it does not dispatch an old runtime. |

The matcher, classifications, count enforcement, schema, and historical IDs were
not relaxed or reassigned. Focused legacy-reference validation reports zero
findings; `validate_source_contracts.py` passes. The complete
`validate_octon_mini.py` source gate passed in 1,443.321 seconds, covering 225
required files, 105 templates, and all six profile/layout builds. The complete
`test_acceptance.py` gate passed in 723.473 seconds: 15 automated criteria passed;
seven project demonstrations remain project-owned. Exact logs and result JSON
are under `/private/tmp/octon-oep1-fix.V1qZ3C/`. These are post-baseline results;
the red IMP-0 observations remain in their original report.
The reviewed source-history and reference fix are pinned by local commit
`2ef01fec7dc0bcc90dd4f950bcbf32733803e85b`.

## Reconciled implementation contracts

Inputs: accepted [source decisions](../ARCHITECTURE_DECISIONS.md#src-dec-0040),
the [OEP-1 specification](../../../../../octon-project-standard/SPECIFICATION.md)
(documentation revision 1.0.1, SHA-256
`44ccec1f62191cfe01026f6230e24fd87277a401222755738eff9003fa4026d0`),
its design `structure-catalog.json` (version 1.0.0, 100 entries, SHA-256
`49dd429b956e048df83c2a6f6bd1ec0b8adfe041855f5d41a68ba6afda470d03`),
and the [ecosystem migration boundary](../../../../../octon_plectarium_quoris_ecosystem_specification/docs/12-migration.md)
(SHA-256 `40697e8c9ac2eda860fed8c6d4b276b059ba420ce454f5bea755f0b711bb643b`).
The current source manifest SHA-256 is
`df7fd2a15884c3babecef19e5af588c92728530ba4c4a88909a60f2f9b759906`.

| Concern | Current accepted contract and target reconciliation |
|---|---|
| Source generation | `SRC-DEC-0007` keeps `shared/source-contracts/profile-manifest.json` as the one authoritative inventory. OEP-1's 100 design entries specify coverage and selection to incorporate there; they do not become a second production registry. Exact copied runtime files, package files, and resulting project paths need manifest-backed inventories and dependency resolution. No catalog entries are copied into generation by this record. |
| Physical paths | Current independent snapshots use `.agent`, `.agents`, `project-dossier`, `.octon-origin.json`, and the root launcher. OEP-1 targets `.octon/agent`, `.octon/agents`, `.octon/dossier`, `.octon/runtime`, and `.octon/manifest.json`; a root launcher is conditional. A versioned resolver must receive explicit root/layout/binding inputs. Neither name similarity nor an occupied `.octon` path proves compatibility with the unrelated original runtime. Existing paths remain active until an exact, collision-aware migration. |
| State and recovery | `SRC-DEC-0008` and `SRC-DEC-0017` preserve one transaction owner, exact plans, preimages, receipts, interruption recovery, and derived current state. OEP-1 requires one live project state writer, explicit external storage bindings, and separate local durable material. Dossier records remain explanatory and cannot grant permission. Relocation must preserve ownership and old receipts, not create parallel stores. |
| Package and invocation ownership | `SRC-DEC-0009`, `SRC-DEC-0013`, `SRC-DEC-0018`, and `SRC-DEC-0019` keep package installation, adoption, activation, and external-effect authority distinct. Current optional package IDs, versions, and digests remain pinned by the source manifest. Basic inspection and recovery must not import optional mechanics. Octon keeps project tasks, decisions, evidence admission, acceptance, and local recovery. An independent specialist owns its domain method; Plectarium owns attempts and reconciliation only for an invocation delegated to it. The IMP-0 capability assessment is an ownership constraint, not code-transfer authority. |
| Compatibility | `SRC-DEC-0039` retains the unpublished 5.0.0 source identity, kernel 4.2.0, historical Mini-lineage wire IDs, origin readers, and explicit released-4.2-to-5.0 upgrade. `SRC-DEC-0040` retains this repository and its history. OEP-1 layout conversion needs a distinct source-version-specific migration and an accepted compatibility horizon; no target runtime version, automatic upgrade, release, or root relocation is declared here. |
| Representation and discovery | `SRC-DEC-0011` keeps compact/separated dossier representations independent of assurance and collaboration. OEP-1 places them within one installation convention while preserving artifact IDs and source ownership. Root `AGENTS.md`, native adapters, and project application files need collision-aware reconciliation; generated projections cannot become another authority source. |

## First bounded implementation slice

IMP-0 measured four static local imports at generated dispatcher load, including
work-completion mechanics. The generated dispatcher now loads those mechanics
only for completion actions or the existing close-plan event. Its public
commands, plan/receipt semantics, and typed refusal reports remain at the same
interface. No generated path, package installation state, source manifest, or
project-owned record changed in this slice.

Focused evidence: 12 work-completion tests and eight launcher tests passed;
Minimal/compact generation created and validated 109 files; generated `octon
check` passed. Static generated-core imports changed from five to four edges,
and the dispatcher from four to three immediate local modules. Eleven fresh
generated `--help` processes had a 0.061 s first observation and 0.056 s later
median, versus IMP-0's 0.070/0.063 s on this host. Help output SHA-256 remained
`d0342d050f7f6d7fa1344ad1159d72471e5f01d5df2cf9e0c81b8152b20d8dc9`.
These are local first-use proxies without cache eviction, not a performance
guarantee.

The disposable IMP-0 and IMP-1 Minimal projects also returned the same exit
code `2` and identical stderr SHA-256
`3917e600079d104213ece65235b2cb97b361f94f8c2c7827e05ec28808dd9e8d`
for disabled `work finish plan --json`, including the existing typed refusal and
no-mutation statement. The complete IMP-1 candidate source gate passed in
1,441.371 seconds; the complete acceptance gate passed in 704.841 seconds,
again with 15 automated criteria passing and seven project demonstrations
remaining project-owned. Exact candidate logs and result JSON are under
`/private/tmp/octon-oep1-candidate.Ha9UcW/`. There are no remaining automated
failures from this slice on the measured host; no cross-platform matrix or
target-project adoption is claimed.

The next bounded entry at this first-slice checkpoint was the explicit
installation root/binding resolver at
the `scaffold_project.py` project-path boundary (`project_local_source_paths`,
`origin_path`, and their callers). `selected_layout` currently means compact
or separated dossier representation and must stay independent of physical
installation layout. The binding and its focused checks are recorded below.
The broader IMP-1 exit gate is not claimed.

## Explicit installation binding slice

The source-side `InstallationBinding` now requires `current` or `oep1_target`.
It anchors paths to an explicit canonical project root, checks portable
project-relative paths and symlink confinement, rejects occupied target
namespaces and old-layout markers, and requires one embedded or explicitly
external live-state owner. The current generator and adoption planner pass a
rooted current binding through project-local sources, derived outputs and the
historical origin. Existing manifest readers retain an unbound current-only
path-shape compatibility shim. A target binding cannot treat the old origin as
`.octon/manifest.json`; no target generation or migration is enabled.

Five focused binding tests passed on local CPython 3.13.9 and 3.14. They cover
current records and transaction roots, target/current separation, lexical and
symlink confinement, reserved `.octon` collisions, a moved project root,
platform-portable path spellings, a single live-state owner, and a real
read-only adoption-plan refusal for an escaping symlink. With the same fixed
fixture inputs, before/after Minimal generation produced the same 109 paths;
105 file hashes matched and the four derived JSON differences were only refresh
time or generation ID fields. Generated `check`, `doctor --json` and transaction
help each returned exit `0` with byte-identical output before and after.

The first complete source run on this slice exited `1` after 1,451.067 seconds
solely because the exact `LEGACY-0051` file digest had become stale after the
adoption-planner edit. Its one reviewed occurrence and
`explicit_legacy_migration_input` classification were unchanged. Updating only
that entry's digest to
`8f30602d7b31921ef3b758d8d7419df06ce7c517d5eef34e2f57b95c47d87393`
cleared the focused check. The final complete source validation exited `0` in
1,472.228 seconds: 226 required files, 105 templates, and all six
profile/representation builds. Both logs and result JSON are in
`/private/tmp/octon-imp1-binding.2DZsLt/`.

Acceptance was not rerun for this source-only slice: the generated path
inventory and the observed read-only command outputs did not change. The
previous acceptance pass remains the exact prior candidate result, not a
qualification of a target-layout project. Real Windows-host execution,
target-manifest reading, target generation/adoption, external-state writing,
project-identity collision checks, and migration of existing records or
receipts remain unqualified. The IMP-0 results remain unchanged.

At the binding-slice checkpoint, the next IMP-1 entry was to define the
versioned target installation manifest
and integrate its selected path inventory into the existing source profile
manifest, then carry explicit bindings through adoption/upgrade and narrow
generated runtime compatibility shims. Qualify source/target identity,
reserved-name disposition, one state owner, and old receipt readability before
any generated path switch.

## Versioned target installation manifest slice

The source profile manifest is now `octon-mini.source.profile-manifest.v2`
(SHA-256 `ac1b35823e5de7e00551f23158b501450afd3528c1f8f61890e51487e2e35bc6`).
It remains the only generation inventory owner. Its current rules and selected
output paths are unchanged. The nested
`octon.source.target-installation-manifest.v1` is version `1.0.0`, lists 13
project/workspace root bindings and 22 core seed files with exact owners,
information classes, tracking treatment, profile floor and stable IDs, and
binds its file inventory by SHA-256
`ade178baff5247131df9d7b2391fd176afac70cf11b1f72d308317b95be3f7b1`.
Every target source-rule ID is `null` and status is
`design_only_not_selectable`. A valid design inventory cannot select target
generation, install runtime assets, adopt a project or migrate state.

Source generation validates this target contract but continues to select the
current installation. A target `InstallationBinding` takes its roots from the
validated manifest rather than a directory-name guess. Source adoption and
upgrade derive the reserved `.octon` path from the same binding and refuse
occupation before planning a current-layout change. The generated dispatcher
uses a rendered current-layout parent depth derived from the validated current
binding; other generated runtime paths and historical origin/receipt readers
remain on their existing routes.

Focused results: eight binding tests passed on local CPython 3.13.9 and 3.14,
including missing/invalid manifest entries, hash-correct but wrongly owned or
escaping files, reserved-root occupation, moved roots and duplicate live-state
paths. Thirty-five architectural-pattern tests, twelve work-completion tests,
eight launcher tests, the source-contract validator and skill-package validator
passed. A fixed Minimal fixture generated the same 109 paths before and after.
Only the dispatcher, its installed provenance and four refreshed JSON records
changed bytes; `--help`, `check`, `doctor --json` and transaction help had
identical exit codes and output hashes. A moved candidate snapshot passed
`octon check`.

The first full source run exited `1` after 1,484.436 seconds with three reports
of one candidate-only issue: the repository template validator lacked the new
current-dispatcher render input. The generator and validator now call the same
manifest-derived helper. The final full source run exited `0` in 1,495.323
seconds, validating 226 required files, 105 templates and all six
profile/representation builds. Because generated bytes changed, the full
acceptance suite was rerun and exited `0` in 754.067 seconds: 15 automated
criteria passed; seven project demonstrations remain project-owned. Exact logs
and result JSON are under `/private/tmp/octon-imp1-target-manifest.sqd2I9/`.

This is a core seed design inventory, not complete OEP-1 applicability or an
actual `.octon/manifest.json` reader. Qualified copied runtime modules and
content digests, target generation, target adoption/upgrade, external-state
writing, real-project migration and independent project acceptance remain
outside this slice. Full Linux/Windows and Python 3.11/3.12 matrix execution
was not performed; Windows-style path spellings were exercised only by local
focused tests. The historical IMP-0 report is unchanged.

The next IMP-1 entry is to qualify pinned copied runtime assets and bind the
target core entries to exact source rules and content digests inside this same
profile manifest. Then add the target installation-manifest reader and catalog
dependency selection with focused compatibility/recovery checks before making
the target layout selectable for a complete IMP-2 slice.
