# Octon Mini 4.0 Compatibility and Clean Break

## Product boundary

Octon Mini 4.0.0 is the first Octon Mini release and the breaking successor to
Project Blueprint 3.x. Octon Mini is the lightweight, project-local version of
Octon. OctonOS is the full-scale agent operating system and governed control
plane. Octon Mini is standalone: it is not a seed, trial, required precursor,
or OctonOS runtime.

Generated projects are independent snapshots. Octon Mini does not create a
runtime link to this source repository and does not rewrite an existing Project
Blueprint snapshot automatically. Structural conformance, harness adoption,
and project readiness remain separate claims.

The fail-closed continuation program is delivered only in new snapshots or a
reviewed upgrade. Existing setup-session v1, transaction-plan/receipt v2,
diagnostic-report v1, project contract v5, validator contract v4, and
project-check evidence v2 artifacts remain truthful historical predecessors.
New source and generated workflows emit setup-session v2, transaction
plan/receipt v3, diagnostic report v2, project contract v6, validator contract
v5, and project-check evidence v3. Predecessors are never rewritten in place.

## Clean command and identity break

`octon` is the sole current command. New source workflows use
`scripts/octon.py`, new generated projects use `./octon`, and their internal
dispatcher is `.agent/scripts/octon.py`.

There is no `pb` alias, wrapper, symlink, parser branch, warning shim, or
runtime compatibility mode. A legacy Project Blueprint snapshot may continue
to use the tools bundled in that independent snapshot, subject to its recorded
limitations, but Octon Mini does not provide or dispatch those tools.

### Cross-platform command entry

The source checkout, installed source bundle, and generated projects use the
same extensionless Python launcher named `octon`. On Unix and macOS, invoke it
as `./octon <arguments>`. On Windows, invoke the same file and arguments as
`python -B octon <arguments>` or `py -3 -B octon <arguments>`. The launcher
disables bytecode, resolves the correct source or generated dispatcher without
recursion, and does not create an alias or second command identity.

The same clean break applies to current product and protocol identity:

- product and package identity is `Octon Mini` / `octon-mini`;
- the bootstrap capability is **Octon Mini Project Bootstrap** and its skill ID
  is `octon-mini-project-bootstrap`;
- current schemas and artifacts use capability-qualified `octon-mini.*`
  identities;
- new provenance is stored in `.octon-mini-origin.json`; and
- new generated and installed inventories record Octon Mini versions and
  roles.

Old identifiers are not repurposed to mean changed Octon Mini formats.

## Source license and generated projects

The public Octon Mini source repository and installed source bundle use the
MIT No Attribution license (`MIT-0`). Generated target snapshots do not contain
the source `LICENSE` file and do not select a target project's overall license.
The target project makes that separate project-owned decision. Licensed source
reuse, structural conformance, harness adoption, readiness, and a completed
Octon Mini release remain separate claims.

## Project Blueprint 3.x to Octon Mini 4.0.0

Upgrade is an explicit, reviewed, recoverable cross-brand migration. It may
recognize legacy `pb`, `.project-blueprint-origin.json`, and
`project-blueprint.*` records only as inputs to transform. It never executes or
dispatches `pb`.

The 3.1.0→4.0.0 path requires reviewed inventory seeding followed by the live
three-way upgrader. It compares the recorded old baseline, the current project,
and the Octon Mini candidate. Unknown pristine hashes, assessed collaboration
v1, authority conflicts, deletion or move requests, symlinks, permission
changes, and modified project-owned or governance paths cannot be migrated
automatically.

A successful migration:

- installs `octon` and `.agent/scripts/octon.py`;
- adds the continuation renderer and successor schemas as reviewed absent
  implementation assets;
- writes `.octon-mini-origin.json` and current Octon Mini identities;
- removes the old launcher, runtime modules, and current legacy provenance only
  through the reviewed migration operation;
- preserves project-owned facts, authority, decisions, evidence, and stable
  record IDs;
- records the exact cross-brand transition and rollback evidence; and
- makes a second application an exact no-op or deterministic refusal under the
  migration contract.

No migration silently adopts a workflow, provider, check, command hook,
cleanup policy, or authorization. It does not infer readiness.

Earlier 1.0.1→2.0.0 and 2.0.0→3.0.0 transformations remain closed historical
references, and 3.0.0→3.1.0 remains the recorded additive source migration.
Historical tags, releases, decisions, fixtures, and changelog entries retain
their Project Blueprint identity.

## Octon Mini 4.0.0 to 4.1.0

4.1.0 adds a dormant generated `octon work run` route, one unassessed package
trigger, and the optional `workflow_capability` package kind. Released 4.0.0
snapshots remain standalone and unchanged. They receive the route only through
an explicit reviewed upgrade. Upgrade does not install or adopt long-running
work; those remain separate package and project decisions.

The immutable package payload lives under
`.agent/capabilities/long-running-work/`; mutable adoption and run records live
under `.agent/work-runs/`. Existing task, evidence, transaction,
work-completion, decision, event, focus/current, and continuation owners are
preserved. See `migrations/4.0.0-to-4.1.0.md`.

## Octon Mini 4.1.0 to 4.2.0

4.2.0 adds project contract `harness.project.v8`, the dormant
`octon delivery` surface, strict autonomous-delivery contracts, and inert local
payloads for network-free activation. Every new snapshot starts
`available_not_activated`, with writes and external effects locked, no selected
delivery profile, no authorization reference, and an unassessed trigger.

The delivery profile is independent from assurance, collaboration,
concurrency, layout, and compute mode. A v2 standing contract selects exactly
one of host-enforced metered API limits or readable included-subscription
allowance only. Confirmed v1 records remain immutable metered-API evidence. A
mode change uses a new stable authorization ID, exact predecessor binding, and
operator-controlled predecessor revocation before successor activation.
Upgrade advertises the capability but never installs,
activates, renews, or broadens authority. Existing delivery configuration is
preserved only while exact bindings remain current; every more-permissive or
changed contract requires a human-confirmed successor.

The reviewed 4.1→4.2 migration adds exact dormant implementation bytes and
derived projections without manufacturing repository/provider facts,
credentials, project decisions, confirmation evidence, standing authority,
adoption, or readiness. See `migrations/4.1.0-to-4.2.0.md`.

## Other 4.0 behavior changes

- scripted generation without `--profile` fails;
- interactive initialization proposes Minimal and requires confirmation;
- interactive initialization, adoption, and upgrade can orchestrate one
  inspect/question/plan/summary/confirmation/apply command while retaining the
  explicit non-interactive plan/apply interfaces;
- compact is the new-project physical layout default;
- current state is derived and operator intent resides in focus;
- Git and domain extensions are trigger-installed packages;
- routine generated tests expose `fast`, `integration`, and `release` tiers;
- evidence-complete work may close directly from an active state;
- new snapshots include decision-governance records and review templates;
- new snapshots include an empty decision-reuse registry, typed continuation
  findings, human plan summaries, conservative routine validation proofs, and
  safe reversible local bundle planning; and
- governed work completion and its event hook remain disabled and
  non-authorizing until explicitly adopted.

Guided setup remains orchestration over the existing initialization, adoption,
and upgrade planners. Its question catalog is not projected into target
authority, and new questions remain unanswered or deferred rather than
receiving defaults.

Dependency-scoped session v2 may preserve an old answer only when its exact
question, dependencies, instructions, evidence, authority, and freshness
bindings remain current. A v1 session requires an explicit reinspection
successor. Accepted decision reuse requires a separately project-owned
applicability record bound to an exact accepted unsuperseded decision; no
runtime authorization or external-action permission is migrated or cached.

## Unsupported shortcuts

Directly copying launchers, runtime modules, setup sessions, packages, Git
workflow files, or origin records is unsupported because it bypasses content,
decision, provenance, and receipt binding. Directly editing derived current
state or a setup digest is also unsupported. A prior authorization never
becomes standing permission.

No compatibility or migration rule authorizes deletion of a project-owned file
or record. Moves, representation changes, and stable-ID changes require an
explicit reviewed migration.
