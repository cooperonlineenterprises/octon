# 2.0.0 to 3.0.0 reference fixtures

`valid/v2-minimal.json` is a closed representative v2 bundle. The reference
migrator preserves its exact bytes and parsed live state as noncurrent rollback
evidence, advances only the contracts changed by 3.0.0, and leaves
collaboration and workflow adoption unassessed.

Files under `invalid/` are closed mutation descriptions applied by
`test_migration_2_0_0_to_3_0_0.py`. They cover mixed authority, divergent or
adopted vague Git policy, fabricated collaboration/workflow state, and invalid
migration authority without duplicating the complete valid bundle.

These fixtures are migration conformance evidence, not project facts,
permission, or a general in-place upgrader.
