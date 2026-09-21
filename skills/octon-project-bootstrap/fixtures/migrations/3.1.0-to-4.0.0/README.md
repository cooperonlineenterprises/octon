# Project Blueprint 3.1.0 to Octon Mini 4.0.0 live-snapshot fixture

The executable fixture is built dynamically by
`scripts/test_migration_3_1_0_to_4_0_0.py`. It creates a disposable separated
Octon Mini snapshot, adds task and evidence records through `octon`, then
rewrites it into a closed Project Blueprint 3.1.0 preimage. Legacy `pb`
launchers, modules, schemas, and origin paths are fixture bytes only: the test
never imports, dispatches, or executes them. It then exercises reviewed
cross-brand inventory seeding and the live three-way upgrader.

The fixture verifies:

- read-only inspection and unchanged target bytes;
- exact old-baseline review binding and deterministic seed generation;
- stale-seed and changed-path refusal;
- proposal-bound review of every non-automatic path;
- one-command upgrade pause on the immutable three-way proposal and exact
  resume after a proposal-bound review;
- explicit project-check evidence v2→v3 header migration that preserves every
  historical record and adds no validation proof;
- staged creation of `octon` and `.octon-mini-origin.json` plus reviewed
  deletion of every legacy runtime and origin path;
- deterministic second-application refusal with unchanged target bytes;
- structural validation, exact receipt generation, exact legacy-preimage
  restoration through current `octon` rollback, and rollback refusal after an
  independent change; and
- separation of structural conformance, harness adoption, and readiness.

This is a deterministic contract fixture, not a claim that every historical
Project Blueprint 3.1 repository has the same pristine bytes. A real 3.1
project must provide its reviewed old baseline hashes. Unknown static
baselines, assessed legacy collaboration, authority conflicts, symlinks,
moves, deletions, permissions, or modified project-owned paths remain manual
review gates. No `pb` compatibility behavior is produced.
