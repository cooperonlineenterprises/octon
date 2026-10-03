# Source-only runtime inventory binding

This bounded IMP-1 increment qualifies caller-pinned integrity and dependency/path
compatibility for a fresh owned plain Minimal/compact disposable target. It does
not authenticate a supply chain, grant permission, adopt a consumer, migrate an
installation, publish a runtime, or complete IMP-1/IMP-2. The existing
[OEP implementation plan](OEP1_IMPLEMENTATION_PLAN.md) alone owns sequencing.

## Inventory and retained readers

`shared/source-contracts/profile-manifest.json` is the single current inventory,
with source profile v4 and inactive target design v2. Only `runtime.manifest`
(`.octon/runtime/manifest.json`) and extensionless `runtime.entry`
(`.octon/runtime/octon`) acquire source-only recipe rules. The other 20 target
entries remain unbound, and `generation_status` remains
`design_only_not_selectable`. The nine required core modules are the existing
copied `.octon/runtime/scripts/*.py` inventory; no namespace alias is introduced.

The exact profile-v3 raw bytes are retained as historical data at
`shared/source-contracts/historical/profile-manifest-v3.json`, SHA-256
`d3b9b33d7136d9806b1839ec198929625bd3a4523a72948d43c925f8bc6916d3`.
The named adapter checks the complete relevant rule, profile/layout, dependency,
module, source-locator, state-owner and project-path semantics against that
snapshot, allowing only the declared v4 source-only additions. Both the local
qualifier and its scaffold subprocess use this checked route. Parent inputs
record the actual historical and actual current locators/digests separately.
Historical bytes are never described as a raw copy of the current v4 file.
Old profile-v2/v3 schemas, installation readers, templates and kernel 4.2 meanings
are retained. Source 5.0.0 remains an unpublished identity-transition candidate.

## Acyclic byte bindings

The raw template, recipe, trusted-reader and new schema bytes feed source-v4
bytes. The actual qualifier's `runtime_entry_text` emits the entry;
`runtime_binding_manifest` assembles the facet, and the bound trusted reader's
`canonical_json` emits its UTF-8 bytes with final LF. The facet binds the current
source raw digest, immutable parent raw digest, all module/entry hashes, all six
actual template parameters and target projection, and the complete parent helper,
executable and schema dependency closure. Raw template and emitted output hashes
are distinct. Canonical JSON payload hashing and raw-file SHA-256 have explicit,
different algorithm labels; the historical inventory's no-final-LF payload
convention is retained.

Neither source v4 nor the facet embeds its own digest or the final candidate Git
SHA. The independent output receipt owns the final facet raw SHA. The graph is
raw inputs → source v4 → emitted modules/entry → retained parent → facet → derived
fingerprint. External facet receipt/pin has no edge back into target bytes.

Before facet insertion every parent asset and all 109 non-null initial output
records are checked against actual bytes. The retained parent has 114 initial
outputs; exactly its existing self row and four Minimal derived JSON rows have
null hashes. The new facet is excluded from that old initial inventory and asset
list, preserving `octon.disposable-installation.v1` meaning. After insertion the
existing explicit refresh owner may persistently change only:

- `.octon/agent/state/current.json`
- `.octon/dossier/ARTIFACT_CATALOG.json`
- `.octon/dossier/MANIFEST.json`
- `.octon/dossier/machine-readable/path-authority.json`

The qualifier exports complete before/after path/type/native-mode/raw-byte
inventories, immutable parent/facet hashes and every non-null/asset binding in its
external stdout receipt. It rejects creation/deletion, changed type/mode,
non-allowed bytes, parent/facet changes, residual staging/bytecode, and forbidden
High Assurance outputs. The complete existing source fingerprint includes the
parent and facet; no template exclusion is widened. An unexpected refresh effect
refuses publication and the owned stage is reconciled.

## Trusted read-only inspection

Use an independently supplied copy of `runtime_binding.py` outside the inspected
target, an external source-v4 snapshot, and **both** expected raw SHA-256 values
from a trusted external build/qualification receipt or caller. The reader checks
its own bytes against the source-pinned reader hash. Neither pin defaults from
target files, a colocated receipt or freshly computed target hash. A supplied hash
alone does not establish how its caller obtained it.

```text
python -I -B /external/trusted/runtime_binding.py \
  --project-root /owned/disposable/target \
  --source-snapshot /external/trusted/profile-v4.json \
  --expected-source-sha256 <trusted-source-raw-sha256> \
  --expected-runtime-sha256 <trusted-facet-raw-sha256> \
  --layout-id oep1_target --state-owner embedded
```

The occupied read-only resolver is distinct from `InstallationBinding.target`;
ordinary generation/adoption collision refusal remains intact. It enforces exact
component spelling and casefold uniqueness, portable paths, regular object types,
one embedded state, and no symlink/junction/reparse escape. Windows reparse checks
work on Python 3.11 without requiring the 3.12 `is_junction` convenience API.

Inspection treats target Python as AST data and verifies the entire pinned local
and stdlib import closure, entry loader, retained helper and schemas. It never
imports target code, delegates to the v2 admission reader, runs a hook, refreshes,
or installs packages. Separately executing the known externally inspected fixture
entry for `installation inspect`, `work start --help` and `check` is qualification
work. Bare `--help` retains its historical exit-2 refusal. Inspection alone is not
an admission-to-execution fence against concurrent malicious replacement.

## Qualification and native evidence

Generate only a fresh owned target with explicit selectors:

```text
python -B skills/octon-project-bootstrap/scripts/qualify_disposable_runtime.py \
  --target /owned/disposable/new-target \
  --disposable-qualification --runtime-binding-qualification
python -B skills/octon-project-bootstrap/scripts/test_runtime_binding.py
```

Admission/protected/durable mixtures, external state, other layouts/profiles and
High Assurance derived modes are unsupported. New bound output writes use explicit
UTF-8/LF bytes. The existing `.gitattributes` LF materialization is required;
unexpected raw source/CRLF drift refuses qualification instead of normalizing it.
Old ordinary/legacy native serialization keeps its historical meanings.

Evidence distinguishes POSIX permission bits from Windows writable/read-only
attributes. Python invokes the extensionless entry on Windows; a fake POSIX
executable bit is not required. Native tests exercise actual bytes, readonly
handling, case spelling, imports, symlink/reparse/junction and preserved target
inventories. Unavailable host capabilities have explicit unsupported dispositions,
never passing protection claims; non-Windows junction creation is not applicable.
The current existing OS/Python 3.11–3.14 matrix supplies actual Windows evidence.

The separate cold-runner audit observes fresh copied entry/dispatcher/validator
processes with source/sibling reads and network unavailable, bytecode disabled and
optional payloads absent. It records actual module imports and timings and proves
its source-read denial with a canary. It does not evict OS caches or establish a
hostile-host sandbox. No source checkout, sibling runtime or Plectarium is needed
by basic copied operation.

The native strict-JSON block binds the complete actual source-file subject, method
inventory, per-case terminal outcomes, actual platform/interpreter and unsupported
capabilities. Missing, duplicate, nonfinite, incoherent or incomplete evidence
cannot qualify. Dirty-source preflights may pass their test suite but cannot be a
clean candidate qualification. Full source/acceptance gates, exact independent
review, all current required PR jobs and the existing full candidate matrix remain
mandatory. Final evidence belongs to the external qualification report and brief;
the reviewable PR stops before merge.
