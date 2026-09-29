# IMP-0 source baseline

Recorded 2026-09-25 (America/Chicago). This is a comparison record for the
existing implementation, not a release, project adoption, or permission grant.
No runtime, generator, schema, template, package, or operating installation was
changed for IMP-0.

## Exact source and environment

- Source `main` and `origin/main`: `a1d528e1cfd4272c953c7d50ea6e9d16d283e002`
  (`git rev-parse --is-shallow-repository` returned `false`). There were 384
  tracked paths. The pre-existing working tree contained only a modified
  `ARCHITECTURE_DECISIONS.md` (SHA-256
  `ee1f86d37665082db052c9c131f6e41e1d9aa928a0fdb6914baed0f3c114f6f6`)
  and untracked `docs/OEP1_IMPLEMENTATION_PLAN.md` (SHA-256
  `9788fd3987ecdfec4bc347d7e0e4dbb1293da086f16daaaaf6ae182de7d7bf89`).
  `git status --short --ignored` listed no ignored paths.
- Product metadata: `VERSION`, `pyproject.toml`, and `octon.json` identify local
  unpublished Octon `5.0.0`; `octon.json` identifies kernel `4.2.0`, minimum
  Python `3.11`, and the source generation manifest. `pyproject.toml` declares
  no runtime dependencies. Existing `v4.2.0` is historical, not fresh
  qualification.
- Host: macOS 26.6.2 / Darwin 25.6.0, arm64, CPython 3.13.9, Git 2.51.1,
  14 logical CPUs. This is one local host and interpreter, not the CI platform
  matrix.
- `shared/source-contracts/profile-manifest.json`: schema
  `octon-mini.source.profile-manifest.v1`, SHA-256
  `df7fd2a15884c3babecef19e5af588c92728530ba4c4a88909a60f2f9b759906`.
  Its reviewed generated-source inventories contain 63 core templates, 17
  Standard templates, 25 High Assurance templates, 39 shared schemas, and two
  single-file contracts (146 entries total). Seven optional package inventories
  contain 42 paths: five packages at `1.0.0` and two at `2.0.0`; their exact IDs,
  digests, selection rules, and paths are in that manifest. The 39 shared schema
  files contain 99 distinct `schema_version` constants, including historical
  readers. A disposable Minimal/compact generation produced and validated 109
  files.
- Committed Git tree IDs for comparison: `shared/schemas`
  `a65c650a279481a0e073dfae49c453c959d7a51b`,
  `shared/source-contracts` `a351f43f7eb9bef0968815d90bc3a6ae621e05a9`,
  templates `aca5f860b32c7eb1382a1957083a6b2fe47a47ef`, packages
  `ed8ce82cc768a519a1e7b52b92fe421fb34034fe`, and scripts
  `c5dddfeab921bd96f0ed74958779e27fb5c79c21`.

## Declared checks and existing failures

Run from the repository root with `python3 -B` and the script paths under
`skills/octon-project-bootstrap/scripts/`, as declared in
`.github/workflows/validate.yml`:

| Check | Exit | Elapsed | Result |
|---|---:|---:|---|
| `validate_skill_package.py` | 0 | 0.032 s | Passed |
| `verify_reference_evidence.py` | 0 | 0.068 s | Passed |
| `test_benchmark_validation.py` | 0 | 8.534 s | 15 tests passed |
| `test_octon_launchers.py` | 0 | 0.820 s | 8 tests passed |
| `validate_octon_mini.py` | 1 | 1394.113 s | Three starting-state documentation findings |
| `test_acceptance.py` | 1 | 686.895 s | Three failures caused by the same starting-state blocker |

The source validator ran its identity-transition, migration, refusal, recovery,
and other executable fixtures and reported no failures from them. Its three
findings were: `LEGACY-0002`'s recorded digest differs from the already-edited
decision file; the untracked implementation plan has unreviewed legacy-identity
references at lines 118 and 122. Acceptance could not validate the staged skill
for the same reasons, then reported missing taxonomy and license in that failed
installation. Those latter two are downstream effects, not separate missing
committed files. A clean checkout at the exact source commit passed
`validate_octon_mini.py --installed-smoke`: 225 required files, 105 templates,
and all six profile/layout builds.

Disposition: preserve both user-owned documentation edits. Review the exact
legacy-reference classifications and digest inventory before claiming a clean
source or acceptance gate; do not silently broaden the allowlist or classify
these existing failures as implementation regressions. No IMP-0 source change
introduced them.

## Dependency and performance comparison points

Static top-level Python AST imports over 49 source scripts found 13 local edges;
the source dispatcher has no static local import edge but loads the continuation
template dynamically and dispatches command scripts in child processes. The ten
core generated Python templates have five static local edges. Generated
`octon.py` imports four local modules immediately: continuation, doctor,
transaction, and work completion. The latter is loaded even for basic command
discovery. This is a static import measure; it does not claim to cover dynamic
loading or subprocess dependencies.

Eleven fresh-process `python3 -B octon --help` observations, without system
cache eviction: source first 0.037 s / later median 0.037 s; generated
Minimal/compact first 0.070 s / later median 0.063 s. The process outputs were
stable; these are local first-use proxies.

| Existing measurement | Exit | Key local result | Raw report SHA-256 |
|---|---:|---|---|
| `benchmark_validation.py --enforce` | 0 | 129/129 samples succeeded; scaffold combined p90 6.909/7.912/9.398 s (Minimal/Standard/High Assurance); 10k check combined p90 1.560 s; worst mutation combined p90 7.611 s; all enforced thresholds passed | `7a2fb9bca7a71b86d593803fc892afb52afa5e1b25939a08342e62b65bbd05da` |
| `benchmark_long_running_work.py --enforce` | 0 | Pass; warm p90 0.128-1.782 s across four read-only calls | `04055e8e8d096e440db2dac8000233858498a6e30f1b1313206cc9762c4ca92f` |
| `benchmark_autonomous_delivery.py --enforce` | 0 | Pass; warm p90 0.112-0.118 s across five read-only surfaces | `999f9ed23a8319b6b047436f12c65747b895523369ab2b63fafe28feb31db844` |
| `profile_large_project.py --sizes 0 2000 10000 20000` | 0 | No execution failures; informational 20k-file transaction total apply 23.012 s, with no threshold | `297607194d25d2b2d7d2a895d3db86ae017c26bc087833342d7e3f2a3e1a45fd` |

The content-free raw reports, check logs, startup samples, and temporary project
are in `/private/tmp/octon-imp0.sMicVO/`. Benchmark thresholds and all elapsed
times are host-specific. The large-project phase timings overlap by design and
are not an enforced performance gate.

## Read-only capability disposition assessment

This applies the [ecosystem migration boundary](../../../../../octon_plectarium_quoris_ecosystem_specification/docs/12-migration.md#octonplectarium-capability-boundary)
to the measured source. It is an IMP-0 assessment, not a code move, accepted
retirement decision, or claim that a proposed specialist already exists.

| Concern | Assessed owner and boundary |
|---|---|
| Project bootstrap, instructions, tasks, accepted decisions, basic read-only checks, evidence admission, diagnostics, local transactions and recovery, package adoption, and project acceptance | **Stay in Octon.** The existing source bootstrap scripts and generated core retain these project-owned responsibilities. The large validator may be modularized, but basic self-validation and exact recovery cannot depend on a specialist or Plectarium. |
| Work completion, `work run`, and autonomous delivery | **Stay as optional Octon project workflows.** Provider mechanics can sit behind narrower, lazily loaded adapters. Octon retains current task identity, scope and authority checks, project continuation, acceptance, and local receipts. A delegated specialist step must not create a second project task or state writer. |
| Rich operations/observability, security/supply-chain, and option/trade-off methods | **Potential independent specialist capabilities**, only after a concrete method, consumers, direct-use contract, and preservation evidence are identified. Current domain templates and local validators do not themselves prove an extractable specialist or a code-saving transfer. Their results may inform Octon checks or decisions, but Octon admits project evidence and accepts the result. |
| A specialist invocation delegated to the suite | **Plectarium owns hosting**: discovery/catalog and version compatibility, plan admission, job and attempt records, runner leases, cancellation, uncertain-attempt reconciliation, and result custody. Octon keeps a narrow optional invocation bridge and opaque receipt/reference, then decides whether to adopt the result. These hosting functions are not counted as existing Octon code to remove. |

Any later removal still needs the complete dependency and consumer inventory,
equivalent behavior and negative cases, authority and recovery evidence, measured
workflow effect, acceptance, and tested backout specified by the migration plan.
Direct specialist use remains possible without Plectarium; an unknown hosted
outcome must be reconciled with its original host rather than replayed elsewhere.

## Recovery and next entry

The source commit, released historical tag, and required predecessor commit
`5e2d3025aea6b1574ab984e5ebb89b5602a38535` were verified as present. A
complete-history bundle at `/private/tmp/octon-imp0.sMicVO/source-history.bundle`
passed `git bundle verify` (SHA-256
`d5eeb92a6967edd4b90b4e93ba1acdd75627e4ac3db9c34f6cc5a05a99e40307`).
Its fresh clone was checked out at the exact source commit. Applying the saved
decision-file patch and copying the saved plan reproduced both pre-existing
working-tree files byte for byte. The patch and plan copy are alongside the
bundle. The normal recovery route is that exact commit through Git history;
the local bundle and document copies are a verified supplementary route, with
temporary storage lifetime. Preserve the existing operating installation and
its project-owned records during candidate work.

The next implementation entry is **IMP-1** in `docs/OEP1_IMPLEMENTATION_PLAN.md`:
reconcile the required source decisions, OEP-1 layout/catalog, package
boundaries, and compatibility promises; then extract cohesive modules behind
the existing observable interfaces, starting with an explicit path resolver and
bounded compatibility shims. Resolve the recorded documentation/allowlist
blocker before presenting a clean source or acceptance gate for a candidate.
